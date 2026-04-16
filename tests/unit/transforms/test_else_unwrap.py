"""Tests for the ElseUnwrap transform.

When an if-else has its true branch unconditionally returning, the else
block is unwrapped into sequential code after the if.
"""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import ElseUnwrapTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic pattern: if true branch returns, unwrap else
        (
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    return a;
                } else {
                    return b;
                }
            }
            """,
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    return a;
                }
                return b;
            }
            """,
        ),
        # Multi-statement true branch
        (
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    Int v = a + b;
                    return v;
                } else {
                    return b;
                }
            }
            """,
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    Int v = a + b;
                    return v;
                }
                return b;
            }
            """,
        ),
        # No-op: true branch doesn't return
        (
            """
            Int f(Bool cond, Int a, Int b) {
                Int x;
                if (cond) {
                    x = a;
                } else {
                    x = b;
                }
                return x;
            }
            """,
            """
            Int f(Bool cond, Int a, Int b) {
                Int x;
                if (cond) {
                    x = a;
                } else {
                    x = b;
                }
                return x;
            }
            """,
        ),
        # No-op: no else block (already Pattern 1)
        (
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    return a;
                }
                return b;
            }
            """,
            """
            Int f(Bool cond, Int a, Int b) {
                if (cond) {
                    return a;
                }
                return b;
            }
            """,
        ),
        # Multi-statement else block
        (
            """
            Int f(Bool cond, Int a, Int b, Int c) {
                if (cond) {
                    return a;
                } else {
                    Int v = b + c;
                    return v;
                }
            }
            """,
            """
            Int f(Bool cond, Int a, Int b, Int c) {
                if (cond) {
                    return a;
                }
                Int v = b + c;
                return v;
            }
            """,
        ),
        # Nested: true branch has nested if-else that unconditionally returns.
        # The transform recurses, so the inner if-else also gets unwrapped.
        (
            """
            Int f(Bool c, Bool d, Int x, Int y, Int z) {
                if (c) {
                    if (d) {
                        return x;
                    } else {
                        return y;
                    }
                } else {
                    return z;
                }
            }
            """,
            """
            Int f(Bool c, Bool d, Int x, Int y, Int z) {
                if (c) {
                    if (d) {
                        return x;
                    }
                    return y;
                }
                return z;
            }
            """,
        ),
    ],
    ids=[
        "basic_unwrap",
        "multi_stmt_true_branch",
        "no_op_no_return",
        "no_op_no_else",
        "multi_stmt_else",
        "nested_unconditional_return",
    ],
)
def test_else_unwrap(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = ElseUnwrapTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
