"""Unit tests for UniqExclusionBranchElimination."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import (
    UniqExclusionBranchElimination,
    UniqExclusionBranchEliminationTransformer,
)
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx_with(**namespace) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def _nondet_prim() -> object:
    return frog_parser.parse_primitive_file(
        "Primitive P(Int n) { BitString<n> eval(); }"
    )


def _det_prim() -> object:
    return frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic BitString<n> eval(BitString<n> x); }"
    )


@pytest.mark.parametrize(
    "method,expected",
    [
        # Direct equality with literal-set <-uniq exclusion: condition is false.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (false) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Symmetric: a == b vs b == a both simplify.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (b == a) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (false) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Inequality flips to true.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (a != b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (true) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Set with multiple elements: each is excluded.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                BitString<8> c <-uniq[{a, b}] BitString<8>;
                if (c == a) {
                    return 1;
                } else if (c == b) {
                    return 2;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                BitString<8> c <-uniq[{a, b}] BitString<8>;
                if (false) {
                    return 1;
                } else if (false) {
                    return 2;
                }
                return 0;
            }
            """,
        ),
        # No <-uniq constraint: condition unchanged.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Reassignment of the sampled variable invalidates the constraint.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Reassignment of an exclusion-set element also invalidates.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                a <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                a <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Element write to the exclusion element's backing map invalidates:
        # after M[0] = b, M[0] == b is true, so folding to false would be
        # unsound.
        (
            """
            Int f(Map<Int, BitString<8>> M) {
                BitString<8> b <-uniq[{M[0]}] BitString<8>;
                M[0] = b;
                if (M[0] == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f(Map<Int, BitString<8>> M) {
                BitString<8> b <-uniq[{M[0]}] BitString<8>;
                M[0] = b;
                if (M[0] == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Write nested inside an if-branch invalidates: on the c path a == b
        # holds after a = b, so folding the later condition to false would be
        # unsound.
        (
            """
            Int f(Bool c) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (c) {
                    a = b;
                }
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f(Bool c) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (c) {
                    a = b;
                }
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Condition with `==` deeper inside an AND chain: still rewritten.
        (
            """
            Bool f(Bool other) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (other && a == b) {
                    return true;
                }
                return false;
            }
            """,
            """
            Bool f(Bool other) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (other && false) {
                    return true;
                }
                return false;
            }
            """,
        ),
    ],
)
def test_uniq_exclusion_branch_elim(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed = UniqExclusionBranchEliminationTransformer().transform(method_ast)
    assert transformed == expected_ast


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-071): a non-deterministic exclusion element must
# not be tracked, so the comparison is NOT folded.
# ---------------------------------------------------------------------------


def test_uniq_exclusion_declines_on_nondeterministic_element() -> None:
    """An exclusion element ``F.eval()`` is a non-deterministic call; the
    later ``b == F.eval()`` is an independent re-evaluation, so the pass must
    NOT fold the comparison to false."""
    game = frog_parser.parse_game("""
        Game G(P F, Int n) {
            Bool Oracle() {
                BitString<n> b <-uniq[{F.eval()}] BitString<n>;
                if (b == F.eval()) {
                    return true;
                }
                return false;
            }
        }
        """)
    ctx = _ctx_with(P=_nondet_prim(), F=_nondet_prim())
    result = UniqExclusionBranchElimination().apply(game, ctx)
    assert result == game  # unchanged: no fold
    assert any(
        nm.transform_name == "Uniq Exclusion Branch Elimination"
        for nm in ctx.near_misses
    )


def test_uniq_exclusion_fires_on_deterministic_control() -> None:
    """Control: a plain sampled exclusion element still lets the pass fold
    ``a == b`` to false."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Bool Oracle() {
                BitString<n> a <- BitString<n>;
                BitString<n> b <-uniq[{a}] BitString<n>;
                if (a == b) {
                    return true;
                }
                return false;
            }
        }
        """)
    ctx = _ctx_with()
    result = UniqExclusionBranchElimination().apply(game, ctx)
    assert result != game  # the comparison was folded to false


# ---------------------------------------------------------------------------
# RC2 self-reference guard (F-070): an exclusion element that mentions the
# sampled variable itself denotes the variable's pre-draw value, so a later
# equality on that variable must NOT be folded (`x <- T \\ {x}; if (x == x)`).
# ---------------------------------------------------------------------------


def test_uniq_exclusion_self_reference_not_folded() -> None:
    method = frog_parser.parse_method("""
        Int f() {
            BitString<8> x <- BitString<8>;
            x <- BitString<8> \\ {x};
            if (x == x) {
                return 1;
            }
            return 0;
        }
        """)
    ctx = _ctx_with()
    transformer = UniqExclusionBranchEliminationTransformer(ctx)
    transformed = transformer.transform(method)
    assert transformed == method  # x == x not folded to false
    assert any(
        nm.transform_name == "Uniq Exclusion Branch Elimination"
        and "pre-draw" in nm.reason
        for nm in ctx.near_misses
    )


def test_uniq_exclusion_keeps_non_self_elements() -> None:
    """Control: a self-referential element is dropped but a sibling
    non-self element still folds (`c <- T \\ {a, c}` keeps the `a` exclusion)."""
    method = frog_parser.parse_method("""
        Int f() {
            BitString<8> a <- BitString<8>;
            BitString<8> c <- BitString<8> \\ {a, c};
            if (c == a) {
                return 1;
            }
            return 0;
        }
        """)
    transformer = UniqExclusionBranchEliminationTransformer(_ctx_with())
    transformed = transformer.transform(method)
    expected = frog_parser.parse_method("""
        Int f() {
            BitString<8> a <- BitString<8>;
            BitString<8> c <- BitString<8> \\ {a, c};
            if (false) {
                return 1;
            }
            return 0;
        }
        """)
    assert transformed == expected


# ---------------------------------------------------------------------------
# RC2 auto-add tracking (F-072): the stateful `<-uniq[S]` form implicitly
# inserts into S, so a constraint whose element reads S must be invalidated
# when a later draw mutates S; otherwise it folds against a stale snapshot.
# ---------------------------------------------------------------------------


def test_uniq_exclusion_invalidated_by_later_auto_add() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Set<BitString<8>> S;
            Array<BitString<8>, n> A;
            Bool Oracle() {
                BitString<8> x <- BitString<8> \\ {A[|S|]};
                BitString<8> z <-uniq[S] BitString<8>;
                if (x == A[|S|]) {
                    return true;
                }
                return false;
            }
        }
        """)
    ctx = _ctx_with()
    result = UniqExclusionBranchElimination().apply(game, ctx)
    assert result == game  # |S| changed by the auto-add: no fold


def test_uniq_exclusion_folds_without_intervening_auto_add() -> None:
    """Control: with no later mutation of S, the `x != A[|S|]` constraint
    holds and the comparison folds to false."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Set<BitString<8>> S;
            Array<BitString<8>, n> A;
            Bool Oracle() {
                BitString<8> x <- BitString<8> \\ {A[|S|]};
                if (x == A[|S|]) {
                    return true;
                }
                return false;
            }
        }
        """)
    ctx = _ctx_with()
    result = UniqExclusionBranchElimination().apply(game, ctx)
    assert result != game  # folded to false
