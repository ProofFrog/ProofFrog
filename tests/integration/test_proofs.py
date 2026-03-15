import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
PROOF_FILES = sorted(REPO_ROOT.glob("examples/**/*.proof"))


_KNOWN_LIMITATIONS: set[str] = {
    # Engine cannot move sample from method body to field (one-time equivalence)
    "examples/Proofs/SymEnc/SymEncPRFSimpleOTUC.proof",
}


@pytest.mark.parametrize(
    "proof_path",
    PROOF_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in PROOF_FILES],
)
def test_proof(proof_path: Path) -> None:
    rel = str(proof_path.relative_to(REPO_ROOT))
    if rel in _KNOWN_LIMITATIONS:
        pytest.xfail(f"Known engine limitation: {rel}")
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(proof_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Proof failed: {proof_path.relative_to(REPO_ROOT)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
