"""Tests that InlineTransformer recurses into arguments of non-inlinable
FuncCalls so that nested scheme-method calls still get inlined.

Before the fix, `transform_func_call` returned the original expression
whenever the outer call was not inlinable, without descending into its
children. That left nested scheme-method calls (e.g.
`RF(S.Helper())`) untouched.
"""

import copy

from proof_frog import frog_ast, visitors


def _make_helper_scheme_lookup() -> dict[
    tuple[str, str], frog_ast.Method
]:
    """S.Helper() returns 42; S.Echo(x) returns x."""
    helper = frog_ast.Method(
        frog_ast.MethodSignature("Helper", frog_ast.IntType(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(42))]),
    )
    echo = frog_ast.Method(
        frog_ast.MethodSignature(
            "Echo",
            frog_ast.IntType(),
            [frog_ast.Parameter(frog_ast.IntType(), "x")],
        ),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Variable("x"))]),
    )
    return {("S", "Helper"): helper, ("S", "Echo"): echo}


def _inline_to_fixed_point(
    game: frog_ast.Game,
    lookup: dict[tuple[str, str], frog_ast.Method],
) -> frog_ast.Game:
    for _ in range(20):
        new_game = visitors.InlineTransformer(lookup).transform(copy.deepcopy(game))
        if new_game == game:
            break
        game = new_game
    return game


def _make_game(stmts: list[frog_ast.Statement]) -> frog_ast.Game:
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", frog_ast.IntType(), []),
        frog_ast.Block(stmts),
    )
    return frog_ast.Game(("TestGame", [], [], [init], []))


def _find_first_assignment(block: frog_ast.Block) -> frog_ast.Assignment:
    for s in block.statements:
        if isinstance(s, frog_ast.Assignment):
            return s
    raise AssertionError("no Assignment in block")


def test_inline_nested_in_non_inlinable_outer_call() -> None:
    """RF(S.Helper()) — RF is not in the lookup, so the outer call is
    non-inlinable; the inner scheme-method call must still be inlined.
    """
    lookup = _make_helper_scheme_lookup()
    s_helper_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"),
        [],
    )
    rf_call = frog_ast.FuncCall(frog_ast.Variable("RF"), [s_helper_call])
    game = _make_game(
        [
            frog_ast.Assignment(frog_ast.IntType(), frog_ast.Variable("x"), rf_call),
            frog_ast.ReturnStatement(frog_ast.Variable("x")),
        ]
    )

    game = _inline_to_fixed_point(game, lookup)

    init = game.get_method("Initialize")
    assign = _find_first_assignment(init.block)
    # After inlining, the assignment value should be RF(42) — inner inlined,
    # outer unchanged.
    assert isinstance(assign.value, frog_ast.FuncCall)
    assert isinstance(assign.value.func, frog_ast.Variable)
    assert assign.value.func.name == "RF"
    assert len(assign.value.args) == 1
    assert isinstance(assign.value.args[0], frog_ast.Integer)
    assert assign.value.args[0].num == 42


def test_inline_nested_in_equality_comparison() -> None:
    """x == S.Helper() — the FuncCall lives inside a BinaryOperation; the
    scheme call must still be inlined (no short-circuit on non-inlinable
    siblings).
    """
    lookup = _make_helper_scheme_lookup()
    cmp_exp = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable("x"),
        frog_ast.FuncCall(
            frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"), []
        ),
    )
    game = _make_game(
        [
            frog_ast.Assignment(frog_ast.BoolType(), frog_ast.Variable("b"), cmp_exp),
            frog_ast.ReturnStatement(frog_ast.Integer(0)),
        ]
    )

    game = _inline_to_fixed_point(game, lookup)

    init = game.get_method("Initialize")
    assign = _find_first_assignment(init.block)
    assert isinstance(assign.value, frog_ast.BinaryOperation)
    # RHS should now be the integer 42, not a FuncCall.
    assert isinstance(assign.value.right_expression, frog_ast.Integer)
    assert assign.value.right_expression.num == 42


def test_inline_nested_in_tuple_and_array_access() -> None:
    """[1, S.Helper()][1] — scheme call nested inside a Tuple expression."""
    lookup = _make_helper_scheme_lookup()
    tup = frog_ast.Tuple(
        [
            frog_ast.Integer(1),
            frog_ast.FuncCall(
                frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"), []
            ),
        ]
    )
    game = _make_game(
        [
            frog_ast.Assignment(
                frog_ast.ProductType([frog_ast.IntType(), frog_ast.IntType()]),
                frog_ast.Variable("t"),
                tup,
            ),
            frog_ast.ReturnStatement(frog_ast.Integer(0)),
        ]
    )

    game = _inline_to_fixed_point(game, lookup)

    init = game.get_method("Initialize")
    assign = _find_first_assignment(init.block)
    assert isinstance(assign.value, frog_ast.Tuple)
    assert isinstance(assign.value.values[1], frog_ast.Integer)
    assert assign.value.values[1].num == 42


def test_inline_nested_in_if_condition() -> None:
    """if (S.Helper() == 0) { ... } — scheme call inside an if condition.

    Uses a non-inlinable outer FuncCall `F(S.Helper())` to guarantee the
    fix is exercised: if we merely relied on BinaryOp COW recursion, this
    case would already pass without the fix.
    """
    lookup = _make_helper_scheme_lookup()
    s_helper_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("S"), "Helper"), []
    )
    f_call = frog_ast.FuncCall(frog_ast.Variable("F"), [s_helper_call])
    cond = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        f_call,
        frog_ast.Integer(0),
    )
    if_stmt = frog_ast.IfStatement(
        [cond],
        [frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(1))])],
    )
    game = _make_game([if_stmt, frog_ast.ReturnStatement(frog_ast.Integer(0))])

    game = _inline_to_fixed_point(game, lookup)

    init = game.get_method("Initialize")
    first = init.block.statements[0]
    assert isinstance(first, frog_ast.IfStatement)
    cond_out = first.conditions[0]
    assert isinstance(cond_out, frog_ast.BinaryOperation)
    # LHS should still be F(...), but its argument must be the integer 42.
    lhs = cond_out.left_expression
    assert isinstance(lhs, frog_ast.FuncCall)
    assert isinstance(lhs.func, frog_ast.Variable) and lhs.func.name == "F"
    assert len(lhs.args) == 1
    assert isinstance(lhs.args[0], frog_ast.Integer)
    assert lhs.args[0].num == 42


def test_non_inlinable_outer_without_nested_inlinable_is_unchanged() -> None:
    """Negative control: non-inlinable call with no nested inlinable
    scheme method inside should return the exact same object (no spurious
    copy-on-write).
    """
    lookup = _make_helper_scheme_lookup()
    outer = frog_ast.FuncCall(
        frog_ast.Variable("RF"),
        [frog_ast.Variable("m"), frog_ast.Integer(3)],
    )
    game = _make_game(
        [
            frog_ast.Assignment(frog_ast.IntType(), frog_ast.Variable("x"), outer),
            frog_ast.ReturnStatement(frog_ast.Variable("x")),
        ]
    )

    # One inlining pass should be a no-op on this game.
    new_game = visitors.InlineTransformer(lookup).transform(copy.deepcopy(game))
    assert new_game == game
