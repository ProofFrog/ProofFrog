"""Unit tests for Move 4's if-fold rows.

Covers the fold-shape matcher (``_fold_shape`` via the dispatch), the
guard-formula rewrite, the deterministic-tail row, and decline mutations.
The tactic shapes are pinned by the probes (``.ec-tmp/move4/fold_probe.ec``,
``absorb_probe.ec``) and the synthesizer-generated EC templates
(``ec_templates/fold_pair_walk.ec`` / ``det_tail_fold.ec``); the lockstep
tests assert template tactic == current synthesizer output.
"""

from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _EvEnv,
    _fold_guard_formula,
    _oracle_step_tactic,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
OPS = frog_ast.BinaryOperators
EMT = {"K": "K_c.Scheme"}
FLAT = [ec_ast.ModuleParam("K", "K_c.Scheme")]
DET = {"K": {"decaps", "enc"}}
ALIAS = {"K": "K_c"}


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _op(
    op: frog_ast.BinaryOperators, a: frog_ast.Expression, b: frog_ast.Expression
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(op, a, b)


def _fold_game(name: str, folded: bool) -> frog_ast.Game:
    fields = [
        frog_ast.Field(BS, "dk0", None),
        frog_ast.Field(BS, "dk1", None),
        frog_ast.Field(BS, "ek0", None),
        frog_ast.Field(BS, "ek1", None),
    ]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("dk0"))]),
    )
    p = _op(
        OPS.AND,
        _op(OPS.EQUALS, _var("d0"), _var("d1")),
        _op(OPS.EQUALS, _var("ct0"), _var("ct1")),
    )
    x = _op(OPS.NOTEQUALS, _var("ek0"), _var("ek1"))
    y = _op(
        OPS.AND,
        _op(OPS.EQUALS, _var("e0"), _var("e1")),
        _op(OPS.NOTEQUALS, _var("ek0"), _var("ek1")),
    )
    stmts: list[frog_ast.Statement] = [
        frog_ast.Assignment(
            BS, _var("d0"), _call("K", "Decaps", _var("dk0"), _var("ct0"))
        ),
        frog_ast.Assignment(
            BS, _var("d1"), _call("K", "Decaps", _var("dk1"), _var("ct1"))
        ),
    ]
    if not folded:
        stmts.append(
            frog_ast.IfStatement([p], [frog_ast.Block([frog_ast.ReturnStatement(x)])])
        )
    stmts += [
        frog_ast.Assignment(BS, _var("e0"), _call("K", "Enc", _var("d0"))),
        frog_ast.Assignment(BS, _var("e1"), _call("K", "Enc", _var("d1"))),
        frog_ast.ReturnStatement(y),
    ]
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge",
            frog_ast.BoolType(),
            [frog_ast.Parameter(BS, "ct0"), frog_ast.Parameter(BS, "ct1")],
        ),
        frog_ast.Block(stmts),
    )
    return frog_ast.Game((name, [], fields, [init, chal]))


def _absorb_game(name: str, absorbed: bool) -> frog_ast.Game:
    fields = [frog_ast.Field(BS, "dk0", None)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("dk0"))]),
    )
    p = _op(OPS.EQUALS, _var("d0"), _var("ct0"))
    x = _op(OPS.EQUALS, _var("s"), _var("ct0"))
    body_if = frog_ast.IfStatement(
        [
            (
                _op(
                    OPS.AND,
                    _op(OPS.NOTEQUALS, _var("d0"), _var("ct0")),
                    _op(OPS.EQUALS, _var("ct0"), _var("ct1")),
                )
                if absorbed
                else _op(OPS.EQUALS, _var("ct0"), _var("ct1"))
            )
        ],
        [frog_ast.Block([frog_ast.Assignment(None, _var("s"), _var("dk0"))])],
    )
    stmts: list[frog_ast.Statement] = [
        frog_ast.Assignment(
            BS, _var("d0"), _call("K", "Decaps", _var("dk0"), _var("ct0"))
        ),
        frog_ast.Assignment(BS, _var("s"), _var("ct0")),
    ]
    if not absorbed:
        stmts.append(
            frog_ast.IfStatement([p], [frog_ast.Block([frog_ast.ReturnStatement(x)])])
        )
    stmts += [body_if, frog_ast.ReturnStatement(x)]
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge",
            frog_ast.BoolType(),
            [frog_ast.Parameter(BS, "ct0"), frog_ast.Parameter(BS, "ct1")],
        ),
        frog_ast.Block(stmts),
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


def _dispatch(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    gb: frog_ast.Game,
    ga: frog_ast.Game,
    pre: str,
    lref: str,
    rref: str,
    reversed_dir: bool = False,
    det: dict[str, set[str]] | None = None,
    canonical: bool = False,
):
    return _oracle_step_tactic(
        gb,
        ga,
        "challenge",
        reversed_dir,
        EMT,
        {},
        modules=mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory()),
        flat_params=FLAT,
        det_methods=det if det is not None else DET,
        micro_pre_text=pre,
        left_ref=lref,
        right_ref=rref,
        clone_alias=ALIAS,
        inj_methods_by_module={},
        use_canonical_fields=canonical,
    )


def _template_proof_body(template: str, lemma: str) -> list[str]:
    text = (
        Path(__file__).parents[2] / "integration" / "ec_templates" / template
    ).read_text()
    block = text.split(f"lemma {lemma} :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [ln.strip() for ln in proof_body.strip().splitlines()]


PRE_F = "={ct0, ct1} /\\ (glob FB(K)){1} = (glob FA(K)){2}"


def test_fold_fwd_lockstep_with_template() -> None:
    """The synthesized fold case tree must stay in LOCKSTEP with the frozen
    EC-validated template (ec_templates/fold_pair_walk.ec)."""
    step = _dispatch(
        _fold_game("FB", False), _fold_game("FA", True), PRE_F, "FB(K)", "FA(K)"
    )
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.det == {("K", "decaps"), ("K", "enc")}
    assert tac == _template_proof_body("fold_pair_walk.ec", "micro_fold_fwd")


def test_fold_rev_lockstep_with_template() -> None:
    pre_r = "={ct0, ct1} /\\ (glob FA(K)){1} = (glob FB(K)){2}"
    step = _dispatch(
        _fold_game("FB", False),
        _fold_game("FA", True),
        pre_r,
        "FA(K)",
        "FB(K)",
        reversed_dir=True,
    )
    assert step is not None
    assert step[0] == _template_proof_body("fold_pair_walk.ec", "micro_fold_rev")


PRE_A = "={ct0, ct1} /\\ (glob AB(K)){1} = (glob AA(K)){2}"


def test_det_tail_lockstep_with_template() -> None:
    step = _dispatch(
        _absorb_game("AB", False), _absorb_game("AA", True), PRE_A, "AB(K)", "AA(K)"
    )
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.det == set()
    assert tac == _template_proof_body("det_tail_fold.ec", "micro_det_tail")


def test_fold_declines_on_init_pre_true() -> None:
    assert (
        _dispatch(
            _fold_game("FB", False), _fold_game("FA", True), "true", "FB(K)", "FA(K)"
        )
        is None
    )


def test_fold_declines_on_nondet_else_call() -> None:
    """An else-region call without a det axiom cannot drain -- the fold row
    declines (and the tails carry calls, so the det-tail row declines too)."""
    assert (
        _dispatch(
            _fold_game("FB", False),
            _fold_game("FA", True),
            PRE_F,
            "FB(K)",
            "FA(K)",
            det={"K": {"decaps"}},
        )
        is None
    )


def test_fold_declines_on_extra_tail_diff() -> None:
    """A straight side whose tail is not exactly the else region declines."""
    ga = _fold_game("FA", True)
    ga.methods[1].block.statements.insert(
        3, frog_ast.Assignment(BS, _var("z"), _var("d0"))
    )
    assert _dispatch(_fold_game("FB", False), ga, PRE_F, "FB(K)", "FA(K)") is None


def test_guard_formula_rewrite_and_gate() -> None:
    assert (
        _fold_guard_formula("d0 = d1 && ct0 = ct1", "1", "SB", {"dk0"})
        == "(d0{1} = d1{1} /\\ ct0{1} = ct1{1})"
    )
    assert (
        _fold_guard_formula("dk0 = ct0", "2", "SB", {"dk0"}) == "(SB.dk0{2} = ct0{2})"
    )
    assert _fold_guard_formula("f x + 1", "1", "SB", set()) is None


def test_guard_formula_declines_foreign_field() -> None:
    """A name that is a field of the SIBLING state only cannot be qualified
    through this state and must not be read as a local either."""
    assert (
        _fold_guard_formula("dkX = ct0", "2", "SB", {"dk0"}, frozenset({"dkX"}))
        is None
    )


# ---------------------------------------------------------------------------
# Canonical f<NN> field naming (the chain-wide decision a random-oracle proof
# makes). The route renders its OWN copy of each state to read the bodies its
# tactic names; rendering that copy under a different field-naming decision
# than the emitted module makes every field pin name a variable that does not
# exist ("unknown variable or constant").
# ---------------------------------------------------------------------------


def test_fold_canonical_fwd_lockstep_with_template() -> None:
    step = _dispatch(
        _fold_game("FB", False),
        _fold_game("FA", True),
        PRE_F,
        "FB(K)",
        "FA(K)",
        canonical=True,
    )
    assert step is not None
    tac, _reqs, rung = step
    assert rung == "synth-param"
    # The pins name the CANONICAL field of the {2}-memory module.
    assert any("FA.f00{2}" in t for t in tac)
    assert not any("FA.dk0{2}" in t for t in tac)
    assert tac == _template_proof_body(
        "fold_pair_walk_canonical.ec", "micro_fold_canon_fwd"
    )


def test_fold_canonical_rev_lockstep_with_template() -> None:
    pre_r = "={ct0, ct1} /\\ (glob FA(K)){1} = (glob FB(K)){2}"
    step = _dispatch(
        _fold_game("FB", False),
        _fold_game("FA", True),
        pre_r,
        "FA(K)",
        "FB(K)",
        reversed_dir=True,
        canonical=True,
    )
    assert step is not None
    assert step[0] == _template_proof_body(
        "fold_pair_walk_canonical.ec", "micro_fold_canon_rev"
    )


def test_ev_env_declines_a_foreign_field_read() -> None:
    """Every pin is qualified against the {2}-memory module, so a name that
    belongs only to the SIBLING state has no pin: the env declines instead of
    emitting a dangling ``<state>.<name>{2}``."""
    env = _EvEnv(DET, ALIAS, set(), {"f00"}, "FA", {}, {}, frozenset({"dkX"}))
    assert env.feed(ec_ast.Assign("y", "f00")) is True
    assert env.feed(ec_ast.Assign("x", "dkX")) is False
