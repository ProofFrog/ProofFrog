"""Tests for the IfSplitBranchAssignment transform.

When an if-else has all branches ending with a typed assignment to the same
variable (as produced by the inliner), and subsequent statements use that
variable, this transform moves the subsequent statements into each branch
with the variable substituted by its branch value.
"""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import IfSplitBranchAssignmentTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic pattern with typed declarations (from inliner output)
        (
            """
            Bool f(Bool cond, Bool a, Bool b) {
                if (cond) {
                    Bool x = a;
                } else {
                    Bool x = b;
                }
                return x;
            }
            """,
            """
            Bool f(Bool cond, Bool a, Bool b) {
                if (cond) {
                    return a;
                } else {
                    return b;
                }
            }
            """,
        ),
        # Multiple subsequent statements: all get folded into branches
        (
            """
            Int f(Bool cond, Int a, Int b, Int c) {
                if (cond) {
                    Int x = a;
                } else {
                    Int x = b;
                }
                Int y = x + c;
                return y;
            }
            """,
            """
            Int f(Bool cond, Int a, Int b, Int c) {
                if (cond) {
                    Int y = a + c;
                    return y;
                } else {
                    Int y = b + c;
                    return y;
                }
            }
            """,
        ),
        # Untyped assignments: still fires (folds subsequent code)
        (
            """
            Bool f(Bool cond, Int a, Int b) {
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
            Bool f(Bool cond, Int a, Int b) {
                if (cond) {
                    return a;
                } else {
                    return b;
                }
            }
            """,
        ),
        # No-op: branches don't assign the same variable
        (
            """
            Int f(Bool cond, Int a, Int b) {
                Int x;
                Int y;
                if (cond) {
                    Int x = a;
                } else {
                    Int y = b;
                }
                return x;
            }
            """,
            """
            Int f(Bool cond, Int a, Int b) {
                Int x;
                Int y;
                if (cond) {
                    Int x = a;
                } else {
                    Int y = b;
                }
                return x;
            }
            """,
        ),
        # No-op: no subsequent statements after if-else
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
                } else {
                    return b;
                }
            }
            """,
        ),
        # With preceding variable declaration to remove
        (
            """
            Bool f(Bool cond, Bool a, Bool b) {
                Bool x;
                if (cond) {
                    Bool x = a;
                } else {
                    Bool x = b;
                }
                return x;
            }
            """,
            """
            Bool f(Bool cond, Bool a, Bool b) {
                if (cond) {
                    return a;
                } else {
                    return b;
                }
            }
            """,
        ),
        # F-161: an element write to the branch variable (`x[0] = 5`, an
        # ArrayAccess l-value) is a reassignment and must block the fold --
        # otherwise the write would be moved into each branch with `x`
        # substituted by its branch value, mutating that branch value.
        (
            """
            Int f(Bool cond, Array<Int, 2> a, Array<Int, 2> b) {
                if (cond) {
                    Array<Int, 2> x = a;
                } else {
                    Array<Int, 2> x = b;
                }
                x[0] = 5;
                return x[1];
            }
            """,
            """
            Int f(Bool cond, Array<Int, 2> a, Array<Int, 2> b) {
                if (cond) {
                    Array<Int, 2> x = a;
                } else {
                    Array<Int, 2> x = b;
                }
                x[0] = 5;
                return x[1];
            }
            """,
        ),
    ],
    ids=[
        "basic_typed",
        "multiple_subsequent",
        "untyped_assignments",
        "no_op_different_vars",
        "no_op_no_subsequent",
        "removes_preceding_declaration",
        "no_op_element_write_to_var",
    ],
)
def test_if_split_branch_assignment(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = IfSplitBranchAssignmentTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
