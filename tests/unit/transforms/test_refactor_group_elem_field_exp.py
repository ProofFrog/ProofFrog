"""Regression tests for RefactorGroupElemFieldExp Initialize-safety guards.

The pass rewrites `Field1 = g^(a*b)` to `Field2 ^ b` when a peer
`Field2 = g^a` exists. Three ways that is unsound, now guarded:

  - F-221: the shared factor must have the SAME value at both field
    positions. If a free variable of the factor is reassigned between them,
    the two occurrences are independent draws (stale exponent).
  - F-386: the same, when the write between them is nested in an `if` or a
    loop (the check looked at each statement's own node only).
  - F-224: if Initialize can return early, moving Field2 changes which traces
    define it (turning a guarded/undefined read into a defined one).
  - F-225: moving Field2's assignment up past an intervening READ of Field2
    changes that read's value.

Each `DECLINED` case is paired with the P0 positive control (the pass still
fires on the sound shape).
"""

import copy

from proof_frog import frog_parser
from proof_frog.transforms.inlining import RefactorGroupElemFieldExp
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _fires(game_src: str) -> bool:
    game = frog_parser.parse_game(game_src)
    after = RefactorGroupElemFieldExp().apply(copy.deepcopy(game), _ctx())
    return str(after) != str(game)


def test_p0_positive_fires() -> None:
    # Clean shape: B = g^x; A = g^(x*3) with x unchanged -> A = B^3.
    assert _fires(
        """
        Game Pos(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Void Initialize() {
                Int x = 2;
                B = G.generator ^ x;
                A = G.generator ^ (x * 3);
            }
        }
        """
    )


def test_f221_stale_exponent_no_move_declines() -> None:
    # x reassigned between B and A -> B's x and A's x are different draws.
    assert not _fires(
        """
        Game Stale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Void Initialize() {
                Int x = 1;
                B = G.generator ^ x;
                x = 3;
                A = G.generator ^ (x * 2);
            }
        }
        """
    )


def test_f221_stale_exponent_move_declines() -> None:
    # A before B, x re-sampled between -> moving B up would conflate draws.
    assert not _fires(
        """
        Game StaleMove(Group G) {
            GroupElem<G> A;
            GroupElem<G> B;
            Void Initialize() {
                Int x = 1;
                A = G.generator ^ (x * x);
                x = 3;
                B = G.generator ^ x;
            }
        }
        """
    )


def test_f224_early_return_in_init_declines() -> None:
    # Moving B above `if (p) { return true; }` changes which traces define B.
    assert not _fires(
        """
        Game EarlyRet(Group G) {
            GroupElem<G> A;
            GroupElem<G> B;
            Bool Initialize(Bool p) {
                Int x = 2;
                A = G.generator ^ (x * 3);
                if (p) { return true; }
                B = G.generator ^ x;
                return false;
            }
        }
        """
    )


def test_f225_read_before_write_move_declines() -> None:
    # `C = B` reads an unassigned B before B is defined; hoisting B above it
    # turns an observable undefined read into a defined value.
    assert not _fires(
        """
        Game ReadBeforeWrite(Group G) {
            GroupElem<G> A;
            GroupElem<G> B;
            GroupElem<G> C;
            Void Initialize() {
                Int x = 2;
                A = G.generator ^ (x * 3);
                C = B;
                B = G.generator ^ x;
            }
        }
        """
    )


def test_f222_cross_group_generators_decline() -> None:
    """F-222: `A = G.generator^(x*y)` must not be refactored as `B^y` when
    `B = H.generator^x` is in a DIFFERENT group -- that crosses groups and is
    ill-typed (`GroupElem<G>` field set to `(GroupElem<H>)^y`)."""
    assert not _fires(
        """
        Game Cross(Group G, Group H, Int x, Int y) {
            GroupElem<H> B;
            GroupElem<G> A;
            Void Initialize() {
                B = H.generator ^ x;
                A = G.generator ^ (x * y);
            }
        }
        """
    )


def test_f222_same_group_generators_still_fire() -> None:
    """Positive control: same group -> the refactor still fires."""
    assert _fires(
        """
        Game Same(Group G, Int x, Int y) {
            GroupElem<G> B;
            GroupElem<G> A;
            Void Initialize() {
                B = G.generator ^ x;
                A = G.generator ^ (x * y);
            }
        }
        """
    )


def test_f386_redraw_in_branch_move_declines() -> None:
    """F-386: A before B, x redrawn inside an `if` between them. When the
    branch runs, B uses the new x, so moving B up and writing A = B^x would
    conflate two draws."""
    assert not _fires(
        """
        Game BranchMove(Group G) {
            GroupElem<G> A;
            GroupElem<G> B;
            Bool c;
            Void Initialize() {
                c <- Bool;
                ModInt<G.order> x <- ModInt<G.order>;
                A = G.generator ^ (x * x);
                if (c) {
                    x <- ModInt<G.order>;
                }
                B = G.generator ^ x;
            }
        }
        """
    )


def test_f386_write_in_branch_no_move_declines() -> None:
    """F-386: B before A, x written inside an `if` between them (no move
    needed, so only the stability check stands in the way)."""
    assert not _fires(
        """
        Game BranchStale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Bool c;
            Void Initialize() {
                c <- Bool;
                Int x = 1;
                B = G.generator ^ x;
                if (c) {
                    x = 3;
                }
                A = G.generator ^ (x * 2);
            }
        }
        """
    )


def test_f386_write_in_else_branch_declines() -> None:
    """F-386: the write sits in an `else` branch."""
    assert not _fires(
        """
        Game ElseStale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Bool c;
            Void Initialize() {
                c <- Bool;
                Int x = 1;
                B = G.generator ^ x;
                if (c) {
                    c = false;
                } else {
                    x = 3;
                }
                A = G.generator ^ (x * 2);
            }
        }
        """
    )


def test_f386_write_in_loop_declines() -> None:
    """F-386: the write sits in a loop body between the two fields."""
    assert not _fires(
        """
        Game LoopStale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Void Initialize() {
                Int x = 1;
                B = G.generator ^ x;
                for (Int i = 0 to 2) {
                    x = x + i;
                }
                A = G.generator ^ (x * 2);
            }
        }
        """
    )


def test_f386_element_write_in_branch_declines() -> None:
    """F-386: the factor reads a map entry that an element write inside a
    branch changes."""
    assert not _fires(
        """
        Game ElementStale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Map<Int, Int> M;
            Bool c;
            Void Initialize() {
                c <- Bool;
                M[0] = 1;
                B = G.generator ^ M[0];
                if (c) {
                    M[0] = 3;
                }
                A = G.generator ^ (M[0] * 2);
            }
        }
        """
    )


def test_f386_uniq_insertion_in_branch_declines() -> None:
    """F-386: the factor reads |S|, and a `<-uniq[S]` draw inside a branch
    inserts into S."""
    assert not _fires(
        """
        Game UniqStale(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Set<BitString<4>> S;
            Bool c;
            Void Initialize() {
                c <- Bool;
                B = G.generator ^ |S|;
                if (c) {
                    BitString<4> y <-uniq[S] BitString<4>;
                }
                A = G.generator ^ (|S| * 2);
            }
        }
        """
    )


def test_f386_branch_writing_other_variable_still_fires() -> None:
    """Positive control: the branch between the fields writes only c, not
    the shared factor x, so A = g^(x*x) equals B^x and the pass fires."""
    assert _fires(
        """
        Game BranchOther(Group G) {
            GroupElem<G> A;
            GroupElem<G> B;
            Bool c;
            Void Initialize() {
                c <- Bool;
                ModInt<G.order> x <- ModInt<G.order>;
                A = G.generator ^ (x * x);
                if (c) {
                    c = false;
                }
                B = G.generator ^ x;
            }
        }
        """
    )


def test_f386_write_after_both_fields_still_fires() -> None:
    """Positive control: x is written inside a branch only after both
    fields are assigned, so both read the same x and the pass fires."""
    assert _fires(
        """
        Game WriteAfter(Group G) {
            GroupElem<G> B;
            GroupElem<G> A;
            Bool c;
            Void Initialize() {
                c <- Bool;
                Int x = 1;
                B = G.generator ^ x;
                A = G.generator ^ (x * 2);
                if (c) {
                    x = 3;
                }
            }
        }
        """
    )
