"""Stores that change the stored value: an ``Int`` written into a ``ModInt``.

The type checker accepts an ``Int`` wherever a ``ModInt<q>`` is expected, and
the stored value is the ``Int`` reduced modulo ``q``: after ``ModInt<q> x =
b;`` (``b : Int``) the variable ``x`` holds ``b mod q``, not ``b``. The same
holds for a plain assignment to a ``ModInt`` variable or field, for an element
of a ``Map``/``Array``/tuple/``Set`` whose element type is (or contains) a
``ModInt``, and so on.

A pass that reads such a variable as the expression it was assigned (it
substitutes the right-hand side for the variable's reads, or replaces later
occurrences of the right-hand side by the variable, or uses ``x == rhs`` as a
fact) drops or adds the reduction, which changes what the game computes:
``G.generator ^ x`` is not ``G.generator ^ b``, and ``x == z`` (with ``ModInt``
values) is not the integer comparison ``b == z``.

:func:`coercing_store_names` collects the names that some store in the game
writes this way, and every pass that forwards a stored value consults it.
The set is name based and game wide, so a name that one method stores with a
reduction is not forwarded anywhere in the game: that can only cost
completeness.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from .. import frog_ast
from ..visitors import (
    NameTypeMap,
    SearchVisitor,
    build_method_type_map,
    expression_type,
    lvalue_base_name,
    type_contains_mod_int,
)
from ._base import NearMiss, PipelineContext


def _in_range_literal(value: frog_ast.Expression, target: frog_ast.ModIntType) -> bool:
    """True if *value* is an integer literal that every ``ModInt`` of
    *target*'s modulus represents as itself: ``0`` for any modulus, and
    ``0 <= n < m`` for a literal modulus ``m``."""
    if not isinstance(value, frog_ast.Integer):
        return False
    if value.num == 0:
        return True
    return isinstance(target.modulus, frog_ast.Integer) and (
        0 <= value.num < target.modulus.num
    )


def _may_change(  # pylint: disable=too-many-return-statements
    target: Optional[frog_ast.Type], value_type: Optional[frog_ast.Type]
) -> bool:
    """True if storing a value of *value_type* into a slot of type *target*
    may change the value, i.e. an ``Int`` part of the value may land in a
    ``ModInt`` part of the slot. An unknown *value_type* (None) may."""
    if not type_contains_mod_int(target):
        return False
    if value_type is None:
        return True
    if isinstance(target, frog_ast.ModIntType):
        return not isinstance(value_type, frog_ast.ModIntType)
    if isinstance(target, frog_ast.OptionalType):
        inner = (
            value_type.the_type
            if isinstance(value_type, frog_ast.OptionalType)
            else value_type
        )
        return _may_change(target.the_type, inner)
    if isinstance(target, frog_ast.ProductType):
        if isinstance(value_type, frog_ast.ProductType) and len(
            value_type.types
        ) == len(target.types):
            return any(
                _may_change(slot, part)
                for slot, part in zip(target.types, value_type.types)
            )
        return True
    if isinstance(target, frog_ast.SetType):
        if isinstance(value_type, frog_ast.SetType):
            return _may_change(target.parameterization, value_type.parameterization)
        return True
    if isinstance(target, frog_ast.ArrayType):
        if isinstance(value_type, frog_ast.ArrayType):
            return _may_change(target.element_type, value_type.element_type)
        return True
    if isinstance(target, frog_ast.MapType):
        if isinstance(value_type, frog_ast.MapType):
            return _may_change(target.key_type, value_type.key_type) or _may_change(
                target.value_type, value_type.value_type
            )
        return True
    if isinstance(target, frog_ast.FunctionType):
        if isinstance(value_type, frog_ast.FunctionType):
            return _may_change(
                target.domain_type, value_type.domain_type
            ) or _may_change(target.range_type, value_type.range_type)
        return True
    return True


def store_keeps_value(
    target_type: Optional[frog_ast.Type],
    value: frog_ast.Expression,
    type_map: NameTypeMap,
    proof_namespace: Optional[frog_ast.Namespace] = None,
) -> bool:
    """True if storing *value* into a slot of *target_type* keeps the value
    exactly, so the slot can be read as *value*.

    False when an ``Int`` part of the value may be reduced into a ``ModInt``
    part of the slot, and also when the slot's type is unknown or the value's
    type cannot be inferred where it would matter. *type_map* must be scoped
    to the method the store sits in.
    """
    if target_type is None:
        return False
    if not type_contains_mod_int(target_type):
        return True
    if isinstance(value, frog_ast.NoneExpression) and isinstance(
        target_type, frog_ast.OptionalType
    ):
        return True
    slot = (
        target_type.the_type
        if isinstance(target_type, frog_ast.OptionalType)
        else target_type
    )
    if isinstance(slot, frog_ast.ModIntType) and _in_range_literal(value, slot):
        return True
    return not _may_change(
        target_type, expression_type(value, type_map, proof_namespace)
    )


def _lvalue_type(
    target: frog_ast.Expression,
    type_map: NameTypeMap,
    proof_namespace: Optional[frog_ast.Namespace],
) -> Optional[frog_ast.Type]:
    if isinstance(target, frog_ast.Variable):
        return type_map.get(target.name)
    if isinstance(target, (frog_ast.ArrayAccess, frog_ast.Slice)):
        return expression_type(target, type_map, proof_namespace)
    return None


def _sampled_element_type(
    domain: frog_ast.ASTNode,
    type_map: NameTypeMap,
    proof_namespace: Optional[frog_ast.Namespace],
) -> Optional[frog_ast.Type]:
    """The type of an element drawn from *domain*: the type itself, or the
    element type of a set-valued expression."""
    if isinstance(domain, frog_ast.Variable):
        declared = type_map.get(domain.name)
        if isinstance(declared, frog_ast.SetType):
            return declared.parameterization
        return domain
    if isinstance(domain, frog_ast.BinaryOperation):
        return _sampled_element_type(domain.left_expression, type_map, proof_namespace)
    if isinstance(domain, frog_ast.Type):
        return domain
    if isinstance(domain, frog_ast.Expression):
        set_type = expression_type(domain, type_map, proof_namespace)
        if isinstance(set_type, frog_ast.SetType):
            return set_type.parameterization
    return None


def _changing_store_target(
    node: frog_ast.ASTNode,
    type_map: NameTypeMap,
    proof_namespace: Optional[frog_ast.Namespace],
) -> Optional[str]:
    """The base name *node* writes if it is a store that may change the
    stored value, else None."""
    if isinstance(node, frog_ast.Assignment):
        target_type = (
            node.the_type
            if node.the_type is not None
            else _lvalue_type(node.var, type_map, proof_namespace)
        )
        if node.the_type is None and target_type is None:
            # An untyped write whose target type is unknown only matters if
            # the target could be a ModInt; the game mentions one, so assume
            # it could.
            return lvalue_base_name(node.var)
        if store_keeps_value(target_type, node.value, type_map, proof_namespace):
            return None
        return lvalue_base_name(node.var)
    if isinstance(node, (frog_ast.Sample, frog_ast.UniqueSample)):
        target_type = (
            node.the_type
            if node.the_type is not None
            else _lvalue_type(node.var, type_map, proof_namespace)
        )
        if not type_contains_mod_int(target_type):
            return None
        element = _sampled_element_type(node.sampled_from, type_map, proof_namespace)
        if _may_change(target_type, element):
            return lvalue_base_name(node.var)
    return None


def _changing_store_targets(
    block: frog_ast.Block,
    type_map: NameTypeMap,
    proof_namespace: Optional[frog_ast.Namespace],
) -> set[str]:
    """Base names written in *block* (at any depth) by a store that may
    change the stored value."""
    names: set[str] = set()

    def _collect(node: frog_ast.ASTNode) -> bool:
        name = _changing_store_target(node, type_map, proof_namespace)
        if name is not None:
            names.add(name)
        return False

    SearchVisitor[frog_ast.ASTNode](_collect).visit(block)
    return names


# One-entry cache: consecutive passes ask about the same game object. Games
# are not mutated in place once built (the pipeline runner relies on that
# too), so the object identities identify the answer. The entry is one tuple,
# replaced in a single assignment, so concurrent callers never see a mixed
# entry.
class _CacheEntry(NamedTuple):
    game: frog_ast.Game
    let_types: Optional[NameTypeMap]
    namespace: Optional[frog_ast.Namespace]
    names: frozenset[str]


_last_answer: list[Optional[_CacheEntry]] = [None]


def coercing_store_names(
    game: frog_ast.Game,
    proof_let_types: Optional[NameTypeMap] = None,
    proof_namespace: Optional[frog_ast.Namespace] = None,
) -> frozenset[str]:
    """Names that some store in *game* writes with a possible change of
    value (an ``Int`` reduced into a ``ModInt``): the target of such a
    declaration, assignment, element write or field initializer.

    A pass must not read one of these names as the expression stored into
    it, nor replace that expression by the name. A game with no ``ModInt``
    type anywhere has none.
    """
    cached = _last_answer[0]
    if (
        cached is not None
        and cached.game is game
        and cached.let_types is proof_let_types
        and cached.namespace is proof_namespace
    ):
        return cached.names
    names: set[str] = set()
    if type_contains_mod_int(game):
        fields_hold_mod_int = any(type_contains_mod_int(f.type) for f in game.fields)
        field_map = NameTypeMap()
        for field in game.fields:
            field_map.set(field.name, field.type)
        if proof_let_types is not None:
            field_map = field_map + proof_let_types
        for field in game.fields:
            if field.value is not None and not store_keeps_value(
                field.type, field.value, field_map, proof_namespace
            ):
                names.add(field.name)
        for method in game.methods:
            if not fields_hold_mod_int and not type_contains_mod_int(method):
                continue
            names |= _changing_store_targets(
                method.block,
                build_method_type_map(game, method, proof_let_types),
                proof_namespace,
            )
    result = frozenset(names)
    _last_answer[0] = _CacheEntry(game, proof_let_types, proof_namespace, result)
    return result


def coercing_store_names_for(
    game: frog_ast.Game, ctx: Optional[PipelineContext]
) -> frozenset[str]:
    """:func:`coercing_store_names` with the proof context of *ctx*."""
    if ctx is None:
        return coercing_store_names(game)
    return coercing_store_names(game, ctx.proof_let_types, ctx.proof_namespace)


def note_coercing_store(
    ctx: Optional[PipelineContext],
    transform_name: str,
    name: str,
    location: Optional[frog_ast.SourceOrigin] = None,
    method: Optional[str] = None,
) -> None:
    """Record that *transform_name* declined to forward *name* because a
    store reduces an ``Int`` into it."""
    if ctx is None:
        return
    ctx.near_misses.append(
        NearMiss(
            transform_name=transform_name,
            reason=(
                f"Cannot forward '{name}': a store converts an Int into its "
                f"ModInt type (reducing it modulo the modulus), so '{name}' "
                f"does not hold the expression it was assigned"
            ),
            location=location,
            suggestion=(
                f"Assign '{name}' a value that already has its ModInt type, or "
                f"write the other game with the same conversion"
            ),
            variable=name,
            method=method,
        )
    )
