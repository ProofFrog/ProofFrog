"""Tests for CheckTypeVisitor handling of literal types."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    """Parse a game string and run CheckTypeVisitor on it."""
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


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
