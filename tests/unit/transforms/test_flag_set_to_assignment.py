"""Tests for FlagSetToAssignment.

``x = false; S; if (C) { x = true; }`` becomes ``x = false; S; x = C;`` when
no statement in S mentions x: x is false right before the if, so afterwards
it equals C either way, and C is evaluated once at the same point.
"""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import FlagSetToAssignment
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={}, proof_let_types=NameTypeMap(), proof_namespace={}, subsets_pairs=[]
    )


def _apply(source: str, ctx: PipelineContext | None = None):
    game = frog_parser.parse_game(source)
    return game, FlagSetToAssignment().apply(game, ctx or _ctx())


def test_flag_set_folds_to_assignment() -> None:
    _, result = _apply("""
        Game G(Set S) {
            S a; S b; Bool bad;
            Void Initialize() {
                bad = false;
                a <- S;
                b <- S;
                if (a == b) {
                    bad = true;
                }
            }
            Bool O() { return bad; }
        }
        """)
    text = str(result)
    assert "if" not in text and "bad = a == b;" in text


def test_intervening_read_blocks_fold() -> None:
    game, result = _apply("""
        Game G(Set S) {
            S a; S b; Bool bad; Bool seen;
            Void Initialize() {
                bad = false;
                a <- S;
                b <- S;
                seen = bad;
                if (a == b) {
                    bad = true;
                }
            }
            Bool O() { return bad; }
        }
        """)
    # Reading bad in between is harmless for the value, but keep the rule
    # simple: any mention of the flag in between declines.
    assert result == game


def test_unknown_prior_value_not_folded() -> None:
    game, result = _apply("""
        Game G(Set S) {
            S a; S b; Bool bad;
            Void Initialize() { bad = false; }
            Void O(S c) {
                if (c == a) {
                    bad = true;
                }
            }
        }
        """)
    assert result == game


def test_prior_true_not_folded() -> None:
    game, result = _apply("""
        Game G(Set S) {
            S a; S b; Bool bad;
            Void Initialize() {
                bad = true;
                a <- S;
                if (a == b) {
                    bad = true;
                }
            }
        }
        """)
    assert result == game


def test_if_with_else_or_extra_statement_not_folded() -> None:
    game, result = _apply("""
        Game G(Set S) {
            S a; S b; Int n; Bool bad;
            Void Initialize() {
                bad = false;
                a <- S;
                if (a == b) {
                    bad = true;
                    n = 1;
                }
            }
        }
        """)
    assert result == game


def test_near_miss_when_flag_mentioned_in_between() -> None:
    ctx = _ctx()
    _apply(
        """
        Game G(Set S) {
            S a; S b; Bool bad; Bool seen;
            Void Initialize() {
                bad = false;
                seen = bad;
                if (a == b) {
                    bad = true;
                }
            }
        }
        """,
        ctx,
    )
    assert any(nm.transform_name == "Flag Set To Assignment" for nm in ctx.near_misses)
