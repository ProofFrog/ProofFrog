import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "game,expected",
    [
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
        # We cannot expand because we do not know all tuple values.
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 100;
                    myTuple[1] = 200;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 100;
                    myTuple[1] = 200;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = [100, 200];
                }
                Void f() {
                    challenger.g(myTuple);
                    challenger.h(myTuple[0], myTuple[1]);
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
                Void f() {
                    challenger.g([myTuple0, myTuple1]);
                    challenger.h(myTuple0, myTuple1);
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = [100, 200];
                }
                Void swap() {
                    Int a = myTuple[0];
                    myTuple[0] = myTuple[1];
                    myTuple[1] = a;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
                Void swap() {
                    Int a = myTuple0;
                    myTuple0 = myTuple1;
                    myTuple1 = a;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int firstTuple;
                Int * Int secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    Int * Int a = firstTuple;
                    firstTuple = secondTuple;
                    secondTuple = a;
                }
            }
            """,
            """
            Game G() {
                Int * Int firstTuple;
                Int * Int secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    Int * Int a = firstTuple;
                    firstTuple = secondTuple;
                    secondTuple = a;
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
    transformed_ast = visitors.ExpandTupleFields().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast
