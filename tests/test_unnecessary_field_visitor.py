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
            [],
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
            ["field"],
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
            [],
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
            [],
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
            [],
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
                    return field2
                }
            }
            """,
            [],
        ),
        # Aspirational test: make it so we can detect with higher fidelity whether fields are necessary
        # (
        #     """
        #     Game G() {
        #         Int field;
        #         Int f() {
        #             Int x = 1;
        #             Int y = 2;
        #             if (y == 2) {
        #                 x = 2;
        #                 field = field + 1;
        #             }
        #             return x;
        #         }
        #     }
        #     """,
        #     ["field"],
        # ),
    ],
)
def test_unnecessary_field_visitor(
    method: str,
    expected: list[str],
) -> None:
    game_ast = frog_parser.parse_game(method)

    received_unnecessary = dependencies.UnnecessaryFieldVisitor({}).visit(game_ast)
    assert expected == received_unnecessary
