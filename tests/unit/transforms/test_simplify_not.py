"""Tests for SimplifyNotPass: ``!`` rewriting and DeMorgan."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import SimplifyNotPass
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
    return SimplifyNotPass().apply(game, _ctx())


def test_not_equals_to_neq() -> None:
    source = """
    Game G() {
        Bool Check(Int a, Int b) {
            return !(a == b);
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int a, Int b) {
            return a != b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_not_neq_to_equals() -> None:
    source = """
    Game G() {
        Bool Check(Int a, Int b) {
            return !(a != b);
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int a, Int b) {
            return a == b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_demorgan_and_to_or() -> None:
    source = """
    Game G() {
        Bool Check(Int a, Int b, Int c, Int d) {
            return !(a == b && c == d);
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int a, Int b, Int c, Int d) {
            return a != b || c != d;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_demorgan_or_to_and() -> None:
    source = """
    Game G() {
        Bool Check(Int a, Int b, Int c, Int d) {
            return !(a == b || c == d);
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int a, Int b, Int c, Int d) {
            return a != b && c != d;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_double_negation_eliminated() -> None:
    source = """
    Game G() {
        Bool Check(Bool a) {
            return !!a;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Bool a) {
            return a;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)
