import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import SimplifyReturnTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
            """
            Int f() {
                return 1;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = g();
                return a;
            }
            """,
            """
            Int f() {
                return g();
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                f(b);
                return a;
            }
            """,
        ),
    ],
)
def test_simplify_return(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SimplifyReturnTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # Intervening statement reassigns a local that appears in expr
        (
            """
            Int f(Int x) {
                Int v = x + 1;
                x = 10;
                return v;
            }
            """,
            """
            Int f(Int x) {
                Int v = x + 1;
                x = 10;
                return v;
            }
            """,
        ),
        # Intervening statement reassigns a different local in expr
        (
            """
            Int f() {
                Int a = 1;
                Int b = 2;
                Int v = a + b;
                a = 99;
                return v;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = 2;
                Int v = a + b;
                a = 99;
                return v;
            }
            """,
        ),
        # Multiple intervening statements, one modifies a dependency
        (
            """
            Int f(Int x, Int y) {
                Int v = x + y;
                Int z = 5;
                x = z;
                return v;
            }
            """,
            """
            Int f(Int x, Int y) {
                Int v = x + y;
                Int z = 5;
                x = z;
                return v;
            }
            """,
        ),
        # Intervening statement does NOT modify any dependency — should still inline
        (
            """
            Int f(Int x) {
                Int v = x + 1;
                Int z = 99;
                return v;
            }
            """,
            """
            Int f(Int x) {
                Int z = 99;
                return x + 1;
            }
            """,
        ),
    ],
)
def test_simplify_return_dependency_safety(
    method: str,
    expected: str,
) -> None:
    """SimplifyReturn must not inline when intervening statements modify
    free variables of the expression being inlined."""
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SimplifyReturnTransformer().transform(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "game,expected",
    [
        # Field modified between assignment and return
        (
            """
            Game G() {
                Int field1;

                Int f(Int x) {
                    Int v = field1 + x;
                    field1 = 42;
                    return v;
                }
            }
            """,
            """
            Game G() {
                Int field1;

                Int f(Int x) {
                    Int v = field1 + x;
                    field1 = 42;
                    return v;
                }
            }
            """,
        ),
    ],
)
def test_simplify_return_field_dependency(
    game: str,
    expected: str,
) -> None:
    """SimplifyReturn must not inline when intervening statements modify
    a field that the inlined expression depends on."""
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = SimplifyReturnTransformer().transform_game(game_ast)
    print(transformed_ast)
    assert expected_ast == transformed_ast
