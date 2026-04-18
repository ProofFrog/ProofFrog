"""Unit tests for scheme-instance descriptor collection."""

from __future__ import annotations

from proof_frog import frog_parser
from proof_frog.export.easycrypt import scheme_instances


def test_collect_otp_single_instance() -> None:
    proof = frog_parser.parse_proof_file("examples/joy/Proofs/Ch2/OTPSecure.proof")
    primitive = frog_parser.parse_file("examples/joy/Primitives/SymEnc.primitive")
    scheme = frog_parser.parse_file("examples/joy/Schemes/SymEnc/OTP.scheme")
    insts = scheme_instances.collect(proof, primitive, scheme)
    assert len(insts) == 1
    assert insts[0].let_name == "E"
    assert insts[0].clone_alias == "E_c"
    # OTP(lambda) -> fields concretize via the scheme's field defs, not here
    # (we only see the primitive-level substitution for "SymEnc" instances).
    # OTP's let value is OTP(lambda), whose ctor name is "OTP" -- matches
    # the scheme name, so scheme-level substitution fires.
    assert set(insts[0].concretized_fields.keys()) >= {"Message", "Ciphertext", "Key"}


def test_collect_ces_three_instances() -> None:
    proof = frog_parser.parse_proof_file(
        "examples/joy/Proofs/Ch2/ChainedEncryptionSecure.proof"
    )
    primitive = frog_parser.parse_file("examples/joy/Primitives/SymEnc.primitive")
    scheme = frog_parser.parse_file(
        "examples/joy/Schemes/SymEnc/ChainedEncryption.scheme"
    )
    insts = scheme_instances.collect(proof, primitive, scheme)
    names = [i.let_name for i in insts]
    assert names == ["E1", "E2", "CE"]
    aliases = [i.clone_alias for i in insts]
    assert aliases == ["E1_c", "E2_c", "CE_c"]

    e1 = insts[0]
    # E1 = SymEnc(IntermediateSpace, CiphertextSpace1, KeySpace1)
    # primitive fields: Message=MessageSpace, Ciphertext=CiphertextSpace, Key=KeySpace
    assert e1.concretized_fields["Message"].name == "IntermediateSpace"  # type: ignore[attr-defined]
    assert e1.concretized_fields["Ciphertext"].name == "CiphertextSpace1"  # type: ignore[attr-defined]
    assert e1.concretized_fields["Key"].name == "KeySpace1"  # type: ignore[attr-defined]

    ce = insts[2]
    # CE.Key = E1.Key -> KeySpace1; CE.Message = E2.Message -> MessageSpace
    assert ce.concretized_fields["Key"].name == "KeySpace1"  # type: ignore[attr-defined]
    assert ce.concretized_fields["Message"].name == "MessageSpace"  # type: ignore[attr-defined]
    # CE.Ciphertext = [E1.Ciphertext, E2.Ciphertext] -> ProductType
    ct = ce.concretized_fields["Ciphertext"]
    from proof_frog import frog_ast

    assert isinstance(ct, frog_ast.ProductType)
    assert [t.name for t in ct.types] == [  # type: ignore[attr-defined]
        "CiphertextSpace1",
        "CiphertextSpace2",
    ]
