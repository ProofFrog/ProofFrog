"""Map key re-indexing under an injective wrapping form (design §3).

:class:`MapKeyReindex` rewrites a ``Map<A, V>`` field to ``Map<B, V>`` when
every use of the map's keys is through a single injective wrapper form.  The
wrapper form is pluggable via the :mod:`_wrappers` protocol; see
``extras/docs/plans/in-progress/2026-04-21-map-reindex-injective-wrapper-protocol.md``
for the design memo.

Historically the only recognized form was a ``FuncCall`` to a
``deterministic injective`` primitive method; that behavior is now owned by
:class:`PrimitiveCallWrapper`.  :class:`GroupExponentWrapper` recognizes
``x ↦ x^k`` on ``GroupElem<G>`` under a ``requires G.order is prime;``
proof-level declaration plus a syntactic known-nonzero check on ``k``.

Soundness argument: see design spec §3.3.  Per-recognizer preconditions
(context-args read-only for primitive calls; prime-order + nonzero exponent
for group exponentiation) are enforced by
:meth:`WrapperShape.precondition_misses` and
:meth:`WrapperShape.context_args_readonly_check`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterator, Optional

from .. import frog_ast
from ..visitors import SearchVisitor, Transformer
from ._base import NearMiss, PipelineContext, TransformPass
from ._wrappers import (
    Recognizer,
    WrapperShape,
    default_recognizers,
    first_match_whole,
    first_match_with_varying,
)


def _first_diagnosis(
    recognizers: list[Recognizer],
    expr: frog_ast.Expression,
    ctx: PipelineContext,
    game: frog_ast.Game,
) -> Optional[str]:
    for r in recognizers:
        diag = r.diagnose_near_miss(expr, ctx, game)
        if diag is not None:
            return diag
    return None


_NAME = "Map Key Reindex"


# ---------------------------------------------------------------------------
# Low-level AST scanning helpers (independent of wrapper form)
# ---------------------------------------------------------------------------


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
    read site, or None for cardinality/iteration sites."""
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


def _map_has_any_access(game: frog_ast.Game, map_name: str) -> bool:
    for method in game.methods:
        if _all_accesses_of_map(method, map_name):
            return True
    return False


# ---------------------------------------------------------------------------
# Shape discovery: dispatch through the recognizer protocol
# ---------------------------------------------------------------------------


def _collect_all_e0_occurrences(
    tree: frog_ast.ASTNode, loop_var: str
) -> list[frog_ast.Expression]:
    occurrences: list[frog_ast.Expression] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        if _is_loop_e0(n, loop_var):
            occurrences.append(n)  # type: ignore[arg-type]
        return False

    SearchVisitor(_visit).visit(tree)
    return occurrences


def _iter_all_nodes(tree: frog_ast.ASTNode) -> Iterator[frog_ast.ASTNode]:
    """Yield every node reachable from *tree* (post-order over attributes)."""
    seen: list[frog_ast.ASTNode] = []

    def _visit(n: frog_ast.ASTNode) -> bool:
        seen.append(n)
        return False

    SearchVisitor(_visit).visit(tree)
    return iter(seen)


def _recognize_e0_wrappers_in_loop(
    loop: frog_ast.GenericFor,
    recognizers: list[Recognizer],
    ctx: PipelineContext,
    game: frog_ast.Game,
) -> tuple[Optional[list[WrapperShape]], Optional[str]]:
    """Scan *loop*'s body for wrapping expressions whose varying-slot argument
    is ``e[0]`` of the loop.

    Returns ``(wrappers, None)`` on success — ``wrappers`` lists one
    :class:`WrapperShape` per discovered wrapping site, and the set of ``e[0]``
    occurrences consumed by those wrappers covers every ``e[0]`` occurrence in
    the loop body.

    Returns ``(None, reason)`` if any ``e[0]`` occurrence is not wrapped by a
    recognized form (bare use).
    """
    loop_var = loop.var_name
    wrappers: list[WrapperShape] = []
    consumed_e0_ids: set[int] = set()

    for n in _iter_all_nodes(loop.block):
        if not isinstance(n, frog_ast.Expression):
            continue
        for e0_node in _collect_all_e0_occurrences(n, loop_var):
            if id(e0_node) in consumed_e0_ids:
                continue
            shape = first_match_with_varying(recognizers, n, e0_node, ctx, game)
            if shape is not None:
                wrappers.append(shape)
                consumed_e0_ids.add(id(e0_node))
                break  # don't re-match the same wrapper for other e[0] kids

    # Verify no bare e[0] remains.
    all_e0 = _collect_all_e0_occurrences(loop.block, loop_var)
    bare = [e for e in all_e0 if id(e) not in consumed_e0_ids]
    if bare:
        return None, (
            "loop body over M.entries uses e[0] outside a recognized "
            "injective wrapper"
        )
    return wrappers, None


@dataclass
class _DiscoveryResult:
    shape: Optional[WrapperShape]
    reason: Optional[str]
    method_name: Optional[str]


def _discover_shape(
    game: frog_ast.Game,
    map_name: str,
    recognizers: list[Recognizer],
    ctx: PipelineContext,
) -> _DiscoveryResult:
    """Two-pass discovery:

    1. Scan every ``M.entries`` loop to pin down the wrapping form and its
       varying slot (via ``e[0]``).  All discovered wrappers must agree on
       :attr:`WrapperShape.identity_key`.
    2. Verify every non-iteration read-site key matches the established shape
       (or, if step 1 discovered nothing, seed the shape from the first valid
       read-site key via :meth:`Recognizer.match_whole`).
    """
    established: Optional[WrapperShape] = None

    def _record(
        shape: WrapperShape, method_name: Optional[str]
    ) -> Optional[_DiscoveryResult]:
        nonlocal established
        if established is None:
            established = shape
            return None
        if established.identity_key == shape.identity_key:
            return None
        return _DiscoveryResult(
            None,
            "call sites disagree on the re-indexing function's shape "
            "(different wrapper form, slot, or context args)",
            method_name,
        )

    # Pass 1: loops.
    for method in game.methods:
        mname = method.signature.name
        for loop in _find_entries_loops(method, map_name):
            wrappers, reason = _recognize_e0_wrappers_in_loop(
                loop, recognizers, ctx, game
            )
            if wrappers is None:
                return _DiscoveryResult(None, reason, mname)
            for w in wrappers:
                bad = _record(w, mname)
                if bad is not None:
                    return bad

    # Pass 2: read sites.
    for method in game.methods:
        mname = method.signature.name
        write_ids = _write_lhs_ids(method, map_name)
        for hit in _all_accesses_of_map(method, map_name):
            if id(hit) in write_ids:
                continue
            key_expr = _extract_read_key(hit)
            if key_expr is None:
                continue
            whole_shape = first_match_whole(recognizers, key_expr, ctx, game)
            if whole_shape is None:
                specific = _first_diagnosis(recognizers, key_expr, ctx, game)
                reason = specific or (
                    "read-site key is not a recognized injective wrapper"
                )
                return _DiscoveryResult(None, reason, mname)
            if established is None:
                established = whole_shape
            else:
                if established.identity_key != whole_shape.identity_key:
                    return _DiscoveryResult(
                        None,
                        "read sites disagree on the re-indexing wrapper shape",
                        mname,
                    )

    if established is None:
        return _DiscoveryResult(None, None, None)
    return _DiscoveryResult(established, None, None)


# ---------------------------------------------------------------------------
# Write-site planning + loop-body rewriting (dispatched through the shape)
# ---------------------------------------------------------------------------


@dataclass
class _WritePlan:
    write_node: frog_ast.Statement
    original_key: frog_ast.Expression
    needs_wrapping: bool


def _collect_writes(
    method: frog_ast.Method,
    map_name: str,
    shape: WrapperShape,
) -> Optional[list[_WritePlan]]:
    """Collect every write ``M[k] = ...`` / ``M[k] <- ...`` in *method*."""
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
            if shape.varying_at(key) is not None:
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


class _WrapKeyTransformer(Transformer):
    """Rewrite occurrences of ``wrapper(..., e[0], ...)`` inside a loop body to
    just ``e[0]`` when the wrapper matches the discovered shape.

    Implemented as a fallback ``transform_ast_node`` so a non-matching node
    falls through to the copy-on-write recursion into children instead of
    being replaced with ``None``.
    """

    def __init__(self, shape: WrapperShape, loop_var: str) -> None:
        self.shape = shape
        self.loop_var = loop_var

    def transform_ast_node(self, node: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        if not isinstance(node, frog_ast.Expression):
            return None
        varying = self.shape.varying_at(node)
        if varying is None or not _is_loop_e0(varying, self.loop_var):
            return None
        return copy.deepcopy(varying)


# ---------------------------------------------------------------------------
# MapKeyReindex — the transform pass
# ---------------------------------------------------------------------------


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a pluggable
    injective wrapping form (see module docstring)."""

    name = _NAME

    def __init__(self, recognizers: Optional[list[Recognizer]] = None) -> None:
        self._recognizers = (
            recognizers if recognizers is not None else default_recognizers()
        )

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for fld in game.fields:
            if not isinstance(fld.type, frog_ast.MapType):
                continue
            rewritten = self._try_rewrite(game, fld, ctx)
            if rewritten is not None:
                return rewritten
        return game

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
                    "keys is wrapped in a single recognized injective form "
                    "(deterministic injective primitive call, or x^k on "
                    "GroupElem<G> with prime-order + nonzero exponent)."
                ),
                variable=map_name,
                method=method_name,
            )
        )

    def _try_rewrite(
        self,
        game: frog_ast.Game,
        fld: frog_ast.Field,
        ctx: PipelineContext,
    ) -> Optional[frog_ast.Game]:
        map_name = fld.name
        disc = _discover_shape(game, map_name, self._recognizers, ctx)
        if disc.shape is None:
            if disc.reason is not None and _map_has_any_access(game, map_name):
                self._emit_near_miss(ctx, disc.reason, map_name, disc.method_name)
            return None
        shape = disc.shape

        # Wrapper-specific context-args check (PrimitiveCallWrapper only).
        bad = shape.context_args_readonly_check(game)
        if bad is not None:
            name, reason = bad
            self._emit_near_miss(
                ctx, f"{reason} (context arg '{name}')", map_name, None
            )
            return None

        # Wrapper-specific preconditions (e.g. prime-order + nonzero exponent).
        pre_misses = shape.precondition_misses(game, ctx)
        if pre_misses:
            for miss in pre_misses:
                self._emit_near_miss(
                    ctx, f"{shape.recognizer_label}: {miss}", map_name, None
                )
            return None

        # Validate writes on the original game.
        for method in game.methods:
            write_plans = _collect_writes(method, map_name, shape)
            if write_plans is None:
                self._emit_near_miss(
                    ctx,
                    "write to the map has a key that is neither a shape-"
                    "matching wrapper nor a simple variable",
                    map_name,
                    method.signature.name,
                )
                return None

        new_game = copy.deepcopy(game)
        self._execute_rewrite(new_game, map_name, shape, ctx)
        if new_game == game:
            return None
        return new_game

    def _execute_rewrite(
        self,
        game: frog_ast.Game,
        map_name: str,
        shape: WrapperShape,
        ctx: PipelineContext,
    ) -> None:
        new_key_type = shape.return_type(game, ctx)
        for fld in game.fields:
            if fld.name == map_name:
                assert isinstance(fld.type, frog_ast.MapType)
                fld.type = frog_ast.MapType(
                    copy.deepcopy(new_key_type),
                    copy.deepcopy(fld.type.value_type),
                )
                break

        for method in game.methods:
            plans = _collect_writes(method, map_name, shape)
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
                target.index = shape.build(target.index)

            for loop in _find_entries_loops(method, map_name):
                self._rewrite_loop(loop, shape, new_key_type)

    def _rewrite_loop(
        self,
        loop: frog_ast.GenericFor,
        shape: WrapperShape,
        new_key_type: frog_ast.Type,
    ) -> None:
        wrapper = _WrapKeyTransformer(shape, loop.var_name)
        loop.block = wrapper.transform(loop.block)
        if isinstance(loop.var_type, frog_ast.ProductType):
            new_types = list(loop.var_type.types)
            if new_types:
                new_types[0] = copy.deepcopy(new_key_type)
            loop.var_type = frog_ast.ProductType(new_types)
