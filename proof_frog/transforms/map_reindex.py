"""Map key re-indexing under an injective deterministic function (design §3).

:class:`MapKeyReindex` rewrites a ``Map<A, V>`` field to ``Map<B, V>`` when every
use of the map's keys is through a ``deterministic injective`` primitive method
``f`` whose varying argument is the map key.  After this pass, scans whose
predicate is ``e[0] == f(..., a, ...)`` become ``e[0] == a`` (under
substitution), which the literal-equality ``LazyMapScan`` can then fold to a
direct lookup.

``f`` may have arity > 1 as long as exactly one argument slot varies across
call sites (the "varying slot", holding the key) and the remaining "context
args" are simple ``Variable`` references to game/scheme fields that are
assigned only inside ``Initialize`` (P1-2 of the design spec §3.2).

Soundness argument: see design spec §3.3 (value preservation, non-collision,
iteration preservation, adversary-invisibility of internal state).  Context
args being read-only post-``Initialize`` ensures ``f`` evaluates to the same
value at every program point for the same varying argument, matching the P1-2
"pure function of the key" requirement.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional, Union

from .. import frog_ast
from ..visitors import SearchVisitor, Transformer
from ._base import NearMiss, PipelineContext, TransformPass, _lookup_primitive_method

_NAME = "Map Key Reindex"


@dataclass(frozen=True)
class _FShape:
    """The shape of the re-indexing function discovered for one map.

    ``context_args`` holds the arg expressions at every non-varying slot of
    ``f``, in positional order (length = arity - 1).  For a single-arg ``f``,
    ``varying_slot == 0`` and ``context_args == ()``.
    """

    f_sig: frog_ast.MethodSignature
    varying_slot: int
    context_args: tuple[frog_ast.Expression, ...]


def _call_matches_shape(
    call: frog_ast.FuncCall,
    shape: _FShape,
    ctx: PipelineContext,
) -> bool:
    """True iff *call* is a call to ``shape.f_sig`` whose non-varying slots
    match ``shape.context_args``."""
    looked_up = _lookup_primitive_method(call.func, ctx.proof_namespace)
    if looked_up is not shape.f_sig:
        return False
    if len(call.args) != len(shape.context_args) + 1:
        return False
    ctx_iter = iter(shape.context_args)
    for i, arg in enumerate(call.args):
        if i == shape.varying_slot:
            continue
        if arg != next(ctx_iter):
            return False
    return True


def _call_varying_arg(call: frog_ast.FuncCall, shape: _FShape) -> frog_ast.Expression:
    return call.args[shape.varying_slot]


def _build_f_call(
    shape: _FShape,
    func_expr: frog_ast.Expression,
    key_expr: frog_ast.Expression,
) -> frog_ast.FuncCall:
    """Build ``f(context..., key, context...)`` with *key_expr* at the varying slot."""
    args: list[frog_ast.Expression] = []
    ctx_iter = iter(shape.context_args)
    total = len(shape.context_args) + 1
    for i in range(total):
        if i == shape.varying_slot:
            args.append(copy.deepcopy(key_expr))
        else:
            args.append(copy.deepcopy(next(ctx_iter)))
    return frog_ast.FuncCall(copy.deepcopy(func_expr), args)


@dataclass(frozen=True)
class _KeyUnderF:
    """A syntactic use of ``M``'s key in the form ``f(..., a, ...)``."""

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
    """A loop over ``M.entries`` where ``e[0]`` is only used inside ``f(..., e[0], ...)``."""

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
    sites (which have no key expression)."""
    if isinstance(hit, frog_ast.ArrayAccess):
        return hit.index
    if isinstance(hit, frog_ast.BinaryOperation):
        return hit.left_expression
    return None


def _is_loop_e0(expr: frog_ast.ASTNode, loop_var: str) -> bool:
    return (
        isinstance(expr, frog_ast.ArrayAccess)
        and isinstance(expr.the_array, frog_ast.Variable)
        and expr.the_array.name == loop_var
        and isinstance(expr.index, frog_ast.Integer)
        and expr.index.num == 0
    )


def _collect_e0_wrapper_calls(
    loop: frog_ast.GenericFor,
    ctx: PipelineContext,
) -> Optional[list[tuple[frog_ast.FuncCall, int]]]:
    """For each ``f(..., e[0], ...)`` call in the loop body, record (call, slot).

    ``slot`` is the argument position occupied by ``e[0]``.  Returns the list on
    success.  Returns ``None`` if any use of ``e[0]`` is bare, or if any
    wrapping call resolves to a non-primitive / non-deterministic /
    non-injective method, or if ``e[0]`` appears in more than one arg slot of
    a single call.
    """
    loop_var = loop.var_name
    results: list[tuple[frog_ast.FuncCall, int]] = []
    allowed_ids: set[int] = set()
    ok = True

    def _scan_calls(n: frog_ast.ASTNode) -> bool:
        nonlocal ok
        if not ok:
            return False
        if isinstance(n, frog_ast.FuncCall):
            slots_with_e0 = [
                i for i, a in enumerate(n.args) if _is_loop_e0(a, loop_var)
            ]
            if not slots_with_e0:
                return False
            if len(slots_with_e0) != 1:
                ok = False
                return False
            looked_up = _lookup_primitive_method(n.func, ctx.proof_namespace)
            if looked_up is None:
                ok = False
                return False
            if not (looked_up.deterministic and looked_up.injective):
                ok = False
                return False
            results.append((n, slots_with_e0[0]))
            allowed_ids.add(id(n.args[slots_with_e0[0]]))
        return False

    SearchVisitor(_scan_calls).visit(loop.block)
    if not ok:
        return None

    def _bare(n: frog_ast.ASTNode) -> bool:
        return _is_loop_e0(n, loop_var) and id(n) not in allowed_ids

    if SearchVisitor(_bare).visit(loop.block) is not None:
        return None
    return results


def _infer_varying_slot_from_fields(
    call: frog_ast.FuncCall,
    game: frog_ast.Game,
) -> Optional[int]:
    """For a multi-arg call, return the unique slot whose argument is not a
    game field reference.  Returns ``None`` if zero or >1 slots qualify.
    """
    field_names = {f.name for f in game.fields}
    non_field_slots: list[int] = []
    for i, arg in enumerate(call.args):
        if isinstance(arg, frog_ast.Variable) and arg.name in field_names:
            continue
        non_field_slots.append(i)
    if len(non_field_slots) == 1:
        return non_field_slots[0]
    return None


def _shape_from_call(
    call: frog_ast.FuncCall,
    varying_slot: int,
    f_sig: frog_ast.MethodSignature,
) -> _FShape:
    ctx_args = tuple(
        copy.deepcopy(a) for i, a in enumerate(call.args) if i != varying_slot
    )
    return _FShape(f_sig=f_sig, varying_slot=varying_slot, context_args=ctx_args)


@dataclass
class _DiscoveryResult:
    shape: Optional[_FShape]
    reason: Optional[str]  # near-miss reason when shape is None
    method_name: Optional[str]  # method in which the failure occurred


def _find_candidate_shape_with_reason(  # pylint: disable=too-many-branches,too-many-return-statements,too-many-locals
    game: frog_ast.Game,
    map_name: str,
    ctx: PipelineContext,
) -> _DiscoveryResult:
    """Discover the ``_FShape`` that describes how this map is re-indexed.

    Algorithm:
      1. Scan all ``M.entries`` loops to collect ``f(..., e[0], ...)`` calls
         and the varying slot each uses.  Every call must agree on
         ``(f_sig, varying_slot, context_args)``.
      2. Verify every read site ``M[k]`` / ``k in M`` has ``k`` matching
         the shape.
      3. If step 1 produced no calls but read sites use ``f(...)`` with a
         consistent arg tuple, fall back to taking the shape from the first
         read site (arity-1 case; for arity > 1 we require a loop to
         disambiguate the varying slot).
    """
    established_shape: Optional[_FShape] = None

    def _record(
        shape: _FShape, method_name: Optional[str]
    ) -> Optional[_DiscoveryResult]:
        nonlocal established_shape
        if established_shape is None:
            established_shape = shape
            return None
        if (
            established_shape.f_sig is shape.f_sig
            and established_shape.varying_slot == shape.varying_slot
            and tuple(established_shape.context_args) == tuple(shape.context_args)
        ):
            return None
        return _DiscoveryResult(
            None,
            "call sites disagree on the re-indexing function's shape "
            "(different f, different varying slot, or different context args)",
            method_name,
        )

    # Pass 1: scan all loops first to pin down varying_slot.
    for method in game.methods:
        mname = method.signature.name
        for loop in _find_entries_loops(method, map_name):
            pairs = _collect_e0_wrapper_calls(loop, ctx)
            if pairs is None:
                return _DiscoveryResult(
                    None,
                    "loop body over M.entries uses e[0] outside a "
                    "deterministic injective wrapper",
                    mname,
                )
            for call, slot in pairs:
                f_sig_here = _lookup_primitive_method(call.func, ctx.proof_namespace)
                assert f_sig_here is not None
                shape = _shape_from_call(call, slot, f_sig_here)
                bad = _record(shape, mname)
                if bad is not None:
                    return bad

    # Pass 2: verify read-site keys.  If no loops established a shape, the
    # first valid read-site call seeds it (arity-1 case or cases where the
    # varying slot is implicit in a single consistent call tuple).
    for method in game.methods:
        mname = method.signature.name
        write_ids = _write_lhs_ids(method, map_name)
        for hit in _all_accesses_of_map(method, map_name):
            if id(hit) in write_ids:
                continue
            key_expr = _extract_read_key(hit)
            if key_expr is None:
                continue
            if not isinstance(key_expr, frog_ast.FuncCall):
                return _DiscoveryResult(
                    None,
                    "read-site key is not a function call wrapping the raw key",
                    mname,
                )
            looked_up = _lookup_primitive_method(key_expr.func, ctx.proof_namespace)
            if looked_up is None:
                return _DiscoveryResult(
                    None,
                    "read-site key wrapper is not a primitive method",
                    mname,
                )
            if not looked_up.deterministic:
                return _DiscoveryResult(
                    None,
                    "read-site key wrapper method is not annotated deterministic",
                    mname,
                )
            if not looked_up.injective:
                return _DiscoveryResult(
                    None,
                    "read-site key wrapper method is not annotated injective",
                    mname,
                )
            if not key_expr.args:
                return _DiscoveryResult(
                    None,
                    "read-site key wrapper has no arguments",
                    mname,
                )
            if established_shape is None:
                # Seed from this read site: only valid if we can unambiguously
                # pick the varying slot.  For arity-1 it's slot 0.  For
                # higher arity we use the heuristic "varying slot is the one
                # that is not a game field reference".
                if len(key_expr.args) == 1:
                    established_shape = _shape_from_call(key_expr, 0, looked_up)
                else:
                    inferred_slot = _infer_varying_slot_from_fields(key_expr, game)
                    if inferred_slot is None:
                        return _DiscoveryResult(
                            None,
                            "multi-arg wrapper has no .entries loop and no "
                            "unique non-field arg to identify the varying slot",
                            mname,
                        )
                    established_shape = _shape_from_call(
                        key_expr, inferred_slot, looked_up
                    )
            else:
                if looked_up is not established_shape.f_sig:
                    return _DiscoveryResult(
                        None,
                        "read sites disagree on which wrapper method to use",
                        mname,
                    )
                if not _call_matches_shape(key_expr, established_shape, ctx):
                    return _DiscoveryResult(
                        None,
                        "read-site call's non-varying slots disagree with the "
                        "established context args",
                        mname,
                    )

    if established_shape is None:
        return _DiscoveryResult(None, None, None)
    return _DiscoveryResult(established_shape, None, None)


def _context_args_are_readonly_fields(
    game: frog_ast.Game,
    shape: _FShape,
) -> Optional[tuple[str, str]]:
    """Verify every context arg is a simple Variable naming a game field that
    is never assigned outside ``Initialize`` (P1-2).

    Returns ``None`` on success, or ``(field_name, reason)`` on failure.
    """
    field_names = {f.name for f in game.fields}
    context_names: set[str] = set()
    for ctx_arg in shape.context_args:
        if not isinstance(ctx_arg, frog_ast.Variable):
            return (
                _expr_label(ctx_arg),
                "context arg is not a simple field reference",
            )
        if ctx_arg.name not in field_names:
            return (
                ctx_arg.name,
                "context arg is not a game/scheme field",
            )
        context_names.add(ctx_arg.name)

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
                n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
                target = n.var
            if isinstance(target, frog_ast.Variable) and target.name in context_names:
                bad = (target.name, "context arg is assigned outside Initialize")
            return False

        SearchVisitor(_visit).visit(method)
        if bad is not None:
            return bad
    return None


def _expr_label(expr: frog_ast.Expression) -> str:
    if isinstance(expr, frog_ast.Variable):
        return expr.name
    return "<non-variable>"


class _WrapKeyTransformer(Transformer):
    """Rewrite occurrences of ``f(..., e[0], ...)`` inside a loop body to
    just ``e[0]`` when ``f`` matches the discovered shape."""

    def __init__(
        self,
        shape: _FShape,
        loop_var: str,
        ctx: PipelineContext,
    ) -> None:
        self.shape = shape
        self.loop_var = loop_var
        self.ctx = ctx

    def transform_func_call(
        self, node: frog_ast.FuncCall
    ) -> Optional[frog_ast.Expression]:
        if not _call_matches_shape(node, self.shape, self.ctx):
            return None
        varying = _call_varying_arg(node, self.shape)
        if not _is_loop_e0(varying, self.loop_var):
            return None
        return copy.deepcopy(varying)


def _find_entries_loops(
    method: frog_ast.Method, map_name: str
) -> list[frog_ast.GenericFor]:
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
    shape: _FShape,
    ctx: PipelineContext,
) -> bool:
    """True if the loop body uses ``e[0]`` outside of a shape-matching wrapper
    call's varying slot."""
    loop_var = loop.var_name
    allowed_ids: set[int] = set()

    def _mark(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.FuncCall) and _call_matches_shape(n, shape, ctx):
            varying = _call_varying_arg(n, shape)
            if _is_loop_e0(varying, loop_var):
                allowed_ids.add(id(varying))
        return False

    SearchVisitor(_mark).visit(loop.block)

    def _bare(n: frog_ast.ASTNode) -> bool:
        return _is_loop_e0(n, loop_var) and id(n) not in allowed_ids

    return SearchVisitor(_bare).visit(loop.block) is not None


@dataclass
class _WritePlan:
    write_node: frog_ast.Statement  # Assignment / Sample / UniqueSample
    original_key: frog_ast.Expression
    needs_wrapping: bool


def _collect_writes(
    method: frog_ast.Method,
    map_name: str,
    shape: _FShape,
    ctx: PipelineContext,
) -> Optional[list[_WritePlan]]:
    """Collect every write ``M[k] = ...`` / ``M[k] <- ...`` in *method*.

    Return a list of plans, or ``None`` if any write has a key that is neither
    a shape-matching ``f(·)`` call nor a simple Variable.
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
            if isinstance(key, frog_ast.FuncCall) and _call_matches_shape(
                key, shape, ctx
            ):
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


def _map_has_any_access(game: frog_ast.Game, map_name: str) -> bool:
    for method in game.methods:
        if _all_accesses_of_map(method, map_name):
            return True
    return False


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a ``deterministic
    injective`` primitive method ``f`` (design §3).  Supports multi-arg ``f``
    where non-varying args are game/scheme fields read-only after
    ``Initialize`` (design §3.2 P1-2)."""

    name = _NAME

    def _emit_near_miss(
        self,
        ctx: PipelineContext,
        reason: str,
        map_name: str,
        method_name: Optional[str],
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_NAME,
                reason=(
                    f"Map '{map_name}'"
                    + (f" in method '{method_name}'" if method_name else "")
                    + f": {reason}"
                ),
                location=None,
                suggestion=(
                    "MapKeyReindex fires only when every use of the map's "
                    "keys is wrapped in a single deterministic injective "
                    "primitive method call sharing the same context args, "
                    "those context args are game fields assigned only in "
                    "Initialize, and write keys are either shape-matching "
                    "calls or simple parameter variables."
                ),
                variable=map_name,
                method=method_name,
            )
        )

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
        disc = _find_candidate_shape_with_reason(game, map_name, ctx)
        if disc.shape is None:
            if disc.reason is not None and _map_has_any_access(game, map_name):
                self._emit_near_miss(ctx, disc.reason, map_name, disc.method_name)
            return None
        shape = disc.shape

        # P1-2: context args must be read-only post-Initialize game fields.
        bad = _context_args_are_readonly_fields(game, shape)
        if bad is not None:
            name, reason = bad
            self._emit_near_miss(
                ctx, f"{reason} (context arg '{name}')", map_name, None
            )
            return None

        # Validate all writes and loops on the ORIGINAL game.
        for method in game.methods:
            write_plans = _collect_writes(method, map_name, shape, ctx)
            if write_plans is None:
                self._emit_near_miss(
                    ctx,
                    "write to the map has a key that is neither a shape-"
                    "matching f(·) call nor a simple variable",
                    map_name,
                    method.signature.name,
                )
                return None
            for loop in _find_entries_loops(method, map_name):
                if _loop_body_has_bare_e0(loop, shape, ctx):
                    self._emit_near_miss(
                        ctx,
                        "loop body over M.entries uses e[0] outside a "
                        "shape-matching wrapper call",
                        map_name,
                        method.signature.name,
                    )
                    return None

        f_call_template = _find_f_call_template(game, shape.f_sig, ctx)

        new_game = copy.deepcopy(game)
        self._execute_rewrite(new_game, map_name, shape, ctx, f_call_template)
        if new_game == game:
            return None
        return new_game

    def _execute_rewrite(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        game: frog_ast.Game,
        map_name: str,
        shape: _FShape,
        ctx: PipelineContext,
        f_call_template: Optional[frog_ast.Expression],
    ) -> None:
        new_key_type = self._infer_new_key_type(game, map_name, shape.f_sig, ctx)
        for fld in game.fields:
            if fld.name == map_name:
                assert isinstance(fld.type, frog_ast.MapType)
                fld.type = frog_ast.MapType(
                    copy.deepcopy(new_key_type),
                    copy.deepcopy(fld.type.value_type),
                )
                break

        for method in game.methods:
            plans = _collect_writes(method, map_name, shape, ctx)
            assert plans is not None
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
                    func_expr = frog_ast.Variable(shape.f_sig.name)
                target.index = _build_f_call(shape, func_expr, raw_key)

            for loop in _find_entries_loops(method, map_name):
                self._rewrite_loop(loop, shape, ctx, new_key_type)

    def _infer_new_key_type(  # pylint: disable=unused-argument
        self,
        game: frog_ast.Game,
        map_name: str,
        f_sig: frog_ast.MethodSignature,
        ctx: PipelineContext,
    ) -> frog_ast.Type:
        ret = f_sig.return_type
        instance_name = _instance_name_for_primitive(game, f_sig, ctx)
        prim: Optional[frog_ast.Primitive] = None
        if instance_name is not None:
            obj = ctx.proof_namespace.get(instance_name)
            if isinstance(obj, frog_ast.Primitive):
                prim = obj
        if prim is None:
            # Post-inline games have no game parameter referencing the
            # primitive; scan proof_namespace for the primitive that owns
            # *f_sig*.
            for obj in ctx.proof_namespace.values():
                if isinstance(obj, frog_ast.Primitive) and any(
                    m is f_sig for m in obj.methods
                ):
                    prim = obj
                    break
        if prim is not None and isinstance(ret, frog_ast.Variable):
            # Prefer the qualified ``<Instance>.<ReturnAlias>`` when the
            # primitive is referenced by a game parameter.
            if instance_name is not None:
                for fld in prim.fields:
                    if fld.name == ret.name:
                        return frog_ast.FieldAccess(
                            frog_ast.Variable(instance_name), ret.name
                        )
            # Otherwise resolve through the primitive's ``Set Image = X;``
            # aliases so the emitted type matches how other fields in this
            # game refer to the same underlying set.
            for fld in prim.fields:
                if fld.name == ret.name and fld.value is not None:
                    return copy.deepcopy(fld.value)
        return copy.deepcopy(ret)

    def _rewrite_loop(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        loop: frog_ast.GenericFor,
        shape: _FShape,
        ctx: PipelineContext,
        new_key_type: frog_ast.Type,
    ) -> None:
        wrapper = _WrapKeyTransformer(shape, loop.var_name, ctx)
        loop.block = wrapper.transform(loop.block)

        if isinstance(loop.var_type, frog_ast.ProductType):
            new_types = list(loop.var_type.types)
            if new_types:
                new_types[0] = copy.deepcopy(new_key_type)
            loop.var_type = frog_ast.ProductType(new_types)


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
