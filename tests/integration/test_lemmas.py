"""Integration tests for the lemma feature."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES = Path(__file__).parent / "lemma_fixtures"


def _run_prove(proof_file: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Run the prove command on a fixture proof file."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "proof_frog",
            "prove",
            *extra_args,
            str(FIXTURES / proof_file),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_lemma_proof_standalone() -> None:
    """The lemma proof file should work as a standalone proof."""
    result = _run_prove("lemma_proof.proof")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Proof Succeeded" in result.stdout


def test_proof_with_lemma_succeeds() -> None:
    """A proof using a verified lemma should succeed."""
    result = _run_prove("outer.proof")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Lemma verified" in result.stdout
    assert "Proof Succeeded" in result.stdout


def test_proof_with_skip_lemmas() -> None:
    """--skip-lemmas should skip verification but still succeed."""
    result = _run_prove("outer.proof", "--skip-lemmas")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "skipped" in result.stdout
    assert "Proof Succeeded" in result.stdout


def test_proof_with_failing_lemma() -> None:
    """A proof whose lemma fails verification should fail."""
    result = _run_prove("outer_bad_lemma.proof")
    assert result.returncode != 0, (
        f"Expected failure but got success.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_failing_lemma_skipped_still_succeeds() -> None:
    """--skip-lemmas should trust even a broken lemma and succeed."""
    result = _run_prove("outer_bad_lemma.proof", "--skip-lemmas")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "skipped" in result.stdout
    assert "Proof Succeeded" in result.stdout
