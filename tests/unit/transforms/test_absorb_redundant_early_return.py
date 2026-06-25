"""Tests for AbsorbRedundantEarlyReturn transform."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import (
    AbsorbRedundantEarlyReturnTransformer,
)


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic absorption: early return absorbed into following if-condition.
        (
            """
            Int f(Int x, Int y) {
                if (x == 1) {
                    return 99;
                }
                if (y == 2) {
                    Int r <- Int;
                    return r;
                }
                return 99;
            }
            """,
            """
            Int f(Int x, Int y) {
                if (x != 1 && y == 2) {
                    Int r <- Int;
                    return r;
                }
                return 99;
            }
            """,
        ),
        # Multiple intervening if-statements: !P AND'd into each.
        (
            """
            Int f(Int x, Int y, Int z) {
                if (x == 1) {
                    return 99;
                }
                if (y == 2) {
                    Int r <- Int;
                    return r;
                }
                if (z == 3) {
                    Int s <- Int;
                    return s;
                }
                return 99;
            }
            """,
            """
            Int f(Int x, Int y, Int z) {
                if (x != 1 && y == 2) {
                    Int r <- Int;
                    return r;
                }
                if (x != 1 && z == 3) {
                    Int s <- Int;
                    return s;
                }
                return 99;
            }
            """,
        ),
        # Statements before the early return are preserved.
        (
            """
            Int f(Int x, Int y) {
                Int common = x + y;
                if (x == 1) {
                    return common;
                }
                if (y == 2) {
                    Int r <- Int;
                    return r;
                }
                return common;
            }
            """,
            """
            Int f(Int x, Int y) {
                Int common = x + y;
                if (x != 1 && y == 2) {
                    Int r <- Int;
                    return r;
                }
                return common;
            }
            """,
        ),
    ],
)
def test_absorbs_when_pattern_matches(method: str, expected: str) -> None:
    parsed = frog_parser.parse_method(method)
    expected_parsed = frog_parser.parse_method(expected)
    result = AbsorbRedundantEarlyReturnTransformer().transform(parsed)
    assert result == expected_parsed


@pytest.mark.parametrize(
    "method",
    [
        # Trailing return value differs structurally.
        """
        Int f(Int x, Int y) {
            if (x == 1) {
                return 99;
            }
            if (y == 2) {
                return 7;
            }
            return 100;
        }
        """,
        # Intervening statement is not an IfStatement.
        """
        Int f(Int x, Int y) {
            if (x == 1) {
                return 99;
            }
            Int z = y + 1;
            if (z == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """,
        # Intervening if has an else block.
        """
        Int f(Int x, Int y) {
            if (x == 1) {
                return 99;
            }
            if (y == 2) {
                Int r <- Int;
                return r;
            } else {
                return 5;
            }
            return 99;
        }
        """,
        # Early-return body has more than one statement.
        """
        Int f(Int x, Int y) {
            if (x == 1) {
                Int z = x + 1;
                return z;
            }
            if (y == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """,
        # No trailing return after the if-statements.
        """
        Int f(Int x, Int y) {
            if (x == 1) {
                return 99;
            }
            if (y == 2) {
                Int r <- Int;
                return r;
            }
        }
        """,
    ],
)
def test_does_not_fire_when_preconditions_unmet(method: str) -> None:
    parsed = frog_parser.parse_method(method)
    expected = frog_parser.parse_method(method)
    result = AbsorbRedundantEarlyReturnTransformer().transform(parsed)
    assert result == expected


def test_skips_nested_if_body() -> None:
    """The transform only fires on the method body's outermost block.
    Nested if-bodies that contain the absorbable pattern are left alone --
    the enclosing condition typically constrains the pattern unreachable,
    and ``RemoveUnreachable`` handles such cases. Adding a stale ``!P``
    conjunct here would prevent canonical equivalence with intermediate
    games that omit it.
    """
    method = """
        Int f(Int x, Int y, Int outer) {
            if (outer == 0) {
                if (x == 1) {
                    return 99;
                }
                if (y == 2) {
                    Int r <- Int;
                    return r;
                }
                return 99;
            }
            return 0;
        }
        """
    parsed = frog_parser.parse_method(method)
    expected = frog_parser.parse_method(method)
    result = AbsorbRedundantEarlyReturnTransformer().transform(parsed)
    assert result == expected


def test_negation_normalizes_equality_to_inequality() -> None:
    """``!(a == b)`` is rewritten to ``a != b`` directly to match the
    surface form preferred by the rest of the canonicalization pipeline.
    """
    method = """
        Int f(Int x, Int y) {
            if (x == 1) {
                return 99;
            }
            if (y == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """
    expected = """
        Int f(Int x, Int y) {
            if (x != 1 && y == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """
    parsed = frog_parser.parse_method(method)
    expected_parsed = frog_parser.parse_method(expected)
    result = AbsorbRedundantEarlyReturnTransformer().transform(parsed)
    assert result == expected_parsed


def test_negation_normalizes_inequality_to_equality() -> None:
    method = """
        Int f(Int x, Int y) {
            if (x != 1) {
                return 99;
            }
            if (y == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """
    expected = """
        Int f(Int x, Int y) {
            if (x == 1 && y == 2) {
                Int r <- Int;
                return r;
            }
            return 99;
        }
        """
    parsed = frog_parser.parse_method(method)
    expected_parsed = frog_parser.parse_method(expected)
    result = AbsorbRedundantEarlyReturnTransformer().transform(parsed)
    assert result == expected_parsed


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-111): absorbing the early-return guard duplicates
# its negation into the intervening guards; a non-deterministic guard would
# be re-evaluated independently, so absorption must be declined.
# ---------------------------------------------------------------------------

from proof_frog.transforms.control_flow import AbsorbRedundantEarlyReturn
from proof_frog.transforms._base import PipelineContext as _PipelineContext
from proof_frog.visitors import NameTypeMap as _NameTypeMap


def _aer_ctx(**namespace):
    return _PipelineContext(
        variables={},
        proof_let_types=_NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def _aer_nondet_prim():
    return frog_parser.parse_primitive_file("Primitive P(Int n) { Bool f(Int x); }")


def _aer_det_prim():
    return frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic Bool f(Int x); }"
    )


def test_aer_declines_on_nondeterministic_guard() -> None:
    """The early-return guard ``F.f(x)`` is non-deterministic; absorbing it
    would duplicate ``!F.f(x)`` into the intervening guard as an independent
    re-evaluation. The pass must decline."""
    game = frog_parser.parse_game("""
        Game G(P F, Int n) {
            Int O(Int x, Bool q) {
                if (F.f(x)) {
                    return 7;
                }
                if (q) {
                    return 5;
                }
                return 7;
            }
        }
        """)
    ctx = _aer_ctx(P=_aer_nondet_prim(), F=_aer_nondet_prim())
    result = AbsorbRedundantEarlyReturn().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "Absorb Redundant Early Return" for nm in ctx.near_misses
    )


def test_aer_fires_on_deterministic_control() -> None:
    """Control: a deterministic early-return guard ``D.f(x)`` is absorbed into
    the intervening guard as usual."""
    game = frog_parser.parse_game("""
        Game G(D F, Int n) {
            Int O(Int x, Bool q) {
                if (F.f(x)) {
                    return 7;
                }
                if (q) {
                    return 5;
                }
                return 7;
            }
        }
        """)
    ctx = _aer_ctx(D=_aer_det_prim(), F=_aer_det_prim())
    result = AbsorbRedundantEarlyReturn().apply(game, ctx)
    assert result != game  # the early-return guard was absorbed
