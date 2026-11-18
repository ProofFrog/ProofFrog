import pytest
from sympy import Rational, symbols, sympify
from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.semantic_analysis import get_sympy_expression
from proof_frog.transforms.symbolic import (
    SymbolicComputationTransformer,
    froglang_text,
    sympy_to_expression,
)
from proof_frog.visitors import FrogToSympyVisitor


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


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("0 / 0", "0 / 0"),
        ("5 / 0", "5 / 0"),
        ("(1 + 1) / (2 - 2)", "2 / 0"),
        # SymPy reduces each operand to 0, the next application sees 0 / 0.
        ("(lambda - lambda) / (lambda - lambda)", "0 / 0"),
    ],
)
def test_division_by_zero_not_folded(expression: str, expected: str) -> None:
    """Division by zero has an unspecified value, not a literal one; Python's
    floor division raised ZeroDivisionError and aborted the whole proof."""
    method = _return(expression)
    for _ in range(2):
        method = SymbolicComputationTransformer(_LAMBDA).transform(method)
    assert method == _return(expected)


@pytest.mark.parametrize(
    "expression, expected",
    [("0 / 5", "0"), ("6 / 3", "2"), ("(4 - 2) / (1 + 1)", "1")],
)
def test_division_by_nonzero_still_folds(expression: str, expected: str) -> None:
    transformed = SymbolicComputationTransformer(_LAMBDA).transform(_return(expression))
    assert transformed == _return(expected)


def test_engine_accepts_equal_divisions_by_zero() -> None:
    """Two divisions by zero with the same operands are the same value."""
    assert _equivalent(
        "Game L() { Int E() { return (1 - 1) / (2 - 2); } }",
        "Game R() { Int E() { return 0 / 0; } }",
    )


@pytest.mark.parametrize(
    "left, right",
    [
        ("Int E() { return 0 / 0; }", "Int E() { return 1 / 0; }"),
        ("Int E() { return 0 / 0; }", "Int E() { return 0; }"),
        (
            "Int E(Int a) { if ((1 - 1) / (2 - 2) == a) { return 1; } return 0; }",
            "Int E(Int a) { return 0; }",
        ),
    ],
)
def test_engine_rejects_unequal_division_by_zero(left: str, right: str) -> None:
    """Refused, not crashed: the pass and the Z3 layer leave ``c / 0`` alone."""
    assert not _equivalent(f"Game L() {{ {left} }}", f"Game R() {{ {right} }}")


# F-392: a folded value was printed with SymPy's ``str`` and parsed back as
# FrogLang, so a power (``k * k`` folds to ``k**2``) crashed the proof with a
# parse error. Powers are now printed with FrogLang's ``^``, and a value with
# no FrogLang Int text of the same meaning is left unfolded.


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("lambda * lambda", "lambda ^ 2"),
        ("lambda * lambda * 2", "2 * lambda ^ 2"),
        ("lambda * (lambda * lambda)", "lambda ^ 3"),
        ("0 - lambda * lambda", "-(lambda ^ 2)"),
        ("(lambda + 1) * (lambda + 1)", "(lambda + 1) ^ 2"),
        ("lambda ^ 2", "lambda ^ 2"),
        ("2 ^ 3", "8"),
        ("2 ^ (lambda - lambda)", "1"),
    ],
)
def test_powers_fold_to_froglang(expression: str, expected: str) -> None:
    transformed = SymbolicComputationTransformer(_LAMBDA).transform(_return(expression))
    assert transformed == _return(expected)


@pytest.mark.parametrize(
    "expression, expected",
    [
        # Python's 2 ** -1 is the float 0.5, SymPy's lambda ** -1 the
        # fraction 1/lambda, printed as an Int division.
        ("2 ^ (0 - 1)", "2 ^ -1"),
        ("lambda ^ (0 - 1)", "lambda ^ -1"),
        # An exponent not known to be >= 0: SymPy would combine powers
        # (lambda ^ a * lambda == lambda ^ (a + 1)), which Int need not obey.
        ("lambda ^ lambda", "lambda ^ lambda"),
        ("(lambda - lambda) ^ lambda", "0 ^ lambda"),
    ],
)
def test_powers_without_froglang_text_not_folded(
    expression: str, expected: str
) -> None:
    transformed = SymbolicComputationTransformer(_LAMBDA).transform(_return(expression))
    assert transformed == _return(expected)


def test_froglang_text() -> None:
    k = symbols("k")
    assert froglang_text(5) == "5"
    assert froglang_text(-5) == "-5"
    assert froglang_text(2 * k + 1) == "2*k + 1"
    assert froglang_text(k**2) == "(k ^ 2)"
    assert froglang_text(-(k**2)) == "-(k ^ 2)"
    assert froglang_text((k + 1) ** 2) == "((k + 1) ^ 2)"
    assert froglang_text(k**-1) is None
    assert froglang_text(k / 2) is None
    assert froglang_text(Rational(1, 2)) is None
    assert froglang_text(0.5) is None
    assert froglang_text(True) is None
    assert froglang_text(k**k) is None
    # The length computations print a rational coefficient as before.
    assert froglang_text(k / 2, fractions=True) == "k/2"
    assert froglang_text(k**2 / 2, fractions=True) == "(k ^ 2)/2"
    assert froglang_text(k**-1, fractions=True) is None


def test_sympy_to_expression() -> None:
    k, n = symbols("k n")
    assert sympy_to_expression(k * k + n) == frog_parser.parse_expression("k ^ 2 + n")
    assert sympy_to_expression(7) == frog_ast.Integer(7)
    assert sympy_to_expression(k / 2) is None


@pytest.mark.parametrize(
    "expression, ok",
    [("k ^ 2 + n", True), ("k ^ 0", True), ("k ^ n", False), ("k ^ -1", False)],
)
def test_sympy_readers_read_natural_powers(expression: str, ok: bool) -> None:
    """The printer writes k * k as k ^ 2, so the readers of lengths read it
    back (an exponent that is an integer >= 0 only)."""
    k, n = symbols("k n")
    node = frog_parser.parse_expression(expression)
    expected = sympify(expression.replace("^", "**"), locals={"k": k, "n": n})
    from_visitor = FrogToSympyVisitor({"k": k, "n": n}).visit(node)
    from_reader = get_sympy_expression(node)
    if ok:
        assert from_visitor == expected
        assert from_reader == expected
    else:
        assert from_visitor is None
        assert from_reader is None


# ``e + 0`` and ``0 + e`` become ``e`` for an Int ``e`` whose value the pass
# does not know (a field, a local, a call), by its declared type. Before,
# only literals and proof let: Int parameters had values, so
# ``Int r = c; c = c + 1; return r + 0;`` never met the same method
# returning ``r``. A ModInt or BitString operand keeps its form.


def _typed(params: str, expression: str, return_type: str = "Int") -> frog_ast.Method:
    return frog_parser.parse_method(
        f"{return_type} f({params}) {{ return {expression}; }}"
    )


@pytest.mark.parametrize(
    "params, expression, expected",
    [
        ("Int x", "x + 0", "x"),
        ("Int x", "0 + x", "x"),
        ("Int x", "(x + 0) + 0", "x"),
        ("Int x", "x + 0 + 1", "x + 1"),
        # The zero may come from a fold.
        ("Int x", "x + (1 - 1)", "x"),
        ("Int x", "x + (lambda - lambda)", "x"),
        ("Int x, Int y", "(x * y) + 0", "x * y"),
        ("Int x", "-x + 0", "-x"),
        ("Set<Int> S", "|S| + 0", "|S|"),
        ("Map<Int, Int> M, Int k", "0 + M[k]", "M[k]"),
    ],
)
def test_plus_zero_folds_for_int(params: str, expression: str, expected: str) -> None:
    transformed = SymbolicComputationTransformer(_LAMBDA).transform(
        _typed(params, expression)
    )
    assert transformed == _typed(params, expected)


@pytest.mark.parametrize(
    "params, expression, return_type",
    [
        # An integer literal next to a ModInt is an Int (F-357).
        ("ModInt<q> u", "u + 0", "ModInt<q>"),
        ("ModInt<q> u", "0 + u", "ModInt<q>"),
        # + on a bit string is XOR.
        ("BitString<8> s", "s + 0", "BitString<8>"),
        ("BitString<8> s", "s + 0^8", "BitString<8>"),
        # y has no declared type.
        ("Int x", "y + 0", "Int"),
    ],
)
def test_plus_zero_kept_unless_int(
    params: str, expression: str, return_type: str
) -> None:
    method = _typed(params, expression, return_type)
    assert SymbolicComputationTransformer(_LAMBDA).transform(method) == method


def test_plus_zero_folds_for_int_field_and_initializer() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int c;
            Int d = c + 0;
            ModInt<q> u;
            Int Test() { return c + 0; }
            ModInt<q> Other() { return u + 0; }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Int c;
            Int d = c;
            ModInt<q> u;
            Int Test() { return c; }
            ModInt<q> Other() { return u + 0; }
        }
        """)
    assert SymbolicComputationTransformer({}, None, game).transform(game) == expected


@pytest.mark.parametrize(
    "body",
    [
        # x shadows the ModInt field x.
        "Int x = 1; return x + 0;",
        # x is declared twice, the second time as a ModInt.
        "if (b) { Int x = 1; return x + 0; } ModInt<q> x = 2; return 5;",
    ],
)
def test_plus_zero_not_folded_for_name_bound_twice(body: str) -> None:
    """The type map gives such a name one type for the whole method."""
    game = frog_parser.parse_game(f"""
        Game G() {{
            ModInt<q> x;
            Int Test(Bool b) {{ {body} }}
        }}
        """)
    assert SymbolicComputationTransformer({}, None, game).transform(game) == game


_READ_THEN_INC = """
    Game G() {{
        Int c;
        Void Initialize() {{ c = 0; }}
        Int Test() {{ Int r = c; c = c + 1; return {returned}; }}
    }}
"""


def test_engine_accepts_read_then_increment_plus_zero() -> None:
    assert _equivalent(
        _READ_THEN_INC.format(returned="r"), _READ_THEN_INC.format(returned="r + 0")
    )
    assert _equivalent(
        _READ_THEN_INC.format(returned="0 + r"), _READ_THEN_INC.format(returned="r")
    )


@pytest.mark.parametrize("returned", ["c", "r + 1", "c + 0"])
def test_engine_rejects_read_then_increment_other_value(returned: str) -> None:
    assert not _equivalent(
        _READ_THEN_INC.format(returned="r + 0"),
        _READ_THEN_INC.format(returned=returned),
    )
