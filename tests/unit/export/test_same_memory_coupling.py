"""Unit tests for the same-memory-coupling equal-body leg.

``sim`` reads a postcondition as equalities BETWEEN the two memories, so an
equal-body leg whose coupling also carries a one-memory conjunct
(``S.f09{1} = S.f08{1}`` -- the survivor-consistency facts a broken chain
threads) makes it give up: *cannot infer the set of equalities*, measured on
``CK_seedbased_LEAK_BIND_K_PK`` ``micro_2_hashg_left_22``. The route closes
the one recoverable shape (call-free body, every touched field paired under
its own name) and declines the rest. The tactic is pinned in lockstep with
the EC-validated template ``ec_templates/same_memory_coupling.ec``.
"""

from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _coupling_defeats_sim,
    _coupling_field_map,
    _oracle_step_tactic,
    _split_conjuncts,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
OPS = frog_ast.BinaryOperators
EMT: dict[str, str] = {}
FLAT: list[ec_ast.ModuleParam] = []
PRE = (
    "={x} /\\ SB.s0{1} = SA.s0{2} /\\ SB.s1{1} = SA.s1{2} "
    "/\\ SB.pk{1} = SA.sk{2} /\\ SB.s0{1} = SB.s1{1}"
)


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _game(name: str, extra_field: str, call: bool = False) -> frog_ast.Game:
    fields = [
        frog_ast.Field(BS, "s0", None),
        frog_ast.Field(BS, "s1", None),
        frog_ast.Field(BS, extra_field, None),
    ]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("s0"))]),
    )
    body: list[frog_ast.Statement] = []
    if call:
        body.append(
            frog_ast.Assignment(
                BS,
                _var("y"),
                frog_ast.FuncCall(
                    frog_ast.FieldAccess(_var("K"), "enc"), [_var("x")]
                ),
            )
        )
    body.append(
        frog_ast.IfStatement(
            [frog_ast.BinaryOperation(OPS.EQUALS, _var("s0"), _var("x"))],
            [
                frog_ast.Block([frog_ast.ReturnStatement(_var("s1"))]),
                frog_ast.Block([frog_ast.ReturnStatement(_var("x"))]),
            ],
        )
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", BS, [frog_ast.Parameter(BS, "x")]),
        frog_ast.Block(body),
    )
    return frog_ast.Game((name, [], fields, [init, chal]))


def _factory() -> Callable[..., Callable[[frog_ast.Expression], frog_ast.Type]]:
    def factory(
        _local: dict[str, frog_ast.Type], _mpt: dict[str, str]
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                return BS
            raise KeyError(e)

        return type_of

    return factory


def _dispatch(pre: str = PRE, call: bool = False, emt: dict[str, str] | None = None):
    flat = (
        [ec_ast.ModuleParam("K", "K_c.Scheme")] if emt else list(FLAT)
    )
    return _oracle_step_tactic(
        _game("SB", "pk", call),
        _game("SA", "sk", call),
        "challenge",
        False,
        emt if emt is not None else EMT,
        {},
        modules=mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory()),
        flat_params=flat,
        det_methods={},
        micro_pre_text=pre,
        left_ref="SB",
        right_ref="SA",
        clone_alias={},
        inj_methods_by_module={},
    )


def test_split_conjuncts_respects_parentheses() -> None:
    assert _split_conjuncts("a = b /\\ (c /\\ d) = e /\\ f") == [
        "a = b",
        "(c /\\ d) = e",
        "f",
    ]


def test_coupling_field_map_and_sim_gate() -> None:
    pairs = _coupling_field_map(PRE, "SB", "SA")
    assert pairs == {"s0": "s0", "s1": "s1", "pk": "sk"}
    assert _coupling_defeats_sim(PRE)
    # A cross-NAMED two-memory pair is fine: sim relates the memories, and a
    # rename is still an equality between them.
    assert not _coupling_defeats_sim("={x} /\\ SB.pk{1} = SA.sk{2} /\\ ={glob K}")


def test_same_memory_coupling_lockstep_with_template() -> None:
    step = _dispatch()
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.det == set()
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "same_memory_coupling.ec"
    ).read_text()
    proof_body = template.split("proof.\n", 1)[1].split("qed.", 1)[0]
    assert tac == [ln.strip() for ln in proof_body.strip().splitlines()]


def test_plain_sim_when_no_same_memory_conjunct() -> None:
    """Without a one-memory conjunct the coupling is a sim coupling, even
    when it renames fields across the two states."""
    pre = "={x} /\\ SB.s0{1} = SA.s0{2} /\\ SB.s1{1} = SA.s1{2} /\\ SB.pk{1} = SA.sk{2}"
    step = _dispatch(pre)
    assert step is not None
    assert step[0] == ["proc; sim."]
    assert step[2] == "synth-static"


def test_declines_when_the_body_has_a_call() -> None:
    """``auto`` cannot pass an abstract call, so the leg declines rather than
    emit a tactic that leaves the goal open."""
    assert _dispatch(call=True, emt={"K": "K_c.Scheme"}) is None


def test_declines_when_a_touched_field_is_cross_named() -> None:
    """The body reads ``s1``; pairing it with a differently-named field on the
    other side leaves the read unjustified, so decline."""
    pre = (
        "={x} /\\ SB.s0{1} = SA.s0{2} /\\ SB.s1{1} = SA.sk{2} "
        "/\\ SB.s0{1} = SB.s1{1}"
    )
    assert _dispatch(pre) is None
