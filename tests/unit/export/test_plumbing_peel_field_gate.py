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

from pathlib import Path

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _backbone_peel,
    _coupled_field_renaming,
    _field_reference_order,
)


def _call(var: str, callee: str, args: str) -> ec_ast.Call:
    return ec_ast.Call(var=var, callee=callee, args=args)


def _assign(var: str, rhs: str) -> ec_ast.Assign:
    return ec_ast.Assign(var=var, rhs=rhs)


LEFT_FIELDS = {"dk0_0", "dk0_1"}
RIGHT_FIELDS = {"field3", "field4"}
ALL_FIELDS = LEFT_FIELDS | RIGHT_FIELDS

RENAME_PRE = (
    "={ct0} /\\ S_L.dk0_0{1} = S_R.field3{2} /\\ S_L.dk0_1{1} = S_R.field4{2}"
)


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
