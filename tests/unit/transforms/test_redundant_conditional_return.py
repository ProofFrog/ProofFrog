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
        # Multi-statement if body — no change
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
    ],
)
def test_redundant_conditional_return(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = RedundantConditionalReturnTransformer().transform(method_ast)
    assert expected_ast == transformed_ast
