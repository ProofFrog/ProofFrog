"""Tests for TupleEqualityDecompose.

Covers rewriting ``a != b`` between tuple-typed expressions to a
component-wise disjunction of ``!=`` per index. The ``==`` direction is
intentionally NOT decomposed; verify it is left alone.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import TupleEqualityDecompose
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return TupleEqualityDecompose().apply(game, _ctx())


def test_tuple_neq_decomposes_to_per_component_disjunction() -> None:
    source = """
    Game G() {
        Bool Check([Int, Int] a, [Int, Int] b) {
            return a != b;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check([Int, Int] a, [Int, Int] b) {
            return a[0] != b[0] || a[1] != b[1];
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_three_component_tuple_neq() -> None:
    source = """
    Game G() {
        Bool Check([Int, Int, Int] a, [Int, Int, Int] b) {
            return a != b;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check([Int, Int, Int] a, [Int, Int, Int] b) {
            return a[0] != b[0] || a[1] != b[1] || a[2] != b[2];
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_tuple_eq_is_not_decomposed() -> None:
    # The == direction is intentionally left atomic.
    source = """
    Game G() {
        Bool Check([Int, Int] a, [Int, Int] b) {
            return a == b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


def test_non_tuple_neq_does_not_fire() -> None:
    source = """
    Game G() {
        Bool Check(Int a, Int b) {
            return a != b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)
