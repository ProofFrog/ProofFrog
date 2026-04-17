"""Unit tests for the EasyCrypt proof translator."""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
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
