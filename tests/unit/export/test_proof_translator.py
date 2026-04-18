"""Unit tests for the EasyCrypt proof translator."""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt import ec_ast
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
    # Scheme param declared first so adversary can reference {-Em}.
    assert adv_axiom.module_args[0].name == "Em"
    assert adv_axiom.module_args[0].module_type == "Scheme"
    assert adv_axiom.module_args[1].name == "A"
    assert adv_axiom.module_args[1].module_type == "OneTimeSecrecy_Adv {-Em}"
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
