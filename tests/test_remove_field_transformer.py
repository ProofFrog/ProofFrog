import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,to_remove,expected",
    [
        (
            """
            Game G() {
                Int field;
                Int f() {
                    return 2;
                }
            }
            """,
            ["field"],
            """
            Game G() {
                Int f() {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    Int x = 1;
                    Int y = 2;
                    if (field > 2) {
                        y = 2;
                    }
                    return x;
                }
            }
            """,
            ["field"],
            """
            Game G() {
                Int f() {
                    Int x = 1;
                    Int y = 2;
                    return x;
                }
            }
            """,
        ),
    ],
)
def test_remove_field_transformer(
    method: str,
    to_remove: list[str],
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(method)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = visitors.RemoveFieldTransformer(to_remove).transform(game_ast)

    print(transformed_ast)
    assert expected_ast == transformed_ast
