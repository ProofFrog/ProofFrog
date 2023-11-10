import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        # Simple substitution
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Shouldn't be transformed (both variables used)
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a += 1;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a += 1;
                return b;
            }
            """,
        ),
        # Many chained together
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                Int c = b;
                Int d = c;
                Int e = d;
                Int f = e;
                return f;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Works in if-statements too
        (
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    Int b = a;
                    x = b;
                } else {
                    Int a = 2;
                    Int b = a;
                    x = b;
                }
            }
            """,
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    x = a;
                } else {
                    Int a = 2;
                    x = a;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a += 1;
                }
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a += 1;
                }
                return b;
            }
            """,
        ),
    ],
)
def test_redundant_copies(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = visitors.RedundantCopyTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast
