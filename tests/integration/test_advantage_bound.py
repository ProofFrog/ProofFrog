"""Integration tests: the `prove` CLI prints the synthesized advantage bound."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _prove(proof_rel: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(REPO_ROOT / proof_rel)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"proof failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_two_reduction_proof_prints_summed_bound() -> None:
    out = _prove(
        "examples/Proofs/SymEnc/INDCPA$_MultiChal_implies_INDCPA_MultiChal.proof"
    )
    assert "Advantage bound:" in out
    assert "Adv^INDCPA_MultiChal(E)(A) <=" in out
    assert "Adv^INDCPA$_MultiChal(E)(B1) + Adv^INDCPA$_MultiChal(E)(B2)" in out


def test_inductive_proof_reports_unsupported_bound() -> None:
    out = _prove("examples/Proofs/PRG/CounterPRG_PRGSecurity.proof")
    assert "Advantage bound:" in out
    assert "not synthesized" in out
    assert "inductive" in out


def test_helper_bound_vanishes_when_single_call() -> None:
    # INDOT$ declares `calls <= 1`, pinning the query count to 1, so the
    # DistinctSampling birthday term evaluates to 0 and drops out.
    out = _prove("examples/Proofs/SymEnc/SymEncPRF_INDOT$.proof")
    assert "Advantage bound: Adv^INDOT$(E)(A) <= Adv^PRFSecurity(F)(B1)" in out
    assert "Adv^DistinctSampling" not in out


def test_birthday_term_in_derived_oracle_count() -> None:
    # The DistinctSampling reduction samples once per CTXT query, so the
    # birthday bound is derived in the CTXT query count; the two opposite-
    # direction hops sum to a single count_CTXT(count_CTXT-1)/|BitString<F.in>|.
    out = _prove("examples/Proofs/SymEnc/SymEncPRF_INDCPA$_MultiChal.proof")
    assert (
        "Adv^PRFSecurity(F)(B1) + count_CTXT*(count_CTXT - 1)/|BitString<F.in>|"
        in out
    )
    assert "Adv^DistinctSampling" not in out


def test_guessing_term_in_derived_oracle_count() -> None:
    # RandomTargetGuessing's Eq oracle is driven once per Solve query.
    out = _prove("examples/Proofs/Group/DDH_implies_CDH.proof")
    assert "Adv^CDH(G)(A) <= Adv^DDH(G)(B1) + count_Solve/|GroupElem<G>|" in out


def test_initialize_time_sampling_is_constant() -> None:
    # NonzeroSampling's Samp fires once in Initialize (not per adversary query),
    # so each hop contributes 1/order and the two hops sum to 2/order.
    out = _prove("examples/Proofs/Group/GapCDH_implies_GapCDH_NZ.proof")
    assert "2/G.order" in out
    assert "Adv^NonzeroSampling" not in out
