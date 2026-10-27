"""A set-literal comparison must not read as a comparison of its elements."""

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "set_literal_fixtures"
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


def test_return_after_false_set_comparison_is_kept() -> None:
    """Remove unreachable blocks of code read ``({3} \\ 3) == {t, t}`` as
    ``t == t`` and deleted Left's ``return false``."""
    result = _prove("set_comparison.proof")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    # Pin the failure to the equivalence hop's `Read` method, so a parse or
    # type error (or a different step failing) cannot satisfy the test.
    assert "Step 1 failed: SetComparison(S).Left -> SetComparison(S).Right" in (
        result.stdout
    ), output
    assert "Method 'Read' differs" in result.stdout, output
    assert "Proof Failed! (1 step(s) failed: 1)" in result.stdout, output


def test_set_equality_is_not_last_elements_equal() -> None:
    """The Z3 residual check read ``{a, b} == {c, b}`` as ``c == b``."""
    result = _prove("set_equality.proof")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert (
        "Step 1 failed: SetEquality(lambda).Left -> SetEquality(lambda).Right"
        in result.stdout
    ), output
    assert "Method 'O' differs" in result.stdout, output
    assert "Proof Failed! (1 step(s) failed: 1)" in result.stdout, output
