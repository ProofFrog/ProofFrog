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
import textwrap
from pathlib import Path

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _backbone_peel,
    _bridge_specs_compose,
    _coupled_field_renaming,
    _coupled_guard_descent,
    _invariant_covers_reads,
    _split_invariant,
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


def test_a_leading_run_before_the_branch_is_split_off() -> None:
    """``if`` is a first-instruction rule, so the run is peeled with ``seq``.

    This case used to decline; the leading-run split is what changed it.
    """
    renaming = _coupled_field_renaming(GUARD_PRE, "S_L", "S_R")
    decl = ec_ast.VarDecl(name="t", type="bs")
    left = [decl, _assign("t", "ct.`1"), *_guard_left()]
    right = [decl, _assign("t", "ct.`1"), *_guard_right()]
    got = _coupled_guard_descent(left, right, GUARD_FIELDS, renaming, GUARD_PRE)
    assert got is not None
    assert got[0][0] == "proc."
    assert got[0][1].startswith("seq 1 1 : (")


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


# --- the leading-run split, and the recursion it unblocks -------------------

LEAD_PRE = (
    "={ct} /\\ ={glob K} /\\ ={glob H} /\\ S_L.dk0{1} = S_R.dk0{2}"
    " /\\ S_L.ctStar{1} = S_R.field2{2}"
)
LEAD_FIELDS = {"dk0", "ctStar", "field2"}


def _decl(name: str, ty: str = "bs") -> ec_ast.VarDecl:
    return ec_ast.VarDecl(name=name, type=ty)


def _lead_left() -> list[ec_ast.EcStmt]:
    return [
        _decl("r0"),
        _decl("r1"),
        _decl("out"),
        _call("r0", "K.decaps", "dk0, ct.`1"),
        _call("r1", "H.evaluate", "comb r0 ct.`2"),
        ec_ast.If(
            guard="r1 = ctStar",
            then_body=[_assign("out", "witness")],
            else_body=[_assign("out", "r1")],
        ),
        ec_ast.Return(expr="out"),
    ]


def _lead_right() -> list[ec_ast.EcStmt]:
    """Same program, a longer leading run, guard field renamed."""
    return [
        _decl("r0"),
        _decl("r1"),
        _decl("c0"),
        _decl("c1"),
        _decl("out"),
        _assign("c0", "ct.`1"),
        _call("r0", "K.decaps", "dk0, c0"),
        _assign("c1", "comb r0 ct.`2"),
        _call("r1", "H.evaluate", "c1"),
        ec_ast.If(
            guard="r1 = field2",
            then_body=[_assign("out", "witness")],
            else_body=[_assign("out", "r1")],
        ),
        ec_ast.Return(expr="out"),
    ]


def test_leading_run_split_matches_the_ec_validated_template() -> None:
    """Lockstep: `seq n m` with n != m, exactly as EasyCrypt accepted it."""
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    got = _coupled_guard_descent(
        _lead_left(), _lead_right(), LEAD_FIELDS, renaming, LEAD_PRE
    )
    assert got is not None
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_leading_run_split.ec"
    ).read_text()
    block = template.split("lemma leading_run_split :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    expected = textwrap.dedent(proof_body).strip().splitlines()
    assert got[0][0] == expected[0]
    assert got[0][1].startswith("seq 2 4 : (")
    # the template writes the invariant over three lines for readability
    assert got[0][2:] == expected[4:]


def test_the_seq_counts_follow_the_LEMMA_sides_not_the_bodies() -> None:
    """The defect that rejected 32 exports: reversed, body1 is the RIGHT.

    `seq` is the only positional tactic this engine emits, so it is the only
    one that can be wrong this way.
    """
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    fwd = _coupled_guard_descent(
        _lead_left(), _lead_right(), LEAD_FIELDS, renaming, LEAD_PRE, False
    )
    rev = _coupled_guard_descent(
        _lead_left(), _lead_right(), LEAD_FIELDS, renaming, LEAD_PRE, True
    )
    assert fwd is not None and rev is not None
    assert fwd[0][1].startswith("seq 2 4 : (")
    assert rev[0][1].startswith("seq 4 2 : (")
    assert fwd[0][2:] == rev[0][2:]


def test_the_invariant_equates_only_same_typed_locals_both_runs_bind() -> None:
    """One-sided locals have nothing to equate to; differing types cannot."""
    left, right = _lead_left(), _lead_right()
    inv = _split_invariant(
        left[3:5],
        right[5:9],
        LEAD_PRE,
        {"r0": "bs", "r1": "bs"},
        {"r0": "bs", "r1": "bs"},
    )
    assert inv.startswith("={r0, r1} /\\ ")
    assert "c0" not in inv and "c1" not in inv
    mixed = _split_invariant(
        left[3:5],
        right[5:9],
        LEAD_PRE,
        {"r0": "bs", "r1": "bs"},
        {"r0": "bs", "r1": "bs * bs"},
    )
    assert mixed.startswith("={r0} /\\ ")


def test_a_branch_reading_an_uncarried_local_declines() -> None:
    """The one condition behind three separate compile failures.

    `seq` throws away everything but the invariant, so a local the branch
    reads that the invariant does not carry is gone and the closer cannot
    finish. Here the right run extracts `c0` and its branch then reads it.
    """
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    right = _lead_right()
    right[-2] = ec_ast.If(
        guard="r1 = field2",
        then_body=[_assign("out", "witness")],
        else_body=[_assign("out", "c0")],
    )
    assert (
        _coupled_guard_descent(_lead_left(), right, LEAD_FIELDS, renaming, LEAD_PRE)
        is None
    )


def test_invariant_coverage_is_asked_of_the_rendered_text() -> None:
    """It poses the question the closer faces, so the two cannot drift.

    The locals are passed as the set IN SCOPE, which is every one this run or
    any enclosing one binds -- ``seq`` discards them all alike.
    """
    branch = ec_ast.If(guard="x = y", then_body=[], else_body=[])
    assert _invariant_covers_reads("={x} /\\ true", {"x"}, branch)
    assert not _invariant_covers_reads("={z} /\\ true", {"x"}, branch)


def test_a_prefix_whose_calls_differ_declines() -> None:
    """A reordered or differing prefix is not this row's shape."""
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    right = _lead_right()
    right[6] = _call("r0", "H.evaluate", "dk0, c0")
    assert (
        _coupled_guard_descent(_lead_left(), right, LEAD_FIELDS, renaming, LEAD_PRE)
        is None
    )


def test_work_after_the_branch_declines() -> None:
    """`_branch_cut` allows only a trailing return after the split."""
    left = _lead_left()
    left.insert(6, _assign("z", "out"))
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    assert (
        _coupled_guard_descent(left, _lead_right(), LEAD_FIELDS, renaming, LEAD_PRE)
        is None
    )


NESTED_PRE = (
    "={ct} /\\ S_L.dk0{1} = S_R.dk0{2} /\\ S_L.ctStar_0{1} = S_R.field2{2}"
    " /\\ S_L.ctStar_1{1} = S_R.field4{2} /\\ S_L.alt{1} = S_R.field6{2}"
)
NESTED_FIELDS = {
    "dk0",
    "ctStar_0",
    "ctStar_1",
    "alt",
    "field2",
    "field4",
    "field6",
}


def _nested(inner_guard: str, outer_guard: str, extra: bool) -> list[ec_ast.EcStmt]:
    tail = ([_assign("c0", "ct.`1")] if extra else []) + [
        _call("r0", "K.decaps", "dk0, " + ("c0" if extra else "ct.`1")),
        _call("r1", "H.evaluate", "comb r0 ct.`2"),
        _assign("out", "r1"),
    ]
    return [
        _decl("r0"),
        _decl("r1"),
        _decl("out"),
        ec_ast.If(
            guard=outer_guard,
            then_body=[_assign("out", "witness")],
            else_body=[
                ec_ast.If(
                    guard=inner_guard,
                    then_body=[
                        _call("r0", "K.decaps", "dk0, ct.`2"),
                        _assign("out", "r0"),
                    ],
                    else_body=tail,
                )
            ],
        ),
        ec_ast.Return(expr="out"),
    ]


def test_nested_descent_matches_the_ec_validated_template() -> None:
    """Lockstep for two levels: the bullets must nest exactly as EC accepted."""
    renaming = _coupled_field_renaming(NESTED_PRE, "S_L", "S_R")
    got = _coupled_guard_descent(
        _nested("ct.`1 = alt", "ct = (ctStar_0, ctStar_1)", False),
        _nested("ct.`1 = field6", "ct = (field2, field4)", True),
        NESTED_FIELDS,
        renaming,
        NESTED_PRE,
    )
    assert got is not None
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_nested_guard_descent.ec"
    ).read_text()
    block = template.split("lemma nested_guard_descent :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    assert got[0] == textwrap.dedent(proof_body).strip().splitlines()


def test_a_common_local_bound_at_different_types_declines() -> None:
    """Skipping it is not enough: the closer would have to reconcile shapes.

    A tuple-expanding canonicalization leaves the same local holding a
    component on one side and the whole pair on the other.
    """
    renaming = _coupled_field_renaming(LEAD_PRE, "S_L", "S_R")
    right = _lead_right()
    right[0] = _decl("r0", "bs * bs")
    assert (
        _coupled_guard_descent(_lead_left(), right, LEAD_FIELDS, renaming, LEAD_PRE)
        is None
    )
