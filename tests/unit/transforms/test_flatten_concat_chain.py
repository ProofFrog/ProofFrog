"""Tests for FlattenConcatChain.

Verifies that ``a || (b || c)`` is rewritten to the left-associative
``(a || b) || c`` form, applied recursively. The pass operates on the
``||`` operator, which in FrogLang is overloaded between Boolean OR and
BitString concatenation; both readings are associative, so the rewrite
is semantics-preserving.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import FlattenConcatChain
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return FlattenConcatChain().apply(game, _ctx())


def _return_expr(game: frog_ast.Game) -> frog_ast.Expression:
    method = game.methods[0]
    last = method.block.statements[-1]
    assert isinstance(last, frog_ast.ReturnStatement)
    return last.expression


def _is_left_assoc_chain(
    expr: frog_ast.Expression, op: frog_ast.BinaryOperators
) -> bool:
    """True if *expr* is left-associative under *op* (no right-nested op)."""
    cur = expr
    while isinstance(cur, frog_ast.BinaryOperation) and cur.operator == op:
        if (
            isinstance(cur.right_expression, frog_ast.BinaryOperation)
            and cur.right_expression.operator == op
        ):
            return False
        cur = cur.left_expression
    return True


def test_shallow_right_grouped_concat_flattens() -> None:
    source = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        BitString<3*n> F() {
            return a || (b || c);
        }
    }
    """
    out = _apply(source)
    expr = _return_expr(out)
    expected_source = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        BitString<3*n> F() {
            return (a || b) || c;
        }
    }
    """
    expected = _return_expr(frog_parser.parse_game(expected_source))
    assert expr == expected


def test_deeply_nested_right_grouped_concat_flattens() -> None:
    source = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        BitString<n> d;
        BitString<4*n> F() {
            return a || (b || (c || d));
        }
    }
    """
    out = _apply(source)
    expr = _return_expr(out)
    assert _is_left_assoc_chain(expr, frog_ast.BinaryOperators.OR)
    # Verify both right-nested and a different starting shape converge.
    source2 = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        BitString<n> d;
        BitString<4*n> F() {
            return (a || b) || (c || d);
        }
    }
    """
    out2 = _apply(source2)
    assert _return_expr(out2) == expr


def test_already_left_associated_chain_unchanged() -> None:
    source = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        BitString<3*n> F() {
            return (a || b) || c;
        }
    }
    """
    parsed = frog_parser.parse_game(source)
    out = FlattenConcatChain().apply(parsed, _ctx())
    assert out == parsed


def test_concat_inside_funccall_arg_flattens() -> None:
    source = """
    Game G(Int n) {
        BitString<n> a;
        BitString<n> b;
        BitString<n> c;
        Bool F() {
            return H.evaluate(a || (b || c)) == H.evaluate((a || b) || c);
        }
    }
    """
    out = _apply(source)
    method = out.methods[0]
    last = method.block.statements[-1]
    assert isinstance(last, frog_ast.ReturnStatement)
    cmp_expr = last.expression
    assert isinstance(cmp_expr, frog_ast.BinaryOperation)
    left = cmp_expr.left_expression
    right = cmp_expr.right_expression
    assert isinstance(left, frog_ast.FuncCall)
    assert isinstance(right, frog_ast.FuncCall)
    # Both H.evaluate args should now be structurally identical (left-assoc).
    assert left.args[0] == right.args[0]


def test_boolean_or_chain_also_left_associates() -> None:
    # Boolean OR is associative; left-associating is semantics-preserving.
    source = """
    Game G() {
        Bool a;
        Bool b;
        Bool c;
        Bool F() {
            return a || (b || c);
        }
    }
    """
    out = _apply(source)
    expr = _return_expr(out)
    assert _is_left_assoc_chain(expr, frog_ast.BinaryOperators.OR)


def test_non_or_binary_op_untouched() -> None:
    # AND chains should not be rewritten by this pass.
    source = """
    Game G() {
        Bool a;
        Bool b;
        Bool c;
        Bool F() {
            return a && (b && c);
        }
    }
    """
    parsed = frog_parser.parse_game(source)
    out = FlattenConcatChain().apply(parsed, _ctx())
    assert out == parsed
