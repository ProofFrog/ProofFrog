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


def _emit_text(tc: TypeCollector) -> str:
    """Render a collector's top-level decls to EC source text."""
    return ec_ast.pretty_print(ec_ast.EcFile(requires=[], decls=tc.emit()))


def test_translate_modint_type_name() -> None:
    """Standalone ModInt<q> -> the stdlib ``ZModRing`` clone type ``ModInt_q.zmod``."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    assert ec.text == "ModInt_q.zmod"


def test_modint_distr_for() -> None:
    """A standalone ModInt yields the clone's uniform ``DZmodP.dunifin``."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    assert tc.distr_for(ec) == "ModInt_q.DZmodP.dunifin"


def test_modint_emits_zmodring_clone() -> None:
    """Standalone ModInt emission is a single stdlib ZModRing clone whose
    modulus is bound to the FrogLang expression (ring ops + uniform distr
    derived, no per-type abstract axioms)."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.ModIntType(frog_ast.Variable("q")))
    text = _emit_text(tc)
    # Modulus bound to ``q`` so the ring is genuinely Z_q, not Z_<abstract p>.
    assert "clone ZModP.ZModRing as ModInt_q with op p <- q." in text
    # No abstract op/axiom emission (the stdlib derives these).
    assert "dmodint_q" not in text
    assert "axiom" not in text


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
    """GroupElem<G> -> the stdlib ``CyclicGroup`` clone type ``G.group``."""
    tc = TypeCollector()
    ec = tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    assert ec.text == "G.group"


def test_groupelem_general_emits_cyclicgroup_and_zmodring() -> None:
    """A non-prime GroupElem emits a CyclicGroup clone + a general ZModRing
    exponent clone, and NO prime axiom."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    text = _emit_text(tc)
    assert "clone CyclicGroup as G." in text
    assert "clone ZModP.ZModRing as G_Exp with op p <- G.order." in text
    assert "prime" not in text  # general path: NO prime axiom
    assert "PowZMod" not in text


def test_groupelem_prime_emits_powzmod_and_prime_axiom() -> None:
    """A prime-declaring GroupElem emits the PowZMod field exponent, FDistr,
    and an assumed ``prime <G>.order`` axiom (justified by the requires)."""
    tc = TypeCollector(prime_group_names={"G"})
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    text = _emit_text(tc)
    assert "clone CyclicGroup as G." in text
    assert "axiom G_prime_order : IntDiv.prime G.order." in text
    assert "clone G.PowZMod as G_P with lemma prime_order <- G_prime_order." in text
    assert "clone G_P.FDistr as G_FD." in text
    assert "ZModRing" not in text  # prime path uses the field, not ZModRing


def test_groupelem_clone_precedes_exponent_clone() -> None:
    """The ``clone CyclicGroup as G`` must precede the ``G_Exp`` exponent clone
    (which references ``G.order``)."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    text = _emit_text(tc)
    assert text.index("clone CyclicGroup as G.") < text.index("ZModRing as G_Exp")


def test_group_exponent_modint_aliases_exponent_ring() -> None:
    """``ModInt<G.order>`` aliases the group's cloned exponent ring (no
    independent ZModRing clone)."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.GroupElemType(frog_ast.Variable("G")))
    ec = tc.translate_type(
        frog_ast.ModIntType(frog_ast.FieldAccess(frog_ast.Variable("G"), "order"))
    )
    assert ec.text == "G_Exp.zmod"
    # No standalone ``ModInt_*`` clone for the group order.
    assert "ModInt_" not in _emit_text(tc)
