"""Integration tests: the ``prove`` CLI checks a proof's claimed ``bound:``.

Each test splices a ``bound:`` clause into a real proof at runtime (writing a
temp file next to the original so its relative imports still resolve), so the
example proofs themselves are left unchanged.
"""

import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _prove_with_bound(proof_rel: str, claim: str, *, skip_bound: bool = False):
    """Run ``prove`` on *proof_rel* with ``bound: <claim>;`` inserted."""
    source = (REPO_ROOT / proof_rel).read_text()
    marker = "\ngames:"
    index = source.index(marker)
    spliced = source[:index] + f"\nbound:\n  {claim};\n" + source[index:]

    original = REPO_ROOT / proof_rel
    temp = original.with_name(f"__tmp_bound_{original.stem}_{uuid.uuid4().hex}.proof")
    temp.write_text(spliced)
    command = [sys.executable, "-m", "proof_frog", "prove"]
    if skip_bound:
        command.append("--skip-bound")
    command.append(str(temp))
    try:
        return subprocess.run(
            command, cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
    finally:
        temp.unlink()


_INDCPA_PROOF = "examples/Proofs/SymEnc/SymEncPRF_INDCPA$_MultiChal.proof"
_INDCPA_EXACT = (
    "advantage(PRFSecurity(F) compose R_PRF(E, F))"
    " + count_CTXT * (count_CTXT - 1) / |BitString<F.in>|"
)


def test_exact_claim_verified() -> None:
    result = _prove_with_bound(_INDCPA_PROOF, _INDCPA_EXACT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Claimed bound verified" in result.stdout


def test_too_tight_claim_fails_proof() -> None:
    # Dropping the birthday term makes the claim too small; the proof fails.
    result = _prove_with_bound(
        _INDCPA_PROOF, "advantage(PRFSecurity(F) compose R_PRF(E, F))"
    )
    assert result.returncode != 0
    assert "Claimed bound NOT verified" in result.stdout


def test_skip_bound_does_not_fail_on_unverified_claim() -> None:
    result = _prove_with_bound(
        _INDCPA_PROOF,
        "advantage(PRFSecurity(F) compose R_PRF(E, F))",
        skip_bound=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Claimed bound NOT verified" in result.stdout
    assert "Proof Succeeded" in result.stdout


def test_loose_claim_verified() -> None:
    # A deliberately looser constant is still a valid upper bound.
    result = _prove_with_bound(
        _INDCPA_PROOF,
        "advantage(PRFSecurity(F) compose R_PRF(E, F))"
        " + count_CTXT ^ 2 / |BitString<F.in>|",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Claimed bound verified" in result.stdout


def test_ddh_derived_count_claim_verified() -> None:
    result = _prove_with_bound(
        "examples/Proofs/Group/DDH_implies_CDH.proof",
        "advantage(DDH(G) compose R(G)) + count_Solve / |GroupElem<G>|",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Claimed bound verified" in result.stdout


def test_undeclared_reduction_rejected_at_typecheck() -> None:
    result = _prove_with_bound(
        _INDCPA_PROOF, "advantage(PRFSecurity(F) compose R_NOPE(E, F))"
    )
    assert result.returncode != 0
    assert "undeclared reduction" in (result.stdout + result.stderr)
