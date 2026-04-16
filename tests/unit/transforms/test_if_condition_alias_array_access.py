import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import IfConditionAliasSubstitutionTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = IfConditionAliasSubstitutionTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # Array access on parameter: c[0] == field1 -> substitute field1 with c[0]
        (
            """
            Game Test() {
                Int field1;
                Int f([Int, Int] c) {
                    if (c[0] == field1) {
                        return field1;
                    }
                    return c[0];
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f([Int, Int] c) {
                    if (c[0] == field1) {
                        return c[0];
                    }
                    return c[0];
                }
            }
            """,
        ),
    ],
)
def test_if_condition_alias_array_access(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)
