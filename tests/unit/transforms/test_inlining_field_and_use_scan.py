"""Regression tests for three family-4 inlining interference gaps.

- F-144 CollapseAssignment: two field stores must not collapse across an
  intervening control-flow exit (the first store is live on the early-return
  path, observable by a later oracle). Locals stay collapsible.
- F-159 IfSplitBranchAssignment: dropping each branch's trailing `x = A` store
  is unsound when `x` is a field (persists across calls); the pass fires only
  for locals.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import (
    CollapseAssignment,
    IfSplitBranchAssignment,
)
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _run(pass_obj, src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(pass_obj.apply(game, _ctx()))


# ---- F-144 CollapseAssignment ----


def test_f144_field_stores_not_collapsed_across_return() -> None:
    out = _run(
        CollapseAssignment(),
        """
        Game G() {
            Int f;
            Int Store(Bool b) {
                f = 0;
                if (b) { return 1; }
                f = 1;
                return f;
            }
            Int Get() { return f; }
        }
        """,
    )
    # Both field stores survive: `f = 0` is NOT deleted.
    assert "f = 0" in out


def test_f144_local_stores_still_collapse() -> None:
    out = _run(
        CollapseAssignment(),
        """
        Game G() {
            Int O() {
                Int v = 0;
                v = 1;
                return v;
            }
        }
        """,
    )
    # `Int v = 0` collapses into `Int v = 1`.
    assert "v = 0" not in out
    assert "v = 1" in out


# ---- F-159 IfSplitBranchAssignment ----


def test_f159_field_branch_assignment_not_dropped() -> None:
    out = _run(
        IfSplitBranchAssignment(),
        """
        Game G() {
            Int x;
            Int Store(Bool c) {
                if (c) { x = 1; } else { x = 2; }
                return x;
            }
            Int Get() { return x; }
        }
        """,
    )
    # The field stores are retained (pass declines): `x = 1` / `x = 2` survive.
    assert "x = 1" in out and "x = 2" in out


def test_f159_local_branch_assignment_still_splits() -> None:
    out = _run(
        IfSplitBranchAssignment(),
        """
        Game G() {
            Int Store(Bool c) {
                Int x;
                if (c) { x = 1; } else { x = 2; }
                return x;
            }
        }
        """,
    )
    # Local x: the pass fires, substituting the value into the moved return.
    assert "return 1" in out and "return 2" in out
