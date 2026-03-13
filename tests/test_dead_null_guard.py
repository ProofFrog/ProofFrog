"""Tests for DeadNullGuardEliminator transformer."""

import pytest
from proof_frog import visitors, frog_parser
from proof_frog.transforms.types import DeadNullGuardEliminator


def _transform(game_str: str) -> str:
    """Parse a game, apply DeadNullGuardEliminator, return string."""
    game = frog_parser.parse_game(game_str)
    type_map = visitors.build_game_type_map(game)
    result = DeadNullGuardEliminator(type_map).transform(game)
    return str(result)


class TestDeadNullGuardRemoval:
    """Tests for removing dead null guards where variable is non-nullable."""

    def test_removes_dead_guard_non_nullable_variable(self) -> None:
        game = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """
        )
        expected = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected

    def test_removes_dead_guard_none_equals_variable(self) -> None:
        """Test None == x form (reversed operand order)."""
        game = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (None == x) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """
        )
        expected = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected


class TestPreservesRealNullGuards:
    """Tests that real null guards (nullable variables) are kept."""

    def test_preserves_guard_on_nullable_variable(self) -> None:
        game = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8>? x = None;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_guard_with_else_block(self) -> None:
        """If-else is not a simple guard pattern — preserve it."""
        game = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (x == None) {
                        return 0^8;
                    } else {
                        return x;
                    }
                }
            }
            """
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_non_null_comparison(self) -> None:
        """if (x == y) is not a null guard — preserve it."""
        game = frog_parser.parse_game(
            """
            Game G() {
                BitString<8> Test(BitString<8> x, BitString<8> y) {
                    if (x == y) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """
        )
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game
