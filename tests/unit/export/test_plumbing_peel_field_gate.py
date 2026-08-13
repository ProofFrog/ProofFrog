"""Unit tests for the plain plumbing peel's FIELD-REFERENCE gate.

The gate compares, per peel segment, which state fields each side mentions.
Read by name it declines every leg whose transform renamed the fields, even
where the two programs agree; read through the coupling's class map it
accepts exactly those, and still declines a role swap.

The tactic shape the accepted legs take is pinned by the EC-validated
template ``tests/integration/ec_templates/plumbing_peel_renamed_fields.ec``;
the lockstep test below asserts template == synthesizer output so the two
cannot drift. Its negative control lives beside the probe
(``.ec-tmp/bystander/renamepeel_negctl.ec``): dropping one rename conjunct
makes EasyCrypt answer *cannot prove goal (strict)*.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _backbone_peel,
    _bridge_specs_compose,
    _coupled_field_renaming,
    _coupled_guard_descent,
    _dead_local_assignments,
    _field_orders_agree,
    _field_reference_order,
)


def _call(var: str, callee: str, args: str) -> ec_ast.Call:
    return ec_ast.Call(var=var, callee=callee, args=args)


def _assign(var: str, rhs: str) -> ec_ast.Assign:
    return ec_ast.Assign(var=var, rhs=rhs)


LEFT_FIELDS = {"dk0_0", "dk0_1"}
RIGHT_FIELDS = {"field3", "field4"}
ALL_FIELDS = LEFT_FIELDS | RIGHT_FIELDS

RENAME_PRE = "={ct0} /\\ S_L.dk0_0{1} = S_R.field3{2} /\\ S_L.dk0_1{1} = S_R.field4{2}"


def _left_body() -> list[ec_ast.EcStmt]:
    return [
        _call("r0", "K.decaps", "dk0_0, ct0.`1"),
        _call("r1", "K.decaps", "dk0_1, ct0.`2"),
        _call("r2", "H.evaluate", "comb r0 r1"),
        ec_ast.Return(expr="r2"),
    ]


def _right_body() -> list[ec_ast.EcStmt]:
    """Same program, fields renamed, plus the plumbing difference."""
    return [
        _assign("c0", "ct0.`1"),
        _call("r0", "K.decaps", "field3, c0"),
        _assign("c1", "ct0.`2"),
        _call("r1", "K.decaps", "field4, c1"),
        _call("r2", "H.evaluate", "comb r0 r1"),
        ec_ast.Return(expr="r2"),
    ]


def test_renamed_fields_differ_when_read_by_name() -> None:
    """The gate as it stood: a rename fails it by construction."""
    assert _field_reference_order(_left_body(), ALL_FIELDS) != _field_reference_order(
        _right_body(), ALL_FIELDS
    )


def test_renamed_fields_agree_when_read_through_the_coupling() -> None:
    renaming = _coupled_field_renaming(RENAME_PRE, "S_L", "S_R")
    assert renaming, "the coupling states the rename, so the class map is non-empty"
    assert _field_reference_order(
        _left_body(), ALL_FIELDS, renaming
    ) == _field_reference_order(_right_body(), ALL_FIELDS, renaming)


def test_whole_glob_coupling_leaves_the_gate_untouched() -> None:
    """The measured shape of every role-swap leg: no per-field conjuncts.

    A whole-glob coupling yields an empty class map, so the retry is the
    identity and the gate keeps declining -- which is what stops the retry
    from resurrecting the false subgoal the gate was written for.
    """
    pre = "={ct0, ct1} /\\ (glob A(K, H)){1} = (glob B(K, H)){2}"
    assert _coupled_field_renaming(pre, "A", "B") == {}


def test_role_swap_still_declines_under_its_own_coupling() -> None:
    """Even given field conjuncts, a genuine role swap must not pass.

    ``field1`` and ``field2`` are coupled to THEMSELVES across the sides, so
    the class map is the identity over them and the two segments keep
    differing -- the closer would otherwise be handed
    ``field1{1} = field2{2}``, which is false.
    """
    pre = "={ct0} /\\ A.field1{1} = B.field1{2} /\\ A.field2{1} = B.field2{2}"
    fields = {"field1", "field2"}
    left = [_call("r", "K.decaps", "field1, ct0"), ec_ast.Return(expr="r")]
    right = [_call("r", "K.decaps", "field2, ct0"), ec_ast.Return(expr="r")]
    renaming = _coupled_field_renaming(pre, "A", "B")
    assert _field_reference_order(left, fields, renaming) != _field_reference_order(
        right, fields, renaming
    )


def test_renaming_is_applied_inside_a_branch() -> None:
    """A branch-local reference counts where it appears, renamed too."""
    pre = "={ct0} /\\ A.a{1} = B.z{2}"
    fields = {"a", "z"}
    left = [ec_ast.If(guard="g", then_body=[_assign("t", "a")], else_body=[])]
    right = [ec_ast.If(guard="g", then_body=[_assign("t", "z")], else_body=[])]
    renaming = _coupled_field_renaming(pre, "A", "B")
    assert _field_reference_order(left, fields) != _field_reference_order(right, fields)
    assert _field_reference_order(left, fields, renaming) == _field_reference_order(
        right, fields, renaming
    )


def _template_proof_body(lemma: str) -> list[str]:
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_renamed_fields.ec"
    ).read_text()
    block = template.split(f"lemma {lemma} :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [
        ln.strip()
        for ln in proof_body.strip().splitlines()
        if ln.strip() and not ln.strip().startswith("(*")
    ]


def test_emitted_tactic_matches_the_ec_validated_template() -> None:
    """Lockstep: what the row emits is what EasyCrypt accepted."""
    emitted = ["proc.", *_backbone_peel(_left_body()), "auto => /#."]
    assert emitted == _template_proof_body("rename_peel")


def test_dead_local_assignment_is_ignored_when_comparing() -> None:
    """Item 4's shape: one side copies fields into locals nothing reads."""
    fields = {"dk0", "ek0", "ek1"}
    live = [
        _call("r0", "K.decaps", "dk0, ct"),
        ec_ast.Return(expr="r0"),
    ]
    with_dead = [
        _assign("a0", "ek0"),
        _assign("a1", "ek1"),
        _call("r0", "K.decaps", "dk0, ct"),
        ec_ast.Return(expr="r0"),
    ]
    assert _field_reference_order(with_dead, fields) != _field_reference_order(
        live, fields
    )
    assert _field_orders_agree(with_dead, live, fields, {})


def test_a_read_local_is_not_dead() -> None:
    """The copy is used, so dropping it would change the program."""
    fields = {"dk0", "ek0"}
    left = [
        _assign("a0", "ek0"),
        _call("r0", "K.decaps", "a0, ct"),
        ec_ast.Return(expr="r0"),
    ]
    right = [_call("r0", "K.decaps", "dk0, ct"), ec_ast.Return(expr="r0")]
    assert _dead_local_assignments(left, fields) == []
    assert not _field_orders_agree(left, right, fields, {})


def test_a_local_read_only_inside_a_branch_is_not_dead() -> None:
    fields = {"ek0"}
    body = [
        _assign("a0", "ek0"),
        ec_ast.If(guard="g", then_body=[_assign("t", "a0")], else_body=[]),
    ]
    assert _dead_local_assignments(body, fields) == []


def test_a_state_field_write_is_never_dead() -> None:
    fields = {"ek0", "cached"}
    body = [_assign("cached", "ek0"), ec_ast.Return(expr="0")]
    assert _dead_local_assignments(body, fields) == []


def test_two_writes_to_one_name_are_both_kept() -> None:
    """Neither is droppable: one occurrence is the whole soundness argument."""
    fields = {"ek0", "ek1"}
    body = [_assign("a0", "ek0"), _assign("a0", "ek1"), ec_ast.Return(expr="0")]
    assert _dead_local_assignments(body, fields) == []


def test_a_body_with_a_while_declines_wholesale() -> None:
    """A name read only in a loop guard would look dead, so decline."""
    fields = {"ek0"}
    body = [
        _assign("a0", "ek0"),
        ec_ast.While(guard="a0 < n", body=[_assign("t", "1")]),
    ]
    assert _dead_local_assignments(body, fields) == []


def test_deadness_composes_with_the_coupling_renaming() -> None:
    """Both widenings at once: renamed fields plus a one-sided dead copy."""
    pre = "={ct} /\\ A.dk0_0{1} = B.field3{2}"
    fields = {"dk0_0", "field3", "ek0"}
    left = [
        _assign("a0", "ek0"),
        _call("r0", "K.decaps", "dk0_0, ct"),
        ec_ast.Return(expr="r0"),
    ]
    right = [_call("r0", "K.decaps", "field3, ct"), ec_ast.Return(expr="r0")]
    renaming = _coupled_field_renaming(pre, "A", "B")
    assert _field_orders_agree(left, right, fields, renaming)
    assert not _field_orders_agree(left, right, fields, {})


def _dead_copies_body() -> list[ec_ast.EcStmt]:
    """The left side of the dead-copies template, verbatim."""
    return [
        _assign("a0", "ek0"),
        _assign("a1", "ek1"),
        _call("r0", "K.decaps", "dk0, ct"),
        _assign("a2", "ek0"),
        _assign("a3", "dk1"),
        _call("r1", "K.decaps", "dk1, ct"),
        _call("r2", "H.evaluate", "comb r0 r1"),
        ec_ast.Return(expr="r2"),
    ]


def test_dead_copies_tactic_matches_the_ec_validated_template() -> None:
    """Lockstep for the dead-copies shape: the peel is over the FULL body.

    The dead assignments are ignored when deciding whether to fire, not when
    generating the tactic -- ``wp`` still has to sweep them, and the template
    is the proof that it does.
    """
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_dead_copies.ec"
    ).read_text()
    block = template.split("lemma dead_assign_peel :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    expected = [
        ln.strip()
        for ln in proof_body.strip().splitlines()
        if ln.strip() and not ln.strip().startswith("(*")
    ]
    emitted = ["proc.", *_backbone_peel(_dead_copies_body()), "auto => /#."]
    assert emitted == expected


# --- the coupled-guard branch descent -------------------------------------

GUARD_PRE = (
    "={ct} /\\ S_L.dk0{1} = S_R.dk0{2} /\\ S_L.ctStar_0{1} = S_R.field2{2}"
    " /\\ S_L.ctStar_1{1} = S_R.field4{2}"
)
GUARD_FIELDS = {"dk0", "ctStar_0", "ctStar_1", "field2", "field4"}


def _guard_left() -> list[ec_ast.EcStmt]:
    return [
        ec_ast.If(
            guard="ct = (ctStar_0, ctStar_1)",
            then_body=[_assign("out", "witness")],
            else_body=[
                _call("r0", "K.decaps", "dk0, ct.`1"),
                _call("r1", "H.evaluate", "comb r0 ct.`2"),
                _assign("out", "r1"),
            ],
        ),
        ec_ast.Return(expr="out"),
    ]


def _guard_right() -> list[ec_ast.EcStmt]:
    """Same program, guard fields renamed, plumbing differs in the else arm."""
    return [
        ec_ast.If(
            guard="ct = (field2, field4)",
            then_body=[_assign("out", "witness")],
            else_body=[
                _assign("c0", "ct.`1"),
                _call("r0", "K.decaps", "dk0, c0"),
                _call("r1", "H.evaluate", "comb r0 ct.`2"),
                _assign("out", "r1"),
            ],
        ),
        ec_ast.Return(expr="out"),
    ]


def test_coupled_guard_descent_fires_on_the_measured_shape() -> None:
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    assert (
        _coupled_guard_descent(_guard_left(), _guard_right(), GUARD_FIELDS, renaming)
        is not None
    )


def test_coupled_guard_descent_matches_the_ec_validated_template() -> None:
    """Lockstep: what the row emits is what EasyCrypt accepted."""
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    got = _coupled_guard_descent(_guard_left(), _guard_right(), GUARD_FIELDS, renaming)
    assert got is not None
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_coupled_guard_descent.ec"
    ).read_text()
    block = template.split("lemma guard_coupled_descent :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    assert got[0] == textwrap.dedent(proof_body).strip().splitlines()


def test_guards_the_coupling_does_not_relate_decline() -> None:
    """A genuinely different test must not be paired: goal one would be FALSE."""
    renaming = _coupled_field_renaming(
        "={ct} /\\ S_L.dk0{1} = S_R.dk0{2}", "S_L", "S_R"
    )
    assert (
        _coupled_guard_descent(_guard_left(), _guard_right(), GUARD_FIELDS, renaming)
        is None
    )


def test_a_leading_run_before_the_branch_declines() -> None:
    """``if`` is a first-instruction rule; a leading run needs its own split."""
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    left = [_assign("t", "ct.`1"), *_guard_left()]
    assert _coupled_guard_descent(left, _guard_right(), GUARD_FIELDS, renaming) is None


def test_an_arm_that_branches_again_declines() -> None:
    """Nested splits are the recursive row, deliberately not this one."""
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    left = _guard_left()
    assert isinstance(left[0], ec_ast.If)
    left[0].else_body = [
        ec_ast.If(
            guard="g",
            then_body=[_call("r0", "K.decaps", "dk0, ct.`1")],
            else_body=[],
        )
    ]
    assert _coupled_guard_descent(left, _guard_right(), GUARD_FIELDS, renaming) is None


def test_an_arm_whose_calls_are_reordered_declines() -> None:
    """A reordered arm needs a reorder route, which this row does not have."""
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    right = _guard_right()
    assert isinstance(right[0], ec_ast.If)
    right[0].else_body = [
        _call("r1", "H.evaluate", "comb r0 ct.`2"),
        _call("r0", "K.decaps", "dk0, ct.`1"),
        _assign("out", "r1"),
    ]
    assert _coupled_guard_descent(_guard_left(), right, GUARD_FIELDS, renaming) is None


# --- the bridge-composition gate ------------------------------------------


def _glob_bridge(left: str, right: str) -> str:
    return f"(glob {left}){{1}} = (glob {right}){{2}}"


FLAT_FIELDS = {"Step_3L_state_0": ["sk", "ctStar"], "Step_3R_state_0": ["sk", "ctStar"]}


def test_a_hop_coupling_that_leaves_a_field_unrelated_declines() -> None:
    """The measured KEMPRF shape: states carry sk and ctStar, hop pins sk."""
    assert not _bridge_specs_compose(
        _glob_bridge,
        "G_RandKey(K, F)",
        "Step_3L_state_0(K, F)",
        "Step_3R_state_0(K, F)",
        "={glob K} /\\ ={glob F} /\\ G_RandKey.sk{1} = R_MultiPRF.sk{2}",
        FLAT_FIELDS,
    )


def test_a_hop_coupling_relating_every_field_composes() -> None:
    """The measured 7_13_Backward shape, which is CLEAN today: must not move."""
    assert _bridge_specs_compose(
        _glob_bridge,
        "E_c.INDCPA_MultiChal_Left(E)",
        "Step_0L_state_0(E)",
        "Step_0R_state_0(E)",
        "={glob E} /\\ E_c.INDCPA_MultiChal_Left.k{1} = E_c.Challenge_Left.k{2}",
        {"Step_0L_state_0": ["k"], "Step_0R_state_0": ["challenger_k", "k"]},
    )


def test_a_seam_mangled_field_counts_as_related() -> None:
    """`challenger_k` in the flat state IS `E_c.Challenge_Left.k` in the hop."""
    assert _bridge_specs_compose(
        _glob_bridge,
        "E_c.INDCPA_MultiChal_Left(E)",
        "Step_0L_state_0(E)",
        "Step_0R_state_0(E)",
        "={glob E} /\\ E_c.INDCPA_MultiChal_Left.k{1} = E_c.Challenge_Left.k{2}",
        {"Step_0L_state_0": ["challenger_k"], "Step_0R_state_0": ["challenger_k"]},
    )


def test_a_fieldwise_bridge_composes_via_its_explicit_witnesses() -> None:
    """A field-wise bridge gets witnesses from `_precond_witness`; leave it."""

    def fieldwise(left: str, right: str) -> str:
        return f"{left}.a{{1}} = {right}.a{{2}}"

    assert _bridge_specs_compose(
        fieldwise, "L", "M", "R", "L.a{1} = R.a{2}", {"M": ["a", "b"], "R": ["a"]}
    )


def test_no_hop_coupling_at_all_composes() -> None:
    """Unknown couplings answer True: the gate only declines what it knows."""
    assert _bridge_specs_compose(
        _glob_bridge, "L", "M", "R", None, {"M": ["a"], "R": ["a"]}
    )
