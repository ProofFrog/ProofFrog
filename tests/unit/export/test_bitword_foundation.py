"""Unit tests for the BitWord bitstring foundation in the EC exporter.

A ``bs_<w>`` whose width is known and which takes part in a length-consistent
concat triple is emitted as an EC ``BitWord`` clone, its slice/concat ops are
DEFINED through the ``ofword``/``mkword`` bridge, and the round-trip laws become
proved lemmas instead of axioms. The mathematics is validated in
``tests/integration/ec_templates/bitword_slice_concat.ec``; what these tests
pin is the GATING, where a mistake would emit a well-typed falsehood:

* a triple whose component widths do not sum to the result's must NOT get the
  defined-op form (its round-trip laws would then be false lemmas);
* a type aliased to an abstract carrier must keep the carrier's type;
* an export with no word-backed type must stay byte-identical (no clone, no
  ``require BitWord``).
"""

from __future__ import annotations

from typing import Any

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.type_collector import TypeCollector


def _bs(expr: frog_ast.Expression) -> frog_ast.BitStringType:
    return frog_ast.BitStringType(parameterization=expr)


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _sum(*names: str) -> frog_ast.Expression:
    expr: frog_ast.Expression = _var(names[0])
    for name in names[1:]:
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD, expr, _var(name)
        )
    return expr


def _register_triple(tc: TypeCollector, left: str, right: str, whole: list[str]) -> None:
    tc.translate_type(_bs(_var(left)))
    tc.translate_type(_bs(_var(right)))
    tc.translate_type(_bs(_sum(*whole)))


def _named(decls: list[Any], cls: type) -> dict[str, Any]:
    return {d.name: d for d in decls if isinstance(d, cls)}


def test_consistent_triple_is_word_backed_and_proved() -> None:
    """Widths that sum: clone + defined ops + proved laws, no round-trip axioms."""
    tc = TypeCollector()
    _register_triple(tc, "na", "nb", ["na", "nb"])
    tc.register_concat("bs_na", "bs_nb", "bs_na_nb")
    decls = tc.emit()

    clones = {d.alias: d for d in decls if isinstance(d, ec_ast.Clone)}
    assert "BW_bs_na" in clones
    assert clones["BW_bs_na"].source_theory == "BitWord"
    assert clones["BW_bs_na"].op_bindings == [("n", "na")]
    # the clone's own obligation is discharged, so it leaves no hidden axiom
    assert clones["BW_bs_na"].proof_clauses == [("gt0_n", "smt(gt0_na)")]

    types = _named(decls, ec_ast.TypeDecl)
    assert types["bs_na"].definition == "BW_bs_na.word"

    ops = _named(decls, ec_ast.OpDecl)
    assert ops["concat_bs_na_bs_nb_to_bs_na_nb"].definition is not None
    assert ops["slice_bs_na_nb_to_bs_na"].definition is not None

    axioms = _named(decls, ec_ast.Axiom)
    lemmas = _named(decls, ec_ast.ProvedLemma)
    for law in ("slice_concat_left", "slice_concat_right", "concat_slices_id"):
        name = f"{law}_bs_na_bs_nb_bs_na_nb"
        assert name not in axioms, f"{name} should no longer be assumed"
        assert name in lemmas, f"{name} should be derived"
    # the positivity residue is TEXTUALLY VISIBLE, one per atomic width
    assert "gt0_na" in axioms and "gt0_nb" in axioms
    assert tc.needs_bitword


def test_length_mismatch_declines_to_axioms() -> None:
    """A triple whose widths do NOT sum keeps uninterpreted ops + axioms.

    This is the soundness gate: with defined ops the round-trip laws would be
    false, and a false lemma cannot be emitted -- so the honest fallback is the
    satisfiable uninterpreted form.
    """
    tc = TypeCollector()
    tc.translate_type(_bs(_var("na")))
    tc.translate_type(_bs(_var("nb")))
    tc.translate_type(_bs(_var("nc")))  # NOT na + nb
    tc.register_concat("bs_na", "bs_nb", "bs_nc")
    decls = tc.emit()

    assert not [d for d in decls if isinstance(d, ec_ast.Clone)]
    ops = _named(decls, ec_ast.OpDecl)
    assert ops["concat_bs_na_bs_nb_to_bs_nc"].definition is None
    axioms = _named(decls, ec_ast.Axiom)
    assert "slice_concat_left_bs_na_bs_nb_bs_nc" in axioms
    assert not tc.needs_bitword


def test_carrier_alias_is_not_word_backed() -> None:
    """A bitstring unified with an abstract carrier keeps the carrier's type."""
    tc = TypeCollector()
    _register_triple(tc, "na", "nb", ["na", "nb"])
    tc.register_concat("bs_na", "bs_nb", "bs_na_nb")
    tc.register_type_alias("bs_na", "PK1Space")
    decls = tc.emit()

    aliases = {d.alias for d in decls if isinstance(d, ec_ast.Clone)}
    assert "BW_bs_na" not in aliases
    types = _named(decls, ec_ast.TypeDecl)
    assert types["bs_na"].definition == "PK1Space"
    # and the whole triple falls back, since the concat cannot bridge to a word
    ops = _named(decls, ec_ast.OpDecl)
    assert ops["concat_bs_na_bs_nb_to_bs_na_nb"].definition is None


def test_triple_free_type_still_derives_its_distribution() -> None:
    """A width-known type in no concat triple is word-backed anyway.

    Its uniform distribution is the clone's ``DWord.dunifin``, so the
    lossless / funiform / full trio is derived -- three assumed facts removed
    for a positivity residue that is shared per ATOM, not per type.
    """
    tc = TypeCollector()
    tc.translate_type(_bs(_var("na")))
    decls = tc.emit()

    assert tc.needs_bitword
    ops = _named(decls, ec_ast.OpDecl)
    assert ops["dbs_na"].definition == "BW_bs_na.DWord.dunifin"
    lemmas = _named(decls, ec_ast.ProvedLemma)
    axioms = _named(decls, ec_ast.Axiom)
    for suffix in ("ll", "fu", "full"):
        assert f"dbs_na_{suffix}" in lemmas
        assert f"dbs_na_{suffix}" not in axioms


def test_unknown_width_stays_abstract() -> None:
    """A bitstring whose width the exporter never learned cannot be cloned."""
    tc = TypeCollector()
    tc.translate_type(frog_ast.BitStringType())
    decls = tc.emit()
    assert not [d for d in decls if isinstance(d, ec_ast.Clone)]
    assert not tc.needs_bitword
    axioms = _named(decls, ec_ast.Axiom)
    assert "dbs_ll" in axioms


def test_clone_renders_with_proof_clause() -> None:
    """``Clone.proof_clauses`` renders as EC's ``proof <name> by <tactic>``."""
    rendered = ec_ast.pretty_print(
        ec_ast.EcFile(
            requires=["AllCore"],
            decls=[
                ec_ast.Clone(
                    "BitWord",
                    "BW_bs_na",
                    op_bindings=[("n", "na")],
                    proof_clauses=[("gt0_n", "smt(gt0_na)")],
                )
            ],
            abstract_requires=["BitWord"],
        )
    )
    assert "require BitWord." in rendered
    assert "clone BitWord as BW_bs_na with" in rendered
    assert "op n <- na" in rendered
    assert "proof gt0_n by smt(gt0_na)." in rendered
    # the binding line must NOT be terminated when a proof clause follows
    assert "op n <- na," not in rendered
    assert "op n <- na." not in rendered
