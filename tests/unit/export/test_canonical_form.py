"""Tests for the per-transform tactic-cache canonical-form serializer.

These tests pin down the determinism guarantees that the sidecar lookup
depends on: idempotency, mangling consistency, and hoist-counter
determinism. Cache lookup is exact string match, so any nondeterminism
silently demotes every entry to a miss.
"""

from __future__ import annotations

import copy

from proof_frog import frog_ast
from proof_frog.export.easycrypt.canonical_form import (
    canonical_text,
    _normalize_for_ec,
    _module_call_return_type,
)


def _make_game(method: frog_ast.Method) -> frog_ast.Game:
    return frog_ast.Game(("Test", [], [], [method]))


def _make_game_call_in_return() -> frog_ast.Game:
    """Game with one method returning a nested ``E.enc(m)`` call.

    Exercises the hoist pass: the nested call inside the binary
    operation gets hoisted to a fresh ``_r0`` variable.
    """
    method = frog_ast.Method(
        frog_ast.MethodSignature(
            "enc",
            frog_ast.Variable("CiphertextSpace"),
            [frog_ast.Parameter(frog_ast.Variable("MessageSpace"), "m")],
        ),
        frog_ast.Block(
            [
                frog_ast.ReturnStatement(
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.ADD,
                        frog_ast.Variable("m"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("E"), "enc"),
                            [frog_ast.Variable("m")],
                        ),
                    )
                ),
            ]
        ),
    )
    return _make_game(method)


def _make_game_with_invalid_name() -> frog_ast.Game:
    """Game whose local variable has an EC-invalid name (``CE.Enc@k0``)."""
    method = frog_ast.Method(
        frog_ast.MethodSignature("enc", frog_ast.Variable("Ciphertext"), []),
        frog_ast.Block(
            [
                frog_ast.VariableDeclaration(frog_ast.Variable("Key"), "CE.Enc@k0"),
                frog_ast.ReturnStatement(frog_ast.Variable("CE.Enc@k0")),
            ]
        ),
    )
    return _make_game(method)


def test_canonical_text_is_idempotent() -> None:
    """Same AST → same text, byte-for-byte."""
    g = _make_game_call_in_return()
    external = {"E": "SymEnc"}
    method_rt: dict[tuple[str, str], frog_ast.Type] = {
        ("SymEnc", "enc"): frog_ast.Variable("Ciphertext")
    }
    a = canonical_text(copy.deepcopy(g), external, method_rt)
    b = canonical_text(copy.deepcopy(g), external, method_rt)
    assert a == b


def test_canonical_text_does_not_mutate_input() -> None:
    """The caller's AST must remain untouched after canonicalization."""
    g = _make_game_call_in_return()
    snapshot = copy.deepcopy(g)
    canonical_text(g, {"E": "SymEnc"}, {("SymEnc", "enc"): frog_ast.Variable("C")})
    # The local variable count and structure should be unchanged.
    assert len(g.methods[0].block.statements) == len(snapshot.methods[0].block.statements)


def test_canonical_text_mangles_invalid_local_names() -> None:
    """Locals like ``CE.Enc@k0`` are mangled to ``v_CE_Enc_k0``."""
    g = _make_game_with_invalid_name()
    text = canonical_text(g, {}, {})
    assert "CE.Enc@k0" not in text
    assert "v_CE_Enc_k0" in text


def test_canonical_text_hoists_nested_module_calls() -> None:
    """Nested module calls become ``_r0 <@ E.method(...)`` statements."""
    g = _make_game_call_in_return()
    external = {"E": "SymEnc"}
    method_rt: dict[tuple[str, str], frog_ast.Type] = {
        ("SymEnc", "enc"): frog_ast.Variable("Ciphertext")
    }
    text = canonical_text(g, external, method_rt)
    assert "_r0 <@ E.enc(m)" in text


def test_canonical_text_two_invocations_use_distinct_hoist_names() -> None:
    """Two hoists in the same method get ``_r0`` and ``_r1`` deterministically."""
    method = frog_ast.Method(
        frog_ast.MethodSignature(
            "enc",
            frog_ast.Variable("C"),
            [frog_ast.Parameter(frog_ast.Variable("M"), "m")],
        ),
        frog_ast.Block(
            [
                frog_ast.ReturnStatement(
                    frog_ast.Tuple(
                        [
                            frog_ast.FuncCall(
                                frog_ast.FieldAccess(
                                    frog_ast.Variable("E"), "enc"
                                ),
                                [frog_ast.Variable("m")],
                            ),
                            frog_ast.FuncCall(
                                frog_ast.FieldAccess(
                                    frog_ast.Variable("E"), "enc"
                                ),
                                [frog_ast.Variable("m")],
                            ),
                        ]
                    )
                )
            ]
        ),
    )
    g = _make_game(method)
    text = canonical_text(
        g, {"E": "SymEnc"}, {("SymEnc", "enc"): frog_ast.Variable("C")}
    )
    assert "_r0 <@ E.enc(m)" in text
    assert "_r1 <@ E.enc(m)" in text


def test_normalize_for_ec_returns_same_object() -> None:
    """The shared normalization is in-place: returns the input game."""
    g = _make_game_with_invalid_name()
    result = _normalize_for_ec(g, {}, {})
    assert result is g


def test_module_call_return_type_qualifies_product_fields() -> None:
    """A ``ProductType`` return must qualify each field with the instance.

    ``K.encaps`` returns ``[SharedSecret, Ciphertext]`` (a ProductType of
    bare field names). For a *specific* instance ``K`` whose
    ``SharedSecret`` differs from the primary scheme's, the hoisted var's
    declared type must be ``[K.SharedSecret, K.Ciphertext]`` so the
    TypeCollector resolves each component through ``K``'s clone (not the
    primary's). Without qualification the bare ``SharedSecret`` resolves
    against the primary, producing a wrong type (the M4 ``bs_out`` bug).
    """
    call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("K"), "encaps"),
        [frog_ast.Variable("pk")],
    )
    external = {"K": "KEM"}
    method_rt: dict[tuple[str, str], frog_ast.Type] = {
        ("KEM", "encaps"): frog_ast.ProductType(
            [frog_ast.Variable("SharedSecret"), frog_ast.Variable("Ciphertext")]
        )
    }
    result = _module_call_return_type(call, external, method_rt)
    assert isinstance(result, frog_ast.ProductType)
    assert all(isinstance(t, frog_ast.FieldAccess) for t in result.types)
    assert str(result) == "[K.SharedSecret, K.Ciphertext]"
