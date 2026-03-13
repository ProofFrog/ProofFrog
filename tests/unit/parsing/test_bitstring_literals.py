import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import (
    XorIdentityTransformer,
    XorCancellationTransformer,
)


class TestParsing:
    """Tests for parsing 0^n and 1^n bitstring literals."""

    def test_zeros_concrete(self) -> None:
        expr = frog_parser.parse_expression("0^3")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 0
        assert expr.length == frog_ast.Integer(3)

    def test_ones_concrete(self) -> None:
        expr = frog_parser.parse_expression("1^5")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 1
        assert expr.length == frog_ast.Integer(5)

    def test_zeros_symbolic(self) -> None:
        expr = frog_parser.parse_expression("0^lambda")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 0
        assert expr.length == frog_ast.Variable("lambda")

    def test_ones_symbolic(self) -> None:
        expr = frog_parser.parse_expression("1^n")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 1
        assert expr.length == frog_ast.Variable("n")

    def test_zeros_compound_length(self) -> None:
        expr = frog_parser.parse_expression("0^(n + 1)")
        assert isinstance(expr, frog_ast.BitStringLiteral)
        assert expr.bit == 0
        assert isinstance(expr.length, frog_ast.BinaryOperation)

    def test_binary_num_still_works(self) -> None:
        expr = frog_parser.parse_expression("0b101")
        assert isinstance(expr, frog_ast.BinaryNum)
        assert expr.num == 5

    def test_in_add_expression(self) -> None:
        expr = frog_parser.parse_expression("x + 0^3")
        assert isinstance(expr, frog_ast.BinaryOperation)
        assert expr.operator == frog_ast.BinaryOperators.ADD
        assert isinstance(expr.right_expression, frog_ast.BitStringLiteral)

    def test_str_roundtrip(self) -> None:
        expr = frog_parser.parse_expression("0^lambda")
        assert str(expr) == "0^lambda"
        expr2 = frog_parser.parse_expression("1^3")
        assert str(expr2) == "1^3"


class TestXorIdentity:
    """Tests for XOR identity simplification: x + 0^n -> x."""

    @pytest.mark.parametrize(
        "method,expected",
        [
            # x + 0^lambda -> x
            (
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return x + 0^lambda;
                }
                """,
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return x;
                }
                """,
            ),
            # 0^lambda + x -> x
            (
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return 0^lambda + x;
                }
                """,
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return x;
                }
                """,
            ),
            # 0^n in a longer chain: a + 0^lambda + b -> a + b
            (
                """
                BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                    return a + 0^lambda + b;
                }
                """,
                """
                BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                    return a + b;
                }
                """,
            ),
            # 1^n is NOT an identity, should be unchanged
            (
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return x + 1^lambda;
                }
                """,
                """
                BitString<lambda> f(BitString<lambda> x) {
                    return x + 1^lambda;
                }
                """,
            ),
            # No zeros, should be unchanged
            (
                """
                BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                    return a + b;
                }
                """,
                """
                BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                    return a + b;
                }
                """,
            ),
        ],
    )
    def test_xor_identity(self, method: str, expected: str) -> None:
        method_ast = frog_parser.parse_method(method)
        expected_ast = frog_parser.parse_method(expected)
        transformed_ast = XorIdentityTransformer().transform(method_ast)
        assert expected_ast == transformed_ast


class TestXorCancellationWithLiterals:
    """Tests for XOR cancellation involving bitstring literals."""

    def test_ones_cancel(self) -> None:
        """1^n + x + 1^n -> x via XOR cancellation."""
        method_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return 1^lambda + x + 1^lambda;
            }
        """)
        expected_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return x;
            }
        """)
        transformed_ast = method_ast
        while True:
            new_ast = XorCancellationTransformer().transform(transformed_ast)
            if new_ast == transformed_ast:
                break
            transformed_ast = new_ast
        assert expected_ast == transformed_ast

    def test_zeros_cancel(self) -> None:
        """0^n + x + 0^n -> x via XOR cancellation."""
        method_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return 0^lambda + x + 0^lambda;
            }
        """)
        expected_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return x;
            }
        """)
        transformed_ast = method_ast
        while True:
            new_ast = XorCancellationTransformer().transform(transformed_ast)
            if new_ast == transformed_ast:
                break
            transformed_ast = new_ast
        assert expected_ast == transformed_ast

    def test_combined_identity_and_cancellation(self) -> None:
        """1^n + x + 1^n + 0^n -> x via cancellation then identity."""
        method_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return 1^lambda + x + 1^lambda + 0^lambda;
            }
        """)
        expected_ast = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return x;
            }
        """)
        transformed_ast = method_ast
        while True:
            new_ast = XorCancellationTransformer().transform(transformed_ast)
            new_ast = XorIdentityTransformer().transform(new_ast)
            if new_ast == transformed_ast:
                break
            transformed_ast = new_ast
        assert expected_ast == transformed_ast
