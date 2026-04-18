"""Unit tests for the EasyCrypt export TypeCollector."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt.type_collector import TypeCollector


def test_resolve_terminates_on_cyclic_aliases() -> None:
    """Cyclic aliases must not infinite-loop; resolve falls back to the unresolved type."""
    a = frog_ast.Variable("A")
    b = frog_ast.Variable("B")
    tc = TypeCollector(aliases={"A": b, "B": a})
    resolved = tc.resolve(a)
    # Any deterministic, non-looping answer is acceptable; we assert termination.
    assert resolved is not None


def test_abstract_types_short_circuit_resolution() -> None:
    """abstract_types wins over alias resolution so primitive-level types
    stay abstract inside an abstract theory."""
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    tc = TypeCollector(
        aliases={"Key": bs},
        abstract_types={"Key": "key"},
    )
    ec_type = tc.translate_type(frog_ast.Variable("Key"))
    assert ec_type.text == "key"
    assert tc.abstract_types_seen == ["key"]


def test_abstract_distr_records_op_and_emits_decls() -> None:
    tc = TypeCollector(abstract_types={"Ciphertext": "ciphertext"})
    ec_type = tc.translate_type(frog_ast.Variable("Ciphertext"))
    distr = tc.distr_for(ec_type)
    assert distr == "dciphertext"
    decls = tc.emit_abstract()
    names = {getattr(d, "name", None) for d in decls}
    assert "ciphertext" in names
    assert "dciphertext" in names
    assert "dciphertext_ll" in names
    assert "dciphertext_fu" in names


def test_field_access_abstract_lookup() -> None:
    """FieldAccess(E, 'Message') should resolve to abstract 'message'."""
    tc = TypeCollector(abstract_types={"Message": "message"})
    fa = frog_ast.FieldAccess(frog_ast.Variable("E"), "Message")
    ec_type = tc.translate_type(fa)
    assert ec_type.text == "message"


def test_translate_tuple_type() -> None:
    tc = TypeCollector()
    pair = frog_ast.ProductType(
        [
            frog_ast.BitStringType(frog_ast.Variable("lambda")),
            frog_ast.BitStringType(frog_ast.Variable("lambda")),
        ]
    )
    ec = tc.translate_type(pair)
    assert ec.text == "bs_lambda * bs_lambda"


def test_resolve_handles_qualified_field_alias() -> None:
    """Qualified alias key ``E1.key`` resolves FieldAccess(E1, 'key')."""
    aliases: dict[str, frog_ast.Type] = {"E1.key": frog_ast.Variable("KeySpace1")}
    tc = TypeCollector(aliases=aliases, known_abstract_types={"KeySpace1"})
    fa = frog_ast.FieldAccess(frog_ast.Variable("E1"), "key")
    resolved = tc.resolve(fa)
    assert isinstance(resolved, frog_ast.Variable) and resolved.name == "KeySpace1"
    # Full translate-through should also hit the abstract pass-through.
    assert tc.translate_type(fa).text == "KeySpace1"


def test_translate_abstract_variable_type() -> None:
    tc = TypeCollector(known_abstract_types={"KeySpace1"})
    ec = tc.translate_type(frog_ast.Variable("KeySpace1"))
    assert ec.text == "KeySpace1"


def test_resolve_qualified_tuple_ciphertext() -> None:
    """Resolving ``CE.ciphertext`` through aliases yields the EC tuple form."""
    aliases: dict[str, frog_ast.Type] = {
        "CE.ciphertext": frog_ast.ProductType(
            [
                frog_ast.Variable("CiphertextSpace1"),
                frog_ast.Variable("CiphertextSpace2"),
            ]
        )
    }
    known: set[str] = {"CiphertextSpace1", "CiphertextSpace2"}
    tc = TypeCollector(aliases=aliases, known_abstract_types=known)
    fa = frog_ast.FieldAccess(frog_ast.Variable("CE"), "ciphertext")
    ec = tc.translate_type(fa)
    assert ec.text == "CiphertextSpace1 * CiphertextSpace2"
