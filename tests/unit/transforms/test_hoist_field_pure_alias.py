import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import HoistFieldPureAliasTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = HoistFieldPureAliasTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # Variable hoisting: field = v where v appears in earlier statement's expression
        (
            """
            Game Test() {
                Int field2;
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = v4 + 1;
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field2;
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                    field2 = field7 + 1;
                }
            }
            """,
        ),
        # Variable not used in earlier statement — no hoisting
        (
            """
            Game Test() {
                Int field7;
                Int field2;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = 42;
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field7;
                Int field2;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = 42;
                    field7 = v4;
                }
            }
            """,
        ),
        # Variable only used in its own definition — no hoisting
        (
            """
            Game Test() {
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                }
            }
            """,
        ),
    ],
)
def test_hoist_field_pure_alias(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


def test_field_to_field_copy_not_hoisted() -> None:
    """field = other_field should NOT be hoisted (only field = local_var)."""
    source = """
    Game Test() {
        Int field1;
        Int field2;
        Int field3;
        Void Initialize() {
            field1 = 42;
            field3 = field1 + 1;
            field2 = field1;
        }
    }
    """
    _transform_and_compare(source, source)
