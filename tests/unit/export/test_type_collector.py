"""Unit tests for the EasyCrypt export TypeCollector."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
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


def test_translate_bool_type() -> None:
    """BoolType maps to EC's built-in ``bool``."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.BoolType())
    assert ec.text == "bool"


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


def test_translate_nested_tuple_parenthesizes_inner_products() -> None:
    # A FrogLang ``[[A, B], [C, D, E]]`` is a *pair* whose elements are
    # themselves tuples (``(A * B) * (C * D * E)``), not a flat 5-tuple.
    # Each product-typed component must be parenthesized so the emitted
    # EC type matches the nested value expressions / ``.`i`` projections
    # the rest of the export renders (the KEMCombiner KeyGen-result shape).
    tc = TypeCollector()
    nested = frog_ast.ProductType(
        [
            frog_ast.ProductType(
                [
                    frog_ast.BitStringType(frog_ast.Variable("a")),
                    frog_ast.BitStringType(frog_ast.Variable("b")),
                ]
            ),
            frog_ast.ProductType(
                [
                    frog_ast.BitStringType(frog_ast.Variable("c")),
                    frog_ast.BitStringType(frog_ast.Variable("d")),
                    frog_ast.BitStringType(frog_ast.Variable("e")),
                ]
            ),
        ]
    )
    ec = tc.translate_type(nested)
    assert ec.text == "(bs_a * bs_b) * (bs_c * bs_d * bs_e)"


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


def test_translate_int_type() -> None:
    """IntType maps to EC's built-in ``int``."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.IntType())
    assert ec.text == "int"


def test_translate_modint_type_name() -> None:
    """ModInt<q> registers as an abstract ``modint_q`` type."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    assert ec.text == "modint_q"


def test_modint_distr_for() -> None:
    """A registered ModInt type yields a ``dmodint_q`` distribution."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    assert tc.distr_for(ec) == "dmodint_q"


def test_modint_emits_group_foundation() -> None:
    """ModInt emission carries a uniform distribution and an additive group
    (add/sub ops + round-trip + commutativity axioms)."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    names = {getattr(d, "name", None) for d in tc.emit()}
    for expected in (
        "modint_q",
        "dmodint_q",
        "dmodint_q_ll",
        "dmodint_q_fu",
        "dmodint_q_full",
        "add_q",
        "sub_q",
        "add_q_sub",
        "sub_q_add",
        "add_q_comm",
    ):
        assert expected in names, f"missing {expected}"


def test_modint_name_canonicalizes_modulus() -> None:
    """Arithmetically-equivalent moduli collapse to one EC type name."""
    tc = TypeCollector()
    a = tc.translate_type(
        frog_ast.ModIntType(
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.Integer(2),
                frog_ast.Variable("q"),
            )
        )
    )
    b = tc.translate_type(
        frog_ast.ModIntType(
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY,
                frog_ast.Variable("q"),
                frog_ast.Integer(2),
            )
        )
    )
    assert a.text == b.text


def _function_type() -> frog_ast.FunctionType:
    return frog_ast.FunctionType(
        frog_ast.BitStringType(parameterization=frog_ast.Variable("a")),
        frog_ast.BitStringType(parameterization=frog_ast.Variable("b")),
    )


def test_translate_function_type_is_arrow() -> None:
    """Function<A, B> translates to EC's native arrow type ``A -> B``."""
    tc = TypeCollector()
    ec = tc.translate_type(_function_type())
    assert ec.text == "bs_a -> bs_b"


def test_function_distr_for() -> None:
    """A sampled random function yields the uniform function-space distr."""
    tc = TypeCollector()
    ec = tc.translate_type(_function_type())
    assert tc.distr_for(ec) == "dfun_bs_a_to_bs_b"


def test_function_emits_foundation_after_bitstring_types() -> None:
    """Function emission carries a uniform function-space distribution plus
    lossless/funiform/full axioms, declared *after* the domain/codomain
    bitstring types so the arrow's operands are in scope."""
    tc = TypeCollector()
    tc.translate_type(_function_type())
    ordered = [getattr(d, "name", None) for d in tc.emit()]
    for expected in (
        "dfun_bs_a_to_bs_b",
        "dfun_bs_a_to_bs_b_ll",
        "dfun_bs_a_to_bs_b_fu",
        "dfun_bs_a_to_bs_b_full",
    ):
        assert expected in ordered, f"missing {expected}"
    # The bitstring types must precede the function distribution op.
    assert ordered.index("bs_a") < ordered.index("dfun_bs_a_to_bs_b")
    assert ordered.index("bs_b") < ordered.index("dfun_bs_a_to_bs_b")


def test_translate_groupelem_type_name() -> None:
    """GroupElem<G> registers as an abstract ``groupelem_G`` type."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    assert ec.text == "groupelem_G"


def test_groupelem_emits_multiplicative_foundation() -> None:
    """GroupElem emission carries generator/identity constants, mul/div group
    ops, and an exp op over the exponent ring ModInt<G.order>."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    names = {getattr(d, "name", None) for d in tc.emit()}
    for expected in (
        "groupelem_G",
        "generator_G",
        "identity_G",
        "mul_G",
        "div_G",
        "exp_G",
        # the exponent ring is auto-registered
        "modint_G_order",
    ):
        assert expected in names, f"missing {expected}"


def test_groupelem_exp_declared_after_exponent_ring() -> None:
    """The exp op (groupelem -> modint -> groupelem) must follow its modint
    exponent type so the signature is in scope."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    ordered = [getattr(d, "name", None) for d in tc.emit()]
    assert ordered.index("modint_G_order") < ordered.index("exp_G")


def test_groupelem_has_no_axioms() -> None:
    """The GroupElem ops are uninterpreted -- no group-law axioms are emitted
    (the algebraic chain micro-lemmas are out of the type foundation's scope,
    and emitting unjustified axioms would enlarge the TCB)."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    axioms = [
        getattr(d, "name", "")
        for d in tc.emit()
        if isinstance(d, ec_ast.Axiom)
    ]
    group_axioms = [a for a in axioms if a.endswith(("_G",)) and "modint" not in a]
    assert not group_axioms, f"unexpected GroupElem axioms: {group_axioms}"


def test_modint_ring_ops_gated_on_use() -> None:
    """ModInt ring ``mmul``/``mzero`` are only emitted when actually rendered;
    a purely additive ModInt keeps just add/sub."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    names = {getattr(d, "name", None) for d in tc.emit()}
    assert "mmul_q" not in names
    assert "mzero_q" not in names
    # After noting use, both appear with their soundness axioms.
    tc.note_modint_mul(ec)
    tc.note_modint_zero(ec)
    names = {getattr(d, "name", None) for d in tc.emit()}
    for expected in ("mmul_q", "mmul_q_comm", "mzero_q", "sub_q_self"):
        assert expected in names, f"missing {expected}"
