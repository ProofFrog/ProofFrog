"""Structural checks behind up-to-bad hops.

The fundamental lemma of game playing: if two games are *identical until
bad* -- they agree on every execution prefix up to the point where a flag
``bad`` is set -- then no adversary distinguishes them with advantage
larger than the probability that ``bad`` gets set. That probability is
itself a distinguishing advantage: against the game that reveals the
flag (an extra ``Bool Reveal() { return bad; }`` oracle) versus the game
that never does (``return false;``), for the adversary that plays and
then calls ``Reveal`` once.

FrogLang has no ``abort`` and every hop is a Left/Right side flip, so the
lemma is encoded structurally:

* A **pair** game file is *identical until bad* when both games declare a
  ``Bool bad`` field, set it to ``false`` at initialization, and differ
  only *after* a ``bad = true;`` statement: inside ``if`` branches that
  open with it, or in the remainder of a block following a top-level
  ``bad = true;`` at the same position on both sides. One more shape is
  accepted as a block's tail: ``if (A != B) { bad = true; } return A;``
  against the same guard followed by ``return B;`` (on a non-bad run the
  guard was false, so the returns agree). Everything before, including
  branch conditions, must be syntactically identical, and ``bad`` may
  appear nowhere else. Because a
  reduction composed with the pair is shared verbatim between the two
  sides, the composed games are identical until bad as well.
* A **flag game** file is *derived from* one side of the pair when its two
  games are that side plus exactly one extra oracle ``Bool Reveal()``
  (conventionally so named; any name absent from the pair is accepted, so a
  pair that itself carries a ``Reveal`` can have a flag game), returning
  ``bad`` in the first game and ``false`` in the second.

The proof engine licenses the side flip ``Pair.X compose R -> Pair.Y
compose R`` as an ``up to bad`` hop when the pair passes
:func:`identical_until_bad` and a flag game passing
:func:`flag_game_mismatch` is in scope (assumed, or proven by a lemma).
The hop's loss is that flag game's advantage. Both checks work on the raw
parsed ASTs, before instantiation or canonicalization, so they are
purely syntactic and independent of the transform pipeline.
"""

from __future__ import annotations

from typing import Optional, Sequence

from . import frog_ast

BAD_FLAG = "bad"
REVEAL = "Reveal"

_NON_SEMANTIC_ATTRS = {"line_num", "column_num", "origin", "block"}


def _is_bad_assignment(stmt: frog_ast.Statement, value: bool) -> bool:
    return (
        isinstance(stmt, frog_ast.Assignment)
        and stmt.the_type is None
        and stmt.var == frog_ast.Variable(BAD_FLAG)
        and stmt.value == frog_ast.Boolean(value)
    )


def _starts_with_bad_true(block: frog_ast.Block) -> bool:
    return bool(block.statements) and _is_bad_assignment(block.statements[0], True)


def _mismatch_operands(
    cond: frog_ast.Expression,
) -> Optional[tuple[frog_ast.Expression, frog_ast.Expression]]:
    """``(A, B)`` when *cond* is ``A != B`` or ``!(A == B)``, else None."""
    if (
        isinstance(cond, frog_ast.BinaryOperation)
        and cond.operator is frog_ast.BinaryOperators.NOTEQUALS
    ):
        return cond.left_expression, cond.right_expression
    if (
        isinstance(cond, frog_ast.UnaryOperation)
        and cond.operator is frog_ast.UnaryOperators.NOT
        and isinstance(cond.expression, frog_ast.BinaryOperation)
        and cond.expression.operator is frog_ast.BinaryOperators.EQUALS
    ):
        return cond.expression.left_expression, cond.expression.right_expression
    return None


def _flag_on_mismatch_then_return(
    xs: Sequence[frog_ast.Statement], ys: Sequence[frog_ast.Statement], i: int
) -> bool:
    """The shape ``if (A != B) { bad = true; } return A;`` versus the same
    guard followed by ``return B;`` (either way round), as the last two
    statements of both blocks. On a run that does not raise the flag the guard
    was false, so ``A == B`` and the two returns agree; nothing runs between the
    guard and the return. Hence the pair is identical until bad."""
    x, y = xs[i], ys[i]
    if not (isinstance(x, frog_ast.IfStatement) and x == y):
        return False
    if len(x.conditions) != 1 or len(x.blocks) != 1:
        return False
    body = list(x.blocks[0].statements)
    if len(body) != 1 or not _is_bad_assignment(body[0], True):
        return False
    operands = _mismatch_operands(x.conditions[0])
    if operands is None:
        return False
    if i + 2 != len(xs) or i + 2 != len(ys):
        return False
    rx, ry = xs[i + 1], ys[i + 1]
    if not (
        isinstance(rx, frog_ast.ReturnStatement)
        and isinstance(ry, frog_ast.ReturnStatement)
    ):
        return False
    a, b = operands
    return all(r.expression in (a, b) for r in (rx, ry))


def _is_bad_guard(stmt: frog_ast.Statement) -> bool:
    """``if (bad) { ... }`` with no ``else``: code that only runs post-bad.

    An ``else`` block would run exactly on the runs where the flag is down,
    so a guard carrying one is not post-bad code and is compared like any
    other statement (which, since ``bad`` may not be read elsewhere, rejects
    the pair)."""
    return (
        isinstance(stmt, frog_ast.IfStatement)
        and len(stmt.conditions) == 1
        and stmt.conditions[0] == frog_ast.Variable(BAD_FLAG)
        and not stmt.has_else_block()
    )


def _blocks_equal_until_bad(a: frog_ast.Block, b: frog_ast.Block) -> bool:
    """Statement-wise equality, except that (1) a ``bad = true;`` statement at
    the same position on both sides ends the comparison: everything after it
    is post-bad and may differ (both executions have raised the flag by
    then); (2) the flag-on-mismatch-then-return shape (see
    :func:`_flag_on_mismatch_then_return`) is accepted as the blocks' tail;
    and (3) ``if (bad) { ... }`` statements are ignored on both sides: their
    bodies run only after the flag was raised, so either side may have them
    with any content."""
    xs = [x for x in a.statements if not _is_bad_guard(x)]
    ys = [y for y in b.statements if not _is_bad_guard(y)]
    for i, (x, y) in enumerate(zip(xs, ys)):
        if _is_bad_assignment(x, True) and _is_bad_assignment(y, True):
            return True
        if _flag_on_mismatch_then_return(xs, ys, i):
            return True
        if not _statements_equal_until_bad(x, y):
            return False
    return len(xs) == len(ys)


def _statements_equal_until_bad(x: frog_ast.Statement, y: frog_ast.Statement) -> bool:
    """Structural equality that skips the bodies of ``bad = true`` branches."""
    if type(x) is not type(y):
        return False
    if isinstance(x, frog_ast.IfStatement):
        assert isinstance(y, frog_ast.IfStatement)
        if x.conditions != y.conditions or len(x.blocks) != len(y.blocks):
            return False
        for bx, by in zip(x.blocks, y.blocks):
            flagged_x = _starts_with_bad_true(bx)
            if flagged_x != _starts_with_bad_true(by):
                return False
            if not flagged_x and not _blocks_equal_until_bad(bx, by):
                return False
        return True
    if isinstance(x, (frog_ast.NumericFor, frog_ast.GenericFor)):
        assert isinstance(y, (frog_ast.NumericFor, frog_ast.GenericFor))
        header_x = {k: v for k, v in vars(x).items() if k not in _NON_SEMANTIC_ATTRS}
        header_y = {k: v for k, v in vars(y).items() if k not in _NON_SEMANTIC_ATTRS}
        return header_x == header_y and _blocks_equal_until_bad(x.block, y.block)
    if isinstance(x, frog_ast.Block):
        assert isinstance(y, frog_ast.Block)
        return _blocks_equal_until_bad(x, y)
    return x == y


def _walk(node: object) -> list[object]:
    """Depth-first list of every node/attribute value reachable from *node*."""
    seen: list[object] = []
    stack: list[object] = [node]
    while stack:
        current = stack.pop()
        seen.append(current)
        if isinstance(current, frog_ast.ASTNode):
            stack.extend(getattr(current, attr) for attr in vars(current))
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return seen


def _sanctioned_flag_writes(game: frog_ast.Game) -> set[int]:
    """Ids of the ``bad`` assignments the discipline allows."""
    allowed: set[int] = set()
    for method in game.methods:
        if method.signature.name == "Initialize":
            allowed.update(
                id(s) for s in method.block.statements if _is_bad_assignment(s, False)
            )
        for node in _walk(method.block):
            if isinstance(node, frog_ast.Block):
                for stmt in node.statements:
                    if _is_bad_assignment(stmt, True):
                        allowed.add(id(stmt))
    return allowed


def _bad_discipline(game: frog_ast.Game) -> Optional[str]:
    """``bad`` may only be reset at initialization, raised by a top-level
    ``bad = true;`` statement of some block (which then marks the rest of that
    block, or the branch it opens, as post-bad), or read as the sole condition
    of an ``if (bad) { ... }`` guarding post-bad code."""
    allowed = _sanctioned_flag_writes(game)
    for method in game.methods:
        stack: list[object] = [method.block]
        while stack:
            current = stack.pop()
            if isinstance(current, frog_ast.Assignment) and id(current) in allowed:
                continue
            if isinstance(current, frog_ast.Statement) and _is_bad_guard(current):
                assert isinstance(current, frog_ast.IfStatement)
                stack.extend(current.blocks)  # the read IS the post-bad guard
                continue
            if isinstance(current, frog_ast.Variable) and current.name == BAD_FLAG:
                return (
                    f"{game.name}.{method.signature.name} uses `{BAD_FLAG}` other"
                    f" than as `{BAD_FLAG} = false;` in Initialize, a"
                    f" top-level `{BAD_FLAG} = true;` statement, or an"
                    f" `if ({BAD_FLAG})` guard"
                )
            if isinstance(current, frog_ast.ASTNode):
                stack.extend(getattr(current, attr) for attr in vars(current))
            elif isinstance(current, (list, tuple)):
                stack.extend(current)
    return None


def _check_bad_field(game: frog_ast.Game) -> Optional[str]:
    field = next((f for f in game.fields if f.name == BAD_FLAG), None)
    if field is None or not isinstance(field.type, frog_ast.BoolType):
        return f"{game.name} has no `Bool {BAD_FLAG}` field"
    if field.value is not None and field.value != frog_ast.Boolean(False):
        return f"{game.name}: `{BAD_FLAG}` must be initialized to false"
    if field.value is None:
        if not game.has_method("Initialize") or not any(
            _is_bad_assignment(s, False)
            for s in game.get_method("Initialize").block.statements
        ):
            return f"{game.name}.Initialize must set `{BAD_FLAG} = false;`"
    return None


def identical_until_bad(pair: frog_ast.GameFile) -> Optional[str]:
    """``None`` if the pair's two games are identical until bad, else why not."""
    left, right = pair.games
    if left.parameters != right.parameters:
        return "the two games take different parameters"
    if left.fields != right.fields:
        return "the two games declare different fields"
    for game in (left, right):
        reason = _check_bad_field(game) or _bad_discipline(game)
        if reason is not None:
            return reason
    if len(left.methods) != len(right.methods):
        return "the two games define different oracles"
    for ml, mr in zip(left.methods, right.methods):
        if ml.signature != mr.signature:
            return (
                f"oracle signatures differ: {ml.signature.name} vs {mr.signature.name}"
            )
        if not _blocks_equal_until_bad(ml.block, mr.block):
            return (
                f"oracle {ml.signature.name} differs before a `{BAD_FLAG} = true;`"
                " statement"
            )
    return None


def _flag_derived_from(base: frog_ast.Game, flag: frog_ast.GameFile) -> Optional[str]:
    expected: list[frog_ast.Expression] = [
        frog_ast.Variable(BAD_FLAG),
        frog_ast.Boolean(False),
    ]
    for game, body in zip(flag.games, expected):
        if game.parameters != base.parameters:
            return f"{game.name} takes different parameters than {base.name}"
        if game.fields != base.fields:
            return f"{game.name} declares different fields than {base.name}"
        base_names = {m.signature.name for m in base.methods}
        reveals = [m for m in game.methods if m.signature.name not in base_names]
        others = [m for m in game.methods if m.signature.name in base_names]
        if len(reveals) != 1:
            return (
                f"{game.name} must add exactly one oracle to {base.name}"
                f" (conventionally `Bool {REVEAL}()`)"
            )
        reveal = reveals[0]
        name = reveal.signature.name
        if reveal.signature.parameters or not isinstance(
            reveal.signature.return_type, frog_ast.BoolType
        ):
            return f"{game.name}.{name} must be `Bool {name}()`"
        statements = list(reveal.block.statements)
        if statements != [frog_ast.ReturnStatement(body)]:
            return f"{game.name}.{name} must be exactly `return {body};`"
        if list(others) != list(base.methods):
            return f"{game.name} differs from {base.name} outside {name}"
    return None


def flag_game_mismatch(
    pair: frog_ast.GameFile, flag: frog_ast.GameFile
) -> Optional[str]:
    """``None`` if *flag* is the flag game of one side of *pair*, else why not.

    The second game of the pair is tried first (the conventional "neutral"
    side), then the first; the fundamental lemma is symmetric, so either
    side's flag game bounds the hop.
    """
    reasons: list[str] = []
    for base in (pair.games[1], pair.games[0]):
        reason = _flag_derived_from(base, flag)
        if reason is None:
            return None
        reasons.append(f"from {base.name}: {reason}")
    return "; ".join(reasons)
