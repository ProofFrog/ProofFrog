"""Tests for CheckTypeVisitor handling of literal types, nullable types, and narrowing."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    """Parse a game string and run CheckTypeVisitor on it."""
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    """Assert that a game string fails type checking."""
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)


class TestBooleanLiterals:
    def test_true_in_assignment(self) -> None:
        _check_game(
            """
            Game G() {
                Bool flag;
                Void Initialize() {
                    flag = true;
                }
            }
            """
        )

    def test_false_in_assignment(self) -> None:
        _check_game(
            """
            Game G() {
                Bool flag;
                Void Initialize() {
                    flag = false;
                }
            }
            """
        )

    def test_boolean_in_return(self) -> None:
        _check_game(
            """
            Game G() {
                Bool Test() {
                    return true;
                }
            }
            """
        )

    def test_boolean_in_local_variable(self) -> None:
        _check_game(
            """
            Game G() {
                Void Initialize() {
                    Bool x = false;
                }
            }
            """
        )


class TestIntegerLiteralControl:
    """Control test: integer literals already work."""

    def test_integer_in_assignment(self) -> None:
        _check_game(
            """
            Game G() {
                Int x;
                Void Initialize() {
                    x = 42;
                }
            }
            """
        )


class TestNullableTypes:
    """Tests for nullable type handling and null-narrowing."""

    def test_nullable_equals_none(self) -> None:
        _check_game(
            """
            Game G() {
                Bool Test(BitString<8>? x) {
                    return x == None;
                }
            }
            """
        )

    def test_nullable_not_equals_none(self) -> None:
        _check_game(
            """
            Game G() {
                Bool Test(BitString<8>? x) {
                    return x != None;
                }
            }
            """
        )

    def test_compare_nullable_with_nonnullable(self) -> None:
        _check_game(
            """
            Game G() {
                Bool Test(BitString<8> x, BitString<8>? y) {
                    return x == y;
                }
            }
            """
        )

    def test_null_narrowing_after_return_guard(self) -> None:
        _check_game(
            """
            Game G() {
                BitString<8> Test(BitString<8>? x) {
                    if (x == None) {
                        return 0^8;
                    }
                    BitString<8> y = x;
                    return y;
                }
            }
            """
        )

    def test_implicit_unwrap_rejected(self) -> None:
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            _check_game(
                """
                Game G() {
                    BitString<8> Test(BitString<8>? x) {
                        BitString<8> y = x;
                        return y;
                    }
                }
                """
            )

    def test_nullable_return_from_nullable_method(self) -> None:
        _check_game(
            """
            Game G() {
                BitString<8>? Test(BitString<8>? x) {
                    return x;
                }
            }
            """
        )

    def test_none_return_from_nullable_method(self) -> None:
        _check_game(
            """
            Game G() {
                BitString<8>? Test() {
                    return None;
                }
            }
            """
        )

    def test_nonnullable_to_nullable_assignment(self) -> None:
        _check_game(
            """
            Game G() {
                BitString<8>? Test(BitString<8> x) {
                    BitString<8>? y = x;
                    return y;
                }
            }
            """
        )


class TestNullNarrowingEdgeCases:
    """Edge cases for null-narrowing after guards."""

    def test_no_narrowing_without_return_in_block(self) -> None:
        """if (x == None) { y = 0^8; } does NOT narrow (no return)."""
        _check_game_fails(
            """
            Game G() {
                BitString<8> y;
                BitString<8> Test(BitString<8>? x) {
                    if (x == None) {
                        y = 0^8;
                    }
                    BitString<8> z = x;
                    return z;
                }
            }
            """
        )

    def test_no_narrowing_with_else_block(self) -> None:
        """if-else doesn't narrow after the block."""
        _check_game_fails(
            """
            Game G() {
                BitString<8> Test(BitString<8>? x) {
                    if (x == None) {
                        return 0^8;
                    } else {
                        return 0^8;
                    }
                    BitString<8> z = x;
                    return z;
                }
            }
            """
        )

    def test_narrowing_with_none_return(self) -> None:
        """Narrowing works when guard returns None."""
        _check_game(
            """
            Game G() {
                BitString<8>? Test(BitString<8>? x) {
                    if (x == None) {
                        return None;
                    }
                    BitString<8> y = x;
                    return y;
                }
            }
            """
        )

    def test_narrowing_allows_nonnullable_assignment(self) -> None:
        """After narrowing, variable can be assigned to non-nullable local."""
        _check_game(
            """
            Game G() {
                BitString<8> Test(BitString<8>? x) {
                    if (x == None) {
                        return 0^8;
                    }
                    BitString<8> y = x;
                    return y;
                }
            }
            """
        )


class TestNullableTypeErrors:
    """Tests that type errors are properly raised for nullable misuse."""

    def test_nullable_field_to_nonnullable_local(self) -> None:
        """Can't assign nullable field to non-nullable local."""
        _check_game_fails(
            """
            Game G() {
                BitString<8>? val;
                BitString<8> Test() {
                    BitString<8> x = val;
                    return x;
                }
            }
            """
        )

    def test_none_to_nonnullable_rejected(self) -> None:
        """Can't assign None to non-nullable type."""
        _check_game_fails(
            """
            Game G() {
                BitString<8> Test() {
                    BitString<8> x = None;
                    return x;
                }
            }
            """
        )

    def test_none_return_from_nonnullable_method(self) -> None:
        """Can't return None from non-nullable method."""
        _check_game_fails(
            """
            Game G() {
                BitString<8> Test() {
                    return None;
                }
            }
            """
        )
