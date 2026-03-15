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

# Files with known checker limitations (not type-alias-related).
# These need deeper feature work and are tracked separately.
_KNOWN_LIMITATIONS = {
    # Empty set literal {} — checker can't infer element type
    "examples/Games/DigitalSignature/Security.game",
    "examples/Games/SymEnc/AE.game",
    # Map.values field access on Map types not supported
    "examples/Games/PRP/Security.game",
    "examples/Games/PRP/StrongSecurity.game",
    # Games must have matching parameters (legitimate structural mismatch)
    "examples/Games/KeyAgreement/Security.game",
    # Set parameter used as type — not supported in standalone check
    "examples/Games/Misc/Predict.game",
    # Array field access type resolution for parameterized types
    "examples/Games/SecretSharing/Correctness.game",
    # Malformed scheme (self-referencing assignment, wrong field name)
    "examples/Schemes/SecretSharing/OTP.scheme",
    # Array indexing on Array types not supported in type checker
    "examples/Schemes/SymEnc/OFB.scheme",
}


@pytest.mark.parametrize(
    "check_path",
    CHECK_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in CHECK_FILES],
)
def test_check(check_path: Path) -> None:
    rel = str(check_path.relative_to(REPO_ROOT))
    if rel in _KNOWN_LIMITATIONS:
        pytest.xfail(f"Known checker limitation: {rel}")
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
