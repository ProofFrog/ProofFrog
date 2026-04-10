import pytest
from proof_frog import frog_parser
from proof_frog.transforms.algebraic import NormalizeCommutativeChainsTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Commutativity: b + a -> a + b
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return b + a;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b;
            }
            """,
        ),
        # Already sorted: a + b unchanged
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
        # Associativity: a + (b + c) -> (a + b) + c (left-assoc after sort)
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + (b + c);
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Both: (c + a) + b -> (a + b) + c
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return (c + a) + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Multiplication: b * a -> a * b
        (
            """
            Int f(Int a, Int b) {
                return b * a;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a * b;
            }
            """,
        ),
        # Non-commutative operator left alone: a - b unchanged
        (
            """
            Int f(Int a, Int b) {
                return a - b;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a - b;
            }
            """,
        ),
        # Mixed: (d + b) + (c + a) -> a + b + c + d
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c, BitString<lambda> d) {
                return (d + b) + (c + a);
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c, BitString<lambda> d) {
                return a + b + c + d;
            }
            """,
        ),
        # Nested in assignment context
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> x = b + a;
                return x;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> x = a + b;
                return x;
            }
            """,
        ),
        # Equality: b == a -> a == b
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return b == a;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
        ),
        # Equality: already sorted unchanged
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
        ),
        # Inequality: b != a -> a != b
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return b != a;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
        ),
        # Structural ordering for equality: FuncCall sorts after Variable
        (
            """
            Bool f(Int a, Int b) {
                return f(a) == a;
            }
            """,
            """
            Bool f(Int a, Int b) {
                return a == f(a);
            }
            """,
        ),
    ],
)
def test_normalize_commutative_chains(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed = NormalizeCommutativeChainsTransformer().transform(method_ast)

    print("EXPECTED:", expected_ast)
    print("TRANSFORMED:", transformed)
    assert expected_ast == transformed
