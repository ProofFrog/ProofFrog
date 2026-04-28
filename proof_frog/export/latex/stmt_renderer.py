"""Render FrogLang ``Statement`` nodes to backend-neutral IR lines."""

from __future__ import annotations

from ... import frog_ast
from . import ir
from .expr_renderer import ExprRenderer


class StmtRenderer:
    """Walk a ``Block`` of FrogLang statements and produce a flat list of IR lines.

    Nested control flow (``if``/``for``) is flattened into ``If``/``Else``/
    ``EndIf`` and ``For``/``EndFor`` markers because the cryptocode backend
    has no nested-block notion — only begin/end markers.
    """

    def __init__(self, expr_renderer: ExprRenderer) -> None:
        self.expr = expr_renderer

    def render_block(self, block: frog_ast.Block) -> list[ir.Line]:
        out: list[ir.Line] = []
        for stmt in block.statements:
            self._render_stmt(stmt, out)
        return out

    # pylint: disable=too-many-branches
    def _render_stmt(self, stmt: frog_ast.Statement, out: list[ir.Line]) -> None:
        if isinstance(stmt, frog_ast.Assignment):
            out.append(
                ir.Assign(
                    lhs=self.expr.render(stmt.var),
                    rhs=self.expr.render(stmt.value),
                )
            )
            return
        if isinstance(stmt, frog_ast.VariableDeclaration):
            out.append(ir.Raw(latex=stmt.name))
            return
        if isinstance(stmt, frog_ast.Sample):
            out.append(
                ir.Sample(
                    lhs=self.expr.render(stmt.var),
                    rhs=self.expr.render(stmt.sampled_from),
                )
            )
            return
        if isinstance(stmt, frog_ast.UniqueSample):
            out.append(
                ir.Sample(
                    lhs=self.expr.render(stmt.var),
                    rhs=(
                        f"{self.expr.render(stmt.sampled_from)}"  # type: ignore[arg-type]
                        f" \\setminus {self.expr.render(stmt.unique_set)}"
                    ),
                )
            )
            return
        if isinstance(stmt, frog_ast.ReturnStatement):
            out.append(ir.Return(expr=self.expr.render(stmt.expression)))
            return
        if isinstance(stmt, frog_ast.IfStatement):
            self._render_if(stmt, out)
            return
        if isinstance(stmt, frog_ast.NumericFor):
            header = (
                f"{stmt.name} = {self.expr.render(stmt.start)} "
                f"\\dots {self.expr.render(stmt.end)}"
            )
            out.append(ir.For(header=header))
            for inner in stmt.block.statements:
                self._render_stmt(inner, out)
            out.append(ir.EndFor())
            return
        if isinstance(stmt, frog_ast.GenericFor):
            header = f"{stmt.var_name} \\in {self.expr.render(stmt.over)}"
            out.append(ir.For(header=header))
            for inner in stmt.block.statements:
                self._render_stmt(inner, out)
            out.append(ir.EndFor())
            return
        if isinstance(stmt, frog_ast.FuncCall):
            out.append(ir.Raw(latex=self.expr.render(stmt)))
            return
        out.append(ir.Raw(latex=f"% unsupported: {type(stmt).__name__}"))

    def _render_if(self, stmt: frog_ast.IfStatement, out: list[ir.Line]) -> None:
        for i, cond in enumerate(stmt.conditions):
            if i == 0:
                out.append(ir.If(cond=self.expr.render(cond)))
            else:
                out.append(ir.Else())
                out.append(ir.If(cond=self.expr.render(cond)))
            for inner in stmt.blocks[i].statements:
                self._render_stmt(inner, out)
        if len(stmt.blocks) > len(stmt.conditions):
            out.append(ir.Else())
            for inner in stmt.blocks[-1].statements:
                self._render_stmt(inner, out)
        out.append(ir.EndIf())
