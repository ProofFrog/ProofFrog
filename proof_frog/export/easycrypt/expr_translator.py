"""Translate FrogLang expressions to EasyCrypt expression strings.

Walking-skeleton scope: variables, binary XOR on BitString. No literals,
no tuples, no sampling expressions (those are handled at the statement
level).
"""

from __future__ import annotations

from typing import Callable

from . import ec_ast
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
        field_renames: dict[str, str] | None = None,
    ) -> None:
        self._types = types
        self._type_of = type_of
        # EC module-global variables must be lowercase-initial. A FrogLang
        # game field with an uppercase initial (e.g. the random function
        # ``RF``) is renamed at its declaration; this map renders every
        # reference to it with the same renamed identifier. Empty for the
        # common all-lowercase case, so non-affected proofs are unchanged.
        self._field_renames: dict[str, str] = field_renames or {}

    def type_of(self, expr: frog_ast.Expression) -> frog_ast.Type:
        """Return the FrogLang type of ``expr`` using the configured resolver."""
        return self._type_of(expr)

    def _is_map(self, expr: frog_ast.Expression) -> bool:
        """True if ``expr`` has a FrogLang finite-map type ``Map<K, V>``."""
        try:
            resolved = self._types.resolve(self._type_of(expr))
        except (NotImplementedError, KeyError):
            return False
        return isinstance(resolved, frog_ast.MapType)

    def translate(self, expr: frog_ast.Expression) -> str:
        """Render `expr` as an EC expression string."""
        if isinstance(expr, frog_ast.Variable):
            return self._field_renames.get(expr.name, expr.name)
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
            # ``G.generator`` / ``G.identity`` on a Group-typed object are
            # the group's distinguished constants -- render them as the
            # abstract ops the GroupElem foundation declares.
            if expr.name in ("generator", "identity"):
                field_type = self._types.resolve(self._type_of(expr))
                if isinstance(field_type, frog_ast.GroupElemType):
                    ec_type = self._types.translate_type(field_type)
                    return (
                        tc.group_generator_name_for(ec_type)
                        if expr.name == "generator"
                        else tc.group_identity_name_for(ec_type)
                    )
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
        if isinstance(expr, frog_ast.ArrayAccess) and self._is_map(expr.the_array):
            # Finite-map lookup ``m[k]`` (a lazy random-oracle table read).
            # SmtMap's ``m.[k]`` returns ``V option``; FrogLang's ``m[k]``
            # returns the value ``V`` and is only evaluated where ``k`` is a
            # key (the game guards every read with ``if (k in m)``), so
            # ``oget`` extracts it. Checked before the integer-index tuple
            # branch so a ``Map<Int, V>`` still routes here.
            arr = self.translate(expr.the_array)
            idx = self.translate(expr.index)
            return f"(oget {_paren(arr)}.[{idx}])"
        if isinstance(expr, frog_ast.ArrayAccess) and isinstance(
            expr.index, frog_ast.Integer
        ):
            inner = self.translate(expr.the_array)
            # EC tuples are 1-indexed via ``t.`N``; FrogLang is 0-indexed.
            return f"{_paren(inner)}.`{expr.index.num + 1}"
        if isinstance(expr, frog_ast.Slice):
            return self._translate_slice(expr)
        if isinstance(expr, frog_ast.FuncCall) and isinstance(
            expr.func, frog_ast.Variable
        ):
            # Application of a sampled random function ``RF(x)`` -> EC's
            # function application ``RF x``. (Module calls ``E.m(...)`` --
            # a FuncCall whose func is a FieldAccess -- are lifted to ``<@``
            # statements by the statement translator and never reach here.)
            func = self.translate(expr.func)
            args = " ".join(_paren(self.translate(a)) for a in expr.args)
            return f"{func} {args}"
        raise NotImplementedError(
            f"Expression translation not implemented for "
            f"{type(expr).__name__}: {expr}"
        )

    def _translate_binop(self, expr: frog_ast.BinaryOperation) -> str:
        if expr.operator in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            # EC uses ``=`` / ``<>`` for (in)equality on any type.
            op = "=" if expr.operator == frog_ast.BinaryOperators.EQUALS else "<>"
            left = self.translate(expr.left_expression)
            right = self.translate(expr.right_expression)
            return f"{_paren(left)} {op} {_paren(right)}"
        if expr.operator == frog_ast.BinaryOperators.IN:
            # ``k in m`` membership. For a finite map this is SmtMap's
            # ``k \in m`` (defined as ``k \in dom m``); EC's ``\in`` notation
            # covers the fmap domain, so no ``dom`` is needed.
            left = self.translate(expr.left_expression)
            right = self.translate(expr.right_expression)
            return f"{_paren(left)} \\in {_paren(right)}"
        if expr.operator == frog_ast.BinaryOperators.ADD:
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            if isinstance(lhs_type, frog_ast.BitStringType):
                ec_type = self._types.translate_type(lhs_type)
                xor = tc.xor_name_for(ec_type)
                left = self.translate(expr.left_expression)
                right = self.translate(expr.right_expression)
                return f"{xor} {_paren(left)} {_paren(right)}"
            if isinstance(lhs_type, frog_ast.ModIntType):
                ec_type = self._types.translate_type(lhs_type)
                add = tc.add_name_for(ec_type)
                left = self._modint_operand(expr.left_expression, ec_type)
                right = self._modint_operand(expr.right_expression, ec_type)
                return f"{add} {_paren(left)} {_paren(right)}"
            # Integer (or other arithmetic) addition: defer to plain EC.
            return self._translate_arith(expr)
        if expr.operator == frog_ast.BinaryOperators.OR:
            # ``||`` is overloaded: logical OR on Bool, concatenation on
            # BitString. Distinguish via the resolved operand types.
            lhs_bs = self._bitstring_type_of(expr.left_expression)
            rhs_bs = self._bitstring_type_of(expr.right_expression)
            if lhs_bs is not None and rhs_bs is not None:
                return self._translate_concat(expr, lhs_bs, rhs_bs)
            return self._translate_arith(expr)
        if expr.operator == frog_ast.BinaryOperators.AND:
            # Logical AND on Bool -- EC accepts ``&&`` (short-circuit bool)
            # verbatim (the operator's ``.value``). ``&&`` is never overloaded
            # (no BitString analogue), so it always renders as the arithmetic op.
            return self._translate_arith(expr)
        if expr.operator == frog_ast.BinaryOperators.SUBTRACT:
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            if isinstance(lhs_type, frog_ast.ModIntType):
                ec_type = self._types.translate_type(lhs_type)
                sub = tc.sub_name_for(ec_type)
                left = self._modint_operand(expr.left_expression, ec_type)
                right = self._modint_operand(expr.right_expression, ec_type)
                return f"{sub} {_paren(left)} {_paren(right)}"
            return self._translate_arith(expr)
        if expr.operator in (
            frog_ast.BinaryOperators.MULTIPLY,
            frog_ast.BinaryOperators.DIVIDE,
        ):
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            if isinstance(lhs_type, frog_ast.GroupElemType):
                ec_type = self._types.translate_type(lhs_type)
                op = (
                    tc.group_mul_name_for(ec_type)
                    if expr.operator == frog_ast.BinaryOperators.MULTIPLY
                    else tc.group_div_name_for(ec_type)
                )
                left = self.translate(expr.left_expression)
                right = self.translate(expr.right_expression)
                return f"{op} {_paren(left)} {_paren(right)}"
            if (
                isinstance(lhs_type, frog_ast.ModIntType)
                and expr.operator == frog_ast.BinaryOperators.MULTIPLY
            ):
                # ModInt ring multiplication (the group's exponent ring).
                ec_type = self._types.translate_type(lhs_type)
                mmul = tc.modint_mul_name_for(ec_type)
                left = self._modint_operand(expr.left_expression, ec_type)
                right = self._modint_operand(expr.right_expression, ec_type)
                return f"{mmul} {_paren(left)} {_paren(right)}"
            return self._translate_arith(expr)
        if expr.operator == frog_ast.BinaryOperators.EXPONENTIATE:
            lhs_type = self._types.resolve(self._type_of(expr.left_expression))
            if isinstance(lhs_type, frog_ast.GroupElemType):
                ec_type = self._types.translate_type(lhs_type)
                left = self.translate(expr.left_expression)
                # The exponent lives in the group's exponent ring
                # ModInt<G.order>; render a literal ``0`` as that ring's zero.
                exp_modint = self._types.translate_type(
                    frog_ast.ModIntType(frog_ast.FieldAccess(lhs_type.group, "order"))
                )
                right = self._modint_operand(expr.right_expression, exp_modint)
                return tc.group_power_for(
                    ec_type, exp_modint, _paren(left), _paren(right)
                )
            return self._translate_arith(expr)
        raise NotImplementedError(
            f"Binary operator translation not implemented: {expr.operator}"
        )

    def _modint_operand(
        self, expr: frog_ast.Expression, ec_modint_type: ec_ast.EcType
    ) -> str:
        """Render ``expr`` in a position typed as ``ec_modint_type``.

        The engine's symbolic exponent arithmetic can collapse a ModInt
        expression to the integer literal ``0`` (e.g. ``x - x``); render it
        as the ring's zero constant so the result stays well-typed."""
        if isinstance(expr, frog_ast.Integer) and expr.num == 0:
            return tc.modint_zero_name_for(ec_modint_type)
        return self.translate(expr)

    def _bitstring_type_of(
        self, expr: frog_ast.Expression
    ) -> frog_ast.BitStringType | None:
        """The BitString type of ``expr`` for concatenation, or ``None``.

        A nested ``||`` is computed *structurally* (recurse and sum the
        operand lengths) -- the engine's recorded type for an inlined
        concat node can be a single carrier rather than the summed
        bitstring, so the concat op for the surrounding level would
        otherwise be built with the wrong operand length. A leaf operand
        resolves via its type: either (1) a genuine BitString, or (2) an
        abstract carrier set unified with a bitstring via a ``requires
        subsets/== BitString<n>`` clause -- the engine inlines the set->bs
        coercion in flat states, so a ``||`` operand can surface
        carrier-typed (e.g. a ``PK1Space``-typed ``pk1`` where
        ``KEM1.PublicKey subsets BitString<pk1len>``).
        """
        if (
            isinstance(expr, frog_ast.BinaryOperation)
            and expr.operator == frog_ast.BinaryOperators.OR
        ):
            lhs = self._bitstring_type_of(expr.left_expression)
            rhs = self._bitstring_type_of(expr.right_expression)
            if (
                lhs is not None
                and rhs is not None
                and lhs.parameterization is not None
                and rhs.parameterization is not None
            ):
                return frog_ast.BitStringType(
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.ADD,
                        lhs.parameterization,
                        rhs.parameterization,
                    )
                )
            return None
        resolved = self._types.resolve(self._type_of(expr))
        if isinstance(resolved, frog_ast.BitStringType):
            return resolved
        if isinstance(resolved, (frog_ast.Variable, frog_ast.FieldAccess)):
            return self._types.bitstring_carrier_type(resolved.name)
        return None

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


def _has_wrapping_parens(s: str) -> bool:
    """True iff ``s``'s leading ``(`` is closed by its trailing ``)``.

    A mere ``s.startswith("(") and s.endswith(")")`` is *not* enough: a
    string like ``(a <> b) || (c <> d)`` starts and ends with a paren yet is
    not parenthesized as a whole -- the leading ``(`` closes after ``b``.
    Treating it as atomic would drop the parens an enclosing operator needs,
    silently changing precedence (e.g. rendering ``x && (y || z)`` as
    ``x && y || z`` = ``(x && y) || z``).
    """
    if not (s.startswith("(") and s.endswith(")")):
        return False
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(s) - 1
    return False


def _paren(s: str) -> str:
    """Wrap a rendered expression in parens if it isn't already atomic.

    Atomic forms (single identifier or integer literal, possibly already
    wrapped in matching outer parens) are left alone. Anything containing
    whitespace or an infix operator is wrapped so it doesn't bind
    incorrectly when inlined as a function argument.
    """
    if _has_wrapping_parens(s):
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
