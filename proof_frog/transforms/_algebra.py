# pylint: disable=duplicate-code
# Recognizing ``G.generator`` in both AST forms repeats a few lines of
# _wrappers.infer_group_of, which does broader group inference.
"""Exact algebraic normal forms for ``ModInt`` and group-element expressions.

The canonicalization pipeline proves two *games* equivalent; some passes
instead need to know that two *expressions* take the same value for every
value of their free names (pointwise equality, not equality in distribution).
This module provides that decision procedure, and a canonical rebuild of an
expression from its normal form for the few passes that rewrite an
expression into a simpler, provably equal one.

Normal forms, all over *atoms* (maximal subexpressions the algebra does not
look into, such as variables, calls and tuple accesses, identified up to
structural equality after their own arguments are normalized):

* ``ModInt<M>``: a polynomial with integer coefficients (SymPy), read modulo
  ``M``. ``+``, ``-``, unary ``-``, ``*`` and ``^`` with a non-negative
  integer literal exponent are interpreted; ``/`` is not (a modular inverse),
  and an operand of another type makes the whole operation an atom.
* ``Int``: a polynomial with integer coefficients (exact integer arithmetic).
* ``GroupElem<G>``: a map from bases to exponents, read as the product of
  ``base ^ exponent``. ``*``, ``/``, ``^``, ``G.generator`` and ``G.identity``
  are interpreted; the group is abelian (FrogLang groups are cyclic). An
  exponent is folded only when it is an ``Int`` or a ``ModInt`` whose modulus
  is syntactically the group's order, since every element's order divides
  the group order; any other exponent makes the power an atom.

Two expressions with equal normal forms are equal for every value of their
atoms: each rewrite above is a ring or abelian-group identity. The converse
does not hold (the procedure is incomplete, e.g. it does not know that
``q * x`` is ``0`` in ``ModInt<q>``), so a caller may only conclude equality
from a positive answer.

A ``ModInt<M>`` value that :meth:`Normalizer.canonical` rebuilds keeps its
type and puts no integer literal next to a ``ModInt`` operand of ``+``,
``-`` or ``*`` (FrogLang refuses ``u + 1`` and ``2 * u`` for a ``ModInt``
``u``; a power's exponent, the ``2`` of ``k ^ 2``, is an ``Int`` anyway): a
term with a small coefficient is that many copies of the term added up
(``u + u`` for ``2 * u``). :meth:`Normalizer.rebuild_poly`, which passes use
for exponents and for an update's delta, still writes integer coefficients.
A ``ModInt<M>`` value that is a nonzero constant has no such
rebuild (an integer literal alone is an ``Int``, and ``2`` is not ``2 mod
M``), nor does a polynomial with a nonzero constant term or a large
coefficient, so :meth:`Normalizer.canonical` keeps that expression as
written. A ``ModInt<M>`` value equal to ``0`` is rebuilt as the literal
``0`` (``0 mod M`` is ``0``) only where an ``Int`` operand does not change
the operation around it: as the base of a power or an operand of ``/`` it
is kept as written too (``(x - x) ^ 0`` is not the ``Int`` power ``0 ^ 0``,
nor ``(x - x) / (y - y)`` the ``Int`` division ``0 / 0``).

Calls are atoms whatever their determinism: two occurrences of the same call
are the same atom only if the caller has ensured the call is deterministic
(the symbolic executor in :mod:`state_relations` replaces every
non-deterministic call by a fresh name before asking).
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Optional, Union

import sympy

from .. import frog_ast
from ..visitors import NameTypeMap

_Ops = frog_ast.BinaryOperators


# ---------------------------------------------------------------------------
# Typing
# ---------------------------------------------------------------------------


def group_of_generator(expr: frog_ast.Expression) -> Optional[frog_ast.Expression]:
    """The group ``G`` if *expr* is ``G.generator`` (either AST form)."""
    if isinstance(expr, frog_ast.GroupGenerator):
        return expr.group
    if (
        isinstance(expr, frog_ast.FieldAccess)
        and expr.name == "generator"
        and isinstance(expr.the_object, frog_ast.Variable)
    ):
        return expr.the_object
    return None


def group_of_identity(
    expr: frog_ast.Expression, type_map: NameTypeMap
) -> Optional[frog_ast.Expression]:
    """The group ``G`` if *expr* is ``G.identity`` with ``G`` typed Group."""
    if (
        isinstance(expr, frog_ast.FieldAccess)
        and expr.name == "identity"
        and isinstance(expr.the_object, frog_ast.Variable)
        and isinstance(type_map.get(expr.the_object.name), frog_ast.GroupType)
    ):
        return expr.the_object
    return None


def is_order_of(modulus: frog_ast.Expression, group: frog_ast.Expression) -> bool:
    """True if *modulus* is syntactically ``group.order`` (either AST form)."""
    if isinstance(modulus, frog_ast.GroupOrder):
        return bool(modulus.group == group)
    return (
        isinstance(modulus, frog_ast.FieldAccess)
        and modulus.name == "order"
        and modulus.the_object == group
    )


def infer_type(  # pylint: disable=too-many-return-statements,too-many-branches
    expr: frog_ast.Expression, type_map: NameTypeMap
) -> Optional[frog_ast.Type]:
    """The type of *expr*, or None when it cannot be determined.

    Variables are looked up in *type_map*; a call is typed by the codomain of
    a ``Function`` it calls; arithmetic takes the type of an operand that has
    a ``ModInt``/group/bit-string type (an integer literal adopts the type of
    the other operand).
    """
    if isinstance(expr, frog_ast.Variable):
        return type_map.get(expr.name)
    if isinstance(expr, frog_ast.Integer):
        return frog_ast.IntType()
    if isinstance(expr, frog_ast.Boolean):
        return frog_ast.BoolType()
    if isinstance(expr, frog_ast.BitStringLiteral):
        return frog_ast.BitStringType(expr.length)
    group = group_of_generator(expr)
    if group is not None:
        return frog_ast.GroupElemType(group)
    group = group_of_identity(expr, type_map)
    if group is not None:
        return frog_ast.GroupElemType(group)
    if isinstance(expr, frog_ast.FuncCall):
        func_type = infer_type(expr.func, type_map)
        if isinstance(func_type, frog_ast.FunctionType):
            return func_type.range_type
        return None
    if isinstance(expr, frog_ast.ArrayAccess) and isinstance(
        expr.index, frog_ast.Integer
    ):
        base_type = infer_type(expr.the_array, type_map)
        if isinstance(base_type, frog_ast.ProductType) and 0 <= expr.index.num < len(
            base_type.types
        ):
            return base_type.types[expr.index.num]
        return None
    if isinstance(expr, frog_ast.UnaryOperation):
        if expr.operator == frog_ast.UnaryOperators.NOT:
            return frog_ast.BoolType()
        if expr.operator == frog_ast.UnaryOperators.MINUS:
            return infer_type(expr.expression, type_map)
        return None
    if isinstance(expr, frog_ast.BinaryOperation):
        if expr.operator == _Ops.OR:
            # ``||`` is logical or on Bool and concatenation on BitString.
            left_type = infer_type(expr.left_expression, type_map)
            if isinstance(left_type, frog_ast.BitStringType):
                return None
            if isinstance(left_type, frog_ast.BoolType):
                return left_type
            return None
        if expr.operator in (
            _Ops.EQUALS,
            _Ops.NOTEQUALS,
            _Ops.LT,
            _Ops.GT,
            _Ops.LEQ,
            _Ops.GEQ,
            _Ops.AND,
            _Ops.IN,
            _Ops.SUBSETS,
        ):
            return frog_ast.BoolType()
        left = infer_type(expr.left_expression, type_map)
        if expr.operator == _Ops.EXPONENTIATE:
            return left
        right = infer_type(expr.right_expression, type_map)
        for candidate in (left, right):
            if isinstance(
                candidate,
                (
                    frog_ast.ModIntType,
                    frog_ast.GroupElemType,
                    frog_ast.BitStringType,
                ),
            ):
                return candidate
        if isinstance(left, frog_ast.IntType) and isinstance(right, frog_ast.IntType):
            return left
        return None
    return None


# ---------------------------------------------------------------------------
# Atoms
# ---------------------------------------------------------------------------


class AtomTable:
    """Maps canonical atom expressions to SymPy symbols and back.

    A symbol's name is derived from the atom's printed form, so the same atom
    gets the same name in every table: rebuilt expressions order their terms
    the same way whichever expression an atom was first met in.
    """

    def __init__(self) -> None:
        self._entries: list[tuple[frog_ast.Expression, sympy.Symbol]] = []
        self._names: set[str] = set()

    def symbol(self, atom: frog_ast.Expression) -> sympy.Symbol:
        for known, sym in self._entries:
            if known == atom:
                return sym
        digest = hashlib.sha256(str(atom).encode()).hexdigest()[:16]
        name = f"atom_{digest}"
        suffix = 0
        while name in self._names:
            suffix += 1
            name = f"atom_{digest}_{suffix}"
        self._names.add(name)
        sym = sympy.Symbol(name)
        self._entries.append((atom, sym))
        return sym

    def expression(self, sym: sympy.Symbol) -> frog_ast.Expression:
        for known, candidate in self._entries:
            if candidate == sym:
                return copy.deepcopy(known)
        raise KeyError(sym)


# ---------------------------------------------------------------------------
# Normal forms
# ---------------------------------------------------------------------------


@dataclass
class ModIntForm:
    """A ``ModInt<modulus>`` (or, with modulus None, ``Int``) polynomial."""

    modulus: Optional[frog_ast.Expression]
    poly: sympy.Expr


@dataclass
class GroupForm:
    """A product of ``base ^ exponent`` in ``GroupElem<group>``.

    *bases* maps a base symbol (the generator or an atom) to its exponent
    polynomial, read modulo the group order. *generator* is the AST used for
    the generator when rebuilding.
    """

    group: frog_ast.Expression
    bases: dict[sympy.Symbol, sympy.Expr]
    generator: frog_ast.Expression


@dataclass
class StructForm:
    """Any other value: its canonical AST, compared structurally."""

    expr: frog_ast.Expression


NormalForm = Union[ModIntForm, GroupForm, StructForm]


# The largest coefficient a ModInt polynomial term is rebuilt with, as that
# many copies of the term added up (see Normalizer._rebuild_ring_poly).
_MAX_REPEATED_TERM = 4


@dataclass
class KeptConstant:
    """A ``ModInt<modulus>`` expression :meth:`Normalizer.canonical` kept as
    written because its value is the constant *value* mod *modulus*.

    FrogLang has no literal of type ``ModInt<q>``: an integer literal is an
    ``Int``, so rebuilding a nonzero constant as one would drop the reduction
    mod ``q`` (``(x + 1 + 1) - x == 0`` would become ``2 == 0``, false,
    although it holds for ``q = 2``). The constant ``0`` is kept only where
    an ``Int`` operand changes the operation; *position* then names that
    place (for example ``"the base of a power"``), and is None otherwise.
    *value* is None for a non-constant polynomial kept for a constant term
    or a coefficient too large to write as repeated addition (F-370(h)).
    """

    expr: frog_ast.Expression
    value: Optional[int]
    modulus: frog_ast.Expression
    position: Optional[str] = None


class Normalizer:
    """Computes normal forms and canonical rebuilds against one atom table."""

    def __init__(
        self,
        type_map: NameTypeMap,
        namespace: Optional[frog_ast.Namespace] = None,
    ) -> None:
        self.type_map = type_map
        self.namespace = namespace or {}
        self.atoms = AtomTable()
        # Every expression canonical() kept as written (see KeptConstant), so
        # that a pass can report a near miss.
        self.kept_constants: list[KeptConstant] = []

    def _type(self, expr: frog_ast.Expression) -> Optional[frog_ast.Type]:
        """:func:`infer_type`, plus a call to a primitive method typed by the
        method's declared return type when *namespace* is given."""
        the_type = infer_type(expr, self.type_map)
        if (
            the_type is None
            and isinstance(expr, frog_ast.FuncCall)
            and isinstance(expr.func, frog_ast.FieldAccess)
            and isinstance(expr.func.the_object, frog_ast.Variable)
        ):
            owner = self.namespace.get(expr.func.the_object.name)
            if isinstance(owner, frog_ast.Primitive):
                for method in owner.methods:
                    if method.name == expr.func.name:
                        return method.return_type
        return the_type

    # -- entry points -------------------------------------------------------

    def normal_form(
        self, expr: frog_ast.Expression, the_type: Optional[frog_ast.Type] = None
    ) -> NormalForm:
        if the_type is None:
            the_type = self._type(expr)
        if isinstance(the_type, frog_ast.ModIntType):
            return ModIntForm(the_type.modulus, self._poly(expr, the_type))
        if isinstance(the_type, frog_ast.IntType):
            return ModIntForm(None, self._poly(expr, the_type))
        if isinstance(the_type, frog_ast.GroupElemType):
            form = self._group(expr, the_type.group)
            if form is not None:
                return form
        return StructForm(self.canonical(expr))

    def equal(
        self,
        left: frog_ast.Expression,
        right: frog_ast.Expression,
        the_type: Optional[frog_ast.Type] = None,
    ) -> bool:
        """True only if *left* and *right* are equal for all atom values."""
        if the_type is None:
            the_type = self._type(left) or self._type(right)
        if isinstance(the_type, frog_ast.ProductType):
            left_values = frog_ast.tuple_literal_values(left)
            right_values = frog_ast.tuple_literal_values(right)
            if (
                left_values is not None
                and right_values is not None
                and len(left_values) == len(right_values) == len(the_type.types)
            ):
                return all(
                    self.equal(lv, rv, t)
                    for lv, rv, t in zip(left_values, right_values, the_type.types)
                )
        return _forms_equal(
            self.normal_form(left, the_type), self.normal_form(right, the_type)
        )

    def canonical(
        self, expr: frog_ast.Expression, position: Optional[str] = None
    ) -> frog_ast.Expression:
        """A canonical AST for *expr*: equal normal forms give equal ASTs.

        ModInt, Int and group-element subexpressions are rebuilt from their
        normal forms; everything else is rebuilt with canonical children.
        One exception: a ``ModInt`` arithmetic expression whose value is a
        nonzero constant, or a polynomial with a nonzero constant term or a
        large coefficient (see :meth:`_rebuild_ring_poly`), has no
        ``ModInt``-typed rebuild, so it is kept as written and recorded in
        :attr:`kept_constants`.

        *position*, when given, says that *expr* is an operand whose
        replacement by an ``Int`` would change the operation it sits in (for
        example ``"the base of a power"``). A ``ModInt`` value equal to ``0``
        is then kept as written as well, since its rebuild is the ``Int``
        literal ``0``. :meth:`_canonical_children` passes it for the
        operands of ``^`` and ``/`` inside *expr*.
        """
        the_type = self._type(expr)
        if isinstance(the_type, (frog_ast.ModIntType, frog_ast.IntType)) and (
            _is_arithmetic(expr)
        ):
            modulus = (
                the_type.modulus if isinstance(the_type, frog_ast.ModIntType) else None
            )
            poly = sympy.expand(self._poly(expr, the_type))
            rebuilt = self._rebuild_in_ring(poly, modulus)
            if rebuilt is not None and not (
                modulus is not None and position is not None and poly == 0
            ):
                return rebuilt
            assert modulus is not None
            self.kept_constants.append(
                KeptConstant(
                    copy.deepcopy(expr),
                    int(poly) if poly.is_number else None,
                    copy.deepcopy(modulus),
                    position if poly == 0 else None,
                )
            )
            # Kept whole, not with canonical children: a child whose value is
            # 0 would be rebuilt as the Int literal 0, and next to a literal
            # sibling that would make the expression an Int again.
            return copy.deepcopy(expr)
        if isinstance(the_type, frog_ast.GroupElemType) and _is_group_arithmetic(
            expr, self.type_map
        ):
            form = self._group(expr, the_type.group)
            if form is not None:
                return self._rebuild_group(form)
        return self._canonical_children(expr)

    def rebuild_poly(self, poly: sympy.Expr) -> frog_ast.Expression:
        """The canonical AST of a polynomial over this table's atoms.

        A constant term is rebuilt as an ``Int`` literal, which is the right
        value only where the result is read modulo a group's order (an
        exponent of that group) or sits next to an atom of the polynomial's
        ring (``f - delta``). For a ``ModInt`` value in any other position use
        :meth:`canonical`, which never drops a modulus.
        """
        return self._rebuild_poly(poly)

    def rebuild(self, form: NormalForm) -> Optional[frog_ast.Expression]:
        """The canonical AST of *form*, or None for a ``ModInt`` form with no
        rebuild free of integer literals: a nonzero constant, or a polynomial
        with a nonzero constant term or a large coefficient (see
        :class:`KeptConstant`)."""
        if isinstance(form, ModIntForm):
            return self._rebuild_in_ring(form.poly, form.modulus)
        if isinstance(form, GroupForm):
            return self._rebuild_group(form)
        return copy.deepcopy(form.expr)

    # -- ModInt / Int polynomials ------------------------------------------

    def _poly(self, expr: frog_ast.Expression, the_type: frog_ast.Type) -> sympy.Expr:
        # pylint: disable=too-many-return-statements
        if isinstance(expr, frog_ast.Integer):
            return sympy.Integer(expr.num)
        if isinstance(expr, frog_ast.UnaryOperation) and (
            expr.operator == frog_ast.UnaryOperators.MINUS
        ):
            if self._same_ring(expr.expression, the_type):
                return -self._poly(expr.expression, the_type)
        if isinstance(expr, frog_ast.BinaryOperation):
            left, right = expr.left_expression, expr.right_expression
            if expr.operator in (_Ops.ADD, _Ops.SUBTRACT, _Ops.MULTIPLY) and (
                self._same_ring(left, the_type) and self._same_ring(right, the_type)
            ):
                lp = self._poly(left, the_type)
                rp = self._poly(right, the_type)
                if expr.operator == _Ops.ADD:
                    return sympy.expand(lp + rp)
                if expr.operator == _Ops.SUBTRACT:
                    return sympy.expand(lp - rp)
                return sympy.expand(lp * rp)
            if (
                expr.operator == _Ops.EXPONENTIATE
                and isinstance(right, frog_ast.Integer)
                and 0 <= right.num <= 8
                and self._same_ring(left, the_type)
            ):
                return sympy.expand(self._poly(left, the_type) ** right.num)
        return self.atoms.symbol(self._canonical_children(expr))

    def _same_ring(self, expr: frog_ast.Expression, the_type: frog_ast.Type) -> bool:
        """True if *expr* lives in the ring of *the_type* (literals do)."""
        if isinstance(expr, frog_ast.Integer):
            return True
        other = self._type(expr)
        if other is None:
            return False
        return bool(other == the_type)

    def _rebuild_in_ring(
        self, poly: sympy.Expr, modulus: Optional[frog_ast.Expression]
    ) -> Optional[frog_ast.Expression]:
        """The canonical AST of *poly* as a value of ``ModInt<modulus>`` (of
        ``Int`` when *modulus* is None), or None when there is none.

        A non-constant ``Int`` polynomial is rebuilt with an atom in its
        first term, its integer literals exact. A non-constant ``ModInt``
        polynomial is rebuilt without integer literals
        (:meth:`_rebuild_ring_poly`), or None when it has no such rebuild. A
        constant ``c`` is an ``Int`` literal: that is the ``ModInt`` value
        only for ``c = 0`` (``0 mod q`` is ``0`` for every ``q``), so any
        other constant of a ``ModInt`` ring gives None.
        """
        poly = sympy.expand(poly)
        if modulus is not None and poly.is_number and poly != 0:
            return None
        if modulus is not None and not poly.is_number:
            return self._rebuild_ring_poly(poly)
        return self._rebuild_poly(poly)

    def _rebuild_ring_poly(self, poly: sympy.Expr) -> Optional[frog_ast.Expression]:
        """A non-constant ``ModInt`` polynomial rebuilt with no integer
        literal next to a ``ModInt`` operand (F-370(h)): FrogLang refuses
        ``2 * u`` and ``u + 1`` for a ``ModInt`` ``u``, and the engine's own
        type helpers read such a shape by its literal, as an ``Int``. A term
        with coefficient ``k`` is ``k`` copies of the term added up (``u +
        u``); a nonzero constant term, or a coefficient above
        :data:`_MAX_REPEATED_TERM`, has no such rebuild and gives None."""
        result: Optional[frog_ast.Expression] = None
        for term in poly.as_ordered_terms():
            coeff, rest = term.as_coeff_Mul()
            if rest == 1 or not coeff.is_integer:
                return None
            negative = coeff < 0
            magnitude = int(-coeff if negative else coeff)
            if magnitude > _MAX_REPEATED_TERM:
                return None
            factors: list[frog_ast.Expression] = []
            for factor in sympy.Mul.make_args(rest):
                base, exp = factor.as_base_exp()
                atom = self.atoms.expression(base)
                factors.append(
                    atom
                    if exp == 1
                    else frog_ast.BinaryOperation(
                        _Ops.EXPONENTIATE, atom, frog_ast.Integer(int(exp))
                    )
                )
            term_ast = factors[0]
            for factor_ast in factors[1:]:
                term_ast = frog_ast.BinaryOperation(_Ops.MULTIPLY, term_ast, factor_ast)
            summed = term_ast
            for _ in range(magnitude - 1):
                summed = frog_ast.BinaryOperation(
                    _Ops.ADD, summed, copy.deepcopy(term_ast)
                )
            if result is None:
                result = (
                    frog_ast.UnaryOperation(frog_ast.UnaryOperators.MINUS, summed)
                    if negative
                    else summed
                )
            else:
                result = frog_ast.BinaryOperation(
                    _Ops.SUBTRACT if negative else _Ops.ADD, result, summed
                )
        return result

    def _rebuild_poly(self, poly: sympy.Expr) -> frog_ast.Expression:
        poly = sympy.expand(poly)
        if poly == 0:
            return frog_ast.Integer(0)
        result: Optional[frog_ast.Expression] = None
        for term in poly.as_ordered_terms():
            coeff, rest = term.as_coeff_Mul()
            negative = coeff < 0
            magnitude = -coeff if negative else coeff
            factors: list[frog_ast.Expression] = []
            if rest != 1:
                for factor in sympy.Mul.make_args(rest):
                    base, exp = factor.as_base_exp()
                    atom = self.atoms.expression(base)
                    if exp == 1:
                        factors.append(atom)
                    else:
                        factors.append(
                            frog_ast.BinaryOperation(
                                _Ops.EXPONENTIATE, atom, frog_ast.Integer(int(exp))
                            )
                        )
            if magnitude != 1 or not factors:
                factors.insert(0, frog_ast.Integer(int(magnitude)))
            term_ast = factors[0]
            for factor_ast in factors[1:]:
                term_ast = frog_ast.BinaryOperation(_Ops.MULTIPLY, term_ast, factor_ast)
            if result is None:
                result = (
                    frog_ast.UnaryOperation(frog_ast.UnaryOperators.MINUS, term_ast)
                    if negative
                    else term_ast
                )
            else:
                result = frog_ast.BinaryOperation(
                    _Ops.SUBTRACT if negative else _Ops.ADD, result, term_ast
                )
        assert result is not None
        return result

    # -- group elements ----------------------------------------------------

    def _generator_symbol(
        self, group: frog_ast.Expression, generator: frog_ast.Expression
    ) -> sympy.Symbol:
        # The atom table matches atoms structurally, so two groups that print
        # alike (a Variable named ``E.G`` and the access ``E.G``) get distinct
        # generator symbols (F-370(e)).
        del generator
        return self.atoms.symbol(
            frog_ast.FieldAccess(copy.deepcopy(group), "generator")
        )

    def _group(
        self, expr: frog_ast.Expression, group: frog_ast.Expression
    ) -> Optional[GroupForm]:
        """Normal form of a ``GroupElem<group>`` expression (None: unsupported)."""
        generator = frog_ast.FieldAccess(copy.deepcopy(group), "generator")
        bases = self._group_bases(expr, group)
        if bases is None:
            return None
        return GroupForm(group, bases, generator)

    def _group_bases(  # pylint: disable=too-many-return-statements
        self, expr: frog_ast.Expression, group: frog_ast.Expression
    ) -> Optional[dict[sympy.Symbol, sympy.Expr]]:
        gen_group = group_of_generator(expr)
        if gen_group is not None:
            if gen_group != group:
                return None
            return {self._generator_symbol(group, expr): sympy.Integer(1)}
        id_group = group_of_identity(expr, self.type_map)
        if id_group is not None:
            return {} if id_group == group else None
        if isinstance(expr, frog_ast.BinaryOperation) and expr.operator in (
            _Ops.MULTIPLY,
            _Ops.DIVIDE,
        ):
            if self._in_group(expr.left_expression, group) and self._in_group(
                expr.right_expression, group
            ):
                left = self._group_bases(expr.left_expression, group)
                right = self._group_bases(expr.right_expression, group)
                if left is None or right is None:
                    return None
                sign = 1 if expr.operator == _Ops.MULTIPLY else -1
                return _merge(left, right, sign)
        if (
            isinstance(expr, frog_ast.BinaryOperation)
            and expr.operator == _Ops.EXPONENTIATE
            and self._in_group(expr.left_expression, group)
        ):
            exponent = self._exponent(expr.right_expression, group)
            if exponent is not None:
                base = self._group_bases(expr.left_expression, group)
                if base is None:
                    return None
                return {
                    sym: sympy.expand(value * exponent) for sym, value in base.items()
                }
        if not self._in_group(expr, group):
            return None
        return {self.atoms.symbol(self.canonical_atom(expr)): sympy.Integer(1)}

    def canonical_atom(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        """Canonical AST for an expression the algebra treats as an atom."""
        return self._canonical_children(expr)

    def _in_group(self, expr: frog_ast.Expression, group: frog_ast.Expression) -> bool:
        the_type = self._type(expr)
        return isinstance(the_type, frog_ast.GroupElemType) and bool(
            the_type.group == group
        )

    def _exponent(
        self, expr: frog_ast.Expression, group: frog_ast.Expression
    ) -> Optional[sympy.Expr]:
        """The exponent polynomial (read modulo the group order), or None."""
        the_type = self._type(expr)
        if isinstance(the_type, frog_ast.IntType):
            return self._poly(expr, the_type)
        if isinstance(the_type, frog_ast.ModIntType) and is_order_of(
            the_type.modulus, group
        ):
            return self._poly(expr, the_type)
        return None

    def _rebuild_group(self, form: GroupForm) -> frog_ast.Expression:
        terms: list[frog_ast.Expression] = []
        for sym in sorted(form.bases, key=lambda s: s.name):
            exponent = sympy.expand(form.bases[sym])
            if exponent == 0:
                continue
            base = self.atoms.expression(sym)
            if exponent == 1:
                terms.append(base)
            else:
                terms.append(
                    frog_ast.BinaryOperation(
                        _Ops.EXPONENTIATE, base, self._rebuild_poly(exponent)
                    )
                )
        if not terms:
            return frog_ast.FieldAccess(copy.deepcopy(form.group), "identity")
        result = terms[0]
        for term in terms[1:]:
            result = frog_ast.BinaryOperation(_Ops.MULTIPLY, result, term)
        return result

    # -- structure ---------------------------------------------------------

    def _canonical_children(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        if isinstance(expr, frog_ast.FuncCall):
            return frog_ast.FuncCall(
                self._canonical_children(expr.func),
                [self.canonical(arg) for arg in expr.args],
            )
        if isinstance(expr, frog_ast.Tuple):
            return frog_ast.Tuple([self.canonical(value) for value in expr.values])
        if isinstance(expr, frog_ast.ArrayAccess):
            return frog_ast.ArrayAccess(
                self.canonical(expr.the_array), self.canonical(expr.index)
            )
        if isinstance(expr, frog_ast.BinaryOperation):
            left_position, right_position = int_sensitive_operands(expr.operator)
            return frog_ast.BinaryOperation(
                expr.operator,
                self.canonical(expr.left_expression, left_position),
                self.canonical(expr.right_expression, right_position),
            )
        if isinstance(expr, frog_ast.UnaryOperation):
            return frog_ast.UnaryOperation(
                expr.operator, self.canonical(expr.expression)
            )
        group = group_of_generator(expr)
        if group is not None:
            return frog_ast.FieldAccess(copy.deepcopy(group), "generator")
        return copy.deepcopy(expr)


def int_sensitive_operands(
    operator: frog_ast.BinaryOperators,
) -> tuple[Optional[str], Optional[str]]:
    """For each operand of *operator* (left, right), the position it is in if
    an ``Int`` there would change the operation, else None.

    ``^`` takes its type from its base, so an ``Int`` base makes it an
    ``Int`` power (``0 ^ 0`` is the ``Int`` 1, not ``1 mod q``); ``/`` on an
    ``Int`` operand reads as ``Int`` division. An ``Int`` exponent is what
    ``^`` expects, and next to a ``ModInt`` operand of ``+``, ``-`` or ``*``,
    or under ``==``, an ``Int`` ``0`` is read as ``0 mod q``.
    """
    if operator == _Ops.EXPONENTIATE:
        return "the base of a power", None
    if operator == _Ops.DIVIDE:
        return "an operand of a division", "an operand of a division"
    return None, None


def _is_arithmetic(expr: frog_ast.Expression) -> bool:
    if isinstance(expr, frog_ast.BinaryOperation):
        return expr.operator in (
            _Ops.ADD,
            _Ops.SUBTRACT,
            _Ops.MULTIPLY,
            _Ops.EXPONENTIATE,
        )
    return isinstance(expr, frog_ast.UnaryOperation) and (
        expr.operator == frog_ast.UnaryOperators.MINUS
    )


def _is_group_arithmetic(expr: frog_ast.Expression, type_map: NameTypeMap) -> bool:
    if isinstance(expr, frog_ast.BinaryOperation):
        return expr.operator in (_Ops.MULTIPLY, _Ops.DIVIDE, _Ops.EXPONENTIATE)
    return (
        group_of_generator(expr) is not None
        or group_of_identity(expr, type_map) is not None
    )


def _merge(
    left: dict[sympy.Symbol, sympy.Expr],
    right: dict[sympy.Symbol, sympy.Expr],
    sign: int,
) -> dict[sympy.Symbol, sympy.Expr]:
    merged = dict(left)
    for sym, value in right.items():
        merged[sym] = sympy.expand(merged.get(sym, sympy.Integer(0)) + sign * value)
    return merged


def _forms_equal(left: NormalForm, right: NormalForm) -> bool:
    if isinstance(left, ModIntForm) and isinstance(right, ModIntForm):
        if left.modulus != right.modulus:
            return False
        return bool(sympy.expand(left.poly - right.poly) == 0)
    if isinstance(left, GroupForm) and isinstance(right, GroupForm):
        if left.group != right.group:
            return False
        for sym in set(left.bases) | set(right.bases):
            difference = left.bases.get(sym, sympy.Integer(0)) - right.bases.get(
                sym, sympy.Integer(0)
            )
            if sympy.expand(difference) != 0:
                return False
        return True
    if isinstance(left, StructForm) and isinstance(right, StructForm):
        return bool(left.expr == right.expr)
    return False


def node_count(node: frog_ast.ASTNode) -> int:
    """Number of AST nodes in *node* (a size measure for rewrites)."""
    count = 1
    for value in vars(node).values():
        if isinstance(value, frog_ast.ASTNode):
            count += node_count(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, frog_ast.ASTNode):
                    count += node_count(item)
    return count
