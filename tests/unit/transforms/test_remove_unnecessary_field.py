import pytest
from proof_frog import dependencies, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Game G() {
                Int field;
                Int f() {
                    return field;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    return field;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field;
                Int f() {
                    return 2;
                }
            }
            """,
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
                    if (field > 2) {
                        return 1;
                    }
                    return 2;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    }
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
                    if (field > 2) {
                        return 1;
                    } else {
                        return 2;
                    }
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    if (field > 2) {
                        return 1;
                    } else {
                        return 2;
                    }
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
                    if (field > 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
            """
            Game G() {
                Int field;
                Int f() {
                    Int x = 1;
                    if (field > 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 > 2) {
                        field2 = 2;
                    }
                    return 0;
                }
                Int g() {
                    return field2;
                }
            }
            """,
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 > 2) {
                        field2 = 2;
                    }
                    return 0;
                }
                Int g() {
                    return field2;
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
                    if (y == 2) {
                        x = 2;
                        field = field + 1;
                    }
                    return x;
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int x = 1;
                    Int y = 2;
                    if (y == 2) {
                        x = 2;
                    }
                    return x;
                }
            }
            """,
        ),
    ],
)
def test_unnecessary_field_visitor(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(method)
    expected_ast = frog_parser.parse_game(expected)
    print("expected AST", expected_ast)
    transformed_ast = dependencies.remove_unnecessary_fields(game_ast)
    print("transformed AST", transformed_ast)
    assert expected_ast == transformed_ast
