import pytest
from proof_frog import proof_engine, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
            }
            Int f() {
                Int value = field1 + field1;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field1 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field1 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field2 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = 100;
                field2 = field1;
            }
            Int f() {
                field2 = 200;
                Int value = field1 + field2;
                return value;
            }
        }""",
        ),
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
                field1 = field1;
            }
            Int f() {
                Int value = 2 * field1;
                return value;
            }
        }""",
            """
               Game Test() {
            Int field1;
            Void Initialize() {
                field1 = 100;
                field1 = field1;
            }
            Int f() {
                Int value = 2 * field1;
                return value;
            }
        }""",
        ),
    ],
)
def test_remove_duplicate_fields(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(method)
    expected_ast = frog_parser.parse_game(expected)

    print("EXPECTED", expected_ast)
    transformed_ast = proof_engine.remove_duplicate_fields(game_ast)
    print("TRANSFORMED", transformed_ast)
    assert transformed_ast == expected_ast
