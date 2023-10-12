from proof_frog import frog_parser, frog_ast, proof_engine

GAME = '''
Game Test(Int a) {
    void f() {
        Int b = a;
        if (a == 0) {
        }
        for (Int c = 0 to a) {
        }
        return a;
    }
}
'''

EXPECTED = '''
Game Test() {
    void f() {
        Int b = 100;
        if (100 == 0) {
        }
        for (Int c = 0 to 100) {
        }
        return 100;
    }
}
'''


def test_substitute_arg() -> None:
    game_ast = frog_parser.parse_game(GAME)
    expected_ast = frog_parser.parse_game(EXPECTED)
    transformed_ast = proof_engine.instantiate_game(game_ast, [frog_ast.Integer(100)])
    print(transformed_ast)
    assert expected_ast == transformed_ast
