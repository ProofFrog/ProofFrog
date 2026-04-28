"""Render FrogLang ``Expression`` AST nodes to LaTeX math.

The renderer is backend-independent. It produces strings suitable for
embedding inside math mode (``$...$``) — the surrounding delimiters are
the caller's responsibility.

Optional ``type_of`` map keyed by ``id(node)`` lets the proof-level
orchestrator inform XOR rendering: a ``+`` whose operand has
``BitStringType`` becomes ``\\oplus``. Without type info we default to
``+``.
"""

from __future__ import annotations

import re

from ... import frog_ast
from .macros import MacroRegistry

_BINOP_LATEX: dict[frog_ast.BinaryOperators, str] = {
    frog_ast.BinaryOperators.EQUALS: "=",
    frog_ast.BinaryOperators.NOTEQUALS: r"\ne",
    frog_ast.BinaryOperators.GT: ">",
    frog_ast.BinaryOperators.LT: "<",
    frog_ast.BinaryOperators.GEQ: r"\ge",
    frog_ast.BinaryOperators.LEQ: r"\le",
    frog_ast.BinaryOperators.AND: r"\land",
    frog_ast.BinaryOperators.OR: r"\lor",
    frog_ast.BinaryOperators.IN: r"\in",
    frog_ast.BinaryOperators.SUBSETS: r"\subseteq",
    frog_ast.BinaryOperators.UNION: r"\cup",
    frog_ast.BinaryOperators.SETMINUS: r"\setminus",
    frog_ast.BinaryOperators.SUBTRACT: "-",
    frog_ast.BinaryOperators.MULTIPLY: r"\cdot",
    frog_ast.BinaryOperators.DIVIDE: "/",
    frog_ast.BinaryOperators.EXPONENTIATE: "^",
}

_KEYWORD_VARIABLES = {"lambda": r"\lambda"}

_SUBSCRIPT_RE = re.compile(r"^(.+?)(\d+)$")


def _looks_like_algorithm_name(name: str) -> bool:
    if not name:
        return False
    return name[0].isupper() or name.isupper()


class ExprRenderer:
    """Render ``frog_ast.Expression`` nodes to LaTeX math strings."""

    def __init__(
        self,
        macros: MacroRegistry,
        type_of: dict[int, frog_ast.Type] | None = None,
    ) -> None:
        self.macros = macros
        self.type_of = type_of or {}

    def render(self, expr: frog_ast.Expression) -> str:
        return self._render(expr)

    # pylint: disable=too-many-return-statements,too-many-branches
    def _render(self, expr: frog_ast.Expression) -> str:
        if isinstance(expr, frog_ast.Variable):
            return self._render_variable(expr.name)
        if isinstance(expr, frog_ast.Integer):
            return str(expr.num)
        if isinstance(expr, frog_ast.Boolean):
            return r"\mathsf{true}" if expr.bool else r"\mathsf{false}"
        if isinstance(expr, frog_ast.NoneExpression):
            return r"\bot"
        if isinstance(expr, frog_ast.BinaryNum):
            return "0b" + format(expr.num, f"0{expr.length}b")
        if isinstance(expr, frog_ast.BitStringLiteral):
            return f"{expr.bit}^{{{self._render(expr.length)}}}"
        if isinstance(expr, frog_ast.GroupGenerator):
            return "g"
        if isinstance(expr, frog_ast.GroupOrder):
            return "q"
        if isinstance(expr, frog_ast.BinaryOperation):
            return self._render_binop(expr)
        if isinstance(expr, frog_ast.UnaryOperation):
            return self._render_unop(expr)
        if isinstance(expr, frog_ast.FuncCall):
            return self._render_call(expr)
        if isinstance(expr, frog_ast.FieldAccess):
            return self._render_field(expr)
        if isinstance(expr, frog_ast.ArrayAccess):
            return f"{self._render(expr.the_array)}[{self._render(expr.index)}]"
        if isinstance(expr, frog_ast.Slice):
            return (
                f"{self._render(expr.the_array)}["
                f"{self._render(expr.start)} : {self._render(expr.end)}]"
            )
        if isinstance(expr, frog_ast.Set):
            inner = ", ".join(self._render(e) for e in expr.elements)
            return f"\\{{{inner}\\}}"
        if isinstance(expr, frog_ast.Tuple):
            inner = ", ".join(self._render(v) for v in expr.values)
            return f"({inner})"
        # Unknown node: defer to repr-like fallback.
        return f"% unsupported: {type(expr).__name__}"

    def _render_variable(self, name: str) -> str:
        if name in _KEYWORD_VARIABLES:
            return _KEYWORD_VARIABLES[name]
        if "_" in name:
            base, _, sub = name.rpartition("_")
            if base and sub:
                return f"{self._render_variable(base)}_{{{sub}}}"
        m = _SUBSCRIPT_RE.match(name)
        if m:
            return f"{self._render_variable(m.group(1))}_{{{m.group(2)}}}"
        return name

    def _render_binop(self, expr: frog_ast.BinaryOperation) -> str:
        left = self._render(expr.left_expression)
        right = self._render(expr.right_expression)
        op = expr.operator
        if op == frog_ast.BinaryOperators.ADD:
            sym = "+"
            left_t = self.type_of.get(id(expr.left_expression))
            right_t = self.type_of.get(id(expr.right_expression))
            if isinstance(left_t, frog_ast.BitStringType) or isinstance(
                right_t, frog_ast.BitStringType
            ):
                sym = r"\oplus"
            return f"{left} {sym} {right}"
        return f"{left} {_BINOP_LATEX[op]} {right}"

    def _render_unop(self, expr: frog_ast.UnaryOperation) -> str:
        inner = self._render(expr.expression)
        if expr.operator == frog_ast.UnaryOperators.NOT:
            return rf"\neg {inner}"
        if expr.operator == frog_ast.UnaryOperators.SIZE:
            return f"|{inner}|"
        if expr.operator == frog_ast.UnaryOperators.MINUS:
            return f"-{inner}"
        return inner

    def _render_call(self, expr: frog_ast.FuncCall) -> str:
        callee = self._render_callee(expr.func)
        args = ", ".join(self._render(a) for a in expr.args)
        return f"{callee}({args})"

    def _render_callee(self, func: frog_ast.Expression) -> str:
        if isinstance(func, frog_ast.Variable) and _looks_like_algorithm_name(
            func.name
        ):
            return self.macros.register_algorithm(func.name)
        if isinstance(func, frog_ast.FieldAccess):
            return self._render_field(func)
        return self._render(func)

    def _render_field(self, expr: frog_ast.FieldAccess) -> str:
        obj = expr.the_object
        if isinstance(obj, frog_ast.Variable) and _looks_like_algorithm_name(obj.name):
            head = self.macros.register_algorithm(obj.name)
        else:
            head = self._render(obj)
        tail = (
            self.macros.register_algorithm(expr.name)
            if _looks_like_algorithm_name(expr.name)
            else expr.name
        )
        return f"{head}.{tail}"
