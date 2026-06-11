"""Tests for the adjacent-game diff pass (D1).

``mark_diff`` flips ``highlight`` to True on the lines of the *new* game that
were inserted or changed relative to the previous game, matched per oracle by
procedure title.
"""

from proof_frog.export.latex import ir
from proof_frog.export.latex.diff import bodies_equal, mark_diff


def _block(title, *lines):
    return ir.ProcedureBlock(title=title, lines=list(lines))


def test_marks_changed_line_only() -> None:
    old = ir.VStack(
        blocks=[
            _block(
                r"\Enc(m)",
                ir.Sample(lhs="k", rhs="K"),
                ir.Assign(lhs="c", rhs="m"),
                ir.Return(expr="c"),
            )
        ]
    )
    new = ir.VStack(
        blocks=[
            _block(
                r"\Enc(m)",
                ir.Sample(lhs="k", rhs="K"),
                ir.Assign(lhs="c", rhs=r"\ENC(k, m)"),
                ir.Return(expr="c"),
            )
        ]
    )
    mark_diff(old, new)
    flags = [ln.highlight for ln in new.blocks[0].lines]
    assert flags == [False, True, False]
    # the old stack is never mutated
    assert all(not ln.highlight for ln in old.blocks[0].lines)


def test_marks_inserted_line() -> None:
    old = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    new = ir.VStack(
        blocks=[_block(r"\O()", ir.Sample(lhs="r", rhs="R"), ir.Return(expr="c"))]
    )
    mark_diff(old, new)
    assert [ln.highlight for ln in new.blocks[0].lines] == [True, False]


def test_identical_blocks_have_no_highlight() -> None:
    old = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    new = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    mark_diff(old, new)
    assert [ln.highlight for ln in new.blocks[0].lines] == [False]


def test_new_oracle_fully_highlighted() -> None:
    old = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    new = ir.VStack(
        blocks=[
            _block(r"\O()", ir.Return(expr="c")),
            _block(r"\P()", ir.Sample(lhs="r", rhs="R"), ir.Return(expr="r")),
        ]
    )
    mark_diff(old, new)
    assert [ln.highlight for ln in new.blocks[0].lines] == [False]
    assert [ln.highlight for ln in new.blocks[1].lines] == [True, True]


def test_depth_change_is_a_change() -> None:
    # A line moved to a deeper nesting level is a structural change worth
    # surfacing even if its content text is unchanged.
    old = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c", depth=0))])
    new = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c", depth=1))])
    mark_diff(old, new)
    assert new.blocks[0].lines[0].highlight is True


def test_procedure_block_bodies_diffable() -> None:
    old = ir.ProcedureBlock(title=r"\O()", lines=[ir.Return(expr="c")])
    new = ir.ProcedureBlock(
        title=r"\O()", lines=[ir.Sample(lhs="r", rhs="R"), ir.Return(expr="c")]
    )
    mark_diff(old, new)
    assert [ln.highlight for ln in new.lines] == [True, False]


def test_mismatched_body_kinds_noop() -> None:
    old = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    new = ir.ProcedureBlock(title=r"\O()", lines=[ir.Return(expr="c")])
    # Should not raise and should not mark anything.
    mark_diff(old, new)
    assert new.lines[0].highlight is False


def test_none_bodies_noop() -> None:
    new = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    mark_diff(None, new)
    assert new.blocks[0].lines[0].highlight is False


def test_bodies_equal_true_for_identical_vstacks() -> None:
    a = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    b = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    assert bodies_equal(a, b) is True


def test_bodies_equal_ignores_highlight_flag() -> None:
    a = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    b = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c", highlight=True))])
    assert bodies_equal(a, b) is True


def test_bodies_equal_false_on_content_change() -> None:
    a = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    b = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="d"))])
    assert bodies_equal(a, b) is False


def test_bodies_equal_false_on_title_change() -> None:
    a = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    b = ir.VStack(blocks=[_block(r"\P()", ir.Return(expr="c"))])
    assert bodies_equal(a, b) is False


def test_bodies_equal_none_handling() -> None:
    body = ir.VStack(blocks=[_block(r"\O()", ir.Return(expr="c"))])
    assert bodies_equal(None, body) is False
    assert bodies_equal(body, None) is False
    assert bodies_equal(None, None) is True
