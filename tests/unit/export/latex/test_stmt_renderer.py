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


def test_variable_declaration_emits_no_line() -> None:
    # An uninitialized declaration (`Foo x;`) has no value, and types are
    # suppressed in bodies, so a bare name line is never correct -- drop it.
    s = frog_ast.VariableDeclaration(frog_ast.IntType(), "x")
    assert _renderer().render_block(_block([s])) == []


def test_variable_declaration_dropped_between_statements() -> None:
    decl = frog_ast.VariableDeclaration(frog_ast.IntType(), "x")
    asgn = frog_ast.Assignment(None, frog_ast.Variable("x"), frog_ast.Integer(1))
    lines = _renderer().render_block(_block([decl, asgn]))
    assert len(lines) == 1
    assert isinstance(lines[0], ir.Assign)


def test_sample_emits_sample() -> None:
    s = frog_ast.Sample(None, frog_ast.Variable("r"), frog_ast.Variable("BitString"))
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Sample)
    assert line.lhs == "r"


def test_return_emits_return() -> None:
    s = frog_ast.ReturnStatement(frog_ast.Variable("x"))
    [line] = _renderer().render_block(_block([s]))
    assert isinstance(line, ir.Return)
    assert line.expr == "x"


def _eq(left: str, right: str) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable(left),
        frog_ast.Variable(right),
    )


def test_bool_return_equality_is_iverson_bracketed() -> None:
    # `return A == B` in a Bool method reads as a 0/1 predicate.
    r = _renderer()
    r.return_type = frog_ast.BoolType()
    [line] = r.render_block(_block([frog_ast.ReturnStatement(_eq("A", "B"))]))
    assert isinstance(line, ir.Return)
    assert line.expr == r"\llbracket A = B \rrbracket"


def test_bool_return_negation_is_iverson_bracketed() -> None:
    r = _renderer()
    r.return_type = frog_ast.BoolType()
    neg = frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, frog_ast.Variable("b"))
    [line] = r.render_block(_block([frog_ast.ReturnStatement(neg)]))
    assert line.expr == r"\llbracket \neg b \rrbracket"


def test_bool_return_bare_boolean_is_not_bracketed() -> None:
    # `return false;` is not a relation, so it stays a bare literal.
    r = _renderer()
    r.return_type = frog_ast.BoolType()
    [line] = r.render_block(_block([frog_ast.ReturnStatement(frog_ast.Boolean(False))]))
    assert line.expr == r"\mathsf{false}"


def test_bool_return_bare_variable_is_not_bracketed() -> None:
    r = _renderer()
    r.return_type = frog_ast.BoolType()
    [line] = r.render_block(_block([frog_ast.ReturnStatement(frog_ast.Variable("b"))]))
    assert line.expr == "b"


def test_non_bool_return_equality_is_not_bracketed() -> None:
    # Without a Bool return type we do not know the expression is a predicate,
    # so no Iverson bracket is applied.
    r = _renderer()
    r.return_type = None
    [line] = r.render_block(_block([frog_ast.ReturnStatement(_eq("A", "B"))]))
    assert line.expr == "A = B"


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


def test_if_body_is_indented_one_level_deeper_than_markers() -> None:
    # The guarded body of an `if` must sit one nesting level deeper than the
    # If/Else/EndIf markers so the structure is visible (A3). The markers stay
    # at the outer depth.
    cond = frog_ast.Variable("b")
    then_blk = _block([frog_ast.ReturnStatement(frog_ast.Integer(1))])
    else_blk = _block([frog_ast.ReturnStatement(frog_ast.Integer(0))])
    s = frog_ast.IfStatement([cond], [then_blk, else_blk])
    lines = _renderer().render_block(_block([s]))
    depths = [(type(ln).__name__, ln.depth) for ln in lines]
    assert depths == [
        ("If", 0),
        ("Return", 1),
        ("Else", 0),
        ("Return", 1),
        ("EndIf", 0),
    ]


def test_for_body_is_indented_one_level_deeper() -> None:
    body = _block([frog_ast.ReturnStatement(frog_ast.Variable("i"))])
    s = frog_ast.NumericFor("i", frog_ast.Integer(0), frog_ast.Integer(5), body)
    lines = _renderer().render_block(_block([s]))
    depths = [(type(ln).__name__, ln.depth) for ln in lines]
    assert depths == [("For", 0), ("Return", 1), ("EndFor", 0)]


def test_nested_if_inside_for_stacks_depth() -> None:
    inner_if = frog_ast.IfStatement(
        [frog_ast.Variable("b")], [_block([frog_ast.ReturnStatement(frog_ast.Integer(1))])]
    )
    body = _block([inner_if])
    s = frog_ast.NumericFor("i", frog_ast.Integer(0), frog_ast.Integer(5), body)
    lines = _renderer().render_block(_block([s]))
    depths = [(type(ln).__name__, ln.depth) for ln in lines]
    assert depths == [
        ("For", 0),
        ("If", 1),
        ("Return", 2),
        ("EndIf", 1),
        ("EndFor", 0),
    ]


def test_top_level_statements_have_depth_zero() -> None:
    s = frog_ast.ReturnStatement(frog_ast.Variable("x"))
    [line] = _renderer().render_block(_block([s]))
    assert line.depth == 0
