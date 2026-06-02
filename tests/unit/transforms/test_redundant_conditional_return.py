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
