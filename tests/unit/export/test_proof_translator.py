"""Unit tests for the EasyCrypt proof translator."""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import oracle_model as om
from proof_frog.export.easycrypt import proof_translator as pt


def _steps_of_otpsecurelr() -> list[frog_ast.ProofStep]:
    proof = frog_parser.parse_proof_file(
        "examples/joy/Proofs/Ch2/OTPSecureLR.proof"
    )
    return proof.steps


def _resolver() -> pt.StepResolver:
    return pt.StepResolver(
        module_name_by_concrete_game={
            ("OneTimeSecrecyLR", "Left"): "OneTimeSecrecyLR_Left",
            ("OneTimeSecrecyLR", "Right"): "OneTimeSecrecyLR_Right",
            ("OneTimeSecrecy", "Real"): "OneTimeSecrecy_Real",
            ("OneTimeSecrecy", "Random"): "OneTimeSecrecy_Random",
        },
        oracle_name_by_game_file={
            "OneTimeSecrecyLR": "enc",
            "OneTimeSecrecy": "enc",
        },
        primitive_name="SymEnc",
        scheme_name="OTP",
    )


def test_step_resolver_plain_step() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _resolver()
    resolved = resolver.resolve(steps[0])
    assert resolved.module_expr == "OneTimeSecrecyLR_Left(OTP)"
    assert resolved.oracle_name == "enc"


def test_step_resolver_composed_step() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _resolver()
    resolved = resolver.resolve(steps[1])
    assert resolved.module_expr == "R1(OTP, OneTimeSecrecy_Real(OTP))"
    assert resolved.oracle_name == "enc"


def test_translate_hops_emits_admit_per_hop() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _resolver()
    lemmas = pt.translate_hops(
        resolver, steps, lambda _i, _a, _b: ["admit.", "qed."]
    )
    assert len(lemmas) == 5
    assert all(lemma.postcondition == "={res}" for lemma in lemmas)
    assert all(lemma.precondition == "true" for lemma in lemmas)
    assert all(lemma.body == ["admit.", "qed."] for lemma in lemmas)


# --- Multi-oracle per-oracle equiv lemmas (P3) -----------------------------


def _multi_oracle_model() -> om.GameOracleModel:
    """A two-oracle (Initialize + Challenge) model for both OTPSecureLR sides."""
    return om.GameOracleModel(
        all_names=["initialize", "challenge"],
        init_name="initialize",
        post_init_names=["challenge"],
    )


def _multi_oracle_resolver() -> pt.StepResolver:
    model = _multi_oracle_model()
    return pt.StepResolver(
        module_name_by_concrete_game={
            ("OneTimeSecrecyLR", "Left"): "OneTimeSecrecyLR_Left",
            ("OneTimeSecrecyLR", "Right"): "OneTimeSecrecyLR_Right",
            ("OneTimeSecrecy", "Real"): "OneTimeSecrecy_Real",
            ("OneTimeSecrecy", "Random"): "OneTimeSecrecy_Random",
        },
        oracle_name_by_game_file={
            "OneTimeSecrecyLR": "initialize",
            "OneTimeSecrecy": "initialize",
        },
        primitive_name="SymEnc",
        scheme_name="OTP",
        oracle_model_by_game_file={
            "OneTimeSecrecyLR": model,
            "OneTimeSecrecy": model,
        },
        oracle_params_by_oracle={
            "OneTimeSecrecyLR": {"initialize": [], "challenge": ["m0", "m1"]},
            "OneTimeSecrecy": {"initialize": [], "challenge": ["m0", "m1"]},
        },
    )


def test_coupling_invariant_shape() -> None:
    inv = pt.coupling_invariant("GL(OTP)", "GR(OTP)")
    assert inv == "(glob GL(OTP)){1} = (glob GR(OTP)){2}"


def test_oracle_model_for_returns_model() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _multi_oracle_resolver()
    model = resolver.oracle_model_for(steps[0])
    assert model is not None and model.is_multi_oracle
    assert model.init_name == "initialize"
    assert model.post_init_names == ["challenge"]


def test_precondition_for_oracle_name_uses_per_oracle_params() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _multi_oracle_resolver()
    # The init oracle has no args; challenge takes m0, m1.
    assert resolver.precondition_for(steps[0], "initialize") == "true"
    assert resolver.precondition_for(steps[0], "challenge") == "={m0, m1}"
    # Without an oracle name the legacy (first-method) params apply.
    assert resolver.precondition_for(steps[0]) == "true"


def test_translate_hops_single_oracle_when_no_callback() -> None:
    """A multi-oracle model is ignored unless an oracle body callback is given."""
    steps = _steps_of_otpsecurelr()
    resolver = _multi_oracle_resolver()
    lemmas = pt.translate_hops(resolver, steps, lambda _i, _a, _b: ["admit.", "qed."])
    assert [lemma.name for lemma in lemmas] == [f"hop_{i}" for i in range(5)]


def test_translate_hops_multi_oracle_emits_per_oracle_lemmas() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _multi_oracle_resolver()
    lemmas = pt.translate_hops(
        resolver,
        steps,
        lambda _i, _a, _b: ["admit.", "qed."],  # legacy path; unused here
        oracle_body_for_hop=lambda _i, _a, _b, _name, _is_init: ["proc; auto.", "qed."],
    )
    # 5 hops x 2 oracles (init + 1 post-init) = 10 lemmas.
    assert len(lemmas) == 10
    names = [lemma.name for lemma in lemmas]
    assert names[:2] == ["hop_0_initialize", "hop_0_challenge"]

    init_lemma = lemmas[0]
    chal_lemma = lemmas[1]
    coupling = pt.coupling_invariant(
        "OneTimeSecrecyLR_Left(OTP)", "R1(OTP, OneTimeSecrecy_Real(OTP))"
    )
    # init: established from `true`, posts the coupling.
    assert init_lemma.left == "OneTimeSecrecyLR_Left(OTP).initialize"
    assert init_lemma.right == "R1(OTP, OneTimeSecrecy_Real(OTP)).initialize"
    assert init_lemma.precondition == "true"
    assert init_lemma.postcondition == f"={{res}} /\\ {coupling}"
    # post-init: preserves the coupling, pre also carries the arg equality.
    assert chal_lemma.left == "OneTimeSecrecyLR_Left(OTP).challenge"
    assert chal_lemma.precondition == f"={{m0, m1}} /\\ {coupling}"
    assert chal_lemma.postcondition == f"={{res}} /\\ {coupling}"
    assert chal_lemma.body == ["proc; auto.", "qed."]


def test_translate_hops_multi_oracle_skips_oracle_when_body_none() -> None:
    steps = _steps_of_otpsecurelr()
    resolver = _multi_oracle_resolver()

    def only_init(
        _i: int, _a: object, _b: object, _name: str, is_init: bool
    ) -> list[str] | None:
        return ["proc; auto.", "qed."] if is_init else None

    lemmas = pt.translate_hops(
        resolver,
        steps,
        lambda _i, _a, _b: ["admit.", "qed."],
        oracle_body_for_hop=only_init,
    )
    # Only the init oracle per hop survives.
    assert all(lemma.name.endswith("_initialize") for lemma in lemmas)
    assert len(lemmas) == 5


def test_translate_assumption_axioms_theory() -> None:
    """One op + two axioms, quantified over abstract scheme Em."""
    decls = pt.translate_assumption_axioms_theory(
        assumption_name="OneTimeSecrecy",
        adversary_type_name="OneTimeSecrecy_Adv",
        scheme_type_name="Scheme",
        scheme_param_name="Em",
        real_wrapper_name="Game_OneTimeSecrecy_Real",
        random_wrapper_name="Game_OneTimeSecrecy_Random",
    )
    op_decls = [d for d in decls if isinstance(d, ec_ast.OpDecl)]
    axiom_decls = [d for d in decls if isinstance(d, ec_ast.Axiom)]
    assert len(op_decls) == 1
    assert op_decls[0].name == "eps_OneTimeSecrecy"
    assert op_decls[0].signature == "real"
    assert len(axiom_decls) == 2
    pos_axiom = next(a for a in axiom_decls if a.name == "eps_OneTimeSecrecy_pos")
    assert pos_axiom.formula == "0%r <= eps_OneTimeSecrecy"
    adv_axiom = next(a for a in axiom_decls if a.name == "OneTimeSecrecy_advantage")
    # Scheme param declared first. The adversary carries no
    # ``{-Em}`` restriction: ProofFrog primitives are stateless, and the
    # restriction would block legitimate reductions (e.g. PRG hybrids)
    # that evaluate the primitive themselves on un-hybridized positions.
    assert adv_axiom.module_args[0].name == "Em"
    assert adv_axiom.module_args[0].module_type == "Scheme"
    assert adv_axiom.module_args[1].name == "A"
    assert adv_axiom.module_args[1].module_type == "OneTimeSecrecy_Adv"
    assert "&m" in adv_axiom.memory_args
    assert "Game_OneTimeSecrecy_Real(Em, A)" in adv_axiom.formula
    assert "Game_OneTimeSecrecy_Random(Em, A)" in adv_axiom.formula
    assert "<= eps_OneTimeSecrecy" in adv_axiom.formula


def test_translate_inlining_hop_pr() -> None:
    lemma = pt.translate_inlining_hop_pr_lemma(
        hop_index=0,
        adversary_type_name="OneTimeSecrecyLR_Adv",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_0",
        right_wrapper_name="Game_step_1",
    )
    assert isinstance(lemma, ec_ast.ProbLemma)
    assert lemma.name == "hop_0_pr"
    assert lemma.module_args[0].name == "A"
    assert lemma.module_args[0].module_type == "OneTimeSecrecyLR_Adv {-OTP}"
    assert "&m" in lemma.memory_args
    assert "Pr[Game_step_0(A).main() @ &m : res]" in lemma.statement
    assert "Pr[Game_step_1(A).main() @ &m : res]" in lemma.statement
    assert "=" in lemma.statement
    body = "\n".join(lemma.body)
    assert "byequiv" in body
    assert "hop_0" in body
    assert "qed." in body


def test_translate_assumption_hop_pr() -> None:
    lemma = pt.translate_assumption_hop_pr_lemma(
        hop_index=1,
        adversary_type_name="OneTimeSecrecyLR_Adv",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_1",
        right_wrapper_name="Game_step_2",
        assumption_name="OneTimeSecrecy",
        reduction_adv_name="R1_Adv",
        left_assumption_wrapper="Game_OneTimeSecrecy_Real",
        right_assumption_wrapper="Game_OneTimeSecrecy_Random",
        reverse_direction=False,
    )
    assert lemma.name == "hop_1_pr"
    assert "<= eps_OneTimeSecrecy" in lemma.statement
    body = "\n".join(lemma.body)
    assert "Game_OneTimeSecrecy_Real(OTP, R1_Adv(A))" in body
    assert "Game_OneTimeSecrecy_Random(OTP, R1_Adv(A))" in body
    assert "OneTimeSecrecy_advantage OTP (R1_Adv(A))" in body
    assert "byequiv" in body
    assert "qed." in body


# --- Multi-oracle Pr lemmas (P4) -------------------------------------------


def _pr_spec() -> pt.MultiOraclePrSpec:
    return pt.MultiOraclePrSpec(
        coupling="(glob GL){1} = (glob GR){2}",
        init_oracle="initialize",
        post_init_oracles=["eval", "chk"],
    )


def test_translate_inlining_hop_pr_multi_oracle_body() -> None:
    """The multi-oracle inlining Pr lemma emits the validated section-2.4 body."""
    lemma = pt.translate_inlining_hop_pr_lemma(
        hop_index=3,
        adversary_type_name="KEM_INDCPA_Adv",
        scheme_module_expr="KEMPRF",
        left_wrapper_name="Game_step_3",
        right_wrapper_name="Game_step_4",
        multi_oracle=_pr_spec(),
    )
    assert lemma.name == "hop_3_pr"
    # The post-init oracles each get a `conseq hop_<i>_<m>` bullet, in order;
    # the init oracle is discharged by the trailing `call hop_<i>_init`.
    assert lemma.body == [
        "byequiv (_: ={glob A} ==> ={res}) => //.",
        "proc.",
        "call (_: (glob GL){1} = (glob GR){2}).",
        "+ conseq hop_3_eval.",
        "+ conseq hop_3_chk.",
        "call hop_3_initialize.",
        "auto.",
        "qed.",
    ]


def test_translate_inlining_hop_pr_single_oracle_unchanged() -> None:
    """Without a multi-oracle spec the legacy single-oracle body is emitted."""
    multi = pt.translate_inlining_hop_pr_lemma(
        hop_index=0,
        adversary_type_name="A_t",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_0",
        right_wrapper_name="Game_step_1",
        multi_oracle=None,
    )
    legacy = pt.translate_inlining_hop_pr_lemma(
        hop_index=0,
        adversary_type_name="A_t",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_0",
        right_wrapper_name="Game_step_1",
    )
    assert multi.body == legacy.body
    assert "call (_: true); first by conseq hop_0." in "\n".join(multi.body)


def test_translate_assumption_hop_pr_multi_oracle_admits_bridge() -> None:
    """The multi-oracle assumption Pr lemma routes its wrapper bridges to a
    guided admit (the differently-named-state coupling is the P5 synthesis
    piece) but keeps the rewrite + advantage-axiom structure intact."""
    lemma = pt.translate_assumption_hop_pr_lemma(
        hop_index=1,
        adversary_type_name="KEM_INDCPA_Adv",
        scheme_module_expr="KEMPRF",
        left_wrapper_name="Game_step_1",
        right_wrapper_name="Game_step_2",
        assumption_name="PRF",
        reduction_adv_name="R1_Adv",
        left_assumption_wrapper="Game_PRF_Real",
        right_assumption_wrapper="Game_PRF_Random",
        reverse_direction=False,
        multi_oracle=_pr_spec(),
    )
    body = "\n".join(lemma.body)
    # The two rewrite bridges are admitted (not silently closed by sim).
    assert sum(1 for line in lemma.body if line.strip() == "admit.") == 2
    assert "sim." not in body
    # The rewrite + axiom application still close the lemma.
    assert "rewrite hL hR." in body
    assert "PRF_advantage KEMPRF (R1_Adv(A))" in body
    assert lemma.body[-1] == "qed."


def test_translate_assumption_hop_pr_single_oracle_unchanged() -> None:
    """Without a multi-oracle spec the legacy assumption body (sim bridges) holds."""
    legacy = pt.translate_assumption_hop_pr_lemma(
        hop_index=1,
        adversary_type_name="A_t",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_1",
        right_wrapper_name="Game_step_2",
        assumption_name="OneTimeSecrecy",
        reduction_adv_name="R1_Adv",
        left_assumption_wrapper="Game_OneTimeSecrecy_Real",
        right_assumption_wrapper="Game_OneTimeSecrecy_Random",
        reverse_direction=False,
    )
    explicit_none = pt.translate_assumption_hop_pr_lemma(
        hop_index=1,
        adversary_type_name="A_t",
        scheme_module_expr="OTP",
        left_wrapper_name="Game_step_1",
        right_wrapper_name="Game_step_2",
        assumption_name="OneTimeSecrecy",
        reduction_adv_name="R1_Adv",
        left_assumption_wrapper="Game_OneTimeSecrecy_Real",
        right_assumption_wrapper="Game_OneTimeSecrecy_Random",
        reverse_direction=False,
        multi_oracle=None,
    )
    assert legacy.body == explicit_none.body
    assert "admit." not in legacy.body
    assert "sim." in "\n".join(legacy.body)


def test_translate_main_theorem_otpsecurelr_shape() -> None:
    """Main theorem statement: bound is sum of eps for assumption hops only."""
    from proof_frog.export.easycrypt import proof_translator as pt
    from proof_frog.export.easycrypt import ec_ast

    hop_kinds = [
        pt.HopKind.INLINING,
        pt.HopKind.ASSUMPTION,
        pt.HopKind.INLINING,
        pt.HopKind.ASSUMPTION,
        pt.HopKind.INLINING,
    ]
    assumption_names_by_hop = {1: "OneTimeSecrecy", 3: "OneTimeSecrecy"}
    lemma = pt.translate_main_theorem(
        adversary_type_name="OneTimeSecrecyLR_Adv",
        scheme_module_expr="OTP",
        first_wrapper_name="Game_step_0",
        last_wrapper_name="Game_step_5",
        hop_kinds=hop_kinds,
        assumption_names_by_hop=assumption_names_by_hop,
        n_hops=5,
    )
    assert isinstance(lemma, ec_ast.ProbLemma)
    assert lemma.name == "main_theorem"
    assert "Pr[Game_step_0(A).main() @ &m : res]" in lemma.statement
    assert "Pr[Game_step_5(A).main() @ &m : res]" in lemma.statement
    assert "<= eps_OneTimeSecrecy + eps_OneTimeSecrecy" in lemma.statement
    body = "\n".join(lemma.body)
    assert "qed." in body


def test_translate_main_theorem_no_assumption_hops_uses_equality() -> None:
    """If there are no assumption hops, the bound is 0 -- emit Pr equality directly."""
    from proof_frog.export.easycrypt import proof_translator as pt

    lemma = pt.translate_main_theorem(
        adversary_type_name="OTPSecure_Adv",
        scheme_module_expr="OTP",
        first_wrapper_name="Game_step_0",
        last_wrapper_name="Game_step_1",
        hop_kinds=[pt.HopKind.INLINING],
        assumption_names_by_hop={},
        n_hops=1,
    )
    assert "=" in lemma.statement
    assert "<=" not in lemma.statement
    assert "eps_" not in lemma.statement
