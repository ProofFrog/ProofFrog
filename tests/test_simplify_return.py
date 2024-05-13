import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
            """
            Int f() {
                return 1;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = g();
                return a;
            }
            """,
            """
            Int f() {
                return g();
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
        ),
    ],
)
def test_simplify_return(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = visitors.SimplifyReturnTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast
