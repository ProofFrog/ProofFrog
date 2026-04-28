from proof_frog import frog_ast
from proof_frog.export.latex import ir
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.stmt_renderer import StmtRenderer


def _renderer() -> StmtRenderer:
    return StmtRenderer(ExprRenderer(MacroRegistry()))


def _block(stmts: list[frog_ast.Statement]) -> frog_ast.Block:
    return frog_ast.Block(stmts)


def test_assignment_emits_assign() -> None:
    s = frog_ast.Assignment(None, frog_ast.Variable("c"), frog_ast.Variable("m"))
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Assign)
    assert line.lhs == "c"
    assert line.rhs == "m"


def test_variable_declaration_emits_assign_dropping_type() -> None:
    s = frog_ast.VariableDeclaration(frog_ast.IntType(), "x")
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Raw)


def test_sample_emits_sample() -> None:
    s = frog_ast.Sample(
        None, frog_ast.Variable("r"), frog_ast.Variable("BitString")
    )
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Sample)
    assert line.lhs == "r"


def test_return_emits_return() -> None:
    s = frog_ast.ReturnStatement(frog_ast.Variable("x"))
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Return)
    assert line.expr == "x"


def test_if_emits_if_else_endif() -> None:
    cond = frog_ast.Variable("b")
    then_blk = _block([frog_ast.ReturnStatement(frog_ast.Integer(1))])
    else_blk = _block([frog_ast.ReturnStatement(frog_ast.Integer(0))])
    s = frog_ast.IfStatement([cond], [then_blk, else_blk])
    lines = _renderer().render_block(_block([s]))
    kinds = [type(ln).__name__ for ln in lines]
    assert kinds == ["If", "Return", "Else", "Return", "EndIf"]


def test_numeric_for_emits_for_endfor() -> None:
    body = _block([frog_ast.ReturnStatement(frog_ast.Variable("i"))])
    s = frog_ast.NumericFor("i", frog_ast.Integer(0), frog_ast.Integer(5), body)
    lines = _renderer().render_block(_block([s]))
    kinds = [type(ln).__name__ for ln in lines]
    assert kinds == ["For", "Return", "EndFor"]


def test_funccall_statement_emits_raw() -> None:
    s = frog_ast.FuncCall(frog_ast.Variable("Foo"), [frog_ast.Variable("x")])
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Raw)
    assert r"\Foo(x)" in line.latex
