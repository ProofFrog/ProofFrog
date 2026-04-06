import pytest
from sympy import symbols
from proof_frog import frog_parser
from proof_frog.transforms.symbolic import SymbolicComputationTransformer


@pytest.mark.parametrize(
    "method,expected,symbol_map",
    [
        # Simple substitution
        (
            """
        Void f() {
            Int x = lambda + lambda;
        }
        """,
            """
        Void f() {
            Int x = 2 * lambda;
        }
        """,
            {"lambda": symbols("lambda")},
        ),
        (
            """
        BitString<lambda + lambda + 2 * lambda> f(BitString<lambda * 2> x, BitString<lambda + lambda> y) {
            return x || y;
        }
        """,
            """
        BitString<4 * lambda> f(BitString<2 * lambda> x, BitString<2 * lambda> y) {
            return x || y;
        }
        """,
            {"lambda": symbols("lambda")},
        ),
        (
            """
        Void f() {
            return 3 + 5;
        }
        """,
            """
        Void f() {
            return 8;
        }
        """,
            {},
        ),
    ],
)
def test_symbolic_computation_transformer(
    method: str,
    expected: str,
    symbol_map: dict[(str, symbols)],
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    print("EXPECTED:", expected_ast)

    transformed_ast = SymbolicComputationTransformer(symbol_map).transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert transformed_ast == expected_ast


def test_integer_division_semantics() -> None:
    """Division should use integer (floor) semantics, not rational.
    5 / 2 in FrogLang is 2 (integer division), not 5/2 (rational)."""
    method = frog_parser.parse_method("""
        Void f() {
            Int x = 5 / 2;
        }
        """)
    expected = frog_parser.parse_method("""
        Void f() {
            Int x = 2;
        }
        """)
    transformed = SymbolicComputationTransformer({}).transform(method)
    assert (
        transformed == expected
    ), "5 / 2 should simplify to 2 (integer division), not 5/2 (rational)"


def test_symbolic_division_uses_floor() -> None:
    """Symbolic n / 2 should use floor division, producing floor(n/2),
    not rational n/2."""
    method = frog_parser.parse_method("""
        Void f() {
            Int x = n / 2;
        }
        """)
    transformed = SymbolicComputationTransformer({"n": symbols("n")}).transform(method)
    # With floordiv, n / 2 should NOT simplify (floor(n/2) doesn't
    # have a clean FrogLang representation), so it stays as n / 2.
    assert transformed == method
