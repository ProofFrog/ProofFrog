"""Render FrogLang ``Type`` AST nodes to LaTeX math."""

from __future__ import annotations

from ... import frog_ast
from .expr_renderer import ExprRenderer


class TypeRenderer:
    """Render ``frog_ast.Type`` nodes to LaTeX math strings."""

    def __init__(self, expr: ExprRenderer) -> None:
        self.expr = expr

    # pylint: disable=too-many-return-statements,too-many-branches
    def render(self, t: frog_ast.Type) -> str:
        if isinstance(t, frog_ast.IntType):
            return r"\mathbb{Z}"
        if isinstance(t, frog_ast.BoolType):
            return r"\{0,1\}"
        if isinstance(t, frog_ast.Void):
            return r"\bot"
        if isinstance(t, frog_ast.BitStringType):
            if t.parameterization is None:
                return r"\{0,1\}^{*}"
            return rf"\{{0,1\}}^{{{self.expr.render(t.parameterization)}}}"
        if isinstance(t, frog_ast.SetType):
            if t.parameterization is None:
                return r"\mathsf{Set}"
            return rf"\mathsf{{Set}}({self.render(t.parameterization)})"
        if isinstance(t, frog_ast.ArrayType):
            return rf"{self.render(t.element_type)}^{{{self.expr.render(t.count)}}}"
        if isinstance(t, frog_ast.MapType):
            return rf"{self.render(t.key_type)} \to {self.render(t.value_type)}"
        if isinstance(t, frog_ast.ModIntType):
            return rf"\mathbb{{Z}}_{{{self.expr.render(t.modulus)}}}"
        if isinstance(t, frog_ast.GroupType):
            return r"\mathsf{Group}"
        if isinstance(t, frog_ast.GroupElemType):
            return rf"{self.expr.render(t.group)}"
        if isinstance(t, frog_ast.ProductType):
            inner = r" \times ".join(self.render(s) for s in t.types)
            return inner
        if isinstance(t, frog_ast.FunctionType):
            return rf"{self.render(t.domain_type)} \to {self.render(t.range_type)}"
        if isinstance(t, frog_ast.OptionalType):
            return rf"{self.render(t.the_type)}^{{?}}"
        if isinstance(t, frog_ast.Variable):
            return self.expr.render(t)
        if isinstance(t, frog_ast.FieldAccess):
            return self.expr.render(t)
        return f"% unsupported type: {type(t).__name__}"
