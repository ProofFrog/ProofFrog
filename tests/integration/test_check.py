"""Integration tests: run ``check`` on all standalone example files.

Ensures that every .primitive, .scheme, and .game file in examples/
passes type checking on its own, not just when instantiated via a proof.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
CHECK_FILES = sorted(
    f
    for ext in ("**/*.primitive", "**/*.scheme", "**/*.game")
    for f in REPO_ROOT.glob(f"examples/{ext}")
)


@pytest.mark.parametrize(
    "check_path",
    CHECK_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in CHECK_FILES],
)
def test_check(check_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "check", str(check_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Check failed: {check_path.relative_to(REPO_ROOT)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
