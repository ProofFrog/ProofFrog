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
  only inside ``if`` branches that open with ``bad = true;``. Everything
  outside those branches, including the branch conditions, must be
  syntactically identical, and ``bad`` may appear nowhere else. Because a
  reduction composed with the pair is shared verbatim between the two
  sides, the composed games are identical until bad as well.
* A **flag game** file is *derived from* one side of the pair when its two
  games are that side plus exactly one extra oracle ``Bool Reveal()``,
  returning ``bad`` in the first game and ``false`` in the second.

The proof engine licenses the side flip ``Pair.X compose R -> Pair.Y
compose R`` as an ``up to bad`` hop when the pair passes
:func:`identical_until_bad` and a flag game passing
:func:`flag_game_mismatch` is in scope (assumed, or proven by a lemma).
The hop's loss is that flag game's advantage. Both checks work on the raw
parsed ASTs, before instantiation or canonicalization, so they are
purely syntactic and independent of the transform pipeline.
"""

from __future__ import annotations

from typing import Optional

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


def _blocks_equal_until_bad(a: frog_ast.Block, b: frog_ast.Block) -> bool:
    if len(a.statements) != len(b.statements):
        return False
    return all(
        _statements_equal_until_bad(x, y) for x, y in zip(a.statements, b.statements)
    )


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
            if isinstance(node, frog_ast.IfStatement):
                for block in node.blocks:
                    if _starts_with_bad_true(block):
                        allowed.add(id(block.statements[0]))
    return allowed


def _bad_discipline(game: frog_ast.Game) -> Optional[str]:
    """``bad`` may only be reset at initialization or raised to open a branch."""
    allowed = _sanctioned_flag_writes(game)
    for method in game.methods:
        stack: list[object] = [method.block]
        while stack:
            current = stack.pop()
            if isinstance(current, frog_ast.Assignment) and id(current) in allowed:
                continue
            if isinstance(current, frog_ast.Variable) and current.name == BAD_FLAG:
                return (
                    f"{game.name}.{method.signature.name} uses `{BAD_FLAG}` other"
                    f" than as `{BAD_FLAG} = false;` in Initialize or"
                    f" `{BAD_FLAG} = true;` opening an if-branch"
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
                f"oracle {ml.signature.name} differs outside a block opened by"
                f" `{BAD_FLAG} = true;`"
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
        reveals = [m for m in game.methods if m.signature.name == REVEAL]
        others = [m for m in game.methods if m.signature.name != REVEAL]
        if len(reveals) != 1:
            return f"{game.name} must define exactly one `Bool {REVEAL}()` oracle"
        reveal = reveals[0]
        if reveal.signature.parameters or not isinstance(
            reveal.signature.return_type, frog_ast.BoolType
        ):
            return f"{game.name}.{REVEAL} must be `Bool {REVEAL}()`"
        statements = list(reveal.block.statements)
        if statements != [frog_ast.ReturnStatement(body)]:
            return f"{game.name}.{REVEAL} must be exactly `return {body};`"
        if list(others) != list(base.methods):
            return f"{game.name} differs from {base.name} outside {REVEAL}"
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
