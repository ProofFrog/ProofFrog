"""Tests for `_z3_residual_equivalence`: the Z3-based escape hatch that
bridges equivalence hops where two games differ only in if-conditions
and/or final return expressions, and the differences are propositionally
equivalent over uninterpreted-function atoms.

Refuses to fire when either differing expression contains a non-
deterministic call (mirroring `BooleanAbsorption`'s Gap-F guard).
"""

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.proof_engine import _z3_residual_equivalence


def _parse_game(src: str) -> frog_ast.Game:
    return frog_parser.parse_game(src)


def _empty_namespace() -> frog_ast.Namespace:
    return {}


def _empty_let_types() -> visitors.NameTypeMap:
    return visitors.NameTypeMap()


# ---------------------------------------------------------------------------
# Positive: propositional tautology in returns is bridged
# ---------------------------------------------------------------------------


def test_return_tautology_redundant_disjunct_resolves() -> None:
    # Two games whose Challenge bodies are identical except for the final
    # return. The returns are propositionally equivalent: the dangling
    # `(a == b)` disjunct in game1's third conjunct resolves against the
    # `(a != b)` literal in another conjunct, leaving `c` which is
    # already a disjunct of game2's middle conjunct. This is the exact
    # shape from CK_expanded_LEAK_BIND_K_CT_DIFFKEY step 3.
    game1 = _parse_game(
        """
        Game G1() {
            Bool Challenge(BitString<8> a, BitString<8> b, Bool c) {
                return (a != b || c) && (c || a == b);
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G2() {
            Bool Challenge(BitString<8> a, BitString<8> b, Bool c) {
                return c && (a != b || c);
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert result.valid, result.failure_detail


def test_identical_games_pass() -> None:
    # Two games with identical bodies pass trivially.
    game1 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a, Bool b) {
                return a && b;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a, Bool b) {
                return a && b;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert result.valid


# ---------------------------------------------------------------------------
# Negative: semantically distinct returns
# ---------------------------------------------------------------------------


def test_distinct_returns_fail() -> None:
    # `a && b` is not equivalent to `a || b`; the hatch must refuse.
    game1 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a, Bool b) {
                return a && b;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a, Bool b) {
                return a || b;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert not result.valid
    assert "return" in (result.failure_detail or "")


def test_structurally_different_bodies_fail() -> None:
    # Differing intermediate statements cannot be bridged by the hatch.
    game1 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a) {
                Bool b = a;
                return b;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G() {
            Bool Challenge(Bool a) {
                return a;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert not result.valid
    assert "structurally" in (result.failure_detail or "")


# ---------------------------------------------------------------------------
# Soundness guard: refuse on non-deterministic calls in differing exprs
# ---------------------------------------------------------------------------


def test_nondeterministic_call_in_return_refused() -> None:
    # `KEM_PQ.KeyGen()` is non-deterministic per the KEM primitive's
    # signature (KeyGen has no `deterministic` annotation). Even if the
    # two return expressions look propositionally equivalent, the
    # escape hatch must refuse: textually identical KeyGen() occurrences
    # would denote independent samples, so memoizing them as a single
    # opaque atom would unsoundly equate their values.
    src_primitive = (
        "Primitive K() {"
        "  BitString<256> KeyGen();"
        "  deterministic BitString<256> Sign(BitString<256> m);"
        "}"
    )
    primitive = frog_parser.parse_primitive_file(src_primitive)
    # `has_nondeterministic_call` looks up `node.func.the_object.name` in
    # proof_namespace and expects a Primitive instance. Register the
    # primitive under the receiver name used in the games below.
    namespace: frog_ast.Namespace = {"K": primitive}
    let_types = visitors.NameTypeMap()

    # Both games' return expressions contain `K.KeyGen()` (non-
    # deterministic). Even if the boolean shape is otherwise equivalent,
    # the escape hatch must refuse: textually identical KeyGen calls
    # would denote independent samples, so memoizing them as the same
    # opaque atom would be unsound.
    game1 = _parse_game(
        """
        Game G1() {
            Bool flag;
            Bool Challenge() {
                return flag && K.KeyGen() == K.KeyGen();
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G2() {
            Bool flag;
            Bool Challenge() {
                return K.KeyGen() == K.KeyGen() && flag;
            }
        }
        """
    )
    result = _z3_residual_equivalence(game1, game2, let_types, namespace)
    assert not result.valid
    assert "non-deterministic" in (result.failure_detail or "")


# ---------------------------------------------------------------------------
# F-328/F-329: duplicate-statement walk desync (audit round 2, family 8)
#
# An earlier version of `_z3_residual_equivalence` enumerated both games'
# returns (and ifs) through a single shared list with structural `==`
# membership. A game containing two structurally identical returns had its
# second occurrence deduped away; the lockstep walk desynced, broke out on
# `None`, and fell through to `valid=True` with a genuinely differing pair
# never Z3-checked. The walk now pairs statements positionally with
# per-game identity-based enumeration, so every pair is checked.
# ---------------------------------------------------------------------------


def test_f328_duplicate_return_masks_differing_return_rejected() -> None:
    # game1's Peek and Guess both `return k` (structurally identical);
    # game2's Guess instead returns the constant. The two games are
    # distinguishable with advantage 1 - 2^-8 (call Peek, then Guess,
    # compare). The desync bug certified this pair; it must be rejected.
    game1 = _parse_game(
        """
        Game G1() {
            BitString<8> k;
            BitString<8> Peek() {
                return k;
            }
            BitString<8> Guess(BitString<8> x) {
                return k;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G2() {
            BitString<8> k;
            BitString<8> Peek() {
                return k;
            }
            BitString<8> Guess(BitString<8> x) {
                return 0^8;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert not result.valid
    assert "return" in (result.failure_detail or "")


def test_f329_duplicate_if_masks_differing_condition_rejected() -> None:
    # game1's A and B share a structurally identical `if (x == k)`;
    # game2's B guards on `x == c` instead. Distinguishable; the
    # if-condition walk variant of the desync certified it.
    game1 = _parse_game(
        """
        Game G1() {
            BitString<8> k;
            BitString<8> c;
            Bool A(BitString<8> x) {
                if (x == k) {
                    return true;
                }
                return false;
            }
            Bool B(BitString<8> x) {
                if (x == k) {
                    return true;
                }
                return false;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G2() {
            BitString<8> k;
            BitString<8> c;
            Bool A(BitString<8> x) {
                if (x == k) {
                    return true;
                }
                return false;
            }
            Bool B(BitString<8> x) {
                if (x == c) {
                    return true;
                }
                return false;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert not result.valid
    assert "if-condition" in (result.failure_detail or "")


def test_duplicate_identical_returns_still_pass() -> None:
    # Positive control: duplicates on BOTH sides with no real difference
    # must still be certified (the fix must not over-reject).
    src = """
        Game G() {
            BitString<8> k;
            BitString<8> Peek() {
                return k;
            }
            BitString<8> Guess(BitString<8> x) {
                return k;
            }
        }
        """
    result = _z3_residual_equivalence(
        _parse_game(src), _parse_game(src), _empty_let_types(), _empty_namespace()
    )
    assert result.valid, result.failure_detail


def test_duplicate_return_with_equivalent_difference_still_passes() -> None:
    # Positive control: one game duplicates a return, and the differing
    # pair is genuinely propositionally equivalent. The fixed walk must
    # CHECK the pair (not skip it) and certify via Z3.
    game1 = _parse_game(
        """
        Game G1() {
            Bool P(Bool a, Bool b) {
                return a && b;
            }
            Bool Q(Bool a, Bool b) {
                return a && b;
            }
        }
        """
    )
    game2 = _parse_game(
        """
        Game G2() {
            Bool P(Bool a, Bool b) {
                return a && b;
            }
            Bool Q(Bool a, Bool b) {
                return b && a;
            }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert result.valid, result.failure_detail


# ---------------------------------------------------------------------------
# F-330/F-331: IN/SUBSETS membership atoms (audit round 2, family 8)
#
# The IN/SUBSETS branch of Z3FormulaVisitor asserted a non-None version map
# (crashing the residual hatch, which supplies none -- F-330) and named its
# atom from a per-visitor-instance counter, so two independently-built
# formulas (one per game) collided `k in S` with `k2 in S` as the same atom
# (F-331 cross-instance false accept). Membership tests are now interned
# structurally, like the opaque-call fallback.
# ---------------------------------------------------------------------------


def test_f330_f331_membership_query_differs_rejected() -> None:
    # Real.Query returns `k in S`, Fake.Query returns `k2 in S`. k and k2 are
    # independent samples, so the games are distinguishable. Pre-fix: an
    # AssertionError crash (F-330); a naive crash fix would false-accept via
    # the counter-named atom collision (F-331). Must cleanly reject.
    game1 = _parse_game(
        """
        Game Real() {
            Set<BitString<8>> S;
            BitString<8> k;
            BitString<8> k2;
            Void Initialize() { k <- BitString<8>; k2 <- BitString<8>; }
            Bool Add(BitString<8> x) { S = S union {x}; return true; }
            Bool Query() { return k in S; }
        }
        """
    )
    game2 = _parse_game(
        """
        Game Fake() {
            Set<BitString<8>> S;
            BitString<8> k;
            BitString<8> k2;
            Void Initialize() { k <- BitString<8>; k2 <- BitString<8>; }
            Bool Add(BitString<8> x) { S = S union {x}; return true; }
            Bool Query() { return k2 in S; }
        }
        """
    )
    result = _z3_residual_equivalence(
        game1, game2, _empty_let_types(), _empty_namespace()
    )
    assert not result.valid
    assert "return" in (result.failure_detail or "")


def test_membership_identical_query_still_passes() -> None:
    # Positive control: structurally identical membership tests must still
    # intern to the same atom (no crash, no over-rejection).
    src = """
        Game G() {
            Set<BitString<8>> S;
            BitString<8> k;
            Bool Add(BitString<8> x) { S = S union {x}; return true; }
            Bool Query() { return k in S; }
        }
        """
    result = _z3_residual_equivalence(
        _parse_game(src), _parse_game(src), _empty_let_types(), _empty_namespace()
    )
    assert result.valid, result.failure_detail
