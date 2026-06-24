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


def _concat_chain() -> frog_ast.BinaryOperation:
    # f(x) || y || g(z) -- operands whose types the per-operand resolver
    # cannot recover (method calls, untyped vars). Defaults to logical-or.
    fx = frog_ast.FuncCall(frog_ast.Variable("f"), [frog_ast.Variable("x")])
    gz = frog_ast.FuncCall(frog_ast.Variable("g"), [frog_ast.Variable("z")])
    inner = frog_ast.BinaryOperation(
        operator=frog_ast.BinaryOperators.OR,
        left_expression=fx,
        right_expression=frog_ast.Variable("y"),
    )
    return frog_ast.BinaryOperation(
        operator=frog_ast.BinaryOperators.OR,
        left_expression=inner,
        right_expression=gz,
    )


def test_overloaded_or_defaults_to_logical_or() -> None:
    r = ExprRenderer(MacroRegistry())
    assert r"\lor" in r.render(_concat_chain())
    assert r"\|" not in r.render(_concat_chain())


def test_bitstring_context_renders_concatenation() -> None:
    # When the chain is marked as BitString context, every overloaded `||`
    # node -- including the ones over method-call operands -- renders concat.
    chain = _concat_chain()
    r = ExprRenderer(MacroRegistry())
    r.note_bitstring_context(chain)
    out = r.render(chain)
    assert out.count(r"\|") == 2
    assert r"\lor" not in out
