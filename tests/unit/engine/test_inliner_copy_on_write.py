"""Method inlining leaves its input game available for later proof hops."""

from proof_frog import frog_ast, visitors


def test_inline_transformer_does_not_mutate_input_game() -> None:
    helper = frog_ast.Method(
        frog_ast.MethodSignature("Helper", frog_ast.IntType(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(42))]),
    )
    call = frog_ast.FuncCall(frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"), [])
    assignment = frog_ast.Assignment(frog_ast.IntType(), frog_ast.Variable("x"), call)
    game = frog_ast.Game(
        (
            "G",
            [],
            [],
            [
                frog_ast.Method(
                    frog_ast.MethodSignature("Run", frog_ast.IntType(), []),
                    frog_ast.Block(
                        [assignment, frog_ast.ReturnStatement(frog_ast.Variable("x"))]
                    ),
                )
            ],
        )
    )
    original = str(game)

    result = visitors.InlineTransformer({("S", "Helper"): helper}).transform(game)

    assert str(game) == original
    assert isinstance(assignment.value, frog_ast.FuncCall)
    assert result != game
