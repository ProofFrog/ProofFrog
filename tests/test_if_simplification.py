import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        # Two that are the same
        (
            """
            Int f() {
                if (x == 1) {
                    return 1;
                } else if (x == 2) {
                    return 1;
                } else {
                    return 0;
                }
            }
            """,
            """
            Int f() {
                if (x == 1 || x == 2) {
                    return 1;
                } else {
                    return 0;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                if (x == 1) {
                    return 0;
                } else if (x == 2) {
                    return 1;
                } else {
                    return 1;
                }
            }
            """,
            """
            Int f() {
                if (x == 1) {
                    return 0;
                } else {
                    return 1;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                if (x == 1) {
                    return 1;
                } else {
                    return 1;
                }
            }
            """,
            """
            Int f() {
                if (true) {
                    return 1;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                if (false) {
                    return 1;
                } else if (true) {
                    return 0;
                } else if (true) {
                    return 1;
                }
            }
            """,
            """
            Int f() {
                if (false) {
                    return 1;
                } else if (true) {
                    return 0;
                } else if (true) {
                    return 1;
                }
            }
            """,
        ),
    ],
)
def test_redundant_copies(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = visitors.SimplifyIfTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast
