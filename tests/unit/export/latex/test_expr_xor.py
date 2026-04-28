from proof_frog import frog_ast
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry


def test_plus_on_bitstring_renders_oplus() -> None:
    a = frog_ast.Variable(name="a")
    b = frog_ast.Variable(name="b")
    expr = frog_ast.BinaryOperation(
        operator=frog_ast.BinaryOperators.ADD,
        left_expression=a,
        right_expression=b,
    )
    type_of = {id(a): frog_ast.BitStringType()}
    r = ExprRenderer(MacroRegistry(), type_of=type_of)
    assert r.render(expr) == r"a \oplus b"


def test_plus_without_type_info_stays_plus() -> None:
    a = frog_ast.Variable(name="a")
    b = frog_ast.Variable(name="b")
    expr = frog_ast.BinaryOperation(
        operator=frog_ast.BinaryOperators.ADD,
        left_expression=a,
        right_expression=b,
    )
    r = ExprRenderer(MacroRegistry())
    assert r.render(expr) == "a + b"
