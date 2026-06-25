import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import RedundantConditionalReturnTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: if (cond) { return X; } return X; → return X;
        (
            """
            Int f(Int x) {
                if (x == 1) {
                    return 42;
                }
                return 42;
            }
            """,
            """
            Int f(Int x) {
                return 42;
            }
            """,
        ),
        # Preceding statements are preserved
        (
            """
            Int f(Int x) {
                Int y = x + 1;
                if (x == 1) {
                    return 42;
                }
                return 42;
            }
            """,
            """
            Int f(Int x) {
                Int y = x + 1;
                return 42;
            }
            """,
        ),
        # Different return values — no change
        (
            """
            Int f(Int x) {
                if (x == 1) {
                    return 1;
                }
                return 2;
            }
            """,
            """
            Int f(Int x) {
                if (x == 1) {
                    return 1;
                }
                return 2;
            }
            """,
        ),
        # If-with-else — no change (has else block, not the pattern)
        (
            """
            Int f(Int x) {
                if (x == 1) {
                    return 42;
                } else {
                    return 42;
                }
            }
            """,
            """
            Int f(Int x) {
                if (x == 1) {
                    return 42;
                } else {
                    return 42;
                }
            }
            """,
        ),
        # Multi-statement if body that does NOT match the fall-through —
        # no change (body length 2, only one statement follows).
        (
            """
            Int f(Int x) {
                if (x == 1) {
                    Int y = 1;
                    return y;
                }
                return 42;
            }
            """,
            """
            Int f(Int x) {
                if (x == 1) {
                    Int y = 1;
                    return y;
                }
                return 42;
            }
            """,
        ),
        # Multi-statement body that unconditionally returns and matches the
        # fall-through exactly — the guard is redundant, so it collapses.
        (
            """
            Int f(Int x, Int y) {
                if (x == 1) {
                    if (y == 2) {
                        return 7;
                    }
                    return 8;
                }
                if (y == 2) {
                    return 7;
                }
                return 8;
            }
            """,
            """
            Int f(Int x, Int y) {
                if (y == 2) {
                    return 7;
                }
                return 8;
            }
            """,
        ),
        # Body matches the fall-through but does NOT unconditionally return —
        # no change (dropping the guard would change behavior: when the guard
        # holds, the body runs and then control continues to the same
        # statements, executing them twice).
        (
            """
            Int f(Int x, Set<Int> s) {
                if (x == 1) {
                    s = s union 9;
                }
                s = s union 9;
                return 0;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (x == 1) {
                    s = s union 9;
                }
                s = s union 9;
                return 0;
            }
            """,
        ),
    ],
)
def test_redundant_conditional_return(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = RedundantConditionalReturnTransformer().transform(method_ast)
    assert expected_ast == transformed_ast


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-087): dropping the redundant guard discards an
# evaluation of its condition; a non-deterministic condition is observable,
# so the fold must be declined.
# ---------------------------------------------------------------------------

from proof_frog.transforms.control_flow import RedundantConditionalReturn
from proof_frog.transforms._base import PipelineContext as _PipelineContext
from proof_frog.visitors import NameTypeMap as _NameTypeMap


def _rcr_ctx(**namespace):
    return _PipelineContext(
        variables={},
        proof_let_types=_NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def _rcr_nondet_prim():
    return frog_parser.parse_primitive_file("Primitive P(Int n) { Bool f(Int x); }")


def _rcr_det_prim():
    return frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic Bool f(Int x); }"
    )


def test_rcr_declines_on_nondeterministic_condition() -> None:
    """``if (F.f(x)) { return 1; } return 1;`` -- body matches fall-through,
    but the guard is non-deterministic, so dropping it would discard an
    observable evaluation. The pass must decline."""
    game = frog_parser.parse_game("""
        Game G(P F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                return 1;
            }
        }
        """)
    ctx = _rcr_ctx(P=_rcr_nondet_prim(), F=_rcr_nondet_prim())
    result = RedundantConditionalReturn().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "Redundant Conditional Return" for nm in ctx.near_misses
    )


def test_rcr_fires_on_deterministic_control() -> None:
    """Control: a deterministic guard evaluation has no observable effect, so
    the redundant guard folds."""
    game = frog_parser.parse_game("""
        Game G(D F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                return 1;
            }
        }
        """)
    ctx = _rcr_ctx(D=_rcr_det_prim(), F=_rcr_det_prim())
    result = RedundantConditionalReturn().apply(game, ctx)
    assert result != game  # the guard was folded away
