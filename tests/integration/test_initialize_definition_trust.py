"""An Initialize statement after a possible return need not have run.

``Initialize`` may return early (``if (c) { return true; }``), and every
statement after that return is then skipped: a field keeps its declared
initial value, a Function field is not a random function, a nonzero sample
never happens. Each fixture below is a two-game hop whose games an adversary
distinguishes only through such a skipped statement (or, in ``chal``, a call
made before the sample it relies on), so ``prove`` must fail. The control
moves the sample above the return and must still verify.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES = Path(__file__).parent / "init_return_fixtures"


def _run_prove(proof_file: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(FIXTURES / proof_file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


@pytest.mark.parametrize(
    "proof_file",
    [
        "early.proof",  # InlineSingleUseField / FoldEquivalentReturnBranch
        "early2.proof",
        "cmp.proof",
        "ie.proof",
        "loc.proof",
        "fresh.proof",  # UniqueRFSimplification
        "fresh2.proof",  # FreshInputRFToUniform
        "chal.proof",  # ChallengeExclusionRFToUniform: call before the sample
        "tolet.proof",  # LocalFunctionFieldToLet
        "reidx.proof",  # MapKeyReindex via is_known_nonzero
        "reidx2.proof",  # ... with the nonzero sample under an if
    ],
)
def test_skippable_initialize_statement_not_trusted(proof_file: str) -> None:
    result = _run_prove(proof_file)
    assert "Proof Failed" in result.stdout, result.stdout + result.stderr


def test_sample_before_the_return_still_trusted() -> None:
    result = _run_prove("fresh_control.proof")
    assert "Proof Succeeded" in result.stdout, result.stdout + result.stderr
