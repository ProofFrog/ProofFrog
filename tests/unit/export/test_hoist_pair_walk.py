"""Unit tests for Move 3c's Hoist-pair micro walk.

Covers the exact pair detection (``_detect_hoist_pair`` -- reverse
substitution + the transform's preservation gate re-check), the per-state
cache-conjunct registry (``_hoist_conjunct_registry``), the leg dispatch
(consumer walk / bystander peel / reversed direction), and decline
mutations. The tactic shapes are pinned by the probes
(``.ec-tmp/move3/hoist_probe.ec``, ``hoist_chain_probe.ec``) and the
synthesizer-generated EC template
(``tests/integration/ec_templates/hoist_pair_walk.ec``); the lockstep test
asserts template tactic == current synthesizer output so the two cannot
drift silently.
"""

import copy
from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _detect_hoist_pair,
    _hoist_conjunct_registry,
    _oracle_step_tactic,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
DET = {"M": {"f"}}
EMT = {"E": "E_c.Scheme", "M": "M_c.FMod"}
FLAT = [ec_ast.ModuleParam("E", "E_c.Scheme"), ec_ast.ModuleParam("M", "M_c.FMod")]
ALIAS = {"M": "M_c"}


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _game(name: str, hoisted: bool) -> frog_ast.Game:
    fields = [frog_ast.Field(BS, "k", None)] + (
        [frog_ast.Field(BS, "h", None)] if hoisted else []
    )
    init_stmts: list[frog_ast.Statement] = [
        frog_ast.Assignment(None, _var("k"), _call("E", "KeyGen"))
    ]
    if hoisted:
        init_stmts.append(
            frog_ast.Assignment(None, _var("h"), _call("M", "F", _var("k")))
        )
    init_stmts.append(frog_ast.ReturnStatement(_var("k")))
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block(init_stmts),
    )
    x_rhs: frog_ast.Expression = _var("h") if hoisted else _call("M", "F", _var("k"))
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", BS, [frog_ast.Parameter(BS, "m")]),
        frog_ast.Block(
            [
                frog_ast.Assignment(BS, _var("a"), _call("E", "Enc", _var("m"))),
                frog_ast.Assignment(BS, _var("x"), x_rhs),
                frog_ast.Assignment(
                    BS, _var("c"), _call("E", "Mix", _var("x"), _var("a"))
                ),
                frog_ast.ReturnStatement(_var("c")),
            ]
        ),
    )
    guess = frog_ast.Method(
        frog_ast.MethodSignature("Guess", BS, [frog_ast.Parameter(BS, "m")]),
        frog_ast.Block(
            [
                frog_ast.Assignment(BS, _var("d"), _call("E", "Enc", _var("m"))),
                frog_ast.ReturnStatement(_var("d")),
            ]
        ),
    )
    return frog_ast.Game((name, [], fields, [init, chal, guess]))


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


def _modules() -> mt.ModuleTranslator:
    return mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())


# --- detection ---------------------------------------------------------------


def test_detects_hoist_pair() -> None:
    pair = _detect_hoist_pair(_game("HB", False), _game("HA", True), DET)
    assert pair is not None
    assert pair.field_name == "h"
    assert (pair.mod, pair.meth) == ("M", "f")
    assert pair.consumers == frozenset({"challenge"})


def test_detection_declines_nondet_callee() -> None:
    assert _detect_hoist_pair(_game("HB", False), _game("HA", True), {"M": set()}) is None


def test_detection_declines_two_extra_fields() -> None:
    ga = _game("HA", True)
    ga.fields.append(frog_ast.Field(BS, "h2", None))
    assert _detect_hoist_pair(_game("HB", False), ga, DET) is None


def test_detection_declines_extra_body_diff() -> None:
    # A consumer body diff beyond the call->field substitution breaks the
    # reverse-substitution equality.
    ga = _game("HA", True)
    ga.methods[1].block.statements[0] = frog_ast.Assignment(
        BS, _var("a"), _call("E", "Enc", _var("a"))
    )
    assert _detect_hoist_pair(_game("HB", False), ga, DET) is None


def test_detection_declines_arg_field_written_in_oracle() -> None:
    # The transform's own preservation gate, re-checked: a non-init write to
    # the arg field invalidates the cache invariant.
    ga = _game("HA", True)
    ga.methods[2].block.statements.insert(
        0, frog_ast.Assignment(None, _var("k"), _var("d"))
    )
    assert _detect_hoist_pair(_game("HB", False), ga, DET) is None


def test_detection_declines_nonfield_arg() -> None:
    # Candidate args must be field reads (v1): a non-field arg declines.
    gb, ga = _game("HB", False), _game("HA", True)
    ga.methods[0].block.statements[1] = frog_ast.Assignment(
        None, _var("h"), _call("M", "F", _var("nonfield"))
    )
    assert _detect_hoist_pair(gb, ga, DET) is None


# --- registry ----------------------------------------------------------------


def test_registry_registers_cache_carrying_states() -> None:
    gb, ga = _game("HB", False), _game("HA", True)
    registry = _hoist_conjunct_registry(
        [gb, ga],
        [gb, ga],
        ["HZ_L0", "HZ_L1"],
        ["HZ_R0", "HZ_R1"],
        lambda n: f"{n}(E, M)",
        _modules(),
        EMT,
        {},
        FLAT,
        DET,
        ALIAS,
    )
    assert registry == {
        "HZ_L1": ["HZ_L1.h__SIDE__ = M_c.ev_f (HZ_L1.k__SIDE__)"],
        "HZ_R1": ["HZ_R1.h__SIDE__ = M_c.ev_f (HZ_R1.k__SIDE__)"],
    }


def test_registry_empty_without_pair() -> None:
    gb = _game("HB", False)
    registry = _hoist_conjunct_registry(
        [gb, gb],
        [gb],
        ["HZ_L0", "HZ_L1"],
        ["HZ_R0"],
        lambda n: f"{n}(E, M)",
        _modules(),
        EMT,
        {},
        FLAT,
        DET,
        ALIAS,
    )
    assert registry == {}


# --- dispatch + template lockstep --------------------------------------------

PRE_FWD = (
    "={m} /\\ ={glob E} /\\ ={glob M} /\\ HZ_L0.k{1} = HZ_L1.k{2} /\\ "
    "HZ_L1.h{2} = M_c.ev_f (HZ_L1.k{2})"
)


def _dispatch(
    oracle: str,
    reversed_dir: bool = False,
    pre: str = PRE_FWD,
    lref: str = "HZ_L0(E, M)",
    rref: str = "HZ_L1(E, M)",
    det: dict[str, set[str]] | None = None,
):
    return _oracle_step_tactic(
        _game("HB", False),
        _game("HA", True),
        oracle,
        reversed_dir,
        EMT,
        {},
        modules=_modules(),
        flat_params=FLAT,
        det_methods=det if det is not None else DET,
        micro_pre_text=pre,
        left_ref=lref,
        right_ref=rref,
        clone_alias=ALIAS,
        inj_methods_by_module={},
    )


def _template_proof_body(lemma: str) -> list[str]:
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "hoist_pair_walk.ec"
    ).read_text()
    block = template.split(f"lemma {lemma} :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [ln.strip() for ln in proof_body.strip().splitlines()]


def test_consumer_lockstep_with_template() -> None:
    """The synthesized consumer tactic must stay in LOCKSTEP with the frozen
    EC-validated template (ec_templates/hoist_pair_walk.ec)."""
    step = _dispatch("challenge")
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.det == {("M", "f")}
    assert tac == _template_proof_body("micro_hz_L0")


def test_bystander_lockstep_with_template() -> None:
    step = _dispatch("guess")
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs.det == set()
    assert tac == _template_proof_body("micro_hz_by")


def test_reversed_consumer_lockstep_with_template() -> None:
    pre_rev = (
        "={m} /\\ ={glob E} /\\ ={glob M} /\\ HZ_R1.k{1} = HZ_R0.k{2} /\\ "
        "HZ_R1.h{1} = M_c.ev_f (HZ_R1.k{1})"
    )
    step = _dispatch(
        "challenge",
        reversed_dir=True,
        pre=pre_rev,
        lref="HZ_R1(E, M)",
        rref="HZ_R0(E, M)",
    )
    assert step is not None
    tac, _reqs, _rung = step
    assert tac == _template_proof_body("micro_hz_R0_rev")


def test_consumer_declines_without_conjunct_in_pre() -> None:
    """Enabling-coupling gate: without the cache conjunct in the pre the
    consumer declines (honest admit), never a runs-but-not-closes peel."""
    pre = "={m} /\\ ={glob E} /\\ ={glob M} /\\ HZ_L0.k{1} = HZ_L1.k{2}"
    assert _dispatch("challenge", pre=pre) is None


def test_consumer_declines_on_init_pre_true() -> None:
    assert _dispatch("challenge", pre="true") is None


def test_detected_pair_is_authoritative_on_nondet() -> None:
    """A pair whose callee is not det is NOT a Hoist pair, so the walk must not
    fire; the cardinality-survivor branch inspects it next and DECLINES.

    It declines because this ``Challenge`` interleaves a deterministic
    assignment (``x <- h``) between two abstract calls, and the survivor peel
    emits consecutive ``call`` steps with no ``wp`` between them -- EasyCrypt
    rejects the second one with "invalid last instruction". Declining is the
    honest outcome: the oracle falls back to the whole-oracle route rather than
    carrying a tactic that cannot close.
    """
    assert _dispatch("challenge", det={"M": set()}) is None
