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
