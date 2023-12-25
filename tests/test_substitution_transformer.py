import pytest
from proof_frog import visitors, frog_parser, frog_ast


@pytest.mark.parametrize(
    "method,expected,substitution_map",
    [
        # Simple substitution
        (
            """
        Void f() {
            Int b = a;
            if (a == 0) {
            }
            for (Int c = 0 to a) {
            }
            return a;
        }
        """,
            """
        Void f() {
            Int b = 100;
            if (100 == 0) {
            }
            for (Int c = 0 to 100) {
            }
            return 100;
        }
        """,
            [(frog_ast.Variable("a"), frog_ast.Integer(100))],
        ),
        # Substitution shouldn't change field names
        (
            """
        Void f(A.a bla) {
            A.a x = bla;
        }
        """,
            """
        Void f(A.a bla) {
            A.a x = bla;
        }
        """,
            [(frog_ast.Variable("a"), frog_ast.Integer(100))],
        ),
        (
            """
        Void f() {
            E.Ciphertext x = a;
        }
        """,
            """
        Void f() {
            Sigma.Ciphertext x = a;
        }
        """,
            [(frog_ast.Variable("E"), frog_ast.Variable("Sigma"))],
        ),
    ],
)
def test_substitution(
    method: str,
    expected: str,
    substitution_map: list[(frog_ast.ASTNode, frog_ast.ASTNode)],
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = visitors.SubstitutionTransformer(substitution_map).transform(
        game_ast
    )
    print(transformed_ast)
    assert expected_ast == transformed_ast
