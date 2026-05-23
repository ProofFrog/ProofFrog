"""Bucket 1b — parametric EC tactic synthesizers.

Each synthesizer takes a :class:`TransformApplication` and returns the
rendered EC tactic body (list of lines), or ``None`` if synthesis fails
(falls back to ``admit.``). The synthesizer reads slot values directly
from the AST diff between ``app.game_before`` and ``app.game_after``;
no heuristics, no fallback guessing.
"""

from __future__ import annotations

import re

from ... import frog_ast
from ...transforms._base import TransformApplication


# Mirrors the mangler in exporter.py — duplicated here to avoid a
# circular import. Keep them in sync.
def _ec_ident(name: str) -> str:
    mangled = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not mangled or not mangled[0].islower():
        mangled = "v_" + mangled
    return mangled


def _ec_expr(e: frog_ast.Expression) -> str | None:
    """Render an expression to EC syntax, or return None if unsupported.

    Mirrors a subset of the exporter's renderer — kept narrow because
    a parametric synthesizer only needs to render the *offset* operand
    of a uniform-XOR transform.
    """
    if isinstance(e, frog_ast.Variable):
        return _ec_ident(e.name)
    return None


def _bitstring_suffix(t: frog_ast.Type) -> str | None:
    """Compute the EC type suffix for a BitString.

    For ``BitString<lambda>`` returns ``"lambda"``. Mirrors
    type_collector's naming convention so emitted tactics reference the
    same op symbols as the preamble.
    """
    if not isinstance(t, frog_ast.BitStringType):
        return None
    text = str(t.parameterization) if t.parameterization is not None else ""
    sanitized = re.sub(r"\W+", "_", text).strip("_")
    return sanitized or None


def uniform_xor_tactic(app: TransformApplication) -> list[str] | None:
    """Synthesize the EC tactic for ``Uniform XOR Simplification``.

    The transform rewrites a single occurrence ``u + m`` (where ``u`` is
    a single-use uniform BitString sample and ``+`` is XOR) to ``u``.
    Strategy:

    1. Walk the top-level statements of the (single) oracle method in
       both ``game_before`` and ``game_after`` in parallel.
    2. Find the first pair whose contained expression differs: the
       ``before`` side has a ``BinaryOperation(ADD, u, m)`` and the
       ``after`` side has just ``u``. The other operand ``m`` is the
       offset; the uniform sample's type gives the bitstring suffix.
    3. Emit::

           rnd (fun z => xor_<suffix> z <offset>{2})
               (fun z => xor_<suffix> z <offset>{2}).
           auto => />; progress; smt(xor_<suffix>_invol dbs_<suffix>_fu).

    Returns ``None`` if the diff doesn't match this exact pattern (e.g.
    transform fired inside a nested block, or both operands changed,
    or the type isn't BitString). The caller then falls back to
    ``admit.``.
    """
    if len(app.game_before.methods) != 1 or len(app.game_after.methods) != 1:
        return None

    before_block = app.game_before.methods[0].block
    after_block = app.game_after.methods[0].block

    if len(before_block.statements) != len(after_block.statements):
        return None

    # Find the changed pair.
    changed_pair: tuple[frog_ast.Statement, frog_ast.Statement] | None = None
    for b, a in zip(before_block.statements, after_block.statements):
        if b != a:
            if changed_pair is not None:
                return None  # ambiguous — more than one statement changed
            changed_pair = (b, a)

    if changed_pair is None:
        return None

    b_stmt, a_stmt = changed_pair
    before_expr = _expr_of(b_stmt)
    after_expr = _expr_of(a_stmt)
    if before_expr is None or after_expr is None:
        return None

    diff = _xor_dropped_operand(before_expr, after_expr)
    if diff is None:
        return None
    uniform_var, dropped_expr = diff

    # The uniform variable was sampled somewhere earlier in the block —
    # find that Sample to read its type.
    sample_type: frog_ast.Type | None = None
    for s in before_block.statements:
        if isinstance(s, frog_ast.Sample) and isinstance(s.var, frog_ast.Variable):
            if s.var.name == uniform_var:
                sample_type = s.the_type
                break
    if sample_type is None:
        return None

    suffix = _bitstring_suffix(sample_type)
    if suffix is None:
        return None

    offset_ec = _ec_expr(dropped_expr)
    if offset_ec is None:
        return None

    xor_op = f"xor_{suffix}"
    distr = f"dbs_{suffix}"
    return [
        "proc.",
        f"rnd (fun z => {xor_op} z {offset_ec}{{2}}) "
        f"(fun z => {xor_op} z {offset_ec}{{2}}).",
        f"auto => />; progress; smt({xor_op}_invol {distr}_fu).",
    ]


def _expr_of(stmt: frog_ast.Statement) -> frog_ast.Expression | None:
    """Return the expression contained in a Return or Assignment, else None."""
    if isinstance(stmt, frog_ast.ReturnStatement):
        return stmt.expression
    if isinstance(stmt, frog_ast.Assignment):
        return stmt.value
    return None


def _xor_dropped_operand(
    before: frog_ast.Expression, after: frog_ast.Expression
) -> tuple[str, frog_ast.Expression] | None:
    """Return ``(uniform_var_name, dropped_operand_expr)`` if ``before`` is
    ``BinaryOperation(ADD, u, m)`` (in either order) and ``after`` is just
    ``u``. Else ``None``."""
    if not isinstance(after, frog_ast.Variable):
        return None
    if not isinstance(before, frog_ast.BinaryOperation):
        return None
    if before.operator != frog_ast.BinaryOperators.ADD:
        return None
    if (
        isinstance(before.left_expression, frog_ast.Variable)
        and before.left_expression.name == after.name
    ):
        return (after.name, before.right_expression)
    if (
        isinstance(before.right_expression, frog_ast.Variable)
        and before.right_expression.name == after.name
    ):
        return (after.name, before.left_expression)
    return None
