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
        if isinstance(expr, frog_ast.Integer):
            return str(expr.num)
        if isinstance(expr, frog_ast.FieldAccess) and isinstance(
            expr.the_object, frog_ast.Variable
        ):
            # ``T.lambda`` in a reduction body refers to the let-binding
            # T's lambda field. After alias substitution this is just
            # the let-name ``lambda``. Resolve through the TypeCollector's
            # alias map; if the alias is an Expression, render that.
            resolved = self._types.resolve_value_alias(expr.the_object.name, expr.name)
            if resolved is not None:
                return self.translate(resolved)
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
        if isinstance(expr, frog_ast.Slice):
            return self._translate_slice(expr)
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
            # Integer (or other arithmetic) addition: defer to plain EC.
            return self._translate_arith(expr)
        if expr.operator == frog_ast.BinaryOperators.OR:
            # ``||`` is overloaded: logical OR on Bool, concatenation on
            # BitString. Distinguish via the resolved operand types.
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            rhs_type = self._types.resolve(self._type_of(expr.right_expression))
            if isinstance(lhs_type, frog_ast.BitStringType) and isinstance(
                rhs_type, frog_ast.BitStringType
            ):
                return self._translate_concat(expr, lhs_type, rhs_type)
            return self._translate_arith(expr)
        if expr.operator in (
            frog_ast.BinaryOperators.SUBTRACT,
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.BinaryOperators.DIVIDE,
        ):
            return self._translate_arith(expr)
        raise NotImplementedError(
            f"Binary operator translation not implemented: {expr.operator}"
        )

    def _translate_arith(self, expr: frog_ast.BinaryOperation) -> str:
        """Render an integer/Bool binary op verbatim into EC source."""
        left = self.translate(expr.left_expression)
        right = self.translate(expr.right_expression)
        return f"{_paren(left)} {expr.operator.value} {_paren(right)}"

    def _translate_slice(self, expr: frog_ast.Slice) -> str:
        src_type = self._types.resolve(self._type_of(expr.the_array))
        if not isinstance(src_type, frog_ast.BitStringType):
            raise NotImplementedError(
                f"Slice translation requires a BitString operand; got {src_type}"
            )
        src_ec = self._types.translate_type(src_type)
        # The result's bit-length is ``end - start``. Build a synthetic
        # BitStringType so the TypeCollector's existing sympy-canonical
        # naming yields the same name as the surrounding variable's
        # declared type (e.g. ``BitString<lambda>`` and
        # ``BitString<lambda - 0>`` both yield ``bs_lambda``).
        dst_len = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBTRACT, expr.end, expr.start
        )
        dst_ec = self._types.translate_type(frog_ast.BitStringType(dst_len))
        op = self._types.register_slice(src_ec.text, dst_ec.text)
        src_str = self.translate(expr.the_array)
        start = self.translate(expr.start)
        end = self.translate(expr.end)
        return f"{op} {_paren(src_str)} {_paren(start)} {_paren(end)}"

    def _translate_concat(
        self,
        expr: frog_ast.BinaryOperation,
        lhs_type: frog_ast.BitStringType,
        rhs_type: frog_ast.BitStringType,
    ) -> str:
        left_ec = self._types.translate_type(lhs_type)
        right_ec = self._types.translate_type(rhs_type)
        # Result length = sum of operand lengths. The TypeCollector
        # canonicalizes the resulting bitstring name via sympy so
        # variants like ``a + b`` and ``b + a`` collapse to one.
        assert lhs_type.parameterization is not None
        assert rhs_type.parameterization is not None
        result_len = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            lhs_type.parameterization,
            rhs_type.parameterization,
        )
        result_ec = self._types.translate_type(frog_ast.BitStringType(result_len))
        op = self._types.register_concat(left_ec.text, right_ec.text, result_ec.text)
        left = self.translate(expr.left_expression)
        right = self.translate(expr.right_expression)
        return f"{op} {_paren(left)} {_paren(right)}"


def _paren(s: str) -> str:
    """Wrap a rendered expression in parens if it contains whitespace."""
    if " " in s:
        return f"({s})"
    return s
