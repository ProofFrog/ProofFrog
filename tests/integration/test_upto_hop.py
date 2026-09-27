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
    # Reported by the checker at the hop's step, with lines into both sides.
    result = _run_prove("outer_not_iub.proof")
    assert result.returncode != 0, _out(result)
    out = result.stdout + result.stderr
    assert "NotIUB is not identical until bad" in out, _out(result)
    assert "Eq: return values differ (left line 16, right line 33)" in out


def test_lemma_file_must_prove_the_entry() -> None:
    result = _run_prove("outer_wrong_lemma.proof")
    assert result.returncode != 0, _out(result)
    assert (
        "proves 'event bad of NotIUB(S)', not 'event bad of BadGuess(S)'"
        in result.stdout + result.stderr
    ), _out(result)


def test_assumed_event_uses_pair_clause() -> None:
    result = _run_prove("outer_assumed.proof")
    assert result.returncode == 0, _out(result)
    assert "up to bad" in result.stdout
    assert "Advantage bound: Adv^TargetGuess(S)(A) <= count_Eq/|S|" in result.stdout


def test_assumed_event_opaque() -> None:
    result = _run_prove("outer_opaque.proof")
    assert result.returncode == 0, _out(result)
    assert "Pr[bad of BadGuess(S)](B1)" in result.stdout


def test_both_routes_is_checker_error() -> None:
    result = _run_prove("outer_both.proof")
    assert result.returncode != 0, _out(result)
    assert "both" in (result.stdout + result.stderr).lower()


def test_claimed_bound_with_event_atom_verifies() -> None:
    result = _run_prove("outer_claim.proof")
    assert result.returncode == 0, _out(result)
    assert "Claimed bound verified" in result.stdout


def test_claimed_bound_below_event_term_fails() -> None:
    result = _run_prove("outer_claim_low.proof")
    assert result.returncode != 0, _out(result)
    assert "Claimed bound NOT verified" in result.stdout


def test_initialize_event_standalone() -> None:
    result = _run_prove("InitCollisionEvent.proof")
    assert result.returncode == 0, _out(result)
    assert (
        "Pr[bad of InitCollision(S) at Initialize](A) <= 1/|S|" in result.stdout
    ), _out(result)


def test_initialize_event_licenses_upto_hop() -> None:
    result = _run_prove("outer_init.proof")
    assert result.returncode == 0, _out(result)
    assert "up to bad" in result.stdout


def test_initialize_event_rejects_oracle_initialize_call() -> None:
    result = _run_prove("outer_init_bad_placement.proof")
    assert result.returncode != 0, _out(result)
    assert "challenger.Initialize" in result.stdout + result.stderr


def test_lemma_file_must_quantify_over_its_parameters() -> None:
    # The lemma proves the event only for U = BitString<8>.
    result = _run_prove("outer_lemma_concrete.proof")
    assert result.returncode != 0, _out(result)
    assert "does not cover" in result.stdout + result.stderr, _out(result)


def test_lemma_file_must_be_about_the_same_game_file() -> None:
    # The lemma's BadGuess is a different file exported under the same name.
    result = _run_prove("outer_lemma_other_file.proof")
    assert result.returncode != 0, _out(result)
    assert "different file" in result.stdout + result.stderr, _out(result)


def test_event_lemma_bound_inlined_into_parent() -> None:
    result = _run_prove("outer.proof")
    assert result.returncode == 0, _out(result)
    assert "Adv^TargetGuess(S)(A) <= count_Eq/|S|" in result.stdout, _out(result)
    assert "(before inlining lemma bounds: Pr[bad of BadGuess(S)](B1))" in result.stdout


def test_initialize_event_bound_inlined_into_parent() -> None:
    result = _run_prove("outer_init.proof")
    assert result.returncode == 0, _out(result)
    assert "Adv^InitCollision(S)(A) <= 1/|S|" in result.stdout, _out(result)


def test_skip_lemmas_leaves_event_term_opaque() -> None:
    result = _run_prove("outer.proof", "--skip-lemmas")
    assert result.returncode == 0, _out(result)
    assert "Adv^TargetGuess(S)(A) <= Pr[bad of BadGuess(S)](B1)" in result.stdout
