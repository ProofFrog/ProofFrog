"""Phase A.1: the per-proof prime-order ``requires`` gate on TypeCollector.

A proof that declares ``requires <group>.order is prime;`` gets the prime
group emission path (PowZMod/ZModField); every other proof gets the general
CyclicGroup/ZModRing path. The exporter threads the declaring group names
into ``TypeCollector`` so ``emit`` can branch.
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt.exporter import _prime_group_names
from proof_frog.export.easycrypt.type_collector import TypeCollector


def test_typecollector_records_prime_groups() -> None:
    tc = TypeCollector(prime_group_names={"G"})
    assert tc.is_prime_group("G") is True
    assert tc.is_prime_group("H") is False


def test_typecollector_defaults_to_no_prime_groups() -> None:
    tc = TypeCollector()
    assert tc.is_prime_group("G") is False


def test_prime_group_names_extracts_declaring_group() -> None:
    """``HashedElGamalKEM_INDCCA`` declares ``G.order is prime;`` -> {"G"}."""
    proof = frog_parser.parse_file("examples/Proofs/KEM/HashedElGamalKEM_INDCCA.proof")
    assert isinstance(proof, frog_ast.ProofFile)
    assert _prime_group_names(proof) == {"G"}


def test_prime_group_names_empty_for_non_declaring_proof() -> None:
    """``DDH_implies_CDH`` is general-cyclic (no prime requires) -> empty."""
    proof = frog_parser.parse_file("examples/Proofs/Group/DDH_implies_CDH.proof")
    assert isinstance(proof, frog_ast.ProofFile)
    assert _prime_group_names(proof) == set()
