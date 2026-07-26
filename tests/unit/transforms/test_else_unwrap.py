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


def test_f123_malformed_multiblock_if_not_unwrapped() -> None:
    """F-123: ElseUnwrap indexed blocks[1] as the else guarded only by
    has_else_block(), which accepts any block surplus. On a malformed
    IfStatement([C], [B0, B1, B2]) it spliced B1 and silently dropped B2. A
    well-formed single-else if has exactly len(conditions)+1 blocks; the pass
    must now decline the malformed shape, leaving B2 intact."""
    from proof_frog import frog_ast

    cond = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, frog_ast.Variable("a"), frog_ast.Integer(1)
    )
    then_block = frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(1))])
    b1 = frog_ast.Block(
        [frog_ast.Assignment(None, frog_ast.Variable("x"), frog_ast.Integer(2))]
    )
    b2 = frog_ast.Block(
        [frog_ast.Assignment(None, frog_ast.Variable("y"), frog_ast.Integer(3))]
    )
    malformed = frog_ast.IfStatement([cond], [then_block, b1, b2])
    block = frog_ast.Block(
        [malformed, frog_ast.ReturnStatement(frog_ast.Integer(9))]
    )
    out = ElseUnwrapTransformer().transform(block)
    assert out == block  # declined -- nothing spliced, B2 not dropped
    assert "y" in str(out)  # B2's write survives


def test_f123_wellformed_if_else_still_unwraps() -> None:
    """Control for F-123: a proper 2-block if-else still unwraps."""
    from proof_frog import frog_ast

    cond = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, frog_ast.Variable("a"), frog_ast.Integer(1)
    )
    wf = frog_ast.IfStatement(
        [cond],
        [
            frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(1))]),
            frog_ast.Block(
                [frog_ast.Assignment(None, frog_ast.Variable("x"), frog_ast.Integer(2))]
            ),
        ],
    )
    block = frog_ast.Block([wf, frog_ast.ReturnStatement(frog_ast.Integer(9))])
    assert ElseUnwrapTransformer().transform(block) != block  # unwrapped
