"""Arithmetic precedence: ``+``/``-`` share one level, as do ``*``/``/``.

Both levels are left-associative, as in C, Java and Python, so
``a - b + c`` is ``(a - b) + c`` and ``a / b * c`` is ``(a / b) * c``.
This holds for expressions, for type-size integer expressions
(``BitString<n - m + 1>``) and for a proof's ``bound:`` clause. The AST
printer must parenthesize so that ``parse(str(e)) == e`` for every
arithmetic AST, since engine passes re-parse printed (SymPy) text.
"""

import random

import pytest

from proof_frog import frog_ast, frog_parser

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


@pytest.mark.parametrize(
    "source, expected",
    [
        # + and - share a level, left-associative.
        ("a - b + c", _bin(Op.ADD, _bin(Op.SUBTRACT, a, b), c)),
        ("a + b - c", _bin(Op.SUBTRACT, _bin(Op.ADD, a, b), c)),
        ("a - b - c", _bin(Op.SUBTRACT, _bin(Op.SUBTRACT, a, b), c)),
        (
            "a - b + c - d",
            _bin(Op.SUBTRACT, _bin(Op.ADD, _bin(Op.SUBTRACT, a, b), c), d),
        ),
        # * and / share a level, left-associative.
        ("a / b * c", _bin(Op.MULTIPLY, _bin(Op.DIVIDE, a, b), c)),
        ("a * b / c", _bin(Op.DIVIDE, _bin(Op.MULTIPLY, a, b), c)),
        ("a / b / c", _bin(Op.DIVIDE, _bin(Op.DIVIDE, a, b), c)),
        # Mixed levels are unchanged: * and / bind tighter than + and -.
        ("a + b * c", _bin(Op.ADD, a, _bin(Op.MULTIPLY, b, c))),
        ("a * b + c", _bin(Op.ADD, _bin(Op.MULTIPLY, a, b), c)),
        ("a - b / c", _bin(Op.SUBTRACT, a, _bin(Op.DIVIDE, b, c))),
        (
            "a - b * c / d",
            _bin(Op.SUBTRACT, a, _bin(Op.DIVIDE, _bin(Op.MULTIPLY, b, c), d)),
        ),
        ("a * b ^ c", _bin(Op.MULTIPLY, a, _bin(Op.EXPONENTIATE, b, c))),
        # Explicit parentheses still win.
        ("a - (b + c)", _bin(Op.SUBTRACT, a, _bin(Op.ADD, b, c))),
        ("a / (b * c)", _bin(Op.DIVIDE, a, _bin(Op.MULTIPLY, b, c))),
        # Unary minus sits between the two levels (position unchanged).
        ("-a + b", _bin(Op.ADD, _neg(a), b)),
        ("-a * b", _neg(_bin(Op.MULTIPLY, a, b))),
    ],
)
def test_expression_parse(source: str, expected: frog_ast.Expression) -> None:
    assert frog_parser.parse_expression(source) == expected


def test_comparison_operand_keeps_left_associative_sum() -> None:
    expr = frog_parser.parse_expression("a - b + c == d")
    assert expr == _bin(Op.EQUALS, _bin(Op.ADD, _bin(Op.SUBTRACT, a, b), c), d)


def _field_type(type_text: str) -> frog_ast.Type:
    game = frog_parser.parse_game(
        f"Game G(Int n, Int m) {{ {type_text} x; Void Initialize() {{ }} }}"
    )
    return game.fields[0].type


n, m = _var("n"), _var("m")
one, two = frog_ast.Integer(1), frog_ast.Integer(2)


@pytest.mark.parametrize(
    "type_text, expected_size",
    [
        ("BitString<n - m + 1>", _bin(Op.ADD, _bin(Op.SUBTRACT, n, m), one)),
        ("BitString<n / 2 * m>", _bin(Op.MULTIPLY, _bin(Op.DIVIDE, n, two), m)),
        ("BitString<n + 2 * m>", _bin(Op.ADD, n, _bin(Op.MULTIPLY, two, m))),
    ],
)
def test_integer_expression_in_type(
    type_text: str, expected_size: frog_ast.Expression
) -> None:
    field_type = _field_type(type_text)
    assert isinstance(field_type, frog_ast.BitStringType)
    assert field_type.parameterization == expected_size


def _claimed_bound(bound: str) -> frog_ast.Expression:
    proof = frog_parser.parse_proof_file(
        "proof:\n"
        "theorem:\n"
        "  Foo(E);\n"
        f"bound:\n  {bound};\n"
        "games:\n"
        "  Foo(E).Left against Foo(E).Adversary;\n"
    )
    assert proof.claimed_bound is not None
    return proof.claimed_bound.bound


@pytest.mark.parametrize(
    "bound, expected",
    [
        ("a - b + c", _bin(Op.ADD, _bin(Op.SUBTRACT, a, b), c)),
        ("a / b * c", _bin(Op.MULTIPLY, _bin(Op.DIVIDE, a, b), c)),
        ("a + b * c", _bin(Op.ADD, a, _bin(Op.MULTIPLY, b, c))),
        ("-a + b", _bin(Op.ADD, _neg(a), b)),
    ],
)
def test_claimed_bound_parse(bound: str, expected: frog_ast.Expression) -> None:
    assert _claimed_bound(bound) == expected


@pytest.mark.parametrize(
    "expr, text",
    [
        (_bin(Op.SUBTRACT, a, _bin(Op.ADD, b, c)), "a - (b + c)"),
        (_bin(Op.SUBTRACT, a, _bin(Op.SUBTRACT, b, c)), "a - (b - c)"),
        (_bin(Op.ADD, _bin(Op.SUBTRACT, a, b), c), "a - b + c"),
        (_bin(Op.DIVIDE, a, _bin(Op.MULTIPLY, b, c)), "a / (b * c)"),
        (_bin(Op.MULTIPLY, a, _bin(Op.DIVIDE, b, c)), "a * (b / c)"),
        (_bin(Op.MULTIPLY, _bin(Op.DIVIDE, a, b), c), "a / b * c"),
        (_bin(Op.MULTIPLY, _bin(Op.ADD, a, b), c), "(a + b) * c"),
        # Unary minus binds looser than *, / and ^ but tighter than + and -.
        (_neg(_bin(Op.ADD, a, b)), "-(a + b)"),
        (_neg(_bin(Op.MULTIPLY, a, b)), "-a * b"),
        (_bin(Op.MULTIPLY, _neg(a), b), "(-a) * b"),
        (_bin(Op.DIVIDE, _neg(a), b), "(-a) / b"),
        (_bin(Op.EXPONENTIATE, _neg(a), frog_ast.Integer(2)), "(-a) ^ 2"),
        (_bin(Op.MULTIPLY, _bin(Op.MULTIPLY, a, _neg(b)), c), "a * (-b) * c"),
        (_bin(Op.ADD, _neg(a), b), "-a + b"),
        (_bin(Op.SUBTRACT, a, _neg(b)), "a - -b"),
    ],
)
def test_print_round_trip(expr: frog_ast.Expression, text: str) -> None:
    assert str(expr) == text
    assert frog_parser.parse_expression(str(expr)) == expr


_ARITHMETIC = [Op.ADD, Op.SUBTRACT, Op.MULTIPLY, Op.DIVIDE, Op.EXPONENTIATE]


def _random_arithmetic(rng: random.Random, depth: int) -> frog_ast.Expression:
    if depth == 0 or rng.random() < 0.25:
        return _var(rng.choice("abcd"))
    if rng.random() < 0.15:
        return _neg(_random_arithmetic(rng, depth - 1))
    return _bin(
        rng.choice(_ARITHMETIC),
        _random_arithmetic(rng, depth - 1),
        _random_arithmetic(rng, depth - 1),
    )


def test_random_arithmetic_round_trips() -> None:
    rng = random.Random(20261027)
    for _ in range(1000):
        expr = _random_arithmetic(rng, 4)
        assert frog_parser.parse_expression(str(expr)) == expr, str(expr)
