import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f() {
                Int a = 1;
                a = 2;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 2;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                a = 2;
                a = 3;
                a = 4;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 4;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a
                a = 2;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a
                a = 2;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = g();
                a = 3;
                return a;
            }
            """,
            """
            Int f() {
                Int a = g();
                a = 3;
                return a;
            }
            """,
        ),
    ],
)
def test_collapse_assignment(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = visitors.CollapseAssignmentTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast
