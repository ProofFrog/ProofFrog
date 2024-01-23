import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        # Two that are the same
        (
            """
            Int f() {
                Int x = 1;
                if (true) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 2;
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (true) {
                    x = 2;
                } else if (false) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 2;
                return x;
            }
            """,
        ),
        (
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 2;
                } else if (true) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 2;
                } else {
                    x = 3;
                }
                return x;
            }
            """,
        ),
        (
            """
            Int f(Int y) {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (y == 1) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f(Int y) {
                Int x = 1;
                if (y == 1) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
        ),
        (
            """
            Int f() {
                Int x = 1;
                if (false) {
                    x = 2;
                } else if (false) {
                    x = 3;
                } else {
                    x = 4;
                }
                return x;
            }
            """,
            """
            Int f() {
                Int x = 1;
                x = 4;
                return x;
            }
            """,
        ),
    ],
)
def test_branch_elimination(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    print("EXPECTED: ", expected_ast)
    transformed_ast = visitors.BranchEliminiationTransformer().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast
