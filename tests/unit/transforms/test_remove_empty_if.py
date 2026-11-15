"""Tests for RemoveEmptyIf.

An ``if`` statement whose every arm is empty changes no state and continues
at the same point on every path, so it is removed when evaluating its
conditions has no effect: no call (a call may be a non-deterministic or
stateful method) and no map/array indexing (an absent-key read).
"""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import RemoveEmptyIf
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _make_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str, ctx: PipelineContext | None = None):
    game = frog_parser.parse_game(source)
    return game, RemoveEmptyIf().apply(game, ctx or _make_ctx())


def test_empty_if_removed() -> None:
    _, result = _apply("""
        Game G(Set S) {
            Set<S> seen;
            S O(S x) {
                Bool hit = x in seen;
                if (hit) {
                }
                return x;
            }
        }
        """)
    assert "if" not in str(result)


def test_empty_if_else_chain_removed() -> None:
    _, result = _apply("""
        Game G() {
            Int O(Int x) {
                if (x == 1) {
                } else if (x == 2) {
                } else {
                }
                return x;
            }
        }
        """)
    assert "if" not in str(result)


def test_nonempty_arm_kept() -> None:
    game, result = _apply("""
        Game G() {
            Int y;
            Int O(Int x) {
                if (x == 1) {
                } else {
                    y = x;
                }
                return x;
            }
        }
        """)
    assert result == game


def test_condition_with_call_kept() -> None:
    game, result = _apply("""
        Game G(Function<Int, Bool> F) {
            Int O(Int x) {
                if (F(x)) {
                }
                return x;
            }
        }
        """)
    assert result == game


def test_condition_with_map_read_kept() -> None:
    game, result = _apply("""
        Game G() {
            Map<Int, Bool> M;
            Int O(Int x) {
                if (M[x]) {
                }
                return x;
            }
        }
        """)
    assert result == game


def test_near_miss_reported_for_call_condition() -> None:
    ctx = _make_ctx()
    _apply(
        """
        Game G(Function<Int, Bool> F) {
            Int O(Int x) {
                if (F(x)) {
                }
                return x;
            }
        }
        """,
        ctx,
    )
    assert any(nm.transform_name == "Remove Empty If" for nm in ctx.near_misses)
