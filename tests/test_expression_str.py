"""Tests for precedence-aware __str__ on BinaryOperation and BitStringLiteral."""

import pytest
from proof_frog import frog_ast, frog_parser


class TestBinaryOperationStr:
    """BinaryOperation.__str__ emits parentheses based on precedence."""

    def test_flat_add(self) -> None:
        # a + b -> "a + b"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            frog_ast.Variable("a"),
            frog_ast.Variable("b"),
        )
        assert str(expr) == "a + b"

    def test_multiply_over_add_no_parens(self) -> None:
        # a * b + c -> "a * b + c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "a * b + c"

    def test_add_inside_multiply_gets_parens_left(self) -> None:
        # (a + b) * c -> "(a + b) * c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.ADD,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "(a + b) * c"

    def test_add_inside_multiply_gets_parens_right(self) -> None:
        # a * (b + c) -> "a * (b + c)"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.ADD,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a * (b + c)"

    def test_right_associative_subtraction_gets_parens(self) -> None:
        # a - (b - c) -> "a - (b - c)"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBTRACT,
            frog_ast.Variable("a"),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.SUBTRACT,
                frog_ast.Variable("b"),
                frog_ast.Variable("c"),
            ),
        )
        assert str(expr) == "a - (b - c)"

    def test_left_associative_subtraction_no_extra_parens(self) -> None:
        # (a - b) - c -> "a - b - c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBTRACT,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.SUBTRACT,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "a - b - c"

    def test_comparison_inside_logical_no_parens(self) -> None:
        # (a == b) && (c == d) -> "a == b && c == d"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.AND,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.Variable("c"),
                frog_ast.Variable("d"),
            ),
        )
        assert str(expr) == "a == b && c == d"

    def test_logical_inside_comparison_gets_parens(self) -> None:
        # (a && b) == c -> "(a && b) == c"
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.AND,
                frog_ast.Variable("a"),
                frog_ast.Variable("b"),
            ),
            frog_ast.Variable("c"),
        )
        assert str(expr) == "(a && b) == c"


class TestBinaryOperationRoundTrip:
    """Expressions round-trip through parse -> str -> parse correctly."""

    @pytest.mark.parametrize(
        "source",
        [
            "n + 1",
            "n * 2 + 1",
            "(n + 1) * 2",
            "a - (b - c)",
            "a - b - c",
            "a * b * c",
        ],
    )
    def test_roundtrip(self, source: str) -> None:
        expr = frog_parser.parse_expression(source)
        reparsed = frog_parser.parse_expression(str(expr))
        assert expr == reparsed


class TestBitStringLiteralStr:
    """BitStringLiteral.__str__ wraps compound lengths in parens."""

    def test_simple_length(self) -> None:
        expr = frog_parser.parse_expression("0^n")
        assert str(expr) == "0^n"

    def test_integer_length(self) -> None:
        expr = frog_parser.parse_expression("1^3")
        assert str(expr) == "1^3"

    def test_compound_length_gets_parens(self) -> None:
        expr = frog_parser.parse_expression("0^(n + 1)")
        assert str(expr) == "0^(n + 1)"

    def test_compound_length_multiply(self) -> None:
        expr = frog_parser.parse_expression("1^(n * 2)")
        assert str(expr) == "1^(n * 2)"

    def test_compound_length_roundtrip(self) -> None:
        """0^(n + 1) must not become 0^n + 1 which is a different expression."""
        expr = frog_parser.parse_expression("0^(n + 1)")
        roundtripped = frog_parser.parse_expression(str(expr))
        assert isinstance(roundtripped, frog_ast.BitStringLiteral)
        assert expr == roundtripped

    def test_in_addition_context(self) -> None:
        """x + 0^(n + 1) must not become x + 0^n + 1."""
        expr = frog_parser.parse_expression("x + 0^(n + 1)")
        roundtripped = frog_parser.parse_expression(str(expr))
        assert expr == roundtripped
