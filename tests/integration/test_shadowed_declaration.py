"""A shadowing bare declaration must not float above a read of the name it shadows."""

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "shadowed_declaration_fixtures"
REPO_ROOT = Path(__file__).parents[2]


def test_shadowing_declaration_stays_below_field_read() -> None:
    """Left reads the field, Right the uninitialized local; they differ."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "proof_frog",
            "prove",
            "--sequential",
            str(FIXTURES / "shadowed_field.proof"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Proof Failed!" in result.stdout
