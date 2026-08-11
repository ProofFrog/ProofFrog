"""Unit tests for Move 3a's delta-det guard-site walk (IES class).

Covers the raw delta matcher (``_raw_guard_delta_site``), the symbolic
ev-term environment (``_EvEnv``), and decline mutations. The tactic shape
itself is pinned by the Q1 probe (``.ec-tmp/q1/probe_legs.ec``
``leg_injective_eq_simplify``, EC-verified) and the walk is EC-gated: every
firing is compiled in EasyCrypt by the per-move gates.
"""

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _EvEnv,
    _raw_guard_delta_site,
)

OPS = frog_ast.BinaryOperators
DET = {"K": {"decaps", "encode"}, "L": {"get"}}


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _det_call(name: str, mod: str, meth: str, *args: str) -> frog_ast.Assignment:
    call = frog_ast.FuncCall(
        frog_ast.FieldAccess(_var(mod), meth), [_var(a) for a in args]
    )
    return frog_ast.Assignment(_var("T"), _var(name), call)


def _guarded(cond: frog_ast.Expression) -> frog_ast.IfStatement:
    body = frog_ast.Block(
        [frog_ast.Assignment(None, _var("out"), _var("x"))]
    )
    return frog_ast.IfStatement([cond], [body])


def _method(statements: list[frog_ast.Statement]) -> frog_ast.Method:
    sig = frog_ast.MethodSignature("challenge", _var("C"), [])
    stmts = statements + [frog_ast.ReturnStatement(_var("out"))]
    return frog_ast.Method(sig, frog_ast.Block(stmts))


def test_raw_delta_matcher_fires_on_delta_plus_guard() -> None:
    eq = frog_ast.BinaryOperation(OPS.EQUALS, _var("a"), _var("b"))
    eq2 = frog_ast.BinaryOperation(OPS.EQUALS, _var("r1"), _var("r2"))
    mb = _method([_det_call("x", "K", "encode", "a"), _guarded(eq)])
    ma = _method(
        [
            _det_call("x", "K", "encode", "a"),
            _det_call("r1", "K", "decaps", "a"),
            _det_call("r2", "K", "decaps", "b"),
            _guarded(eq2),
        ]
    )
    assert _raw_guard_delta_site(mb, ma, DET)


def test_raw_delta_matcher_declines_without_delta() -> None:
    eq = frog_ast.BinaryOperation(OPS.EQUALS, _var("a"), _var("b"))
    tru = frog_ast.Boolean(True)
    mb = _method([_det_call("x", "K", "encode", "a"), _guarded(eq)])
    ma = _method([_det_call("x", "K", "encode", "a"), _guarded(tru)])
    assert not _raw_guard_delta_site(mb, ma, DET)


def test_raw_delta_matcher_declines_on_nondet_extra() -> None:
    eq = frog_ast.BinaryOperation(OPS.EQUALS, _var("a"), _var("b"))
    mb = _method([_guarded(eq)])
    ma = _method(
        [_det_call("r1", "K", "keygen"), _guarded(eq)]  # keygen not det
    )
    assert not _raw_guard_delta_site(mb, ma, DET)


def test_raw_delta_matcher_declines_on_two_guard_diffs() -> None:
    eq = frog_ast.BinaryOperation(OPS.EQUALS, _var("a"), _var("b"))
    tru = frog_ast.Boolean(True)
    mb = _method([_guarded(eq), _guarded(eq)])
    ma = _method(
        [
            _det_call("r1", "K", "decaps", "a"),
            _guarded(tru),
            _guarded(tru),
        ]
    )
    assert not _raw_guard_delta_site(mb, ma, DET)


def test_raw_delta_matcher_declines_on_other_stmt_diff() -> None:
    eq = frog_ast.BinaryOperation(OPS.EQUALS, _var("a"), _var("b"))
    tru = frog_ast.Boolean(True)
    mb = _method(
        [frog_ast.Assignment(_var("T"), _var("z"), _var("a")), _guarded(eq)]
    )
    ma = _method(
        [frog_ast.Assignment(_var("T"), _var("z"), _var("b")), _guarded(tru)]
    )
    assert not _raw_guard_delta_site(mb, ma, DET)


# --- _EvEnv symbolic environment -------------------------------------------


def _env() -> _EvEnv:
    return _EvEnv(
        det_methods=DET,
        clone_alias={"K": "K_c", "L": "L_c"},
        param_names={"ct0", "ct1"},
        global_names={"dk0", "dk1"},
        side_ref="Step_X",
        pins={},
        glob_pins={},
    )


def test_ev_env_assignment_pins_param() -> None:
    env = _env()
    assert env.feed(ec_ast.Assign("a9", "ct0.`2"))
    assert env.env["a9"] == "kv0.`2"
    assert env.pins == {"ct0{2}": "kv0"}


def test_ev_env_det_call_builds_ev_term_and_drain() -> None:
    env = _env()
    assert env.feed(ec_ast.Assign("a9", "ct0.`2"))
    assert env.feed(ec_ast.Call("r1", "K.decaps", "dk0, a9"))
    assert env.env["r1"] == "K_c.ev_decaps (kv1) ((kv0.`2))"
    assert env.glob_pins == {"K": "gv0"}
    assert env.pins["Step_X.dk0{2}"] == "kv1"
    assert env.drains[-1] == "(K_decaps_det gv0 (kv1) ((kv0.`2)))."
    assert ("K", "decaps") in env.det_used


def test_ev_env_nested_composition() -> None:
    env = _env()
    assert env.feed(ec_ast.Call("r1", "K.decaps", "dk0, ct0"))
    assert env.feed(ec_ast.Call("e1", "K.encode", "r1"))
    assert env.env["e1"] == "K_c.ev_encode ((K_c.ev_decaps (kv0) (kv1)))"


def test_ev_env_declines_nondet_call() -> None:
    env = _env()
    assert not env.feed(ec_ast.Call("r1", "K.keygen", ""))


def test_ev_env_declines_sample() -> None:
    env = _env()
    assert not env.feed(ec_ast.Sample("r1", "dK"))


# --- End-to-end dispatch + template lockstep ---------------------------------


from typing import Callable  # noqa: E402  pylint: disable=wrong-import-position,wrong-import-order
from pathlib import Path  # noqa: E402  pylint: disable=wrong-import-position,wrong-import-order

from proof_frog.export.easycrypt import module_translator as mt  # noqa: E402  pylint: disable=wrong-import-position
from proof_frog.export.easycrypt import type_collector as tc  # noqa: E402  pylint: disable=wrong-import-position
from proof_frog.export.easycrypt.chain_emitter import (  # noqa: E402  pylint: disable=wrong-import-position
    _oracle_step_tactic,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
BOOL = frog_ast.BoolType()


def _typed_det(var: str, mod: str, meth: str, *args: str) -> frog_ast.Assignment:
    call = frog_ast.FuncCall(
        frog_ast.FieldAccess(_var(mod), meth), [_var(a) for a in args]
    )
    return frog_ast.Assignment(BS, _var(var), call)


def _walk_game(name: str, guard: frog_ast.Expression, delta: bool) -> frog_ast.Game:
    fields = [frog_ast.Field(BS, "dk0", None), frog_ast.Field(BS, "dk1", None)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("dk0"))]),
    )
    stmts: list[frog_ast.Statement] = [
        _typed_det("r0", "K", "decaps", "dk0", "ct0"),
        _typed_det("e0", "K", "encode", "r0"),
        _typed_det("r1", "K", "decaps", "dk1", "ct1"),
        _typed_det("e1", "K", "encode", "r1"),
    ]
    if delta:
        stmts += [
            _typed_det("x0", "K", "decaps", "dk0", "ct0"),
            _typed_det("x1", "K", "decaps", "dk1", "ct1"),
        ]
    stmts += [
        frog_ast.VariableDeclaration(BOOL, "out"),
        frog_ast.IfStatement(
            [guard],
            [
                frog_ast.Block(
                    [frog_ast.Assignment(None, _var("out"), frog_ast.Boolean(True))]
                ),
                frog_ast.Block(
                    [frog_ast.Assignment(None, _var("out"), frog_ast.Boolean(False))]
                ),
            ],
        ),
        frog_ast.ReturnStatement(_var("out")),
    ]
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge",
            BOOL,
            [frog_ast.Parameter(BS, "ct0"), frog_ast.Parameter(BS, "ct1")],
        ),
        frog_ast.Block(stmts),
    )
    return frog_ast.Game((name, [], fields, [init, chal]))


def _walk_type_of_factory() -> Callable[
    [dict[str, frog_ast.Type], dict[str, str]],
    Callable[[frog_ast.Expression], frog_ast.Type],
]:
    def factory(
        _local: dict[str, frog_ast.Type], _mpt: dict[str, str]
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                return BS
            raise KeyError(e)

        return type_of

    return factory


def _dispatch_walk(inj: dict[str, set[str]], canonical: bool = False):
    def eqop(a: str, b: str) -> frog_ast.BinaryOperation:
        return frog_ast.BinaryOperation(OPS.EQUALS, _var(a), _var(b))

    gb = _walk_game("SB", eqop("e0", "e1"), delta=False)
    ga = _walk_game("SA", eqop("x0", "x1"), delta=True)
    return _oracle_step_tactic(
        gb,
        ga,
        "challenge",
        False,
        {"K": "K_c.Scheme"},
        {},
        modules=mt.ModuleTranslator(
            tc.TypeCollector(aliases={}), _walk_type_of_factory()
        ),
        flat_params=[ec_ast.ModuleParam("K", "K_c.Scheme")],
        det_methods={"K": {"decaps", "encode"}},
        micro_pre_text=(
            "={ct0, ct1} /\\ (glob State20(K)){1} = (glob State21(K)){2}"
        ),
        left_ref="State20(K)",
        right_ref="State21(K)",
        clone_alias={"K": "K_c"},
        inj_methods_by_module=inj,
        use_canonical_fields=canonical,
    )


def test_dispatch_synthesizes_template_tactic() -> None:
    """The synthesized tactic must stay in LOCKSTEP with the frozen
    EC-validated template (ec_templates/ies_delta_walk.ec)."""
    step = _dispatch_walk({"K": {"encode"}})
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.inj == {("K", "encode")}
    assert reqs.det == {("K", "decaps"), ("K", "encode")}
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "ies_delta_walk.ec"
    ).read_text()
    proof_body = template.split("proof.\n", 1)[1].split("qed.", 1)[0]
    frozen = [ln.strip() for ln in proof_body.strip().splitlines()]
    assert tac == frozen


def test_dispatch_declines_without_licensed_inj() -> None:
    assert _dispatch_walk({}) is None


def test_dispatch_canonical_fields_lockstep_with_template() -> None:
    """Under the chain-wide canonical ``f<NN>`` field naming (what a
    random-oracle proof uses), the pins must name the CANONICAL field of the
    {2}-memory module -- the route renders its own copy of each state, and
    rendering it under a different field-naming decision than the emitted
    module produced ``unknown variable or constant``."""
    step = _dispatch_walk({"K": {"encode"}}, canonical=True)
    assert step is not None
    tac, _reqs, rung = step
    assert rung == "synth-param"
    assert any("State21.f00{2}" in t for t in tac)
    assert not any("State21.dk0{2}" in t for t in tac)
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "ies_delta_walk_canonical.ec"
    ).read_text()
    proof_body = template.split("proof.\n", 1)[1].split("qed.", 1)[0]
    assert tac == [ln.strip() for ln in proof_body.strip().splitlines()]
