"""Map key re-indexing under an injective deterministic function (design §3).

:class:`MapKeyReindex` rewrites a ``Map<A, V>`` field to ``Map<B, V>`` when every
use of the map's keys is through a ``deterministic injective`` primitive method
``f : A -> B``.  After this pass, scans whose predicate is ``e[0] == f(a)``
become ``e[0] == a`` (under substitution), which the literal-equality
``LazyMapScan`` can then fold to a direct lookup.

Soundness argument: see design spec §3.3 (value preservation, non-collision,
iteration preservation, adversary-invisibility of internal state).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional, Union

from .. import frog_ast
from ..visitors import SearchVisitor, Transformer
from ._base import PipelineContext, TransformPass, _lookup_primitive_method

_NAME = "Map Key Reindex"


@dataclass(frozen=True)
class _KeyUnderF:
    """A syntactic use of ``M``'s key in the form ``f(arg)``."""

    f_call: frog_ast.FuncCall
    location: frog_ast.SourceOrigin | None


@dataclass(frozen=True)
class _KeyRaw:
    """A syntactic use of ``M``'s key not through ``f`` (near-miss)."""

    key_expr: frog_ast.Expression
    location: frog_ast.SourceOrigin | None
    detail: str


@dataclass(frozen=True)
class _LoopKeyE0:
    """A loop over ``M.entries`` where ``e[0]`` is only used inside ``f(e[0])``."""

    loop: frog_ast.GenericFor


_KeyUse = Union[_KeyUnderF, _KeyRaw, _LoopKeyE0]


def _all_accesses_of_map(
    method: frog_ast.Method,
    map_name: str,
) -> list[frog_ast.ASTNode]:
    """Return every syntactic sub-expression or statement that touches ``M``.

    Covers: ``M[k]`` (read or write LHS), ``k in M``, ``M.entries`` /
    ``M.keys`` / ``M.values`` / ``|M|``, and bare membership checks.
    """
    hits: list[frog_ast.ASTNode] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        if (
            isinstance(n, frog_ast.ArrayAccess)
            and isinstance(n.the_array, frog_ast.Variable)
            and n.the_array.name == map_name
        ):
            hits.append(n)
        if (
            isinstance(n, frog_ast.FieldAccess)
            and isinstance(n.the_object, frog_ast.Variable)
            and n.the_object.name == map_name
        ):
            hits.append(n)
        if (
            isinstance(n, frog_ast.BinaryOperation)
            and n.operator == frog_ast.BinaryOperators.IN
            and isinstance(n.right_expression, frog_ast.Variable)
            and n.right_expression.name == map_name
        ):
            hits.append(n)
        if (
            isinstance(n, frog_ast.UnaryOperation)
            and n.operator == frog_ast.UnaryOperators.SIZE
            and isinstance(n.expression, frog_ast.Variable)
            and n.expression.name == map_name
        ):
            hits.append(n)
        return False

    SearchVisitor(_visit).visit(method)
    return hits


def _expr_is_call_of(
    expr: frog_ast.Expression,
    method_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[frog_ast.FuncCall]:
    """True iff *expr* is ``f(·)`` where f resolves to *method_sig*."""
    if not isinstance(expr, frog_ast.FuncCall):
        return None
    looked_up = _lookup_primitive_method(expr.func, ctx.proof_namespace)
    if looked_up is not method_sig:
        return None
    if len(expr.args) != 1:
        return None
    return expr


def _classify_key_expr(
    key_expr: frog_ast.Expression,
    candidate_f: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> bool:
    """True iff *key_expr* is literally ``candidate_f(·)``."""
    return _expr_is_call_of(key_expr, candidate_f, ctx) is not None


def _write_lhs_ids(method: frog_ast.Method, map_name: str) -> set[int]:
    """Return ids of ArrayAccess nodes that are the LHS of writes to ``M``."""
    ids: set[int] = set()

    def _visit(n: frog_ast.ASTNode) -> bool:
        target: Optional[frog_ast.Expression] = None
        if isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)):
            target = n.var
        if (
            target is not None
            and isinstance(target, frog_ast.ArrayAccess)
            and isinstance(target.the_array, frog_ast.Variable)
            and target.the_array.name == map_name
        ):
            ids.add(id(target))
        return False

    SearchVisitor(_visit).visit(method)
    return ids


def _extract_read_key(hit: frog_ast.ASTNode) -> Optional[frog_ast.Expression]:
    """Given a hit from _all_accesses_of_map, return the key expression at a
    read site (``M[k]``, ``k in M``, etc.), or None for cardinality/iteration
    sites (which have no key expression).

    Note: this returns the index of **any** ``ArrayAccess`` including write
    LHSes; the caller is responsible for disambiguating.
    """
    if isinstance(hit, frog_ast.ArrayAccess):
        return hit.index
    if isinstance(hit, frog_ast.BinaryOperation):
        return hit.left_expression
    return None


def _find_candidate_f(
    game: frog_ast.Game,
    map_name: str,
    ctx: PipelineContext,
) -> Optional[frog_ast.MethodSignature]:
    """Scan all read-site key expressions of M across all methods.  Return the
    unique primitive method ``f`` used at every read site, or ``None`` if no
    such f exists (too many candidates, non-injective, not deterministic, or a
    read site uses a raw key).
    """
    read_site_f: Optional[frog_ast.MethodSignature] = None
    for method in game.methods:
        write_ids = _write_lhs_ids(method, map_name)
        for hit in _all_accesses_of_map(method, map_name):
            if id(hit) in write_ids:
                continue
            key_expr = _extract_read_key(hit)
            if key_expr is None:
                continue
            if not isinstance(key_expr, frog_ast.FuncCall):
                return None
            looked_up = _lookup_primitive_method(key_expr.func, ctx.proof_namespace)
            if looked_up is None:
                return None
            if not (looked_up.deterministic and looked_up.injective):
                return None
            if len(key_expr.args) != 1:
                return None
            if read_site_f is None:
                read_site_f = looked_up
            elif read_site_f is not looked_up:
                return None
    return read_site_f


@dataclass
class _WritePlan:
    write_node: frog_ast.Statement  # Assignment / Sample / UniqueSample
    original_key: frog_ast.Expression
    needs_wrapping: bool


@dataclass
class _LoopPlan:
    loop: frog_ast.GenericFor


class _WrapKeyTransformer(Transformer):
    """Rewrite occurrences of ``f(e[0])`` inside a loop body to just ``e[0]``."""

    def __init__(
        self,
        f_sig: frog_ast.MethodSignature,
        loop_var: str,
        ctx: PipelineContext,
    ) -> None:
        self.f_sig = f_sig
        self.loop_var = loop_var
        self.ctx = ctx

    def transform_func_call(
        self, node: frog_ast.FuncCall
    ) -> Optional[frog_ast.Expression]:
        looked_up = _lookup_primitive_method(node.func, self.ctx.proof_namespace)
        if looked_up is not self.f_sig:
            return None
        if len(node.args) != 1:
            return None
        arg = node.args[0]
        if (
            isinstance(arg, frog_ast.ArrayAccess)
            and isinstance(arg.the_array, frog_ast.Variable)
            and arg.the_array.name == self.loop_var
            and isinstance(arg.index, frog_ast.Integer)
            and arg.index.num == 0
        ):
            return copy.deepcopy(arg)
        return None


def _find_entries_loops(
    method: frog_ast.Method, map_name: str
) -> list[frog_ast.GenericFor]:
    """Return all GenericFor loops iterating over ``M.entries``."""
    loops: list[frog_ast.GenericFor] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        if (
            isinstance(n, frog_ast.GenericFor)
            and isinstance(n.over, frog_ast.FieldAccess)
            and n.over.name == "entries"
            and isinstance(n.over.the_object, frog_ast.Variable)
            and n.over.the_object.name == map_name
        ):
            loops.append(n)
        return False

    SearchVisitor(_visit).visit(method)
    return loops


def _loop_body_has_bare_e0(
    loop: frog_ast.GenericFor,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> bool:
    """True if the loop body uses ``e[0]`` outside of ``f(e[0])``."""
    loop_var = loop.var_name
    allowed_ids: set[int] = set()

    def _mark(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.FuncCall):
            looked_up = _lookup_primitive_method(n.func, ctx.proof_namespace)
            if looked_up is f_sig and len(n.args) == 1:
                a = n.args[0]
                if (
                    isinstance(a, frog_ast.ArrayAccess)
                    and isinstance(a.the_array, frog_ast.Variable)
                    and a.the_array.name == loop_var
                    and isinstance(a.index, frog_ast.Integer)
                    and a.index.num == 0
                ):
                    allowed_ids.add(id(a))
        return False

    SearchVisitor(_mark).visit(loop.block)

    def _bare(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, frog_ast.ArrayAccess)
            and isinstance(n.the_array, frog_ast.Variable)
            and n.the_array.name == loop_var
            and isinstance(n.index, frog_ast.Integer)
            and n.index.num == 0
            and id(n) not in allowed_ids
        )

    return SearchVisitor(_bare).visit(loop.block) is not None


def _collect_writes(
    method: frog_ast.Method,
    map_name: str,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[list[_WritePlan]]:
    """Collect every write ``M[k] = ...`` / ``M[k] <- ...`` in *method*.

    Return a list of plans, or ``None`` if any write has a key that is neither
    ``f(·)`` nor a simple Variable.
    """
    plans: list[_WritePlan] = []
    ok = True

    def _visit(n: frog_ast.ASTNode) -> bool:
        nonlocal ok
        if not ok:
            return False
        target: Optional[frog_ast.Expression] = None
        if isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)):
            target = n.var
        if (
            target is not None
            and isinstance(target, frog_ast.ArrayAccess)
            and isinstance(target.the_array, frog_ast.Variable)
            and target.the_array.name == map_name
        ):
            key = target.index
            if _expr_is_call_of(key, f_sig, ctx) is not None:
                plans.append(
                    _WritePlan(
                        write_node=n,  # type: ignore[arg-type]
                        original_key=key,
                        needs_wrapping=False,
                    )
                )
            elif isinstance(key, frog_ast.Variable):
                plans.append(
                    _WritePlan(
                        write_node=n,  # type: ignore[arg-type]
                        original_key=key,
                        needs_wrapping=True,
                    )
                )
            else:
                ok = False
        return False

    SearchVisitor(_visit).visit(method)
    return plans if ok else None


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a ``deterministic
    injective`` primitive method ``f : A -> B`` (design §3)."""

    name = _NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for fld in game.fields:
            if not isinstance(fld.type, frog_ast.MapType):
                continue
            rewritten = self._try_rewrite(game, fld, ctx)
            if rewritten is not None:
                return rewritten
        return game

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        fld: frog_ast.Field,
        ctx: PipelineContext,
    ) -> Optional[frog_ast.Game]:
        map_name = fld.name
        f_sig = _find_candidate_f(game, map_name, ctx)
        if f_sig is None:
            return None

        # Validate all writes and loops on the ORIGINAL game, bail out if any
        # write has an unsupported key shape or any loop has a bare e[0].
        for method in game.methods:
            write_plans = _collect_writes(method, map_name, f_sig, ctx)
            if write_plans is None:
                return None
            for loop in _find_entries_loops(method, map_name):
                if _loop_body_has_bare_e0(loop, f_sig, ctx):
                    return None

        # We need a reference call expression like ``TT.Eval`` to clone when
        # wrapping raw write keys.  Grab one from the existing read sites.
        f_call_template = _find_f_call_template(game, f_sig, ctx)

        # All preconditions pass; produce a deep-copied rewritten game.
        new_game = copy.deepcopy(game)
        self._execute_rewrite(new_game, map_name, f_sig, ctx, f_call_template)
        if new_game == game:
            return None
        return new_game

    def _execute_rewrite(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        game: frog_ast.Game,
        map_name: str,
        f_sig: frog_ast.MethodSignature,
        ctx: PipelineContext,
        f_call_template: Optional[frog_ast.Expression],
    ) -> None:
        # 1. Rewrite field type: Map<A, V> -> Map<B, V>
        #    Use a field-type taken from a read-site call if available so the
        #    written type uses the same reference shape as the source text
        #    (e.g. ``TT.Image`` rather than the bare ``Image`` that appears on
        #    the primitive method's return type).
        new_key_type = self._infer_new_key_type(game, map_name, f_sig, ctx)
        for fld in game.fields:
            if fld.name == map_name:
                assert isinstance(fld.type, frog_ast.MapType)
                fld.type = frog_ast.MapType(
                    copy.deepcopy(new_key_type),
                    copy.deepcopy(fld.type.value_type),
                )
                break

        # 2. For each method: rewrite writes and loops.
        for method in game.methods:
            # Wrap write keys where needed.
            plans = _collect_writes(method, map_name, f_sig, ctx)
            assert plans is not None  # validated in _try_rewrite
            for plan in plans:
                if not plan.needs_wrapping:
                    continue
                write = plan.write_node
                assert isinstance(
                    write,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                target = write.var
                assert isinstance(target, frog_ast.ArrayAccess)
                raw_key = target.index
                if f_call_template is not None:
                    func_expr: frog_ast.Expression = copy.deepcopy(f_call_template)
                else:
                    func_expr = frog_ast.Variable(f_sig.name)
                target.index = frog_ast.FuncCall(func_expr, [copy.deepcopy(raw_key)])

            # Rewrite loop bodies: wrap e[0] element type and strip f(e[0]).
            for loop in _find_entries_loops(method, map_name):
                self._rewrite_loop(loop, f_sig, ctx)

    def _infer_new_key_type(  # pylint: disable=unused-argument
        self,
        game: frog_ast.Game,
        map_name: str,
        f_sig: frog_ast.MethodSignature,
        ctx: PipelineContext,
    ) -> frog_ast.Type:
        """Pick the type to use for the new map key.

        Prefer ``<Instance>.<ReturnAlias>`` (e.g. ``TT.Image``) when the
        primitive declares the method's return type as a named alias matching
        a ``Set`` field on the primitive; otherwise use ``f_sig.return_type``.
        """
        ret = f_sig.return_type
        # Identify the primitive instance name used in the game (via a
        # read-site call or by scanning game parameters).
        instance_name = _instance_name_for_primitive(game, f_sig, ctx)
        if instance_name is None:
            return copy.deepcopy(ret)
        if isinstance(ret, frog_ast.Variable):
            # Check that the primitive declares a field/Set named ret.name.
            prim = ctx.proof_namespace.get(instance_name)
            if isinstance(prim, frog_ast.Primitive):
                for fld in prim.fields:
                    if fld.name == ret.name:
                        return frog_ast.FieldAccess(
                            frog_ast.Variable(instance_name), ret.name
                        )
        return copy.deepcopy(ret)

    def _rewrite_loop(
        self,
        loop: frog_ast.GenericFor,
        f_sig: frog_ast.MethodSignature,
        ctx: PipelineContext,
    ) -> None:
        # Strip f(e[0]) -> e[0] inside the body.
        wrapper = _WrapKeyTransformer(f_sig, loop.var_name, ctx)
        loop.block = wrapper.transform(loop.block)

        # Update loop variable's tuple type: [A, V] -> [B, V] if it's a product.
        if isinstance(loop.var_type, frog_ast.ProductType):
            new_types = list(loop.var_type.types)
            if new_types:
                new_types[0] = copy.deepcopy(f_sig.return_type)
            loop.var_type = frog_ast.ProductType(new_types)


def _instance_name_for_primitive(
    game: frog_ast.Game,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[str]:
    """Return the name under which the primitive containing *f_sig* is
    referenced in *game* (via its parameters).

    If any parameter of *game* has a type whose name resolves (in
    ``ctx.proof_namespace``) to a primitive containing *f_sig*, return the
    parameter name.  Else return None.
    """
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


def _find_f_call_template(
    game: frog_ast.Game,
    f_sig: frog_ast.MethodSignature,
    ctx: PipelineContext,
) -> Optional[frog_ast.Expression]:
    """Return the ``.func`` expression from any existing call to *f_sig* in
    *game*, which we clone when wrapping raw write keys."""
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
    if found:
        return found[0]
    return None
