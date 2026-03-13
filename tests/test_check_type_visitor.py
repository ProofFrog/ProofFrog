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


_NULLABLE_ORACLE_GAME = """\
Game Left() {
    BitString<8>? Challenge() {
        BitString<8>? result = None;
        return result;
    }
}
Game Right() {
    BitString<8>? Challenge() {
        BitString<8>? result = None;
        return result;
    }
}
export as SecurityGame;
"""


def _check_reduction(reduction_str: str) -> None:
    """Parse a reduction string and run CheckTypeVisitor on it."""
    security_game = frog_parser.parse_game_file(_NULLABLE_ORACLE_GAME)
    reduction = frog_parser.parse_reduction(reduction_str)
    checker = semantic_analysis.CheckTypeVisitor(
        {"SecurityGame": security_game}, "test", {}
    )
    checker.visit(reduction)


def _check_reduction_fails(reduction_str: str) -> None:
    """Assert that a reduction string fails type checking."""
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_reduction(reduction_str)


class TestReductionTypeChecking:
    """Tests for type checking of reduction bodies, including nullable challenger calls."""

    def test_reduction_returning_nullable_from_nonnullable_oracle(self) -> None:
        """Reduction returning nullable challenger result from non-nullable oracle is a type error."""
        _check_reduction_fails(
            """
            Reduction R() compose SecurityGame() against SecurityGame().Adversary {
                BitString<8> Challenge() {
                    return challenger.Challenge();
                }
            }
            """
        )

    def test_reduction_with_null_narrowing_passes(self) -> None:
        """Reduction using null-narrowing before returning challenger result type-checks."""
        _check_reduction(
            """
            Reduction R() compose SecurityGame() against SecurityGame().Adversary {
                BitString<8> Challenge() {
                    BitString<8>? result = challenger.Challenge();
                    if (result == None) {
                        return 0^8;
                    }
                    return result;
                }
            }
            """
        )

    def test_reduction_returning_nullable_from_nullable_oracle_passes(self) -> None:
        """Reduction declaring nullable return type can return challenger result directly."""
        _check_reduction(
            """
            Reduction R() compose SecurityGame() against SecurityGame().Adversary {
                BitString<8>? Challenge() {
                    return challenger.Challenge();
                }
            }
            """
        )
