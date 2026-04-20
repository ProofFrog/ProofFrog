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

from dataclasses import dataclass
from typing import Optional, Union

from .. import frog_ast
from ..visitors import SearchVisitor
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
        for hit in _all_accesses_of_map(method, map_name):
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


class MapKeyReindex(TransformPass):
    """Re-index a ``Map<A, V>`` field to ``Map<B, V>`` under a ``deterministic
    injective`` primitive method ``f : A -> B`` (design §3)."""

    name = _NAME

    def apply(
        self, game: frog_ast.Game, ctx: PipelineContext
    ) -> frog_ast.Game:  # pylint: disable=unused-argument
        return game  # implemented in subsequent tasks
