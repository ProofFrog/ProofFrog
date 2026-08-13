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


def _seq_branch_body() -> list[ec_ast.EcStmt]:
    """The measured shape of 39 of the 43 legs: the else-arm is
    ``[Assign, Call, If]`` -- it branches again, after a call."""
    return [
        ec_ast.If(
            guard="ct = ctStar",
            then_body=[_assign("r", "None")],
            else_body=[
                _assign("t", "ct"),
                _call("a", "K.decaps", "dk_0, t"),
                ec_ast.If(
                    guard="t = ctStar",
                    then_body=[_assign("r", "None")],
                    else_body=[
                        _call("b", "K.decaps", "dk_1, t"),
                        _call("c", "K.combine", "a, b"),
                        _assign("r", "Some (c)"),
                    ],
                ),
            ],
        ),
        ec_ast.Return(expr="r"),
    ]


SEQ_PRE = (
    "={ct} /\\ ={glob K} /\\ SC0.dk_0{1} = SC1.dk_0{2} /\\ "
    "SC0.dk_1{1} = SC1.dk_1{2} /\\ SC0.ctStar{1} = SC1.ctStar{2}"
)


def test_seq_split_descent_fires_on_the_measured_shape() -> None:
    """The arm is split with ``seq`` before the inner ``if``.

    Applying ``if`` a second time straight after the first is REFUTED --
    EasyCrypt answers *invalid first instruction*, since ``if`` is a
    first-instruction rule and the arm opens with an assignment and a call.
    """
    got = _equal_body_peel_tactic(_seq_branch_body(), SEQ_PRE)
    assert got is not None
    # The leading run is split off, and its length is read from the arm.
    assert any(ln.startswith("seq 2 2 : (={t, a} /\\ ") for ln in got), got
    # The descent then recurses into the inner branch.
    assert got.count("if.") == 2
    assert got[-1] == "auto => /#."


def test_seq_split_declines_without_a_usable_coupling() -> None:
    """The ``seq`` invariant IS the coupling, so a ``true`` precondition
    leaves nothing to carry across the split and the leg declines."""
    assert _equal_body_peel_tactic(_seq_branch_body(), "true") is None


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


def _three_level_body() -> list[ec_ast.EcStmt]:
    """The measured residue: branches nested three deep."""
    innermost = ec_ast.If(
        guard="t = ctStar",
        then_body=[_assign("r", "None")],
        else_body=[_call("c", "K.combine", "a, b"), _assign("r", "Some (c)")],
    )
    middle = ec_ast.If(
        guard="t = ctStar",
        then_body=[_assign("r", "None")],
        else_body=[_call("b", "K.decaps", "dk_1, t"), innermost],
    )
    return [
        ec_ast.If(
            guard="ct = ctStar",
            then_body=[_assign("r", "None")],
            else_body=[
                _assign("t", "ct"),
                _call("a", "K.decaps", "dk_0, t"),
                middle,
            ],
        ),
        ec_ast.Return(expr="r"),
    ]


def test_descent_recurses_and_accumulates_the_invariant() -> None:
    """Three levels, and each ``seq`` invariant carries every local bound so
    far -- exactly what the next guard and its arms read."""
    got = _equal_body_peel_tactic(_three_level_body(), SEQ_PRE)
    assert got is not None
    seqs = [ln for ln in got if ln.startswith("seq ")]
    assert len(seqs) == 2, got
    assert seqs[0].startswith("seq 2 2 : (={t, a} /\\ ")
    # The second level ADDS the local its own leading call binds.
    assert seqs[1].startswith("seq 1 1 : (={t, a, b} /\\ ")
    assert got.count("if.") == 3
    assert got[-1] == "auto => /#."
