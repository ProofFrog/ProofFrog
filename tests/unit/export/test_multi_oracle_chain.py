"""Unit tests for the multi-oracle per-oracle chain emitter (P3 Part B).

Every multi-oracle proof in the corpus has an independent companion blocker,
so this path has no EC-compiling target yet; these tests pin the *emitted
shape* (shared flat-state modules once, oracle-suffixed artifacts, the
state-coupling invariant in every chain spec, init established from ``true``)
against the validated template ``ec_templates/multi_oracle_indist.ec``.
"""

from __future__ import annotations

from typing import Callable

from proof_frog import frog_ast
from proof_frog.transforms._base import TransformApplication
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _coupling_spec,
    _emit_one_oracle_chain,
    _glob_coupling,
    _oracle_step_tactic,
    _project_to_method,
    _render_coupling_chain_body,
    emit_multi_oracle_chain_for_hop,
)


def _bs() -> frog_ast.BitStringType:
    return frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))


def _two_oracle_game(name: str) -> frog_ast.Game:
    """A two-oracle stateful game: ``Initialize`` + ``Challenge(m0)``, field ``sk``."""
    field = frog_ast.Field(_bs(), "sk", None)
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _bs(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Variable("sk"))]),
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", _bs(), [frog_ast.Parameter(_bs(), "m0")]),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Variable("m0"))]),
    )
    return frog_ast.Game((name, [], [field], [init, chal]))


def _type_of_factory() -> Callable[
    [dict[str, frog_ast.Type], dict[str, str]],
    Callable[[frog_ast.Expression], frog_ast.Type],
]:
    def factory(
        _local: dict[str, frog_ast.Type], _mpt: dict[str, str]
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                return _bs()
            raise KeyError(e)

        return type_of

    return factory


# --- pure helpers ----------------------------------------------------------


def test_glob_coupling_shape() -> None:
    assert _glob_coupling("GL(E)", "GR(E)") == "(glob GL(E)){1} = (glob GR(E)){2}"


def test_coupling_spec_init_establishes_from_true() -> None:
    spec = _coupling_spec("L", "R", is_init=True, eq_args="true")
    assert spec == "(true ==> ={res} /\\ (glob L){1} = (glob R){2})"


def test_coupling_spec_post_init_carries_args_and_coupling() -> None:
    spec = _coupling_spec("L", "R", is_init=False, eq_args="={m0}")
    assert spec == "(={m0} /\\ (glob L){1} = (glob R){2} ==> " "={res} /\\ (glob L){1} = (glob R){2})"


def test_coupling_spec_post_init_no_args_is_bare_coupling() -> None:
    spec = _coupling_spec("L", "R", is_init=False, eq_args="true")
    assert spec == "((glob L){1} = (glob R){2} ==> ={res} /\\ (glob L){1} = (glob R){2})"


def test_project_to_method_picks_named_method() -> None:
    g = _two_oracle_game("G")
    proj = _project_to_method(g, "challenge")
    assert proj is not None
    assert [m.signature.name for m in proj.methods] == ["Challenge"]
    assert _project_to_method(g, "nonexistent") is None


def test_oracle_step_tactic_identity_is_coupling_preserving_sim() -> None:
    g = _two_oracle_game("G")
    # Same game on both sides: the oracle body is unchanged -> proc; sim.
    tac = _oracle_step_tactic(
        g, _two_oracle_game("G"), "challenge", False, {}, {}
    )
    assert tac == ["proc; sim."]


# --- per-oracle chain assembly --------------------------------------------


def test_emit_one_oracle_chain_no_transforms_init() -> None:
    g = _two_oracle_game("G")
    chunks, outer = _emit_one_oracle_chain(
        hop_index=0,
        oracle_name="initialize",
        is_init=True,
        eq_args="true",
        left_mods=["Step_0L_state_0"],
        right_mods=["Step_0R_state_0"],
        left_states=[g],
        right_states=[_two_oracle_game("G")],
        left_apps=[],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
    )
    # Canonically-identical init endpoints (same game body) => the raw wrappers
    # are inline-equivalent, so the lemma closes directly via the canned
    # inline-equivalence tactic and emits NO per-transform chain artifacts.
    assert chunks == []
    outer_text = "\n".join(outer)
    assert "proc; inline *; sim." in outer_text
    assert "synth-static" in outer_text  # ladder rung 1 (fixed canned tactic)
    assert outer[-1] == "qed."


def test_emit_one_oracle_chain_init_inline_equiv_gated_on_canonical_equality() -> None:
    # When the two init endpoints' canonical bodies DIFFER, the inline-
    # equivalence shortcut must NOT fire -- the chain (bridge + chain lemma) is
    # emitted instead, so the emitter never silently claims inline-equivalence
    # for genuinely different init bodies.
    g_left = _two_oracle_game("G")
    g_right = _two_oracle_game("G")
    # Make the right init body differ (append an extra return so it is not equal
    # to the left init body, and not a pure reorder of a single statement).
    g_right.methods[0].block.statements.append(
        frog_ast.ReturnStatement(frog_ast.Variable("sk"))
    )
    chunks, outer = _emit_one_oracle_chain(
        hop_index=0,
        oracle_name="initialize",
        is_init=True,
        eq_args="true",
        left_mods=["Step_0L_state_0"],
        right_mods=["Step_0R_state_0"],
        left_states=[g_left],
        right_states=[g_right],
        left_apps=[],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
    )
    text = "\n".join(chunks)
    assert chunks != []
    assert "hop_0_initialize_chain" in text
    assert "proc; inline *; sim." not in "\n".join(outer)


def test_emit_one_oracle_chain_post_init_carries_args() -> None:
    g = _two_oracle_game("G")
    chunks, _outer = _emit_one_oracle_chain(
        hop_index=0,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_0L_state_0"],
        right_mods=["Step_0R_state_0"],
        left_states=[g],
        right_states=[_two_oracle_game("G")],
        left_apps=[],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
    )
    text = "\n".join(chunks)
    assert "canon_bridge_0_challenge" in text
    # post-init precondition carries both the arg equality and the coupling.
    assert "={m0} /\\ (glob Step_0L_state_0){1} = (glob Step_0R_state_0){2}" in text


def test_render_coupling_chain_body_walks_left_bridge_right() -> None:
    body = _render_coupling_chain_body(
        oracle_name="eval",
        is_init=False,
        eq_args="={x}",
        left_refs=["L0", "L1"],
        right_refs=["R0", "R1"],
        micros_left=["micro_0_eval_left_0"],
        micros_right_rev=["micro_0_eval_right_0_rev"],
        bridge_name="canon_bridge_0_eval",
    )
    text = "\n".join(body)
    # One left micro, then the bridge (to the last right state), then the
    # final reversed right micro applied directly.
    assert "apply micro_0_eval_left_0" in text
    assert "apply canon_bridge_0_eval" in text
    assert "apply micro_0_eval_right_0_rev." in text
    # Transitivity middle-specs carry per-step coupling invariants: the first
    # left micro couples L0~L1, and its second spec couples L1 to the final
    # right endpoint R0.
    assert "(glob L0){1} = (glob L1){2}" in text
    assert "(glob L1){1} = (glob R0){2}" in text


# --- full emission ---------------------------------------------------------


def test_emit_multi_oracle_chain_full_shape() -> None:
    types = tc.TypeCollector(aliases={})
    info = emit_multi_oracle_chain_for_hop(
        hop_index=0,
        left_game=_two_oracle_game("GL"),
        right_game=_two_oracle_game("GR"),
        left_apps=[],
        right_apps=[],
        oracles=[("initialize", True), ("challenge", False)],
        oracle_eq_args={"initialize": "true", "challenge": "={m0}"},
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        types=types,
        type_of_factory=_type_of_factory(),
        external_module_types={},
        method_return_types={},
    )
    decls = "\n".join(info.extra_decls)
    # Shared flat-state modules emitted exactly ONCE (not per oracle).
    assert decls.count("module Step_0L_state_0") == 1
    assert decls.count("module Step_0R_state_0") == 1
    # Stateful game => the shared module declares its state var.
    assert "var sk" in decls
    # init endpoints are canonically identical => inline-equivalence tactic, no
    # init chain artifacts; the post-init oracle still chains per-transform.
    assert "hop_0_initialize_chain" not in decls
    assert "hop_0_challenge_chain" in decls
    # Both oracles produced an outer tactic body.
    assert set(info.tactic_body_by_oracle) == {"initialize", "challenge"}
    init_body = "\n".join(info.tactic_body_by_oracle["initialize"])
    chal_body = "\n".join(info.tactic_body_by_oracle["challenge"])
    assert "proc; inline *; sim." in init_body
    assert "apply hop_0_challenge_chain" in chal_body
    # The post-init oracle threads its argument equality into the bridge spec.
    assert "={m0}" in chal_body


def test_emit_multi_oracle_chain_admits_changed_post_init_body() -> None:
    # A post-init oracle whose body genuinely changes across a (synthetic)
    # transform step is not discharged by the identical-state first cut: the
    # whole oracle routes to a coupling-pending admit, with no chain artifacts.
    g0 = _two_oracle_game("GL")
    g1 = _two_oracle_game("GL")
    # Mutate challenge's body on the "after" state so it differs and is not a
    # pure reorder (a single statement cannot be a permutation of two).
    g1.methods[1].block.statements.append(
        frog_ast.ReturnStatement(frog_ast.Variable("m0"))
    )

    left_apps = [
        TransformApplication(
            iteration=0,
            transform_name="Synthetic",
            game_before=g0,
            game_after=g1,
        )
    ]
    types = tc.TypeCollector(aliases={})
    info = emit_multi_oracle_chain_for_hop(
        hop_index=0,
        left_game=g0,
        right_game=_two_oracle_game("GR"),
        left_apps=left_apps,
        right_apps=[],
        oracles=[("initialize", True), ("challenge", False)],
        oracle_eq_args={"initialize": "true", "challenge": "={m0}"},
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        types=types,
        type_of_factory=_type_of_factory(),
        external_module_types={},
        method_return_types={},
    )
    chal_body = "\n".join(info.tactic_body_by_oracle["challenge"])
    assert "admit." in chal_body
    # init endpoints are canonically identical => inline-equivalence tactic.
    init_body = "\n".join(info.tactic_body_by_oracle["initialize"])
    assert "proc; inline *; sim." in init_body
