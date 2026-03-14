"""Tests that 'this' references in scheme methods are rewritten for inlining."""

import copy

from proof_frog import frog_ast, visitors
from proof_frog.proof_engine import rewrite_this_in_scheme


def _make_scheme_with_this_call() -> frog_ast.Scheme:
    """Build a minimal scheme where KeyGen calls this.Helper()."""
    helper_method = frog_ast.Method(
        frog_ast.MethodSignature("Helper", frog_ast.IntType(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(42))]),
    )
    keygen_body = frog_ast.Block(
        [
            frog_ast.ReturnStatement(
                frog_ast.FuncCall(
                    frog_ast.FieldAccess(frog_ast.Variable("this"), "Helper"),
                    [],
                )
            )
        ]
    )
    keygen_method = frog_ast.Method(
        frog_ast.MethodSignature("KeyGen", frog_ast.IntType(), []),
        keygen_body,
    )
    return frog_ast.Scheme(
        imports=[],
        name="TestScheme",
        parameters=[],
        primitive_name="SomePrimitive",
        fields=[],
        requirements=[],
        methods=[helper_method, keygen_method],
    )


def test_this_rewritten_in_method_lookup() -> None:
    """After rewrite_this_in_scheme, 'this.Helper()' becomes 'S.Helper()'."""
    scheme = _make_scheme_with_this_call()
    rewritten = rewrite_this_in_scheme("S", copy.deepcopy(scheme))

    keygen = next(m for m in rewritten.methods if m.signature.name == "KeyGen")
    ret_stmt = keygen.block.statements[0]
    assert isinstance(ret_stmt, frog_ast.ReturnStatement)
    func_call = ret_stmt.expression
    assert isinstance(func_call, frog_ast.FuncCall)
    assert isinstance(func_call.func, frog_ast.FieldAccess)
    assert isinstance(func_call.func.the_object, frog_ast.Variable)
    assert func_call.func.the_object.name == "S"


def test_this_inlined_via_fixed_point() -> None:
    """A this.Helper() call inside KeyGen should be fully inlined."""
    scheme = _make_scheme_with_this_call()
    rewritten = rewrite_this_in_scheme("S", copy.deepcopy(scheme))

    lookup = {}
    for method in rewritten.methods:
        lookup[("S", method.signature.name)] = method

    # Build a trivial game that calls S.KeyGen()
    game_body = frog_ast.Block(
        [
            frog_ast.Assignment(
                frog_ast.IntType(),
                frog_ast.Variable("x"),
                frog_ast.FuncCall(
                    frog_ast.FieldAccess(frog_ast.Variable("S"), "KeyGen"),
                    [],
                ),
            )
        ]
    )
    game_method = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", frog_ast.Void(), []),
        game_body,
    )
    game = frog_ast.Game(("TestGame", [], [], [game_method], []))

    # Run fixed-point inlining
    for _ in range(10):
        new_game = visitors.InlineTransformer(lookup).transform(copy.deepcopy(game))
        if new_game == game:
            break
        game = new_game

    # After inlining, x should equal 42 (the return value of Helper)
    init = game.get_method("Initialize")
    assign = init.block.statements[-1]
    assert isinstance(assign, frog_ast.Assignment)
    assert isinstance(assign.value, frog_ast.Integer)
    assert assign.value.num == 42
