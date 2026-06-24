"""Adjacent-game diff pass (D1).

Game-hopping papers highlight, in each game, the lines that changed relative to
the previous game so a reader can see at a glance what each hop did. This module
provides ``mark_diff(prev_body, cur_body)``: a line-level diff that flips
``highlight`` to True on the lines of ``cur_body`` that were inserted or changed
relative to ``prev_body``. Only the *new* body is mutated; backends turn the
flag into a visible highlight (e.g. cryptocode's ``\\gamechange`` colorbox).

Granularity is per line: procedures (oracles) are matched by title, and within
a matched pair the line sequences are diffed with :class:`difflib.SequenceMatcher`.
A procedure present only in the new game is highlighted in full. Deleted lines
are not surfaced (only the new game is rendered).
"""

from __future__ import annotations

import dataclasses
import difflib

from . import ir


def mark_diff(
    prev_body: ir.VStack | ir.ProcedureBlock | None,
    cur_body: ir.VStack | ir.ProcedureBlock | None,
) -> None:
    """Highlight lines of ``cur_body`` that changed vs ``prev_body``.

    A no-op unless both bodies are the same kind (two ``VStack``\\ s or two
    ``ProcedureBlock``\\ s); mixed or ``None`` bodies are left untouched so a
    start/end step (heading only) or a structural mismatch degrades gracefully.
    """
    if isinstance(prev_body, ir.VStack) and isinstance(cur_body, ir.VStack):
        _diff_vstacks(prev_body, cur_body)
    elif isinstance(prev_body, ir.ProcedureBlock) and isinstance(
        cur_body, ir.ProcedureBlock
    ):
        _diff_blocks(prev_body, cur_body)


def bodies_equal(
    a: ir.VStack | ir.ProcedureBlock | None,
    b: ir.VStack | ir.ProcedureBlock | None,
) -> bool:
    """Whether two figure bodies are structurally identical (ignoring highlight).

    Used to suppress the redundant redraw of an unchanged reduction across an
    assumption hop in symbolic mode: ``DDH.Left compose R`` and
    ``DDH.Right compose R`` share the same reduction body ``R``, so the second
    points back to the first rather than drawing the same box again.
    """
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, ir.VStack) and isinstance(b, ir.VStack):
        return len(a.blocks) == len(b.blocks) and all(
            _block_equal(x, y) for x, y in zip(a.blocks, b.blocks)
        )
    if isinstance(a, ir.ProcedureBlock) and isinstance(b, ir.ProcedureBlock):
        return _block_equal(a, b)
    return False


def _block_equal(a: ir.ProcedureBlock, b: ir.ProcedureBlock) -> bool:
    return a.title == b.title and [_line_key(x) for x in a.lines] == [
        _line_key(y) for y in b.lines
    ]


def _diff_vstacks(old: ir.VStack, new: ir.VStack) -> None:
    old_by_title = {b.title: b for b in old.blocks}
    for block in new.blocks:
        match = old_by_title.get(block.title)
        if match is not None:
            _diff_blocks(match, block)
        else:
            # A wholly new oracle: every line is a change.
            for line in block.lines:
                line.highlight = True


def _diff_blocks(old: ir.ProcedureBlock, new: ir.ProcedureBlock) -> None:
    old_keys = [_line_key(line) for line in old.lines]
    new_keys = [_line_key(line) for line in new.lines]
    matcher = difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            for line in new.lines[j1:j2]:
                line.highlight = True


def _line_key(line: ir.Line) -> tuple[object, ...]:
    """A comparison key for a line: its type plus every field but ``highlight``.

    ``depth`` is included, so a line that moved to a different nesting level
    counts as a change even when its text is identical.
    """
    fields = tuple(
        getattr(line, f.name) for f in dataclasses.fields(line) if f.name != "highlight"
    )
    return (type(line).__name__, *fields)
