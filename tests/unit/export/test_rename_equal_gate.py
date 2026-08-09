"""Unit tests for the Move 1 rename-equality gate (``_rename_equal_projection``).

The gate must fire exactly when two projected oracle bodies are equal modulo
a positional renaming of typed local binders (the ``Alpha Rename`` /
``Variable Standardization`` legs), and DECLINE on every shadowing hazard —
never risking a maybe-tactic (MAP principle 2). The end-to-end ``proc; sim.``
tactic is probe-validated (``.ec-tmp/q1/probe_legs.ec`` ``leg_alpha_rename``)
and pinned by ``tests/integration/ec_templates/local_rename_sim.ec``.
"""

from proof_frog import frog_ast
from proof_frog.export.easycrypt.chain_emitter import _rename_equal_projection


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _typed_call(name: str, obj: str, method: str, *args: str) -> frog_ast.Assignment:
    call = frog_ast.FuncCall(
        frog_ast.FieldAccess(_var(obj), method), [_var(a) for a in args]
    )
    return frog_ast.Assignment(_var("T"), _var(name), call)


def _untyped(name: str, value: str) -> frog_ast.Assignment:
    return frog_ast.Assignment(None, _var(name), _var(value))


def _sample(name: str) -> frog_ast.Sample:
    return frog_ast.Sample(_var("T"), _var(name), _var("D"))


def _ret(expr_name: str) -> frog_ast.ReturnStatement:
    return frog_ast.ReturnStatement(_var(expr_name))


def _game(
    statements: list[frog_ast.Statement],
    fields: list[frog_ast.Field] | None = None,
    params: list[frog_ast.Parameter] | None = None,
) -> frog_ast.Game:
    sig = frog_ast.MethodSignature("foo", _var("C"), params or [])
    method = frog_ast.Method(sig, frog_ast.Block(statements))
    return frog_ast.Game(("G", [], fields or [], [method]))


def _field(name: str) -> frog_ast.Field:
    return frog_ast.Field(_var("T"), name, None)


def test_fires_on_typed_assignment_rename() -> None:
    before = _game([_typed_call("a", "E", "f", "k"), _ret("a")], [_field("k")])
    after = _game([_typed_call("b", "E", "f", "k"), _ret("b")], [_field("k")])
    assert _rename_equal_projection(before, after)


def test_fires_on_sample_var_rename() -> None:
    # The dead-call-drop rename branch cannot take this (sample backbones are
    # tagged by bound var); Move 1 is the only route.
    before = _game([_sample("a"), _typed_call("x", "E", "f", "a"), _ret("x")])
    after = _game([_sample("b"), _typed_call("y", "E", "f", "b"), _ret("y")])
    assert _rename_equal_projection(before, after)


def test_fires_on_alpha_style_names() -> None:
    before = _game([_typed_call("__a4__", "E", "f", "k"), _ret("__a4__")])
    after = _game([_typed_call("__a28__", "E", "f", "k"), _ret("__a28__")])
    assert _rename_equal_projection(before, after)


def test_declines_on_value_change() -> None:
    before = _game([_typed_call("a", "E", "f", "k"), _ret("a")])
    after = _game([_typed_call("b", "E", "g", "k"), _ret("b")])
    assert not _rename_equal_projection(before, after)


def test_declines_on_field_rename() -> None:
    before = _game([_typed_call("a", "E", "f", "x"), _ret("a")], [_field("x")])
    after = _game([_typed_call("a", "E", "f", "y"), _ret("a")], [_field("y")])
    assert not _rename_equal_projection(before, after)


def test_declines_on_statement_reorder() -> None:
    before = _game(
        [_typed_call("a", "E", "f", "k"), _sample("s"), _ret("a")], [_field("k")]
    )
    after = _game(
        [_sample("t"), _typed_call("b", "E", "f", "k"), _ret("b")], [_field("k")]
    )
    assert not _rename_equal_projection(before, after)


def test_declines_on_duplicate_binder() -> None:
    before = _game(
        [_typed_call("a", "E", "f", "k"), _typed_call("a", "E", "g", "k"), _ret("a")]
    )
    after = _game(
        [_typed_call("a", "E", "f", "k"), _typed_call("b", "E", "g", "k"), _ret("b")]
    )
    assert not _rename_equal_projection(before, after)


def test_declines_on_use_before_binding() -> None:
    # ``x`` is read (outer scope) before its typed binding — Alpha Rename
    # preserves the early read per-occurrence; a name substitution cannot.
    before = _game(
        [_untyped("y", "x"), _typed_call("x", "E", "f", "k"), _ret("x")]
    )
    after = _game(
        [_untyped("y", "x"), _typed_call("z", "E", "f", "k"), _ret("z")]
    )
    assert not _rename_equal_projection(before, after)


def test_declines_on_binder_colliding_with_param() -> None:
    params = [frog_ast.Parameter(_var("T"), "m")]
    before = _game([_typed_call("m", "E", "f", "k"), _ret("m")], params=params)
    after = _game([_typed_call("n", "E", "f", "k"), _ret("n")], params=params)
    assert not _rename_equal_projection(before, after)


def test_declines_on_param_rename() -> None:
    before = _game(
        [_typed_call("a", "E", "f", "m"), _ret("a")],
        params=[frog_ast.Parameter(_var("T"), "m")],
    )
    after = _game(
        [_typed_call("a", "E", "f", "n"), _ret("a")],
        params=[frog_ast.Parameter(_var("T"), "n")],
    )
    assert not _rename_equal_projection(before, after)


def test_declines_on_binder_type_change() -> None:
    before = _game([_typed_call("a", "E", "f", "k"), _ret("a")])
    call = frog_ast.FuncCall(frog_ast.FieldAccess(_var("E"), "f"), [_var("k")])
    after = _game(
        [frog_ast.Assignment(_var("U"), _var("b"), call), _ret("b")]
    )
    assert not _rename_equal_projection(before, after)


def test_declines_on_exactly_equal_bodies_only_if_caller_handles() -> None:
    # Equal bodies also satisfy the gate (identity renaming); the dispatch
    # order in ``_oracle_step_tactic`` puts the exact-equal branch first, so
    # this is unreachable there — asserted here so a dispatch reorder that
    # would change rungs is caught deliberately.
    g = _game([_typed_call("a", "E", "f", "k"), _ret("a")])
    assert _rename_equal_projection(g, g)
