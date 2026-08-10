"""Unit tests for the multi-oracle per-oracle chain emitter (P3 Part B).

Every multi-oracle proof in the corpus has an independent companion blocker,
so this path has no EC-compiling target yet; these tests pin the *emitted
shape* (shared flat-state modules once, oracle-suffixed artifacts, the
state-coupling invariant in every chain spec, init established from ``true``)
against the validated template ``ec_templates/multi_oracle_indist.ec``.
"""

from __future__ import annotations

import re
from typing import Callable

from proof_frog import frog_ast
from proof_frog.transforms._base import TransformApplication
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt.chain_emitter import (
    MicroRequests,
    _chain_role_map,
    _coupling_spec,
    _dead_call_drop_tags,
    _emit_one_oracle_chain,
    _glob_coupling,
    _make_field_aware_coupling,
    _oracle_step_tactic,
    _project_to_method,
    _ref_base,
    _render_coupling_chain_body,
    emit_multi_oracle_chain_for_hop,
)


def _bs() -> frog_ast.BitStringType:
    return frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))


def _two_oracle_game(name: str, stateful_challenge: bool = False) -> frog_ast.Game:
    """A two-oracle stateful game: ``Initialize`` + ``Challenge(m0)``, field ``sk``.

    ``Challenge`` returns its argument by default -- a PURE function of its
    arguments, which the chain emitter deliberately collapses to a single
    endpoint lemma (no micros, no canon bridge). Pass ``stateful_challenge`` for
    a body that also reads the field ``sk``, the realistic post-init oracle
    shape, when a test needs the per-transform chain machinery to be exercised.
    """
    field = frog_ast.Field(_bs(), "sk", None)
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _bs(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Variable("sk"))]),
    )
    chal_ret = frog_ast.Variable("sk" if stateful_challenge else "m0")
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", _bs(), [frog_ast.Parameter(_bs(), "m0")]),
        frog_ast.Block([frog_ast.ReturnStatement(chal_ret)]),
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


def _modules() -> mt.ModuleTranslator:
    """A ``ModuleTranslator`` for the direct ``_emit_one_oracle_chain`` calls
    (the init backbone-peel synthesizer translates each endpoint to EC to read
    off its probabilistic backbone)."""
    return mt.ModuleTranslator(tc.TypeCollector(aliases={}), _type_of_factory())


# --- pure helpers ----------------------------------------------------------


def test_glob_coupling_shape() -> None:
    assert _glob_coupling("GL(E)", "GR(E)") == "(glob GL(E)){1} = (glob GR(E)){2}"


def test_coupling_spec_init_establishes_from_true() -> None:
    spec = _coupling_spec("L", "R", is_init=True, eq_args="true")
    assert spec == "(true ==> ={res} /\\ (glob L){1} = (glob R){2})"


def test_coupling_spec_post_init_carries_args_and_coupling() -> None:
    spec = _coupling_spec("L", "R", is_init=False, eq_args="={m0}")
    assert (
        spec == "(={m0} /\\ (glob L){1} = (glob R){2} ==> "
        "={res} /\\ (glob L){1} = (glob R){2})"
    )


def test_ref_base_strips_functor_application() -> None:
    assert _ref_base("Step_0R_state_5(K)") == "Step_0R_state_5"
    assert _ref_base("GR") == "GR"


def test_field_aware_coupling_same_cardinality_is_whole_glob() -> None:
    # Equal glob cardinality (identical names OR a pure positional rename) keeps
    # the whole-glob tuple equality verbatim -- clean proofs stay byte-identical.
    fields = {"L": ["dk0", "dk1"], "R": ["field1", "field2"]}
    coupling = _make_field_aware_coupling(fields, {}, ["K"])
    assert coupling("L(K)", "R(K)") == "(glob L(K)){1} = (glob R(K)){2}"


def test_field_aware_coupling_removal_uses_survivor_invariant() -> None:
    # R carries redundant dk0/dk1 (survivors challenger_dk0/1); L has them removed.
    fields = {
        "L": ["challenger_dk0", "challenger_dk1"],
        "R": ["challenger_dk0", "challenger_dk1", "dk0", "dk1"],
    }
    survivor = {"dk0": "challenger_dk0", "dk1": "challenger_dk1"}
    coupling = _make_field_aware_coupling(fields, survivor, ["K"])
    assert coupling("L(K)", "R(K)") == (
        "={glob K} /\\ "
        "L.challenger_dk0{1} = R.challenger_dk0{2} /\\ "
        "L.challenger_dk1{1} = R.challenger_dk1{2} /\\ "
        "R.dk0{2} = R.challenger_dk0{2} /\\ "
        "R.dk1{2} = R.challenger_dk1{2}"
    )


def _fields_game(name: str, field_names: list[str]) -> frog_ast.Game:
    """A field-only flat-state game (methods irrelevant to the role map)."""
    fields = [frog_ast.Field(_bs(), n, None) for n in field_names]
    return frog_ast.Game((name, [], fields, []))


def test_chain_role_map_unifies_survivor_and_positional_rename() -> None:
    # L side renames dk0/dk1 -> field1/field2 (same cardinality, positional);
    # R side removes dk0/dk1 (survivors challenger_dk0/1) then renames to
    # field1/field2. The role map must unify {dk0, challenger_dk0, field1} and
    # {dk1, challenger_dk1, field2} so a canonical endpoint couples by role.
    left = [
        _fields_game("L0", ["dk0", "dk1"]),
        _fields_game("L1", ["field1", "field2"]),
    ]
    right = [
        _fields_game("R0", ["challenger_dk0", "challenger_dk1", "dk0", "dk1"]),
        _fields_game("R1", ["challenger_dk0", "challenger_dk1"]),
        _fields_game("R2", ["field1", "field2"]),
    ]
    survivor = {"dk0": "challenger_dk0", "dk1": "challenger_dk1"}
    role = _chain_role_map(left, right, survivor)
    assert role["dk0"] == role["challenger_dk0"] == role["field1"]
    assert role["dk1"] == role["challenger_dk1"] == role["field2"]
    assert role["dk0"] != role["dk1"]


def test_field_aware_coupling_rename_role_correspondence() -> None:
    # The P5 case: a canonical endpoint L (field1/field2) coupled to the anchor R
    # (challenger_dk0/1, dk0/1). No field is shared by NAME, but the role map pairs
    # field1<->challenger_dk0 (declaration-order rep of role0) etc., and the within-R
    # survivor invariants thread consistently. Without the role cross-side terms the
    # coupling would be vacuous on {1} and the transitivity glue could not compose.
    fields = {
        "L": ["field1", "field2"],
        "R": ["challenger_dk0", "challenger_dk1", "dk0", "dk1"],
    }
    survivor = {"dk0": "challenger_dk0", "dk1": "challenger_dk1"}
    role = _chain_role_map(
        [_fields_game("L", ["dk0", "dk1"]), _fields_game("L", ["field1", "field2"])],
        [_fields_game("R", ["challenger_dk0", "challenger_dk1", "dk0", "dk1"])],
        survivor,
    )
    coupling = _make_field_aware_coupling(fields, survivor, ["K"], role)
    assert coupling("L(K)", "R(K)") == (
        "={glob K} /\\ "
        "L.field1{1} = R.challenger_dk0{2} /\\ "
        "L.field2{1} = R.challenger_dk1{2} /\\ "
        "R.dk0{2} = R.challenger_dk0{2} /\\ "
        "R.dk1{2} = R.challenger_dk1{2}"
    )


def test_field_aware_coupling_no_relatable_field_falls_back_not_vacuous() -> None:
    # Different cardinality AND no shared name / recoverable survivor: never emit
    # a vacuous coupling -- fall back to the (ill-typed) whole-glob so EC rejects
    # loudly (honest gating), rather than a bare ={glob K} that could vacuously
    # discharge a transitivity side-condition.
    fields = {"L": ["field1", "field2"], "R": ["challenger_dk0"]}
    coupling = _make_field_aware_coupling(fields, {}, ["K"])
    assert coupling("L(K)", "R(K)") == "(glob L(K)){1} = (glob R(K)){2}"


def test_coupling_spec_post_init_no_args_is_bare_coupling() -> None:
    spec = _coupling_spec("L", "R", is_init=False, eq_args="true")
    assert (
        spec == "((glob L){1} = (glob R){2} ==> ={res} /\\ (glob L){1} = (glob R){2})"
    )


def test_project_to_method_picks_named_method() -> None:
    g = _two_oracle_game("G")
    proj = _project_to_method(g, "challenge")
    assert proj is not None
    assert [m.signature.name for m in proj.methods] == ["Challenge"]
    assert _project_to_method(g, "nonexistent") is None


def test_dead_call_drop_tags_marks_extra_deterministic_call() -> None:
    # The PRF-random final hop: the longer side carries an extra deterministic
    # ``F.evaluate`` (dead -- overwritten by a later fresh sample). Aligning the
    # shorter backbone as a subsequence marks exactly that call as a drop.
    longer = [
        ("call", "K.keygen"),
        ("call", "K.encaps"),
        ("call", "F.evaluate"),
        ("sample", "s0"),
    ]
    shorter = [("call", "K.keygen"), ("call", "K.encaps"), ("sample", "s1")]
    tags = _dead_call_drop_tags(longer, shorter, {"F": {"evaluate"}})
    assert tags == [False, False, True, False]


def test_dead_call_drop_tags_rejects_non_deterministic_extra() -> None:
    # An extra call whose method is NOT deterministic cannot be dropped soundly
    # (no ``_pres`` axiom is justified) -> None, so the caller admits.
    longer = [("call", "K.keygen"), ("call", "K.encaps"), ("sample", "s0")]
    shorter = [("call", "K.keygen"), ("sample", "s1")]
    assert _dead_call_drop_tags(longer, shorter, {"F": {"evaluate"}}) is None


def test_oracle_step_tactic_identity_is_coupling_preserving_sim() -> None:
    g = _two_oracle_game("G")
    # Same game on both sides (equal glob cardinality): the oracle body is
    # unchanged and no field is removed -> proc; sim (not the field-removal peel).
    tac = _oracle_step_tactic(
        g,
        _two_oracle_game("G"),
        "challenge",
        False,
        {},
        {},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    # Third element is the automation-ladder rung the caller tags the micro
    # with: a fixed tactic text selected by a structural gate -> synth-static.
    # Middle element: the leg's MicroRequests record (empty -- sim needs no
    # axiom families).
    assert tac == (["proc; sim."], MicroRequests(), "synth-static")


# --- pure-of-args chain collapse -------------------------------------------


def _const_challenge_game(name: str, n_fields: int) -> frog_ast.Game:
    """A game whose ``Challenge`` returns a constant (pure in its arguments),
    with ``n_fields`` unrelated fields so successive states differ in glob
    cardinality -- the shape whose per-state transitivity used to be emitted."""
    fields = [frog_ast.Field(_bs(), f"f{i}", None) for i in range(n_fields)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _bs(), []),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Variable("f0"))]),
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", _bs(), [frog_ast.Parameter(_bs(), "m0")]),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Boolean(False))]),
    )
    return frog_ast.Game((name, [], fields, [init, chal]))


def test_emit_one_oracle_chain_pure_oracle_collapses_whole_chain() -> None:
    # An oracle that is a PURE function of its arguments in EVERY chain state (a
    # binding ``Unbreakable.Challenge`` ``return false``) needs no per-transform
    # transitivity: the states differ only in fields it never reads. The chain
    # collapses to one endpoint lemma -- no micros, no canon bridge -- which is
    # what dissolves the mixed whole-glob/field-wise composition wall.
    left = [_const_challenge_game("L", n) for n in (3, 4, 3)]
    right = [_const_challenge_game("R", 3)]
    chunks, _outer, _pres = _emit_one_oracle_chain(
        hop_index=10,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_10L_state_0", "Step_10L_state_1", "Step_10L_state_2"],
        right_mods=["Step_10R_state_0"],
        left_states=left,
        right_states=right,
        left_apps=[
            TransformApplication(
                iteration=0,
                transform_name="Synthetic",
                game_before=left[i],
                game_after=left[i + 1],
            )
            for i in range(2)
        ],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    text = "\n".join(chunks)
    assert "micro_10_challenge" not in text
    assert "canon_bridge_10_challenge" not in text
    assert "transitivity" not in text
    assert "proc; auto => /#." in text


def test_emit_one_oracle_chain_sampling_oracle_keeps_its_chain() -> None:
    # Same shape, but the oracle SAMPLES: ``auto`` cannot discharge a (even dead)
    # ``<$``, so the collapse must decline and the per-transform chain stay.
    left = [_const_challenge_game("L", n) for n in (3, 4)]
    for g in left:
        g.methods[1].block.statements.insert(
            0,
            frog_ast.Sample(
                frog_ast.Variable("MessageSpace"),
                frog_ast.Variable("dead"),
                frog_ast.Variable("MessageSpace"),
            ),
        )
    chunks, _outer, _pres = _emit_one_oracle_chain(
        hop_index=10,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_10L_state_0", "Step_10L_state_1"],
        right_mods=["Step_10R_state_0"],
        left_states=left,
        right_states=[_const_challenge_game("R", 3)],
        left_apps=[
            TransformApplication(
                iteration=0,
                transform_name="Synthetic",
                game_before=left[0],
                game_after=left[1],
            )
        ],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    assert "proc; auto => /#." not in "\n".join(chunks)


# --- per-oracle chain assembly --------------------------------------------


def test_emit_one_oracle_chain_no_transforms_init() -> None:
    g = _two_oracle_game("G")
    chunks, outer, _pres = _emit_one_oracle_chain(
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
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    # Canonically-identical init endpoints (same game body) => the raw wrappers
    # are inline-equivalent, so the lemma closes directly and emits NO per-
    # transform chain artifacts. This init body has no *deterministic* call to
    # trip ``sim`` up, so the synthesizer keeps the historical ``proc; inline *;
    # sim.`` (byte-identical, rung ``synth-static``); the backbone peel is only
    # for inits carrying an ``F.evaluate`` over renamed ``encaps`` projections.
    assert chunks == []
    outer_text = "\n".join(outer)
    assert "proc; inline *; sim." in outer_text
    assert "synth-static" in outer_text
    assert outer[-1] == "qed."


def test_emit_one_oracle_chain_init_inline_equiv_gated_on_body_equality() -> None:
    # The inline-equivalence shortcut (``proc; inline *; sim``) fires iff the two
    # FIRST flat-state (raw-wrapper) bodies are identical -- what ``sim`` actually
    # relates. It must NOT fire for GENUINELY different init bodies (else it is a
    # silently-failing vacuous tactic). Here the right init SAMPLES its field (a
    # real difference that survives flat rendering, unlike a dead post-``return``
    # statement), so the raw wrappers differ and the chain (bridge + chain lemma)
    # is emitted instead. (A later CHAIN state diverging while the raw wrappers
    # stay equal -- e.g. one side unpacking a packed key it reads component-wise
    # -- is the opposite case and DOES take the shortcut; see the expanded
    # LEAK-BIND-K-CT proofs.)
    g_left = _two_oracle_game("G")
    g_right = _two_oracle_game("G")
    # Make the right init body genuinely differ: sample the returned field. A
    # sample is not dead code, so it survives into the flat state (an appended
    # post-return statement would be dropped and leave the bodies equal).
    g_right.methods[0].block.statements.insert(
        0,
        frog_ast.Sample(_bs(), frog_ast.Variable("sk"), frog_ast.Variable("D")),
    )
    chunks, outer, _pres = _emit_one_oracle_chain(
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
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    text = "\n".join(chunks)
    assert chunks != []
    assert "hop_0_initialize_chain" in text
    assert "proc; inline *; sim." not in "\n".join(outer)


def test_emit_one_oracle_chain_post_init_carries_args() -> None:
    # A STATE-READING challenge: the pure-of-args collapse must not fire, so the
    # per-transform chain artifacts (canon bridge + arg-carrying specs) appear.
    g = _two_oracle_game("G", stateful_challenge=True)
    chunks, _outer, _pres = _emit_one_oracle_chain(
        hop_index=0,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_0L_state_0"],
        right_mods=["Step_0R_state_0"],
        left_states=[g],
        right_states=[_two_oracle_game("G", stateful_challenge=True)],
        left_apps=[],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    text = "\n".join(chunks)
    assert "canon_bridge_0_challenge" in text
    # post-init precondition carries both the arg equality and the coupling.
    assert "={m0} /\\ (glob Step_0L_state_0){1} = (glob Step_0R_state_0){2}" in text


def test_multi_oracle_micros_carry_transform_and_resolution_tags() -> None:
    """Every emitted multi-oracle micro is attributable to its transform.

    An EC-accepted micro is a machine-checked test case for ONE application of
    ONE transform, but that evidence is only countable when the micro carries
    both the ``(* transform: NAME (bucket=...) *)`` header and a
    ``(* resolution: <rung> *)`` tag -- the pair the dashboard parser pairs by
    adjacency, exactly as it does for single-oracle micros. Both are EC
    comments, so the tagging is semantics-neutral.
    """
    left = [_two_oracle_game(n, stateful_challenge=True) for n in ("L0", "L1")]
    right = [_two_oracle_game(n, stateful_challenge=True) for n in ("R0", "R1")]
    chunks, _outer, _pres = _emit_one_oracle_chain(
        hop_index=3,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_3L_state_0", "Step_3L_state_1"],
        right_mods=["Step_3R_state_0", "Step_3R_state_1"],
        left_states=left,
        right_states=right,
        left_apps=[
            TransformApplication(
                iteration=0,
                transform_name="Alpha Rename",
                game_before=left[0],
                game_after=left[1],
            )
        ],
        right_apps=[
            TransformApplication(
                iteration=0,
                transform_name="Topological Sorting",
                game_before=right[0],
                game_after=right[1],
            )
        ],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    text = "\n".join(chunks)
    assert "(* transform: Alpha Rename (bucket=canned) *)" in text
    # The right chain is proven in the reverse direction; the marker matches the
    # single-oracle path's so the same suffix-stripping reads both.
    assert "(* transform: Topological Sorting (reversed) (bucket=canned) *)" in text
    # Mirrors the dashboard parser's adjacency pairing: a transform comment then
    # the rung tag opening that micro's proof body.
    pairs = re.findall(
        r"\(\* transform: (.+?) \(bucket=\w+\) \*\)"
        r".*?\(\* resolution: ([\w-]+) \*\)",
        text,
        re.DOTALL,
    )
    assert pairs == [
        ("Alpha Rename", "synth-static"),
        ("Topological Sorting (reversed)", "synth-static"),
    ]


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
    # STATE-READING challenge: the argument-pure bypass must not fire, so the
    # post-init oracle really goes through the per-transform chain.
    types = tc.TypeCollector(aliases={})
    info = emit_multi_oracle_chain_for_hop(
        hop_index=0,
        left_game=_two_oracle_game("GL", stateful_challenge=True),
        right_game=_two_oracle_game("GR", stateful_challenge=True),
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
    # Call-free init endpoints (no deterministic call) => ``sim`` aligns them, so
    # the synthesizer keeps the historical ``proc; inline *; sim.``.
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
    # Mutate challenge's body on the "after" state so it genuinely differs by a
    # live probabilistic statement: sample a fresh ``mPrime`` before the return.
    # This is not the identical-state first cut, not a pure reorder, and not a
    # dead-call drop (the extra backbone event is a sample, not a droppable
    # deterministic call), so the oracle must route to a coupling-pending admit.
    g1.methods[1].block.statements.insert(
        0,
        frog_ast.Sample(
            frog_ast.Variable("MessageSpace"),
            frog_ast.Variable("mPrime"),
            frog_ast.Variable("MessageSpace"),
        ),
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
    # Call-free init endpoints (no deterministic call) => ``sim`` aligns them.
    init_body = "\n".join(info.tactic_body_by_oracle["initialize"])
    assert "proc; inline *; sim." in init_body


# --- evidence-only micro emission ------------------------------------------


def _sampling_variant(g: frog_ast.Game) -> frog_ast.Game:
    """``g`` with a live sample prepended to ``Challenge`` -- the difference no
    micro route closes (not identity, not a reorder, not a droppable
    deterministic call), so a leg into it declines."""
    out = _two_oracle_game(g.name, stateful_challenge=True)
    out.methods[1].block.statements.insert(
        0,
        frog_ast.Sample(
            frog_ast.Variable("MessageSpace"),
            frog_ast.Variable("mPrime"),
            frog_ast.Variable("MessageSpace"),
        ),
    )
    return out


def _broken_chain_chunks() -> tuple[list[str], list[str]]:
    """Emit a 2-leg chain whose first leg closes and whose second declines."""
    s0 = _two_oracle_game("GL", stateful_challenge=True)
    s1 = _two_oracle_game("GL", stateful_challenge=True)
    s2 = _sampling_variant(s1)
    left = [s0, s1, s2]
    chunks, outer, _pres = _emit_one_oracle_chain(
        hop_index=0,
        oracle_name="challenge",
        is_init=False,
        eq_args="={m0}",
        left_mods=["Step_0L_state_0", "Step_0L_state_1", "Step_0L_state_2"],
        right_mods=["Step_0R_state_0"],
        left_states=left,
        right_states=[_two_oracle_game("GR", stateful_challenge=True)],
        left_apps=[
            TransformApplication(
                iteration=i,
                transform_name="Synthetic",
                game_before=left[i],
                game_after=left[i + 1],
            )
            for i in range(2)
        ],
        right_apps=[],
        mod_ref=lambda n: n,
        left_wrapper_expr="GL(E)",
        right_wrapper_expr="GR(E)",
        bridge_tactic="proc; inline *; sp; wp; sim",
        external_module_types={},
        method_return_types={},
        modules=_modules(),
        flat_params=[],
        det_methods={},
    )
    return chunks, outer


def test_broken_chain_emits_its_closable_leg_as_evidence() -> None:
    # The chain cannot carry the oracle (leg 1 declines), but leg 0 -- an
    # identity step ``proc; sim`` closes -- is still a machine-checkable
    # statement about one transform application. It is emitted standalone,
    # flagged evidence-only, so EasyCrypt accepting the file is evidence for
    # that application even though the hop is carried elsewhere.
    chunks, _outer = _broken_chain_chunks()
    text = "\n".join(chunks)
    assert "lemma micro_0_challenge_left_0 :" in text
    assert "proc; sim." in text
    assert "evidence-only" in text
    # Nothing is emitted for the declining leg, and no chain artifact claims
    # the oracle is carried by these lemmas.
    assert "micro_0_challenge_left_1" not in text
    assert "canon_bridge_0_challenge" not in text
    assert "hop_0_challenge_chain" not in text


def test_broken_chain_never_emits_an_admitting_micro() -> None:
    # The load-bearing guarantee of evidence-only emission: an unclosable leg
    # emits NOTHING. If it emitted ``admit.`` instead, an admit-free proof
    # would gain admits and a clean proof would regress to warn.
    chunks, outer = _broken_chain_chunks()
    assert "admit" not in "\n".join(chunks)
    # The oracle itself still routes exactly as before -- here, to the honest
    # coupling-pending admit in the whole-oracle body.
    assert "admit" in "\n".join(outer)
