"""Integration tests for up-to-bad hops (proof_frog.upto + engine wiring)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES = Path(__file__).parent / "upto_fixtures"


def _run_prove(proof_file: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(FIXTURES / proof_file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_flag_lemma_standalone() -> None:
    """The flag-game lemma is an ordinary left/right proof and verifies."""
    result = _run_prove("BadGuessFlag.proof")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Proof Succeeded" in result.stdout
    # The reduction's `if (challenger.Eq(c))` is one Eq query per Eq call.
    assert "count_Eq/|S|" in result.stdout


def test_upto_hop_with_lemma() -> None:
    result = _run_prove("outer.proof")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Proof Succeeded" in result.stdout
    assert "upto" in result.stdout
    # The lemma's bound (count_Eq / |S| in the flag game's Eq count) is inlined
    # through the outer reduction, whose Eq forwards one query per call.
    assert "Advantage bound: Adv^TargetGuess(S)(A) <= count_Eq/|S|" in result.stdout
    assert "(before inlining lemma bounds: Adv^BadGuessFlag(S)(B1))" in result.stdout


def test_upto_hop_with_assumed_flag_game() -> None:
    result = _run_prove("outer_assumed.proof")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Proof Succeeded" in result.stdout
    assert "Adv^BadGuessFlag(S)(B1)" in result.stdout


def test_side_flip_without_flag_game_fails_with_hint() -> None:
    result = _run_prove("outer_no_flag.proof")
    assert result.returncode != 0
    assert "Proof Failed" in result.stdout
    assert "identical until bad" in result.stdout


def test_pair_not_identical_until_bad_is_not_licensed() -> None:
    result = _run_prove("outer_wrong_pair.proof")
    assert result.returncode != 0
    assert "Proof Failed" in result.stdout
