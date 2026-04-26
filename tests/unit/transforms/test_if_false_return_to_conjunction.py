"""Tests for IfFalseReturnToConjunction.

Covers absorbing ``if (P) { return false; } ...; return BoolExpr;`` into
``...; return !P && BoolExpr;`` when intervening statements are
side-effect-free typed-local declarations.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.control_flow import IfFalseReturnToConjunction
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx(namespace: frog_ast.Namespace | None = None) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


def _apply(
    source: str, namespace: frog_ast.Namespace | None = None
) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return IfFalseReturnToConjunction().apply(game, _ctx(namespace))


def test_adjacent_if_false_return_absorbs() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            return x != 0;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int x, Int y) {
            return x != 0 && x != y;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_pure_intervening_locals_absorbed() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            Int z = x + y;
            Bool b = z != 0;
            return b;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int x, Int y) {
            Int z = x + y;
            Bool b = z != 0;
            return b && x != y;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_does_not_fire_with_sample_in_between() -> None:
    # A Sample is a side effect; absorbing would change observable
    # randomness when P holds.
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            BitString<8> r <- BitString<8>;
            return r != 0^8;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


def test_does_not_fire_when_early_return_is_not_false() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return true;
            }
            return x != 0;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


# --------------------------------------------------------------------------
# Soundness gap regression test (Gap G: RHS side-effect detection)
# --------------------------------------------------------------------------


NS_NONDET_HELPER = """
Primitive T() {
    Int Helper(Int x);
}
"""


def test_gap_g_typed_local_rhs_with_nondet_call_blocks_absorption() -> None:
    """Gap G distinguisher: a typed-local declaration whose RHS calls a
    non-deterministic helper (which may mutate game-visible state) cannot
    be hoisted past the early ``if (P) { return false; }`` — when ``P``
    holds, the original skips the call entirely."""
    prim = frog_parser.parse_primitive_file(NS_NONDET_HELPER)
    namespace: frog_ast.Namespace = {"T": prim}
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            Int z = T.Helper(x);
            return z == 1;
        }
    }
    """
    # Post-fix: the RHS contains a non-deterministic FuncCall, so the
    # transform refuses to absorb the early return.
    assert _apply(source, namespace) == frog_parser.parse_game(source)


def test_does_not_fire_when_if_has_else_block() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            } else {
                return true;
            }
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)
