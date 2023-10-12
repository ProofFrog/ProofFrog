import pytest
from proof_frog import frog_ast, frog_parser


@pytest.mark.parametrize("method,expected,substitution_map", [
    # Simple substitution
    (
        '''
        void f() {
            Int b = a;
            if (a == 0) {
            }
            for (Int c = 0 to a) {
            }
            return a;
        }
        ''',
        '''
        void f() {
            Int b = 100;
            if (100 == 0) {
            }
            for (Int c = 0 to 100) {
            }
            return 100;
        }
        ''',
        {'a': frog_ast.Integer(100)}
    )
])
def test_substitution(method: str, expected: str, substitution_map: dict[str, frog_ast.ASTNode]) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformer = frog_ast.SubstitutionTransformer(substitution_map)
    transformed_ast = game_ast.transform(transformer)
    print(transformed_ast)
    assert expected_ast == transformed_ast
