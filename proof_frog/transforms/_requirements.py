"""Helpers for consuming proof-level ``requires:`` declarations in transforms."""

from __future__ import annotations

from .. import frog_ast
from ..visitors import SearchVisitor, lvalue_base_name


def _set_contains_literal_zero(expr: frog_ast.Expression) -> bool:
    """True if *expr* is a :class:`frog_ast.Set` containing a literal ``0``."""
    if not isinstance(expr, frog_ast.Set):
        return False
    for element in expr.elements:
        if isinstance(element, frog_ast.Integer) and element.num == 0:
            return True
    return False


def is_known_nonzero(var_name: str, game: frog_ast.Game) -> bool:
    """True if *var_name* is provably nonzero throughout *game*.

    The exponent that re-keys a persistent map must itself be a persistent
    game FIELD whose nonzero value is established once, at setup, and never
    disturbed:

    * ``var_name`` must be a game field (a local/parameter of the same name is
      not the persistent key, and an adversary parameter is untrusted);
    * its nonzero value must come from a ``<-uniq[S]`` with literal ``0 in S``
      in ``Initialize`` -- the method guaranteed to run once before any oracle.
      A uniq sample in some other oracle (``Unrelated``) may never run, so the
      field would stay at its default (F-136 variant B); and
    * NO other write to the field exists anywhere -- a later ``k = 0``, a plain
      sample, a ``<-uniq`` without ``0``, or any write outside ``Initialize``
      voids the guarantee (F-136 variant A).
    """
    if var_name not in {f.name for f in game.fields}:
        return False
    for method in game.methods:
        for param in method.signature.parameters:
            if param.name == var_name:
                return False

    def _writes_to_field(method: frog_ast.Method) -> list[frog_ast.Statement]:
        out: list[frog_ast.Statement] = []

        def _visit(node: frog_ast.ASTNode) -> bool:
            if (
                isinstance(
                    node,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and lvalue_base_name(node.var) == var_name
            ):
                out.append(node)
            return False

        SearchVisitor(_visit).visit(method)
        return out

    has_nonzero_sample = False
    for method in game.methods:
        in_initialize = method.signature.name == "Initialize"
        for write in _writes_to_field(method):
            is_uniq_zero = isinstance(
                write, frog_ast.UniqueSample
            ) and _set_contains_literal_zero(write.unique_set)
            if in_initialize and is_uniq_zero:
                has_nonzero_sample = True
            else:
                # Any non-uniq-zero write, or any write outside Initialize, may
                # leave the field zero or unknown.
                return False
    return has_nonzero_sample
