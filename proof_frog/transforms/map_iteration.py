"""Iteration-shape canonicalization (design spec §5.2).

Currently contains:

- :class:`LazyMapScan` -- rewrite

      for ([K, V] e in M.entries) { if (e[0] == key) { return Body(e); } }

  to

      if (key in M) { return Body[e[0]:=key, e[1]:=M[key]]; }

  under the soundness preconditions S1 (body shape) and implicit
  map-key uniqueness (no ``injective`` annotation required for literal
  equality -- at most one ``entry[0]`` equals ``key``).

The injective-challenger-call variant of S2 is handled in the §5.4
oracle-patching plan, not here.
"""

from __future__ import annotations

import copy
from typing import Optional

from .. import frog_ast
from ..visitors import SearchVisitor, Transformer
from ._base import NearMiss, PipelineContext, TransformPass

_LAZY_MAP_SCAN_NAME = "Lazy Map Scan"


def _is_var(expr: frog_ast.ASTNode, name: str) -> bool:
    return isinstance(expr, frog_ast.Variable) and expr.name == name


def _is_tuple_index(expr: frog_ast.ASTNode, var_name: str, idx: int) -> bool:
    """True iff *expr* is ``var_name[idx]`` with ``idx`` a literal integer."""
    if not isinstance(expr, frog_ast.ArrayAccess):
        return False
    if not _is_var(expr.the_array, var_name):
        return False
    i = expr.index
    return isinstance(i, frog_ast.Integer) and i.num == idx


def _references_var(node: frog_ast.ASTNode, var_name: str) -> bool:
    def matcher(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == var_name

    return SearchVisitor(matcher).visit(node) is not None


def _is_entries_access(expr: frog_ast.ASTNode, field_names: set[str]) -> Optional[str]:
    """If *expr* is ``<M>.entries`` where ``M`` is in *field_names*, return ``M``.
    Else return None."""
    if not isinstance(expr, frog_ast.FieldAccess):
        return None
    if expr.name != "entries":
        return None
    if not isinstance(expr.the_object, frog_ast.Variable):
        return None
    if expr.the_object.name not in field_names:
        return None
    return expr.the_object.name


class _TupleAccessSubstitution(Transformer):
    """Replace ``var[0]`` with *zero_repl* and ``var[1]`` with *one_repl*."""

    def __init__(
        self,
        var_name: str,
        zero_repl: frog_ast.Expression,
        one_repl: frog_ast.Expression,
    ) -> None:
        self.var_name = var_name
        self.zero_repl = zero_repl
        self.one_repl = one_repl

    def transform_array_access(
        self, node: frog_ast.ArrayAccess
    ) -> Optional[frog_ast.Expression]:
        if _is_tuple_index(node, self.var_name, 0):
            return copy.deepcopy(self.zero_repl)
        if _is_tuple_index(node, self.var_name, 1):
            return copy.deepcopy(self.one_repl)
        return None


def _bare_references(expr: frog_ast.Expression, var_name: str) -> bool:
    """True iff *expr* contains a ``Variable(var_name)`` reference that is
    NOT the array-base of an ``ArrayAccess(Variable(var_name), Integer(k))``
    for some literal integer ``k``.
    """
    allowed_ids: set[int] = set()

    def _collect(n: frog_ast.ASTNode) -> bool:
        if (
            isinstance(n, frog_ast.ArrayAccess)
            and _is_var(n.the_array, var_name)
            and isinstance(n.index, frog_ast.Integer)
        ):
            allowed_ids.add(id(n.the_array))
        return False

    # Use SearchVisitor purely to walk the tree; predicate always returns False.
    SearchVisitor(_collect).visit(expr)

    def _is_bare(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, frog_ast.Variable)
            and n.name == var_name
            and id(n) not in allowed_ids
        )

    return SearchVisitor(_is_bare).visit(expr) is not None


def _match_scan_body(
    gf: frog_ast.GenericFor,
) -> "tuple[frog_ast.Expression, frog_ast.Expression] | str":
    """Check S1 body shape.

    Return ``(key_expr, body_expr)`` on success, or a string describing the
    first failure (for near-miss reasons).
    """
    stmts = gf.block.statements
    if len(stmts) != 1 or not isinstance(stmts[0], frog_ast.IfStatement):
        return "body is not exactly a single if-statement"
    if_stmt = stmts[0]
    if len(if_stmt.conditions) != 1 or len(if_stmt.blocks) != 1:
        return "if-statement has else or else-if branches"
    if if_stmt.has_else_block():
        return "if-statement has else or else-if branches"
    cond = if_stmt.conditions[0]
    if not (
        isinstance(cond, frog_ast.BinaryOperation)
        and cond.operator == frog_ast.BinaryOperators.EQUALS
    ):
        return "if condition is not a literal equality"
    e_name = gf.var_name
    left, right = cond.left_expression, cond.right_expression
    if _is_tuple_index(left, e_name, 0):
        key_expr = right
    elif _is_tuple_index(right, e_name, 0):
        key_expr = left
    else:
        return "if condition is not of the form e[0] == <expr>"
    if _references_var(key_expr, e_name):
        return "key expression references the loop variable"
    body = if_stmt.blocks[0].statements
    if len(body) != 1 or not isinstance(body[0], frog_ast.ReturnStatement):
        return "if body is not a single return"
    ret = body[0]
    if ret.expression is None:
        return "if body returns no expression"
    body_expr = ret.expression
    if _bare_references(body_expr, e_name):
        return "return expression references loop variable outside e[0]/e[1]"
    return key_expr, body_expr


class LazyMapScan(TransformPass):
    """Rewrite literal-equality scan loops over ``M.entries`` to direct
    lookups (design spec §5.2 / S1)."""

    name = _LAZY_MAP_SCAN_NAME

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        map_fields = {
            f.name for f in game.fields if isinstance(f.type, frog_ast.MapType)
        }
        if not map_fields:
            return game
        new_game = copy.deepcopy(game)
        changed = False
        for method in new_game.methods:
            new_stmts, method_changed = self._rewrite_block(
                list(method.block.statements),
                map_fields,
                method.signature.name,
                ctx,
            )
            if method_changed:
                method.block = frog_ast.Block(new_stmts)
                changed = True
        return new_game if changed else game

    def _rewrite_block(
        self,
        stmts: list[frog_ast.Statement],
        map_fields: set[str],
        method_name: str,
        ctx: PipelineContext,
    ) -> tuple[list[frog_ast.Statement], bool]:
        out: list[frog_ast.Statement] = []
        changed = False
        for stmt in stmts:
            new_stmt = self._try_rewrite_scan(stmt, map_fields, method_name, ctx)
            if new_stmt is None:
                out.append(stmt)
            else:
                out.append(new_stmt)
                changed = True
        return out, changed

    def _try_rewrite_scan(
        self,
        stmt: frog_ast.Statement,
        map_fields: set[str],
        method_name: str,
        ctx: PipelineContext,
    ) -> Optional[frog_ast.Statement]:
        if not isinstance(stmt, frog_ast.GenericFor):
            return None
        map_name = _is_entries_access(stmt.over, map_fields)
        if map_name is None:
            return None
        match = _match_scan_body(stmt)
        if isinstance(match, str):
            self._emit_near_miss(ctx, match, stmt, map_name, method_name)
            return None
        key_expr, body_expr = match
        one_repl = frog_ast.ArrayAccess(
            frog_ast.Variable(map_name), copy.deepcopy(key_expr)
        )
        sub = _TupleAccessSubstitution(stmt.var_name, key_expr, one_repl)
        rewritten_body = sub.transform(copy.deepcopy(body_expr))
        return frog_ast.IfStatement(
            [
                frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.IN,
                    copy.deepcopy(key_expr),
                    frog_ast.Variable(map_name),
                )
            ],
            [frog_ast.Block([frog_ast.ReturnStatement(rewritten_body)])],
        )

    def _emit_near_miss(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        ctx: PipelineContext,
        reason: str,
        stmt: frog_ast.GenericFor,
        map_name: str,
        method_name: str,
    ) -> None:
        ctx.near_misses.append(
            NearMiss(
                transform_name=_LAZY_MAP_SCAN_NAME,
                reason=(
                    f"Loop over '{map_name}.entries' in method "
                    f"'{method_name}' does not match LazyMapScan's literal-"
                    f"equality shape: {reason}"
                ),
                location=getattr(stmt, "origin", None),
                suggestion=(
                    "LazyMapScan fires only on loops whose body is exactly "
                    "`if (e[0] == <key-expr>) { return <body-expr>; }` with "
                    "the key expression not referencing the loop variable "
                    "and the body referencing the loop variable only via "
                    "e[0] / e[1]."
                ),
                variable=map_name,
                method=method_name,
            )
        )
