import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
PROOF_FILES = sorted(
    p for p in REPO_ROOT.glob("**/examples/**/*.proof")
)


@pytest.mark.parametrize(
    "proof_path",
    PROOF_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in PROOF_FILES],
)
def test_proof(proof_path: Path) -> None:
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
