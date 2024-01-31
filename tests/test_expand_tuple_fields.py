import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "game,expected",
    [
        # Two that are the same
        (
            """
            Game G() {
                Int * Int * Int * Int myTuple;
                Void Initialize() {
                    myTuple = [1, 2, 3, 4];
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Int myTuple2;
                Int myTuple3;
                Void Initialize() {
                    myTuple0 = 1;
                    myTuple1 = 2;
                    myTuple2 = 3;
                    myTuple3 = 4;
                }
            }
            """,
        ),
    ],
)
def test_expand_tuple_fields(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    print("EXPECTED: ", expected_ast)
    transformed_ast = visitors.ExpandFieldTuples().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast
