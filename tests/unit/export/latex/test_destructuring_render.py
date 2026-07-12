"""Part 2: tuple-destructuring (no-desugar parse mode + DestructuringBinding render)."""

from pathlib import Path

from proof_frog import frog_ast, frog_parser
from proof_frog.export.latex import ir
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.stmt_renderer import StmtRenderer

REPO = Path(__file__).resolve().parents[4]
FIXTURE = str(REPO / "tests/unit/export/latex/fixtures/destructuring.game")


def _render_one(stmt: frog_ast.Statement) -> ir.Line:
    renderer = StmtRenderer(ExprRenderer(MacroRegistry()))
    [line] = renderer.render_block(frog_ast.Block([stmt]))
    return line


# the_type is not rendered (types are suppressed in bodies), so any Type works.
_TYPE = frog_ast.IntType()


def _left_statements(desugar: bool) -> list[frog_ast.Statement]:
    gf = frog_parser.parse_game_file(FIXTURE, desugar=desugar)
    return list(gf.games[0].methods[0].block.statements)


def test_no_desugar_keeps_destructuring_binding() -> None:
    stmts = _left_statements(desugar=False)
    kinds = [s for s in stmts if isinstance(s, frog_ast.DestructuringBinding)]
    assert len(kinds) == 2
    assign, sample = kinds
    assert assign.kind == "assign"
    assert assign.names == ["a", "b"]
    assert sample.kind == "sample"
    assert sample.names == ["u", "v"]
    # No desugared temporaries leaked into the body.
    assert not any(
        isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name.startswith("_tup")
        for s in stmts
    )


def test_default_still_desugars() -> None:
    stmts = _left_statements(desugar=True)
    assert not any(isinstance(s, frog_ast.DestructuringBinding) for s in stmts)
    assert any(
        isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name.startswith("_tup")
        for s in stmts
    )


def test_render_assign_destructuring() -> None:
    stmt = frog_ast.DestructuringBinding(
        _TYPE, ["a", "b"], frog_ast.Variable("E"), kind="assign"
    )
    line = _render_one(stmt)
    assert isinstance(line, ir.Assign)
    assert line.lhs == "(a, b)"
    assert line.rhs == "E"


def test_render_sample_destructuring() -> None:
    stmt = frog_ast.DestructuringBinding(
        _TYPE, ["a", "b"], frog_ast.Variable("E"), kind="sample"
    )
    line = _render_one(stmt)
    assert isinstance(line, ir.Sample)
    assert line.lhs == "(a, b)"
    assert line.rhs == "E"


def test_destructuring_names_are_subscripted() -> None:
    # Each LHS name must route through the expression renderer so it gets the
    # same subscripting as in expression position. `ss_T_e` must become a
    # single-level subscript with the tail segments comma-joined (`ss_{T,e}`),
    # never a raw double-underscore name that pdflatex rejects as a double
    # subscript.
    stmt = frog_ast.DestructuringBinding(
        _TYPE, ["ss_T_e", "ct1"], frog_ast.Variable("E"), kind="sample"
    )
    line = _render_one(stmt)
    assert isinstance(line, ir.Sample)
    # Multi-letter stems are one italic unit; the tail segments comma-join into a
    # single subscript group (never a stacked double subscript).
    assert line.lhs == r"(\mathit{ss}_{T,e}, \mathit{ct}_{1})"
    assert line.lhs.count("_{") == 2  # one subscript per name, no stacking


def test_render_sample_minus_destructuring() -> None:
    stmt = frog_ast.DestructuringBinding(
        _TYPE,
        ["a", "b"],
        frog_ast.Variable("E"),
        kind="sample_minus",
        exclusion=frog_ast.Variable("S"),
    )
    line = _render_one(stmt)
    assert isinstance(line, ir.Sample)
    assert line.lhs == "(a, b)"
    assert line.rhs == r"E \setminus S"
