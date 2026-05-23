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
    # shape from CK_expanded_LEAK_BIND_K_CT step 3.
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
