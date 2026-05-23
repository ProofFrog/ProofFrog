"""Helpers for consuming proof-level ``requires:`` declarations in transforms."""

from __future__ import annotations

from .. import frog_ast
from ..visitors import SearchVisitor


def _set_contains_literal_zero(expr: frog_ast.Expression) -> bool:
    """True if *expr* is a :class:`frog_ast.Set` containing a literal ``0``."""
    if not isinstance(expr, frog_ast.Set):
        return False
    for element in expr.elements:
        if isinstance(element, frog_ast.Integer) and element.num == 0:
            return True
    return False


def is_known_nonzero(var_name: str, game: frog_ast.Game) -> bool:
    """True if *var_name* is sampled via ``<-uniq[S]`` with ``0 ∈ S`` (literal).

    The analysis is purely syntactic: scan *game* for a :class:`UniqueSample`
    whose bound variable is ``var_name`` and inspect the exclusion set. Return
    ``True`` iff the exclusion set is a set literal that contains the integer
    literal ``0``.
    """

    found: list[bool] = []

    def _visit(node: frog_ast.ASTNode) -> bool:
        if not isinstance(node, frog_ast.UniqueSample):
            return False
        bound = node.var
        if not isinstance(bound, frog_ast.Variable) or bound.name != var_name:
            return False
        if _set_contains_literal_zero(node.unique_set):
            found.append(True)
        return False

    SearchVisitor(_visit).visit(game)
    return bool(found)
