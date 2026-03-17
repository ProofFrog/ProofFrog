import pytest
from proof_frog import frog_parser
from proof_frog.transforms.standardization import (
    _StabilizeIndependentStatementsTransformer,
)


@pytest.mark.parametrize(
    "source,expected",
    [
        # Basic swap: second assignment sorts before first → swapped
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = B();
                    Int v2 = A();
                    return v1 + v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v2 = A();
                    Int v1 = B();
                    return v1 + v2;
                }
            }
            """,
        ),
        # Already sorted — no change
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = A();
                    Int v2 = B();
                    return v1 + v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v1 = A();
                    Int v2 = B();
                    return v1 + v2;
                }
            }
            """,
        ),
        # Dependent statements — no change (v2 depends on v1)
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = 42;
                    Int v2 = v1 + 1;
                    return v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v1 = 42;
                    Int v2 = v1 + 1;
                    return v2;
                }
            }
            """,
        ),
        # Field assignments — no change (only typed declarations are swapped)
        (
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = 2;
                    field2 = 1;
                    return field1 + field2;
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = 2;
                    field2 = 1;
                    return field1 + field2;
                }
            }
            """,
        ),
    ],
)
def test_stabilize_independent(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"
