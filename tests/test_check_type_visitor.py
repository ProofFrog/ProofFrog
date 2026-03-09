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
