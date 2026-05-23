import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent

# WIP proofs with intentionally failing steps (need engine features not yet
# implemented, e.g. identical-until-bad).
_WIP_PROOFS = {"UG-KEM-CCA-SDH.proof"}

# Deduplicate by resolved path so symlinks (e.g. extras/examples/examples ->
# ../../examples) don't cause the same proof to run twice.
_seen: set[Path] = set()
PROOF_FILES: list[Path] = []
for _p in sorted(REPO_ROOT.glob("**/examples/**/*.proof")):
    if _p.name in _WIP_PROOFS:
        continue
    _resolved = _p.resolve()
    if _resolved in _seen:
        continue
    _seen.add(_resolved)
    PROOF_FILES.append(_p)


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
