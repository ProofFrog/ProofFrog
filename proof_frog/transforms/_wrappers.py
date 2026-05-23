"""Injective-wrapper protocol for :mod:`proof_frog.transforms.map_reindex`.

``MapKeyReindex`` rewrites ``Map<A, V>`` to ``Map<B, V>`` when every use of
the map's keys is through a single injective wrapper form.  Historically the
only recognized form was a ``FuncCall`` to a ``deterministic injective``
primitive method (``PrimitiveCallWrapper``).  This module generalizes the
notion so additional forms (initially ``x ↦ x^k`` on ``GroupElem<G>`` under
a prime-order requirement) can plug in as stateless recognizer classes
without rewriting ``MapKeyReindex`` for each new shape.

Design memo: ``extras/docs/plans/in-progress/2026-04-21-map-reindex-injective-wrapper-protocol.md``.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Hashable, Optional

from .. import frog_ast
from ..visitors import SearchVisitor
from ._base import PipelineContext, _lookup_primitive_method
from ._requirements import is_known_nonzero

# ---------------------------------------------------------------------------
# WrapperShape: the polymorphic "established match" carrier
# ---------------------------------------------------------------------------


class WrapperShape(ABC):
    """Identity + operations of an injective wrapper discovered on the game.

    A ``WrapperShape`` instance is the thing ``MapKeyReindex`` pins down
    during discovery: it answers "is this other AST site the same wrapping
    form?", "what was its varying-slot sub-expression?", and "how do I
    re-wrap a raw key with this same wrapper?".
    """

    @property
    @abstractmethod
    def identity_key(self) -> Hashable:
        """Hashable value; two shapes are "the same wrapping form" iff their
        identity keys compare equal."""

    @property
    @abstractmethod
    def recognizer_label(self) -> str:
        """Stable short label, used in near-miss text."""

    @abstractmethod
    def varying_at(self, expr: frog_ast.Expression) -> Optional[frog_ast.Expression]:
        """If *expr* is an occurrence of this wrapper with the same identity,
        return the varying-slot sub-expression at this site.  Else None."""

    @abstractmethod
    def build(self, key_expr: frog_ast.Expression) -> frog_ast.Expression:
        """Build a new wrapper instance with *key_expr* at the varying slot."""

    @abstractmethod
    def return_type(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Type:
        """Return type of this wrapper — becomes the new map-key type."""

    def precondition_misses(
        self,
        game: frog_ast.Game,  # pylint: disable=unused-argument
        ctx: PipelineContext,  # pylint: disable=unused-argument
    ) -> list[str]:
        """Extra preconditions beyond shape matching.  Empty list = OK."""
        return []

    def context_args_readonly_check(
        self, game: frog_ast.Game  # pylint: disable=unused-argument
    ) -> Optional[tuple[str, str]]:
        """Wrapper-specific: if this shape carries context args, verify each
        is a game field assigned only in ``Initialize`` (§3.2 P1-2).

        Return ``None`` on success, or ``(field_name, reason)`` on failure.
        Default for wrappers with no context args: always ``None``.
        """
        return None


# ---------------------------------------------------------------------------
# Recognizer: the plug-in point — one per injective form
# ---------------------------------------------------------------------------


class Recognizer(ABC):
    """Recognizes a specific injective wrapping form in AST.

    Recognizers are stateless; they are registered in a module-level list on
    ``MapKeyReindex`` and consulted in order.  First match wins.
    """

    @abstractmethod
    def match_with_varying(
        self,
        wrapping_expr: frog_ast.Expression,
        varying_expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        """Try to recognize *wrapping_expr* as an instance of this wrapper
        whose varying-slot sub-expression is *varying_expr*.

        Used when the varying expression is known from context (e.g. ``e[0]``
        inside an ``M.entries`` loop).  Return the induced :class:`WrapperShape`
        or None.
        """

    @abstractmethod
    def match_whole(
        self,
        expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        """Try to recognize *expr* as a whole instance of this wrapper, with
        the varying slot inferred by recognizer-specific heuristics.

        Used for read-site keys ``M[k]`` where ``k`` is the wrapping
        expression itself.  Return the induced :class:`WrapperShape` or None.
        """

    def diagnose_near_miss(
        self,
        expr: frog_ast.Expression,  # pylint: disable=unused-argument
        ctx: PipelineContext,  # pylint: disable=unused-argument
        game: frog_ast.Game,  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """If *expr* looks like this wrapper form but some precondition
        prevents matching, return a specific human-readable explanation.

        Called only after :meth:`match_whole` returned ``None``; used to
        preserve specificity in near-miss text.  Default: no diagnosis.
        """
        return None


def first_match_with_varying(
    recognizers: list[Recognizer],
    wrapping_expr: frog_ast.Expression,
    varying_expr: frog_ast.Expression,
    ctx: PipelineContext,
    game: frog_ast.Game,
) -> Optional[WrapperShape]:
    """Walk *recognizers* in order; return the first non-None match."""
    for r in recognizers:
        shape = r.match_with_varying(wrapping_expr, varying_expr, ctx, game)
        if shape is not None:
            return shape
    return None


def first_match_whole(
    recognizers: list[Recognizer],
    expr: frog_ast.Expression,
    ctx: PipelineContext,
    game: frog_ast.Game,
) -> Optional[WrapperShape]:
    """Walk *recognizers* in order; return the first non-None match."""
    for r in recognizers:
        shape = r.match_whole(expr, ctx, game)
        if shape is not None:
            return shape
    return None


# ---------------------------------------------------------------------------
# PrimitiveCallWrapper — the original behavior
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PrimCallShape(WrapperShape):
    """Wrapper ``f(..., x, ...)`` where ``f`` is a ``deterministic injective``
    primitive method, ``varying_slot`` holds the key, and ``context_args`` are
    the non-varying argument expressions in positional order."""

    f_sig: frog_ast.MethodSignature
    varying_slot: int
    context_args: tuple[frog_ast.Expression, ...]
    # The callee ``.func`` expression from some existing call site; cloned
    # when rebuilding calls in :meth:`build`.  Set after discovery.
    func_template: frog_ast.Expression

    @property
    def identity_key(self) -> Hashable:
        return (
            "prim-call",
            id(self.f_sig),
            self.varying_slot,
            tuple(str(a) for a in self.context_args),
        )

    @property
    def recognizer_label(self) -> str:
        return "deterministic injective primitive method"

    def varying_at(self, expr: frog_ast.Expression) -> Optional[frog_ast.Expression]:
        if not isinstance(expr, frog_ast.FuncCall):
            return None
        if len(expr.args) != len(self.context_args) + 1:
            return None
        ctx_iter = iter(self.context_args)
        for i, arg in enumerate(expr.args):
            if i == self.varying_slot:
                continue
            if arg != next(ctx_iter):
                return None
        return expr.args[self.varying_slot]

    def build(self, key_expr: frog_ast.Expression) -> frog_ast.Expression:
        args: list[frog_ast.Expression] = []
        ctx_iter = iter(self.context_args)
        total = len(self.context_args) + 1
        for i in range(total):
            if i == self.varying_slot:
                args.append(copy.deepcopy(key_expr))
            else:
                args.append(copy.deepcopy(next(ctx_iter)))
        return frog_ast.FuncCall(copy.deepcopy(self.func_template), args)

    def return_type(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Type:
        return _infer_prim_call_return_type(game, self.f_sig, ctx)

    def context_args_readonly_check(
        self, game: frog_ast.Game
    ) -> Optional[tuple[str, str]]:
        field_names = {f.name for f in game.fields}
        context_names: set[str] = set()
        for c_arg in self.context_args:
            if not isinstance(c_arg, frog_ast.Variable):
                label = (
                    c_arg.name
                    if isinstance(c_arg, frog_ast.Variable)
                    else "<non-variable>"
                )
                return (label, "context arg is not a simple field reference")
            if c_arg.name not in field_names:
                return (c_arg.name, "context arg is not a game/scheme field")
            context_names.add(c_arg.name)
        if not context_names:
            return None
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            bad: Optional[tuple[str, str]] = None

            def _visit(n: frog_ast.ASTNode) -> bool:
                nonlocal bad
                if bad is not None:
                    return False
                target: Optional[frog_ast.Expression] = None
                if isinstance(
                    n,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                ):
                    target = n.var
                if (
                    isinstance(target, frog_ast.Variable)
                    and target.name in context_names
                ):
                    bad = (target.name, "context arg is assigned outside Initialize")
                return False

            SearchVisitor(_visit).visit(method)
            if bad is not None:
                return bad
        return None


def _infer_prim_call_return_type(
    game: frog_ast.Game,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> frog_ast.Type:
    """Mirror of the historical :meth:`MapKeyReindex._infer_new_key_type` logic
    for primitive-call wrappers."""
    ret = f_sig.return_type
    instance_name = _instance_name_for_primitive(game, f_sig, ctx)
    prim: Optional[frog_ast.Primitive] = None
    if instance_name is not None:
        obj = ctx.proof_namespace.get(instance_name)
        if isinstance(obj, frog_ast.Primitive):
            prim = obj
    if prim is None:
        for obj in ctx.proof_namespace.values():
            if isinstance(obj, frog_ast.Primitive) and any(
                m is f_sig for m in obj.methods
            ):
                prim = obj
                break
    if prim is not None and isinstance(ret, frog_ast.Variable):
        if instance_name is not None:
            for fld in prim.fields:
                if fld.name == ret.name:
                    return frog_ast.FieldAccess(
                        frog_ast.Variable(instance_name), ret.name
                    )
        for fld in prim.fields:
            if fld.name == ret.name and fld.value is not None:
                return copy.deepcopy(fld.value)  # type: ignore[return-value]
    return copy.deepcopy(ret)


def _instance_name_for_primitive(
    game: frog_ast.Game,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[str]:
    for param in game.parameters:
        type_name: Optional[str] = None
        if isinstance(param.type, frog_ast.Variable):
            type_name = param.type.name
        if type_name is None:
            continue
        obj = ctx.proof_namespace.get(type_name)
        if not isinstance(obj, frog_ast.Primitive):
            continue
        for m in obj.methods:
            if m is f_sig:
                return param.name
    return None


def _find_prim_call_template(
    game: frog_ast.Game,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[frog_ast.Expression]:
    found: list[frog_ast.Expression] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.FuncCall):
            if (
                _lookup_primitive_method(n.func, ctx.proof_namespace) is f_sig
                and not found
            ):
                found.append(n.func)
        return False

    SearchVisitor(_visit).visit(game)
    return found[0] if found else None


def _infer_varying_slot_from_fields(
    call: frog_ast.FuncCall, game: frog_ast.Game
) -> Optional[int]:
    field_names = {f.name for f in game.fields}
    non_field_slots: list[int] = []
    for i, arg in enumerate(call.args):
        if isinstance(arg, frog_ast.Variable) and arg.name in field_names:
            continue
        non_field_slots.append(i)
    return non_field_slots[0] if len(non_field_slots) == 1 else None


class PrimitiveCallWrapper(Recognizer):
    """Recognizes ``f(...)`` where ``f`` is a ``deterministic injective``
    primitive method."""

    def diagnose_near_miss(
        self,
        expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[str]:
        if not isinstance(expr, frog_ast.FuncCall):
            return None
        looked_up = _lookup_primitive_method(expr.func, ctx.proof_namespace)
        if looked_up is None:
            return "read-site key wrapper is not a primitive method"
        if not looked_up.deterministic:
            return "read-site key wrapper method is not annotated deterministic"
        if not looked_up.injective:
            return "read-site key wrapper method is not annotated injective"
        if not expr.args:
            return "read-site key wrapper has no arguments"
        if len(expr.args) > 1:
            return (
                "multi-arg wrapper has no .entries loop and no unique "
                "non-field arg to identify the varying slot"
            )
        return None

    def match_with_varying(
        self,
        wrapping_expr: frog_ast.Expression,
        varying_expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        if not isinstance(wrapping_expr, frog_ast.FuncCall):
            return None
        slots_with_var = [
            i for i, a in enumerate(wrapping_expr.args) if a is varying_expr
        ]
        if len(slots_with_var) != 1:
            return None
        slot = slots_with_var[0]
        looked_up = _lookup_primitive_method(wrapping_expr.func, ctx.proof_namespace)
        if looked_up is None:
            return None
        if not (looked_up.deterministic and looked_up.injective):
            return None
        ctx_args = tuple(
            copy.deepcopy(a) for i, a in enumerate(wrapping_expr.args) if i != slot
        )
        return _PrimCallShape(
            f_sig=looked_up,
            varying_slot=slot,
            context_args=ctx_args,
            func_template=copy.deepcopy(wrapping_expr.func),
        )

    def match_whole(
        self,
        expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        if not isinstance(expr, frog_ast.FuncCall):
            return None
        looked_up = _lookup_primitive_method(expr.func, ctx.proof_namespace)
        if looked_up is None:
            return None
        if not (looked_up.deterministic and looked_up.injective):
            return None
        if not expr.args:
            return None
        if len(expr.args) == 1:
            slot = 0
        else:
            slot_opt = _infer_varying_slot_from_fields(expr, game)
            if slot_opt is None:
                return None
            slot = slot_opt
        ctx_args = tuple(copy.deepcopy(a) for i, a in enumerate(expr.args) if i != slot)
        return _PrimCallShape(
            f_sig=looked_up,
            varying_slot=slot,
            context_args=ctx_args,
            func_template=copy.deepcopy(expr.func),
        )


# ---------------------------------------------------------------------------
# GroupExponentWrapper — x ↦ x^k on GroupElem<G> under prime-order + nonzero
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GroupExpShape(WrapperShape):
    """Wrapper ``x ↦ x^k`` where ``x: GroupElem<G>``, ``k`` is known-nonzero,
    and ``G.order is prime`` is declared by the proof's ``requires:`` block."""

    group_expr: frog_ast.Expression
    k_expr: frog_ast.Expression

    @property
    def identity_key(self) -> Hashable:
        return ("group-exp", str(self.group_expr), str(self.k_expr))

    @property
    def recognizer_label(self) -> str:
        return "group exponentiation x^k on GroupElem<G>"

    def varying_at(self, expr: frog_ast.Expression) -> Optional[frog_ast.Expression]:
        if not isinstance(expr, frog_ast.BinaryOperation):
            return None
        if expr.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return None
        if expr.right_expression != self.k_expr:
            return None
        return expr.left_expression

    def build(self, key_expr: frog_ast.Expression) -> frog_ast.Expression:
        return frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            copy.deepcopy(key_expr),
            copy.deepcopy(self.k_expr),
        )

    def return_type(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Type:
        return frog_ast.GroupElemType(copy.deepcopy(self.group_expr))

    def precondition_misses(
        self, game: frog_ast.Game, ctx: PipelineContext
    ) -> list[str]:
        misses: list[str] = []
        if not ctx.has_prime_order_requirement(self.group_expr):
            misses.append(
                f"exponent wrapper `x^{self.k_expr}` requires "
                f"`requires {self.group_expr}.order is prime;` in the proof"
            )
        k_expr = self.k_expr
        if isinstance(k_expr, frog_ast.Integer):
            if k_expr.num == 0:  # pylint: disable=no-member
                misses.append("exponent k is the literal 0; x^0 is not injective")
        elif isinstance(k_expr, frog_ast.Variable):
            if not is_known_nonzero(k_expr.name, game):
                misses.append(
                    f"exponent `{k_expr.name}` is not known-nonzero; "
                    f"sample it via `<-uniq[{{0}}] T` (or `<- T \\ {{0}}`) "
                    f"so the engine can treat x^{k_expr.name} as injective"
                )
        return misses


def _find_generic_fors_with_name(
    method: frog_ast.Method, loop_var_name: str
) -> list[frog_ast.GenericFor]:
    found: list[frog_ast.GenericFor] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.GenericFor) and n.var_name == loop_var_name:
            found.append(n)
        return False

    SearchVisitor(_visit).visit(method)
    return found


def _expr_is_group_elem_on_game(
    expr: frog_ast.Expression, game: frog_ast.Game
) -> Optional[frog_ast.Expression]:
    """Lightweight check: is *expr* typed ``GroupElem<G>`` in *game*'s scope?

    Returns the ``G`` expression on success, else ``None``.  Handles the
    cases that matter for §4.3: *expr* is a game field, a game parameter, or
    a method parameter whose declared type is ``GroupElem<G>``.  Deeper
    expressions (compositions, array accesses) fall through to ``None``.
    """
    if isinstance(expr, frog_ast.Variable):
        name = expr.name
        for fld in game.fields:
            if fld.name == name and isinstance(fld.type, frog_ast.GroupElemType):
                return fld.type.group
        for param in game.parameters:
            if param.name == name and isinstance(param.type, frog_ast.GroupElemType):
                return param.type.group
        for method in game.methods:
            for param in method.signature.parameters:
                if param.name == name and isinstance(
                    param.type, frog_ast.GroupElemType
                ):
                    return param.type.group
        return None
    if (
        isinstance(expr, frog_ast.ArrayAccess)
        and isinstance(expr.the_array, frog_ast.Variable)
        and isinstance(expr.index, frog_ast.Integer)
    ):
        loop_var_name = expr.the_array.name
        slot = expr.index.num
        for method in game.methods:
            loops = _find_generic_fors_with_name(method, loop_var_name)
            for loop in loops:
                vt = loop.var_type
                if isinstance(vt, frog_ast.ProductType) and slot < len(vt.types):
                    elem_t = vt.types[slot]
                    if isinstance(elem_t, frog_ast.GroupElemType):
                        return elem_t.group
    return None


class GroupExponentWrapper(Recognizer):
    """Recognizes ``x^k`` where ``x: GroupElem<G>``."""

    def _try_build_shape(
        self,
        expr: frog_ast.BinaryOperation,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        group = _expr_is_group_elem_on_game(expr.left_expression, game)
        if group is None:
            return None
        return _GroupExpShape(
            group_expr=copy.deepcopy(group),
            k_expr=copy.deepcopy(expr.right_expression),
        )

    def match_with_varying(
        self,
        wrapping_expr: frog_ast.Expression,
        varying_expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        if not isinstance(wrapping_expr, frog_ast.BinaryOperation):
            return None
        if wrapping_expr.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return None
        if wrapping_expr.left_expression is not varying_expr:
            return None
        return self._try_build_shape(wrapping_expr, game)

    def match_whole(
        self,
        expr: frog_ast.Expression,
        ctx: PipelineContext,
        game: frog_ast.Game,
    ) -> Optional[WrapperShape]:
        if not isinstance(expr, frog_ast.BinaryOperation):
            return None
        if expr.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return None
        return self._try_build_shape(expr, game)


# ---------------------------------------------------------------------------
# Default registry
# ---------------------------------------------------------------------------


def default_recognizers() -> list[Recognizer]:
    """Ordered list of recognizers consulted by :class:`MapKeyReindex`."""
    return [PrimitiveCallWrapper(), GroupExponentWrapper()]
