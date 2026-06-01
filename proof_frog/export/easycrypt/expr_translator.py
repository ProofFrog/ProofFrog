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
        if isinstance(expr, frog_ast.Boolean):
            return "true" if expr.bool else "false"
        if isinstance(expr, frog_ast.BitStringLiteral):
            if expr.bit != 0:
                raise NotImplementedError(
                    "BitStringLiteral with bit=1 not yet supported by the EC "
                    "exporter; only 0^n is currently translated."
                )
            bs_type = frog_ast.BitStringType(expr.length)
            ec_type = self._types.translate_type(bs_type)
            return tc.zero_name_for(ec_type)
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
        # Canonicalize the int arguments via sympy so that
        # arithmetically-equivalent variants (``2 * lambda`` vs
        # ``lambda * 2``) emit identical EC text. The slice op is
        # uninterpreted on its int args, so EC's ``sim`` requires
        # syntactic identity; canonicalization here lets ``sim`` close
        # micro lemmas whose only difference is commutative rearrangement
        # of the int arguments. Aliases (e.g. ``T.lambda`` -> ``lambda``)
        # are resolved first so the canonical form is the same across
        # reduction-body translations (which see ``T.lambda``) and
        # scheme/flat-state translations (which see bare ``lambda``).
        start_resolved = self._resolve_aliases(expr.start)
        end_resolved = self._resolve_aliases(expr.end)
        start = _canonical_int_str(start_resolved) or self.translate(start_resolved)
        end = _canonical_int_str(end_resolved) or self.translate(end_resolved)
        return f"{op} {_paren(src_str)} {_paren(start)} {_paren(end)}"

    def _resolve_aliases(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        """Recursively replace ``FieldAccess(Variable(o), name)`` with the
        alias-resolved expression (e.g. ``T.lambda`` -> ``lambda``).

        Used to normalize int arguments before sympy canonicalization.
        Non-``FieldAccess`` nodes are recursed into; nodes the resolver
        doesn't know about (or whose alias is non-Expression) are kept
        as-is.
        """
        if isinstance(expr, frog_ast.FieldAccess) and isinstance(
            expr.the_object, frog_ast.Variable
        ):
            resolved = self._types.resolve_value_alias(expr.the_object.name, expr.name)
            if resolved is not None:
                return self._resolve_aliases(resolved)
            return expr
        if isinstance(expr, frog_ast.BinaryOperation):
            return frog_ast.BinaryOperation(
                expr.operator,
                self._resolve_aliases(expr.left_expression),
                self._resolve_aliases(expr.right_expression),
            )
        if isinstance(expr, frog_ast.UnaryOperation):
            return frog_ast.UnaryOperation(
                expr.operator, self._resolve_aliases(expr.expression)
            )
        return expr

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
    """Wrap a rendered expression in parens if it isn't already atomic.

    Atomic forms (single identifier or integer literal, possibly already
    wrapped in matching outer parens) are left alone. Anything containing
    whitespace or an infix operator is wrapped so it doesn't bind
    incorrectly when inlined as a function argument.
    """
    if s.startswith("(") and s.endswith(")"):
        return s
    if " " in s:
        return f"({s})"
    if any(op in s for op in "+-*/"):
        return f"({s})"
    return s


def _canonical_int_str(expr: frog_ast.Expression) -> str | None:
    """Return a canonical EC int-expression string for ``expr``, or None.

    Routes ``expr`` through sympy when it's purely arithmetic over bare
    integer-typed variables (no ``FieldAccess`` or other constructs the
    visitor doesn't handle). Returns ``None`` if sympy can't represent
    the expression or if the canonical form would contain identifiers
    the EC scope doesn't have.
    """
    # pylint: disable=import-outside-toplevel
    if _contains_field_access(expr):
        return None
    try:
        from sympy import Symbol  # noqa: F401
        from ... import visitors as _vis
    except ImportError:
        return None
    names: set[str] = set()
    if not _collect_bare_variable_names(expr, names):
        return None
    variables = {n: Symbol(n) for n in names}
    visitor = _vis.FrogToSympyVisitor(variables)
    try:
        visitor.visit(expr)
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    result = visitor.result()
    if result is None:
        return None
    return str(result)


def _contains_field_access(expr: frog_ast.Expression) -> bool:
    if isinstance(expr, frog_ast.FieldAccess):
        return True
    if isinstance(expr, frog_ast.BinaryOperation):
        return _contains_field_access(expr.left_expression) or _contains_field_access(
            expr.right_expression
        )
    if isinstance(expr, frog_ast.UnaryOperation):
        return _contains_field_access(expr.expression)
    return False


def _collect_bare_variable_names(expr: frog_ast.Expression, out: set[str]) -> bool:
    """Collect bare ``Variable`` names; return False on unsupported node."""
    if isinstance(expr, frog_ast.Variable):
        out.add(expr.name)
        return True
    if isinstance(expr, frog_ast.Integer):
        return True
    if isinstance(expr, frog_ast.BinaryOperation):
        return _collect_bare_variable_names(
            expr.left_expression, out
        ) and _collect_bare_variable_names(expr.right_expression, out)
    if isinstance(expr, frog_ast.UnaryOperation):
        return _collect_bare_variable_names(expr.expression, out)
    return False
