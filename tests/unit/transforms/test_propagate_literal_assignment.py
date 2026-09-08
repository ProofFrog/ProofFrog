"""Tests for PropagateLiteralAssignment (proof_frog.transforms.control_flow)."""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import PropagateLiteralAssignmentTransformer


def _apply(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(PropagateLiteralAssignmentTransformer().transform(game))


def _same(src: str) -> bool:
    return _apply(src) == str(frog_parser.parse_game(src))


def test_bool_literal_reaches_following_condition() -> None:
    src = """
    Game G() {
        BitString<k> Oracle(BitString<k> a, BitString<k> b) {
            hit = true;
            if (hit) {
                return a;
            }
            return b;
        }
    }
    """
    expected = """
    Game G() {
        BitString<k> Oracle(BitString<k> a, BitString<k> b) {
            hit = true;
            if (true) {
                return a;
            }
            return b;
        }
    }
    """
    assert _apply(src) == str(frog_parser.parse_game(expected))


def test_int_literal_reaches_nested_read() -> None:
    src = """
    Game G() {
        Int Oracle(Bool c) {
            n = 3;
            if (c) {
                return n + 1;
            }
            return n;
        }
    }
    """
    expected = """
    Game G() {
        Int Oracle(Bool c) {
            n = 3;
            if (c) {
                return 3 + 1;
            }
            return 3;
        }
    }
    """
    assert _apply(src) == str(frog_parser.parse_game(expected))


def test_stops_at_a_later_write() -> None:
    assert _same("""
    Game G() {
        Int Oracle(Bool c) {
            n = 3;
            n = n + 1;
            return n;
        }
    }
    """)


def test_stops_at_a_statement_that_may_write_in_a_branch() -> None:
    assert _same("""
    Game G() {
        Bool Oracle(Bool c) {
            hit = true;
            if (c) {
                hit = false;
            }
            return hit;
        }
    }
    """)


def test_stops_at_a_shadowing_declaration() -> None:
    """The outer literal must not reach the shadowed inner `hit`; the inner
    block's own literal is propagated within that block."""
    src = """
    Game G() {
        Bool Oracle(Bool c) {
            hit = true;
            if (c) {
                Bool hit = false;
                return hit;
            }
            return c;
        }
    }
    """
    expected = """
    Game G() {
        Bool Oracle(Bool c) {
            hit = true;
            if (c) {
                Bool hit = false;
                return false;
            }
            return c;
        }
    }
    """
    assert _apply(src) == str(frog_parser.parse_game(expected))


def test_non_literal_assignment_is_not_propagated() -> None:
    assert _same("""
    Game G() {
        Bool Oracle(Bool c) {
            hit = c;
            if (hit) {
                return true;
            }
            return false;
        }
    }
    """)
