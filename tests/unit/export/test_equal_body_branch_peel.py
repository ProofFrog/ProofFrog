"""Unit tests for the equal-rendered-body peel and its branch descent.

The tactic shape is pinned by the EC-validated template
``tests/integration/ec_templates/equal_body_branch_peel.ec``; the lockstep
test below asserts template == synthesizer output so the two cannot drift.
"""

from __future__ import annotations

from pathlib import Path

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _equal_body_peel_tactic,
    _same_memory_conjunct_fields,
    _written_state_fields,
)


def _call(var: str, callee: str, args: str) -> ec_ast.Call:
    return ec_ast.Call(var=var, callee=callee, args=args)


def _assign(var: str, rhs: str) -> ec_ast.Assign:
    return ec_ast.Assign(var=var, rhs=rhs)


def _branch_body() -> list[ec_ast.EcStmt]:
    """The measured shape: a decapsulation oracle refusing the challenge."""
    return [
        ec_ast.If(
            guard="ct = ctStar",
            then_body=[_assign("r", "None")],
            else_body=[
                _call("a", "K.decaps", "dk_0, ct"),
                _call("b", "K.decaps", "dk_1, ct"),
                _call("c", "K.combine", "a, b"),
                _assign("r", "Some (c)"),
            ],
        ),
        ec_ast.Return(expr="r"),
    ]


def _template_proof_body(lemma: str) -> list[str]:
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "equal_body_branch_peel.ec"
    ).read_text()
    block = template.split(f"lemma {lemma} :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [
        ln.strip()
        for ln in proof_body.strip().splitlines()
        if ln.strip() and not ln.strip().startswith("(*")
    ]


def test_flat_body_takes_the_ordinary_peel() -> None:
    body: list[ec_ast.EcStmt] = [
        _call("a", "K.decaps", "dk_0, ct"),
        ec_ast.Return(expr="a"),
    ]
    assert _equal_body_peel_tactic(body) == [
        "proc.",
        "wp.",
        "call (_: true).",
        "auto => /#.",
    ]


def test_branch_descent_lockstep_with_template() -> None:
    """The synthesized branch descent must stay in LOCKSTEP with the frozen
    EC-validated template."""
    got = _equal_body_peel_tactic(_branch_body())
    assert got is not None
    assert got == _template_proof_body("micro_branch")


def test_declines_a_second_level_of_branching() -> None:
    """REFUTED shape: an else-arm that itself branches after a call.

    EasyCrypt answers *invalid first instruction* if a second ``if`` is
    applied there -- ``if`` is a first-instruction rule and the arm opens
    with an assignment and a call. Measured on 39 of the 43 corpus legs;
    they must decline rather than carry a peel that cannot close.
    """
    body: list[ec_ast.EcStmt] = [
        ec_ast.If(
            guard="ct = ctStar",
            then_body=[_assign("r", "None")],
            else_body=[
                _call("a", "K.decaps", "dk_0, ct"),
                ec_ast.If(
                    guard="ct = ctStar",
                    then_body=[_assign("r", "None")],
                    else_body=[_call("b", "K.decaps", "dk_1, ct")],
                ),
            ],
        ),
        ec_ast.Return(expr="r"),
    ]
    assert _equal_body_peel_tactic(body) is None


def test_declines_two_top_level_branches() -> None:
    """Two call-bearing top-level ``if``s: one ``if`` tactic cannot serve
    both, and the descent is written for exactly one."""
    body: list[ec_ast.EcStmt] = [
        ec_ast.If(
            guard="g1",
            then_body=[_call("a", "K.decaps", "x")],
            else_body=[_assign("a", "witness")],
        ),
        ec_ast.If(
            guard="g2",
            then_body=[_call("b", "K.decaps", "y")],
            else_body=[_assign("b", "witness")],
        ),
    ]
    assert _equal_body_peel_tactic(body) is None


def test_call_free_branches_take_the_ordinary_peel() -> None:
    """A branch with no call is not an obstacle: the top-level peel reaches
    every event, so the flat shape applies and ``auto`` handles the
    deterministic arms."""
    body: list[ec_ast.EcStmt] = [
        ec_ast.If(guard="g", then_body=[_assign("r", "None")], else_body=[]),
    ]
    assert _equal_body_peel_tactic(body) == ["proc.", "auto => /#."]


def test_same_memory_conjunct_fields_picks_one_sided_conjuncts() -> None:
    pre = (
        "={ct} /\\ S1.f00{1} = S2.f00{2} /\\ "
        "S2.f01{2} = M_c.ev_f (S2.f02{2})"
    )
    got = _same_memory_conjunct_fields(pre, {"f00", "f01", "f02"})
    # Only the one-sided conjunct's fields; the cross-side pair is not one.
    assert got == {"f01", "f02"}


def test_written_state_fields_sees_branch_writes() -> None:
    body: list[ec_ast.EcStmt] = [
        ec_ast.If(
            guard="g",
            then_body=[_assign("f00", "witness")],
            else_body=[_call("f01", "K.decaps", "x")],
        ),
    ]
    assert _written_state_fields(body, {"f00", "f01", "f02"}) == {"f00", "f01"}
