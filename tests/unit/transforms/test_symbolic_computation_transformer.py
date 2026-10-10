import pytest
from sympy import symbols
from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine
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


_LAMBDA = {"lambda": symbols("lambda")}


def _return(expression: str) -> frog_ast.Method:
    return frog_parser.parse_method(f"Void f() {{ return {expression}; }}")


@pytest.mark.parametrize(
    "expression",
    [
        # + on bit strings is XOR, and 1^2 is not the Int 2.
        "1^2 + 0^2",
        "1^2 + 1^2",
        "0^lambda + 1^lambda",
        # A negation is not its operand.
        "5 - -3",
        "-2 + 2",
        "2 * -2",
        "lambda + -lambda",
        # |0b11| has no value, so |0b11| * 5 is not 5.
        "|0b11| * 5 + 1",
    ],
)
def test_operand_without_int_value_not_folded(expression: str) -> None:
    method = _return(expression)
    assert SymbolicComputationTransformer(_LAMBDA).transform(method) == method


def test_bit_string_literal_lengths_fold_but_xor_stays() -> None:
    method = _return("1^(1 + 1) + 0^(lambda + lambda)")
    expected = _return("1^2 + 0^(2 * lambda)")
    assert SymbolicComputationTransformer(_LAMBDA).transform(method) == expected


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("(3 - 5) * 2", "-4"),
        ("-(2 + 3)", "-5"),
        ("2 * lambda - lambda", "lambda"),
        ("0^(lambda + lambda)", "0^(2 * lambda)"),
        ("|x| + (1 + 2)", "|x| + 3"),
        ("F(1 + 2) + 1", "F(3) + 1"),
    ],
)
def test_int_arithmetic_still_folds(expression: str, expected: str) -> None:
    transformed = SymbolicComputationTransformer(_LAMBDA).transform(_return(expression))
    assert transformed == _return(expected)


def _equivalent(left: str, right: str) -> bool:
    return (
        ProofEngine()
        .check_equivalent(frog_parser.parse_game(left), frog_parser.parse_game(right))
        .valid
    )


@pytest.mark.parametrize(
    "left, right",
    [
        # The reported pair: Left returns 0b11, Right 0b00.
        (
            "BitString<2> E() { return 1^2 + 0^2; }",
            "BitString<2> E() { return 1^2 + 1^2; }",
        ),
        ("Int E() { return 5 - -3; }", "Int E() { return 2; }"),
        # The fold of 3 - 5 is the negation -2, inlined into x * 2.
        ("Int E() { Int x = 3 - 5; return x * 2; }", "Int E() { return 4; }"),
    ],
)
def test_engine_rejects_different_values(left: str, right: str) -> None:
    assert not _equivalent(f"Game L() {{ {left} }}", f"Game R() {{ {right} }}")


@pytest.mark.parametrize(
    "left, right",
    [
        ("BitString<2> E() { return 1^2 + 0^2; }", "BitString<2> E() { return 1^2; }"),
        ("Int E() { return 3 + 5; }", "Int E() { return 8; }"),
        ("Int E() { return 5 - -3; }", "Int E() { return 8; }"),
        ("Int E() { Int x = 3 - 5; return x * 2; }", "Int E() { return -4; }"),
    ],
)
def test_engine_accepts_equal_values(left: str, right: str) -> None:
    assert _equivalent(f"Game L() {{ {left} }}", f"Game R() {{ {right} }}")
