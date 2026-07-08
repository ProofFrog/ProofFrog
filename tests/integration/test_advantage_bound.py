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
