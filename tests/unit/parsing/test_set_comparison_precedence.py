"""Precedence of the set, comparison and Boolean operators.

Below ``+``/``-`` the levels are, tightest first: ``union`` and ``\\``;
the relational tests ``<`` ``<=`` ``>`` ``>=`` ``in`` ``subsets``; the
equality tests ``==`` ``!=``; ``&&``; ``||``. Operators sharing a level
are left-associative. So ``x in A union B`` is ``x in (A union B)``,
``A \\ B union C`` is ``(A \\ B) union C`` and ``a < b == c < d`` is
``(a < b) == (c < d)``. The AST printer must parenthesize so that
``parse(str(e)) == e`` for every expression over these operators.
"""

import random

import pytest

from proof_frog import frog_ast, frog_parser, semantic_analysis

Op = frog_ast.BinaryOperators


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _bin(
    op: frog_ast.BinaryOperators, left: frog_ast.Expression, right: frog_ast.Expression
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(op, left, right)


def _neg(expr: frog_ast.Expression) -> frog_ast.UnaryOperation:
    return frog_ast.UnaryOperation(frog_ast.UnaryOperators.MINUS, expr)


a, b, c, d = _var("a"), _var("b"), _var("c"), _var("d")
x, A, B, C = _var("x"), _var("A"), _var("B"), _var("C")


@pytest.mark.parametrize(
    "source, expected",
    [
        # union and \ share a level, left-associative.
        ("A \\ B union C", _bin(Op.UNION, _bin(Op.SETMINUS, A, B), C)),
        ("A union B \\ C", _bin(Op.SETMINUS, _bin(Op.UNION, A, B), C)),
        ("A \\ B \\ C", _bin(Op.SETMINUS, _bin(Op.SETMINUS, A, B), C)),
        ("A union B union C", _bin(Op.UNION, _bin(Op.UNION, A, B), C)),
        # The set level binds tighter than the comparisons ...
        ("x in A union B", _bin(Op.IN, x, _bin(Op.UNION, A, B))),
        ("x in A \\ B", _bin(Op.IN, x, _bin(Op.SETMINUS, A, B))),
        ("A union B subsets C", _bin(Op.SUBSETS, _bin(Op.UNION, A, B), C)),
        ("A == B union C", _bin(Op.EQUALS, A, _bin(Op.UNION, B, C))),
        # ... and looser than + and - (and unary minus).
        ("a + b union c", _bin(Op.UNION, _bin(Op.ADD, a, b), c)),
        ("a union b - c", _bin(Op.UNION, a, _bin(Op.SUBTRACT, b, c))),
        ("-a union b", _bin(Op.UNION, _neg(a), b)),
        # The relational tests share a level, left-associative.
        ("a < b <= c", _bin(Op.LEQ, _bin(Op.LT, a, b), c)),
        ("a >= b > c", _bin(Op.GT, _bin(Op.GEQ, a, b), c)),
        ("a in b subsets c", _bin(Op.SUBSETS, _bin(Op.IN, a, b), c)),
        ("a subsets b in c", _bin(Op.IN, _bin(Op.SUBSETS, a, b), c)),
        ("a > b in c", _bin(Op.IN, _bin(Op.GT, a, b), c)),
        # == and != share a level, left-associative.
        ("a == b != c", _bin(Op.NOTEQUALS, _bin(Op.EQUALS, a, b), c)),
        ("a != b == c", _bin(Op.EQUALS, _bin(Op.NOTEQUALS, a, b), c)),
        ("a == b == c", _bin(Op.EQUALS, _bin(Op.EQUALS, a, b), c)),
        # The relational level binds tighter than the equality level.
        ("a < b == c < d", _bin(Op.EQUALS, _bin(Op.LT, a, b), _bin(Op.LT, c, d))),
        (
            "x in A != x in B",
            _bin(Op.NOTEQUALS, _bin(Op.IN, x, A), _bin(Op.IN, x, B)),
        ),
        ("a == b < c", _bin(Op.EQUALS, a, _bin(Op.LT, b, c))),
        # Equality binds tighter than &&, which binds tighter than ||.
        (
            "a == b && c != d",
            _bin(Op.AND, _bin(Op.EQUALS, a, b), _bin(Op.NOTEQUALS, c, d)),
        ),
        ("a || b && c", _bin(Op.OR, a, _bin(Op.AND, b, c))),
        ("a && b || c", _bin(Op.OR, _bin(Op.AND, a, b), c)),
        ("a && b && c", _bin(Op.AND, _bin(Op.AND, a, b), c)),
        # || (also bitstring concatenation) stays below the comparisons.
        ("a == b || c", _bin(Op.OR, _bin(Op.EQUALS, a, b), c)),
        # Explicit parentheses still win.
        ("A \\ (B union C)", _bin(Op.SETMINUS, A, _bin(Op.UNION, B, C))),
        ("(x in A) == b", _bin(Op.EQUALS, _bin(Op.IN, x, A), b)),
        ("a == (b == c)", _bin(Op.EQUALS, a, _bin(Op.EQUALS, b, c))),
    ],
)
def test_expression_parse(source: str, expected: frog_ast.Expression) -> None:
    assert frog_parser.parse_expression(source) == expected


def test_membership_in_union_type_checks() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Set<BitString<8>> S;
            Set<BitString<8>> T;
            Bool Query(BitString<8> x) {
                return x in S union T && x in S \\ T == false;
            }
        }
        """)
    semantic_analysis.CheckTypeVisitor({}, "test", {}).visit(game)


@pytest.mark.parametrize(
    "expr, text",
    [
        (_bin(Op.UNION, _bin(Op.SETMINUS, A, B), C), "A \\ B union C"),
        (_bin(Op.SETMINUS, A, _bin(Op.UNION, B, C)), "A \\ (B union C)"),
        (_bin(Op.SETMINUS, A, _bin(Op.SETMINUS, B, C)), "A \\ (B \\ C)"),
        (_bin(Op.IN, x, _bin(Op.UNION, A, B)), "x in A union B"),
        (_bin(Op.UNION, _bin(Op.IN, x, A), B), "(x in A) union B"),
        (_bin(Op.UNION, _bin(Op.ADD, a, b), c), "a + b union c"),
        (_bin(Op.ADD, _bin(Op.UNION, a, b), c), "(a union b) + c"),
        (_bin(Op.UNION, _neg(a), b), "-a union b"),
        (_neg(_bin(Op.UNION, a, b)), "-(a union b)"),
        (_bin(Op.EQUALS, _bin(Op.LT, a, b), _bin(Op.LT, c, d)), "a < b == c < d"),
        (_bin(Op.LT, _bin(Op.EQUALS, a, b), c), "(a == b) < c"),
        (_bin(Op.LT, a, _bin(Op.LT, b, c)), "a < (b < c)"),
        (_bin(Op.IN, _bin(Op.SUBSETS, a, b), c), "a subsets b in c"),
        (_bin(Op.EQUALS, a, _bin(Op.NOTEQUALS, b, c)), "a == (b != c)"),
        (_bin(Op.AND, _bin(Op.OR, a, b), c), "(a || b) && c"),
        (_bin(Op.OR, a, _bin(Op.AND, b, c)), "a || b && c"),
        (_bin(Op.AND, _bin(Op.EQUALS, a, b), c), "a == b && c"),
        (_bin(Op.EQUALS, _bin(Op.AND, a, b), c), "(a && b) == c"),
        (_bin(Op.EQUALS, _bin(Op.OR, a, b), c), "(a || b) == c"),
    ],
)
def test_print_round_trip(expr: frog_ast.Expression, text: str) -> None:
    assert str(expr) == text
    assert frog_parser.parse_expression(str(expr)) == expr


@pytest.mark.parametrize(
    "statement",
    [
        "BitString<8> r <- BitString<8> \\ (S \\ T);",
        "BitString<8> r <- BitString<8> \\ (S union T);",
        "r <- BitString<8> \\ (S \\ T);",
        "BitString<8> r <- BitString<8> \\ S;",
    ],
)
def test_sample_minus_exclusion_round_trips(statement: str) -> None:
    def parse(text: str) -> frog_ast.Statement:
        return frog_parser.parse_method(f"Void f() {{ {text} }}").block.statements[0]

    parsed = parse(statement)
    assert isinstance(parsed, frog_ast.UniqueSample)
    assert str(parsed) == statement
    assert parse(str(parsed)) == parsed


def test_sample_minus_exclusion_extends_over_union() -> None:
    # The statement splits at its last `\`; `union` stays in the exclusion.
    parsed = frog_parser.parse_method(
        "Void f() { BitString<8> r <- BitString<8> \\ S union T; }"
    ).block.statements[0]
    assert isinstance(parsed, frog_ast.UniqueSample)
    assert parsed.unique_set == _bin(Op.UNION, _var("S"), _var("T"))


def test_sample_minus_splits_at_the_last_backslash() -> None:
    parsed = frog_parser.parse_method(
        "Void f() { r <- T \\ S \\ U; }"
    ).block.statements[0]
    assert isinstance(parsed, frog_ast.UniqueSample)
    assert parsed.sampled_from == _bin(Op.SETMINUS, _var("T"), _var("S"))
    assert parsed.unique_set == _var("U")


_OPERATORS = [
    Op.ADD,
    Op.SUBTRACT,
    Op.MULTIPLY,
    Op.DIVIDE,
    Op.EXPONENTIATE,
    Op.UNION,
    Op.SETMINUS,
    Op.LT,
    Op.LEQ,
    Op.GT,
    Op.GEQ,
    Op.IN,
    Op.SUBSETS,
    Op.EQUALS,
    Op.NOTEQUALS,
    Op.AND,
    Op.OR,
]


def _random_expression(rng: random.Random, depth: int) -> frog_ast.Expression:
    if depth == 0 or rng.random() < 0.2:
        return _var(rng.choice("abcd"))
    roll = rng.random()
    if roll < 0.08:
        return _neg(_random_expression(rng, depth - 1))
    if roll < 0.12:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.NOT, _random_expression(rng, depth - 1)
        )
    return _bin(
        rng.choice(_OPERATORS),
        _random_expression(rng, depth - 1),
        _random_expression(rng, depth - 1),
    )


def test_random_expressions_round_trip() -> None:
    rng = random.Random(20261027)
    for _ in range(2000):
        expr = _random_expression(rng, 4)
        assert frog_parser.parse_expression(str(expr)) == expr, str(expr)
