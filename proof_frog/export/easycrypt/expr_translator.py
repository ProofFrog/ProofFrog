"""Translate FrogLang expressions to EasyCrypt expression strings.

Walking-skeleton scope: variables, binary XOR on BitString. No literals,
no tuples, no sampling expressions (those are handled at the statement
level).
"""

from __future__ import annotations

from typing import Callable

from . import type_collector as tc
from ... import frog_ast


class ExpressionTranslator:
    """Render a FrogLang expression as an EC expression string.

    A type resolver is required for operators whose EC form depends on
    operand type (e.g. ``+`` on BitString becomes ``xor_lambda a b``).
    """

    def __init__(
        self,
        types: tc.TypeCollector,
        type_of: Callable[[frog_ast.Expression], frog_ast.Type],
    ) -> None:
        self._types = types
        self._type_of = type_of

    def type_of(self, expr: frog_ast.Expression) -> frog_ast.Type:
        """Return the FrogLang type of ``expr`` using the configured resolver."""
        return self._type_of(expr)

    def translate(self, expr: frog_ast.Expression) -> str:
        """Render `expr` as an EC expression string."""
        if isinstance(expr, frog_ast.Variable):
            return expr.name
        if isinstance(expr, frog_ast.BinaryOperation):
            return self._translate_binop(expr)
        if isinstance(expr, frog_ast.Tuple):
            parts = [self.translate(v) for v in expr.values]
            return "(" + ", ".join(parts) + ")"
        if isinstance(expr, frog_ast.ArrayAccess) and isinstance(
            expr.index, frog_ast.Integer
        ):
            inner = self.translate(expr.the_array)
            # EC tuples are 1-indexed via ``t.`N``; FrogLang is 0-indexed.
            return f"{_paren(inner)}.`{expr.index.num + 1}"
        raise NotImplementedError(
            f"Expression translation not implemented for "
            f"{type(expr).__name__}: {expr}"
        )

    def _translate_binop(self, expr: frog_ast.BinaryOperation) -> str:
        if expr.operator == frog_ast.BinaryOperators.ADD:
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            if isinstance(lhs_type, frog_ast.BitStringType):
                ec_type = self._types.translate_type(lhs_type)
                xor = tc.xor_name_for(ec_type)
                left = self.translate(expr.left_expression)
                right = self.translate(expr.right_expression)
                return f"{xor} {_paren(left)} {_paren(right)}"
        raise NotImplementedError(
            f"Binary operator translation not implemented: {expr.operator}"
        )


def _paren(s: str) -> str:
    """Wrap a rendered expression in parens if it contains whitespace."""
    if " " in s:
        return f"({s})"
    return s
