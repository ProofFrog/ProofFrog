"""Render FrogLang ``Statement`` nodes to backend-neutral IR lines."""

from __future__ import annotations

from ... import frog_ast
from . import ir
from .expr_renderer import ExprRenderer

# Boolean-valued (predicate) operators. A ``return`` of such an expression in a
# ``Bool``-returning method is wrapped in an Iverson bracket (``\llbracket ...
# \rrbracket``) so ``return A == B`` reads as ``[[A = B]]`` -- a 0/1-valued
# predicate -- rather than a bare relation. ``||`` (OR) is included because the
# ``Bool`` return-type gate already excludes the BitString-concatenation
# overload of the same operator.
_PREDICATE_BINOPS = frozenset(
    {
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.BinaryOperators.NOTEQUALS,
        frog_ast.BinaryOperators.GT,
        frog_ast.BinaryOperators.LT,
        frog_ast.BinaryOperators.GEQ,
        frog_ast.BinaryOperators.LEQ,
        frog_ast.BinaryOperators.AND,
        frog_ast.BinaryOperators.OR,
        frog_ast.BinaryOperators.IN,
        frog_ast.BinaryOperators.SUBSETS,
    }
)


def _is_predicate(expr: frog_ast.Expression) -> bool:
    """Whether ``expr`` is a boolean relation/combination worth Iverson-bracketing.

    Bare booleans (a variable, ``true``/``false``) are excluded -- only actual
    relations (``==``, ``<``, ...), logical combinations (``&&``, ``||``), set
    membership (``in``, ``subsets``), and negation (``!``) are wrapped.
    """
    if isinstance(expr, frog_ast.BinaryOperation):
        return expr.operator in _PREDICATE_BINOPS
    if isinstance(expr, frog_ast.UnaryOperation):
        return expr.operator == frog_ast.UnaryOperators.NOT
    return False


class StmtRenderer:
    """Walk a ``Block`` of FrogLang statements and produce a flat list of IR lines.

    Nested control flow (``if``/``for``) is flattened into ``If``/``Else``/
    ``EndIf`` and ``For``/``EndFor`` markers because the cryptocode backend
    has no nested-block notion — only begin/end markers.
    """

    def __init__(self, expr_renderer: ExprRenderer) -> None:
        self.expr = expr_renderer
        # Return type of the method currently being rendered, set by the module
        # renderer. Used to disambiguate an overloaded ``||`` / ``+`` in a
        # ``return`` expression as concat/XOR when the method returns a
        # BitString.
        self.return_type: frog_ast.Type | None = None
        # Current control-flow nesting depth. Stamped onto each emitted line so
        # backends can indent guarded bodies one level deeper than their
        # markers (A3).
        self._depth = 0

    def _emit(self, out: list[ir.Line], line: ir.Line) -> None:
        """Append ``line`` stamped with the current nesting depth."""
        line.depth = self._depth
        out.append(line)

    def render_block(self, block: frog_ast.Block) -> list[ir.Line]:
        self._depth = 0
        out: list[ir.Line] = []
        for stmt in block.statements:
            self._render_stmt(stmt, out)
        return out

    # pylint: disable=too-many-branches
    def _render_stmt(self, stmt: frog_ast.Statement, out: list[ir.Line]) -> None:
        if isinstance(stmt, frog_ast.Assignment):
            if isinstance(stmt.the_type, frog_ast.BitStringType):
                self.expr.note_bitstring_context(stmt.value)
            self._emit(
                out,
                ir.Assign(
                    lhs=self.expr.render(stmt.var),
                    rhs=self.expr.render(stmt.value),
                ),
            )
            return
        if isinstance(stmt, frog_ast.VariableDeclaration):
            # An uninitialized declaration (`Foo x;`) has no value, and types
            # are suppressed in bodies, so a bare name line would be
            # meaningless. Drop it; a later assignment introduces the name.
            return
        if isinstance(stmt, frog_ast.DestructuringBinding):
            self._render_destructuring(stmt, out)
            return
        if isinstance(stmt, frog_ast.Sample):
            self._emit(
                out,
                ir.Sample(
                    lhs=self.expr.render(stmt.var),
                    rhs=self.expr.render(stmt.sampled_from),
                ),
            )
            return
        if isinstance(stmt, frog_ast.UniqueSample):
            self._emit(
                out,
                ir.Sample(
                    lhs=self.expr.render(stmt.var),
                    rhs=(
                        f"{self.expr.render(stmt.sampled_from)}"  # type: ignore[arg-type]
                        f" \\setminus {self.expr.render(stmt.unique_set)}"
                    ),
                ),
            )
            return
        if isinstance(stmt, frog_ast.ReturnStatement):
            if isinstance(self.return_type, frog_ast.BitStringType):
                self.expr.note_bitstring_context(stmt.expression)
            rendered = self.expr.render(stmt.expression)
            # A predicate returned from a Bool-typed method is an Iverson
            # bracket: `return A == B` -> `\llbracket A = B \rrbracket`. Gating
            # on Bool keeps the concat overload of `||` (BitString return)
            # untouched.
            if isinstance(self.return_type, frog_ast.BoolType) and _is_predicate(
                stmt.expression
            ):
                rendered = rf"\llbracket {rendered} \rrbracket"
            self._emit(out, ir.Return(expr=rendered))
            return
        if isinstance(stmt, frog_ast.IfStatement):
            self._render_if(stmt, out)
            return
        if isinstance(stmt, frog_ast.NumericFor):
            header = (
                f"{stmt.name} = {self.expr.render(stmt.start)} "
                f"\\dots {self.expr.render(stmt.end)}"
            )
            self._emit(out, ir.For(header=header))
            self._depth += 1
            for inner in stmt.block.statements:
                self._render_stmt(inner, out)
            self._depth -= 1
            self._emit(out, ir.EndFor())
            return
        if isinstance(stmt, frog_ast.GenericFor):
            header = f"{stmt.var_name} \\in {self.expr.render(stmt.over)}"
            self._emit(out, ir.For(header=header))
            self._depth += 1
            for inner in stmt.block.statements:
                self._render_stmt(inner, out)
            self._depth -= 1
            self._emit(out, ir.EndFor())
            return
        if isinstance(stmt, frog_ast.FuncCall):
            self._emit(out, ir.Raw(latex=self.expr.render(stmt)))
            return
        self._emit(out, ir.Raw(latex=f"% unsupported: {type(stmt).__name__}"))

    def _render_destructuring(
        self, stmt: frog_ast.DestructuringBinding, out: list[ir.Line]
    ) -> None:
        """Render a tuple-destructuring binding as a single tuple-LHS line.

        Only reached when the file was parsed with ``desugar=False`` (the LaTeX
        export path); otherwise the parser has already rewritten the node into
        temp+index reads.
        """
        # Route each name through the expression renderer so destructuring-LHS
        # names get the same subscripting as in expression position (a raw
        # `ss_T_e` would be a pdflatex double subscript).
        names = ", ".join(
            self.expr.render(frog_ast.Variable(name)) for name in stmt.names
        )
        lhs = f"({names})"
        rhs = self.expr.render(stmt.value)
        if stmt.kind == "assign":
            self._emit(out, ir.Assign(lhs=lhs, rhs=rhs))
            return
        if stmt.kind == "sample_minus":
            rhs = f"{rhs} \\setminus {self.expr.render(stmt.exclusion)}"  # type: ignore[arg-type]
        self._emit(out, ir.Sample(lhs=lhs, rhs=rhs))

    def _render_if(self, stmt: frog_ast.IfStatement, out: list[ir.Line]) -> None:
        # Markers (If/Else/EndIf) sit at the enclosing depth; the guarded body
        # statements between them are rendered one level deeper.
        def render_body(block: frog_ast.Block) -> None:
            self._depth += 1
            for inner in block.statements:
                self._render_stmt(inner, out)
            self._depth -= 1

        for i, cond in enumerate(stmt.conditions):
            if i == 0:
                self._emit(out, ir.If(cond=self.expr.render(cond)))
            else:
                self._emit(out, ir.Else())
                self._emit(out, ir.If(cond=self.expr.render(cond)))
            render_body(stmt.blocks[i])
        if len(stmt.blocks) > len(stmt.conditions):
            self._emit(out, ir.Else())
            render_body(stmt.blocks[-1])
        self._emit(out, ir.EndIf())
