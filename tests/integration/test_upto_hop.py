"""Integration tests for event theorems and identical-until-bad hops."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES = Path(__file__).parent / "upto_fixtures"


def _run_prove(proof_file: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
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


def _out(result: subprocess.CompletedProcess[str]) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_event_lemma_standalone() -> None:
    result = _run_prove("BadGuessEvent.proof")
    assert result.returncode == 0, _out(result)
    assert "Proof Succeeded" in result.stdout
    assert "Advantage bound: Pr[bad of BadGuess(S)]" in result.stdout, _out(result)
    assert "count_Eq" in result.stdout and "|S|" in result.stdout
    assert "flag unreachable" in result.stdout


def test_event_chain_through_intermediate_game() -> None:
    result = _run_prove("BadGuessEventViaGame.proof")
    assert result.returncode == 0, _out(result)
    assert "count_Eq/|S|" in result.stdout


def test_event_chain_must_track_the_flag() -> None:
    # A reduction that never raises the flag is not a chain for the event.
    result = _run_prove("BadGuessEventLosesFlag.proof")
    assert result.returncode != 0, _out(result)
    assert "Step 1 failed" in result.stdout


def test_event_chain_must_make_flag_unreachable() -> None:
    # Staying in the pair leaves the flag reachable: the terminal hop fails.
    result = _run_prove("BadGuessEventNoChain.proof")
    assert result.returncode != 0, _out(result)
    assert "flag unreachable  FAILED" in result.stdout


def test_upto_hop_by_lemma() -> None:
    result = _run_prove("outer.proof")
    assert result.returncode == 0, _out(result)
    assert "up to bad" in result.stdout and "Proof Succeeded" in result.stdout
    assert "Pr[bad of BadGuess(S)](B1)" in result.stdout, _out(result)


def test_upto_hop_skip_lemmas_stays_upto() -> None:
    result = _run_prove("outer.proof", "--skip-lemmas")
    assert result.returncode == 0, _out(result)
    assert "up to bad" in result.stdout


def test_no_licence_fails_with_hint() -> None:
    result = _run_prove("outer_no_licence.proof")
    assert result.returncode != 0, _out(result)
    assert "event bad of BadGuess" in result.stdout, _out(result)


def test_not_iub_fails_at_the_hop() -> None:
    result = _run_prove("outer_not_iub.proof")
    assert result.returncode != 0, _out(result)
    assert "Lemma verified" in result.stdout, _out(result)
    assert "Step 2 failed" in result.stdout, _out(result)
    assert "Eq" in result.stdout and "line" in result.stdout, _out(result)


def test_lemma_file_must_prove_the_entry() -> None:
    result = _run_prove("outer_wrong_lemma.proof")
    assert result.returncode != 0, _out(result)
    assert (
        "proves 'event bad of NotIUB(S)', not 'event bad of BadGuess(S)'"
        in result.stdout + result.stderr
    ), _out(result)
