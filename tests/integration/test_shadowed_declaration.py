"""A shadowing bare declaration must not float above a read of the name it shadows."""

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "shadowed_declaration_fixtures"
REPO_ROOT = Path(__file__).parents[2]


def _prove(proof_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "proof_frog",
            "prove",
            "--sequential",
            str(FIXTURES / proof_name),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_shadowing_declaration_stays_below_field_read() -> None:
    """Left reads the field, Right the uninitialized local; they differ."""
    result = _prove("shadowed_field.proof")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Proof Failed!" in result.stdout


def test_shadowing_map_declaration_stays_below_field_read() -> None:
    """The same hole with no unassigned read on either side: the shadowing
    local is a map, empty once declared, so Right's membership test is a
    well-defined ``false`` where Left's (on the field) is ``true``."""
    result = _prove("shadowed_map_field.proof")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Proof Failed!" in result.stdout


def test_reads_above_shadowing_declaration_still_reorder() -> None:
    """Sound twin: the field read and an independent draw trade places, both
    above the shadowing declaration. The games are equal and still verify."""
    result = _prove("shadowed_map_field_control.proof")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Proof Succeeded!" in result.stdout
