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
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        expected = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected

    def test_removes_dead_guard_none_equals_variable(self) -> None:
        """Test None == x form (reversed operand order)."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    if (None == x) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        expected = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = 0^8;
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == expected


class TestPreservesRealNullGuards:
    """Tests that real null guards (nullable variables) are kept."""

    def test_preserves_guard_on_nullable_variable(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test() {
                    BitString<8>? x = None;
                    if (x == None) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_guard_with_else_block(self) -> None:
        """If-else is not a simple guard pattern — preserve it."""
        game = frog_parser.parse_game("""
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
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_non_null_comparison(self) -> None:
        """if (x == y) is not a null guard — preserve it."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8> Test(BitString<8> x, BitString<8> y) {
                    if (x == y) {
                        return 0^8;
                    }
                    return x;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert result == game

    def test_preserves_guard_when_nonnull_var_reassigned_to_none(self) -> None:
        """If a variable is declared from a non-nullable expr but later
        reassigned to None, the null guard is reachable and must be kept."""
        game = frog_parser.parse_game("""
            Game G() {
                BitString<8>? Test(BitString<8> x) {
                    BitString<8>? v = x;
                    v = None;
                    if (v == None) {
                        return 0^8;
                    }
                    return v;
                }
            }
            """)
        type_map = visitors.build_game_type_map(game)
        result = DeadNullGuardEliminator(type_map).transform(game)
        assert (
            result == game
        ), "Guard on variable reassigned to None should not be eliminated"


class TestNullableLocalWrites:
    """A nullable local stays nullable if any later statement may write it."""

    @pytest.mark.parametrize(
        "write",
        [
            "if (c) { v = None; }",
            "if (c) { } else { v = None; }",
            "for (Int i = 0 to 2) { v = None; }",
            "if (c) { if (c) { v = None; } }",
        ],
    )
    def test_nested_write_keeps_guard(self, write: str) -> None:
        game = frog_parser.parse_game(f"""
            Game G() {{
                Int Test(Int x, Bool c) {{
                    Int? v = x;
                    {write}
                    if (v == None) {{
                        return 0;
                    }}
                    return 1;
                }}
            }}
            """)
        assert "if (v == None)" in _transform(str(game))

    def test_no_write_removes_guard(self) -> None:
        result = _transform("""
            Game G() {
                Int Test(Int x, Bool c) {
                    Int? v = x;
                    if (c) { x = 0; }
                    if (v == None) {
                        return 0;
                    }
                    return 1;
                }
            }
            """)
        assert "v == None" not in result

    def test_guard_before_declaration_kept(self) -> None:
        """The guard reads the field v, not the later local."""
        result = _transform("""
            Game G() {
                Int? v;
                Int Test(Int x) {
                    if (v == None) {
                        return 0;
                    }
                    Int? v = x;
                    return 1;
                }
            }
            """)
        assert "if (v == None)" in result
