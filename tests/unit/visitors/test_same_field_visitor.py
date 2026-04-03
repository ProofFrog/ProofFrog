import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "game,pair,expected",
    [
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = 0;
                    field2 = 1;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = 1;
                    field2 = 1;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    Int x = 3;
                    field1 = x;
                    field2 = x;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    Int x = 3;
                    field1 = x;
                    x = 5;
                    field2 = x;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = challenger.g();
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        (
            """
            Game G() {
                Set<Int> s1;
                Set<Int> s2;
                Void f() {
                    Int x = 5;
                    s1 = s1 union x;
                    s2 = s2 union x;
                }
            }
            """,
            ("s1", "s2"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    Int a = 2;
                    x = 5;
                    y = 5;
                    a = a + 1;
                    a = a * a;
                    a = a + x + y;
                    x = x + 1;
                    y = y + 1;
                }
            }
            """,
            ("x", "y"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    x = 5;
                    if (True) {
                        y = 10;
                    }
                    y = 5;
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            True,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    a[0] = 100;
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    [Int, Int] a = [5, 10];
                    x = a[0];
                    a = [20, 30];
                    y = a[0];
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        (
            """
            Game G() {
                Int x;
                Int y;
                Void f() {
                    x = 5;
                    y = 5;

                    x = 10;
                    Int a = y;
                    y = 10;
                    return a;
                }
            }
            """,
            ("x", "y"),
            False,
        ),
        # Direct field copy after function call: field1 = f(); field2 = field1
        # This IS a valid duplicate — the copy doesn't replicate the call.
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = field1;
                }
            }
            """,
            ("field1", "field2"),
            True,
        ),
        # Two independent function calls — NOT the same
        # (each call may return a different value)
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Void f() {
                    field1 = challenger.g();
                    field2 = challenger.h();
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
        # Direct copy but pair field read before copy — NOT safe
        (
            """
            Game G() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = challenger.g();
                    Int x = field2;
                    field2 = field1;
                    return x;
                }
            }
            """,
            ("field1", "field2"),
            False,
        ),
    ],
)
def test_same_field_visitor(game: str, pair: tuple[str, str], expected: bool) -> None:
    game_ast = frog_parser.parse_game(game)

    print("GAME", game_ast)
    are_the_same = visitors.SameFieldVisitor(pair).visit(game_ast)

    if expected:
        assert isinstance(are_the_same, list)
    else:
        assert are_the_same is None
