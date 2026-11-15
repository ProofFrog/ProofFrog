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


def test_lemma_bound_inlined() -> None:
    """The lemma's own bound replaces its opaque term in the parent's bound."""
    result = _run_prove("outer.proof")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Adv^DerivedSecurity(G)(A) <= Adv^BaseAssumption(G)(B1)" in result.stdout
    assert "before inlining lemma bounds: Adv^DerivedSecurity(G)(A)" in result.stdout


def test_lemma_with_query_cap_is_refused() -> None:
    """A lemma proven under `calls <= N` does not hold for the parent's
    adversaries in general, so it cannot discharge a lemma entry."""
    result = _run_prove("outer_capped_lemma.proof")
    assert result.returncode != 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "calls <= 1" in result.stdout + result.stderr
