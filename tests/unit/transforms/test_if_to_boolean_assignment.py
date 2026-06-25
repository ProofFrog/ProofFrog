"""Tests for IfToBooleanAssignment.

Collapses ``if (C) { x = true; } else { x = false; }`` into ``x = C;`` (and the
negated form). RC4 binding-kind / hoist guards ensure the merge does not change
which storage is written (field vs branch-local) or capture a later reference.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.control_flow import IfToBooleanAssignment
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return IfToBooleanAssignment().apply(game, _ctx())


def test_plain_assignment_both_branches_fires() -> None:
    """Control: both branches are plain assignments to the same existing
    binding, so the merge to ``x = c;`` is sound."""
    source = """
    Game G() {
        Void Store(Bool c) {
            Bool x = false;
            if (c) {
                x = true;
            } else {
                x = false;
            }
        }
    }
    """
    expected = """
    Game G() {
        Void Store(Bool c) {
            Bool x = false;
            x = c;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_negated_form_fires() -> None:
    source = """
    Game G() {
        Void Store(Bool c) {
            Bool x = false;
            if (c) {
                x = false;
            } else {
                x = true;
            }
        }
    }
    """
    expected = """
    Game G() {
        Void Store(Bool c) {
            Bool x = false;
            x = !c;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_both_typed_declarations_unused_after_fires() -> None:
    """Control: both branches are typed declarations and the name is NOT
    referenced after the if, so hoisting is harmless and the rewrite fires."""
    source = """
    Game G() {
        Void Store(Bool c) {
            if (c) {
                Bool x = true;
            } else {
                Bool x = false;
            }
        }
    }
    """
    expected = """
    Game G() {
        Void Store(Bool c) {
            Bool x = c;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


# ---------------------------------------------------------------------------
# RC4 binding-kind guard (F-084): a field write in one branch and a typed-local
# declaration in the other share a name but write different storage. Merging
# them would either erase the field write or hoist the local. Decline.
# ---------------------------------------------------------------------------


def test_mixed_kind_field_write_and_decl_declines() -> None:
    """ATTACK-1 shape: ``flag = true;`` (field write) vs ``Bool flag = false;``
    (branch-local decl). Mixed binding kind -- decline."""
    source = """
    Game G() {
        Bool flag;
        Void SetFlag(Bool c) {
            if (c) {
                flag = true;
            } else {
                Bool flag = false;
            }
        }
    }
    """
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    result = IfToBooleanAssignment().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "If To Boolean Assignment" and "binding kinds" in nm.reason
        for nm in ctx.near_misses
    )


def test_mixed_kind_decl_and_field_write_declines() -> None:
    """Mirror of the above: typed decl in then-branch, field write in else."""
    source = """
    Game G() {
        Bool flag;
        Void SetFlag(Bool c) {
            if (c) {
                Bool flag = true;
            } else {
                flag = false;
            }
        }
    }
    """
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    result = IfToBooleanAssignment().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "If To Boolean Assignment" for nm in ctx.near_misses
    )


def test_both_decls_with_later_reference_declines() -> None:
    """ATTACK-2 shape: both branches declare a typed local ``flag`` but a later
    statement writes the field ``flag``. Hoisting the declaration would capture
    that later write -- decline."""
    source = """
    Game G() {
        Bool flag;
        Void SetFlag(Bool c) {
            if (c) {
                Bool flag = true;
            } else {
                Bool flag = false;
            }
            flag = true;
        }
    }
    """
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    result = IfToBooleanAssignment().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "If To Boolean Assignment" and "capture" in nm.reason
        for nm in ctx.near_misses
    )
