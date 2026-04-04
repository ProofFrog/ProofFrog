import pytest
from proof_frog import frog_parser
from proof_frog.transforms.algebraic import (
    XorCancellationTransformer,
    ReflexiveComparisonTransformer,
)


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: k + k + m -> m
        (
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return k + k + m;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return m;
            }
            """,
        ),
        # Just XOR cancellation: a + b + a -> b
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return b;
            }
            """,
        ),
        # Three terms, middle cancels: a + b + c + b -> a + c
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + c;
            }
            """,
        ),
        # No cancellation: a + b (different terms)
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
        # XOR cancellation does not inline variables (engine does that separately)
        (
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                BitString<lambda> x = k + m;
                BitString<lambda> y = k + x;
                return y;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                BitString<lambda> x = k + m;
                BitString<lambda> y = k + x;
                return y;
            }
            """,
        ),
        # Multiple pairs cancel: a + b + a + b -> all cancel.
        # Without type_map, the result is unchanged (can't produce 0^n).
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a + b;
            }
            """,
        ),
    ],
)
def test_xor_cancellation(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    # Apply repeatedly to handle iterative cancellation
    transformed_ast = method_ast
    while True:
        new_ast = XorCancellationTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # Reflexive equality: m == m -> true
        (
            """
            Bool f(BitString<lambda> m) {
                return m == m;
            }
            """,
            """
            Bool f(BitString<lambda> m) {
                return true;
            }
            """,
        ),
        # Reflexive inequality: m != m -> false
        (
            """
            Bool f(BitString<lambda> m) {
                return m != m;
            }
            """,
            """
            Bool f(BitString<lambda> m) {
                return false;
            }
            """,
        ),
        # Non-reflexive equality: should NOT simplify
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
        # Complex equal expressions: (a + b) == (a + b) -> true
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a + b == a + b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return true;
            }
            """,
        ),
        # Non-reflexive inequality: should NOT simplify
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
        ),
        # Reflexive equality on Int: x == x -> true
        (
            """
            Bool f(Int x) {
                return x == x;
            }
            """,
            """
            Bool f(Int x) {
                return true;
            }
            """,
        ),
    ],
)
def test_reflexive_comparison(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = ReflexiveComparisonTransformer().transform(method_ast)

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_xor_all_terms_cancel_returns_zero() -> None:
    """When all terms cancel (k + k), the result should be 0^n, not the
    original expression unchanged."""
    from proof_frog.visitors import build_game_type_map

    game_ast = frog_parser.parse_game("""
        Game G(Int lambda) {
            BitString<lambda> f(BitString<lambda> k) {
                return k + k;
            }
        }
    """)
    expected_ast = frog_parser.parse_game("""
        Game G(Int lambda) {
            BitString<lambda> f(BitString<lambda> k) {
                return 0^lambda;
            }
        }
    """)

    type_map = build_game_type_map(game_ast)
    transformed_ast = game_ast
    while True:
        new_ast = XorCancellationTransformer(type_map).transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    assert expected_ast == transformed_ast, (
        "k + k should simplify to 0^lambda"
    )


def test_xor_cancellation_with_reflexive_comparison() -> None:
    """Combined: k + k + m == m -> true (XOR cancellation then reflexive comparison)."""
    method_ast = frog_parser.parse_method("""
        Bool f(BitString<lambda> k, BitString<lambda> m) {
            return k + k + m == m;
        }
    """)
    expected_ast = frog_parser.parse_method("""
        Bool f(BitString<lambda> k, BitString<lambda> m) {
            return true;
        }
    """)

    transformed_ast = method_ast
    while True:
        new_ast = XorCancellationTransformer().transform(transformed_ast)
        new_ast = ReflexiveComparisonTransformer().transform(new_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    assert expected_ast == transformed_ast
