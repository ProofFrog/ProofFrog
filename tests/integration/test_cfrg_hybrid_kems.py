"""CFRG hybrid-KEM export regression gate.

The short-term EasyCrypt-export deliverable is to drive every proof under
``examples/applications/cfrg-hybrid-kems/`` to clean EC (see the project
MAP). While the security/binding layer is still in progress, these tests
lock in the part that is *already* clean — the eight ``*_Correctness``
proofs — so that exporter churn aimed at the security layer cannot silently
regress the correctness baseline.

Two gates:

* a fast, Docker-free gate asserting each correctness proof still exports
  with zero ``admit.`` (the inner-loop signal); and
* a ``slow`` + Docker-gated gate asserting each still type-checks in
  EasyCrypt end-to-end (the full clean guarantee).

Per-proof status for the whole 46-proof set is tracked by the dashboard
(``extras/scripts/easycrypt_dashboard.py``; ``--scope cfrg`` for a fast CFRG
view), not enumerated here — that would duplicate a generated source of
truth and rot as the security layer lands.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter

REPO_ROOT = Path(__file__).resolve().parents[2]
CFRG_ROOT = REPO_ROOT / "examples" / "applications" / "cfrg-hybrid-kems" / "proofs"
EC_SCRIPT = REPO_ROOT / "scripts" / "easycrypt.sh"

# The clean baseline: the CFRG correctness proofs, discovered by glob so a
# newly-added framework is picked up automatically. The count assert guards
# against a silent drop (a rename/move that makes the glob miss them).
CFRG_CORRECTNESS_PROOFS = sorted(CFRG_ROOT.glob("*/*_Correctness.proof"))
EXPECTED_CORRECTNESS_COUNT = 8


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def test_cfrg_correctness_baseline_is_discovered() -> None:
    """All eight CFRG correctness proofs are present.

    If this fails, the glob no longer matches the correctness layer (a
    rename/move), so the regression gate below would silently cover nothing.
    """
    assert len(CFRG_CORRECTNESS_PROOFS) == EXPECTED_CORRECTNESS_COUNT, (
        f"Expected {EXPECTED_CORRECTNESS_COUNT} CFRG *_Correctness proofs under "
        f"{CFRG_ROOT.relative_to(REPO_ROOT)}, found "
        f"{[p.name for p in CFRG_CORRECTNESS_PROOFS]}."
    )


@pytest.mark.parametrize(
    "proof_path",
    CFRG_CORRECTNESS_PROOFS,
    ids=[p.stem for p in CFRG_CORRECTNESS_PROOFS],
)
def test_cfrg_correctness_exports_admit_free(proof_path: Path) -> None:
    """Each CFRG correctness proof exports with zero admits (Docker-free).

    A guided/admit fallback creeping into the correctness layer would show
    up here immediately, without needing an EasyCrypt run.
    """
    output = exporter.export_proof_file(str(proof_path))
    n_admits = output.count("admit.")
    assert n_admits == 0, (
        f"{proof_path.name} exported with {n_admits} admit(s); the CFRG "
        f"correctness clean baseline has regressed."
    )


@pytest.mark.slow
@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
@pytest.mark.parametrize(
    "proof_path",
    CFRG_CORRECTNESS_PROOFS,
    ids=[p.stem for p in CFRG_CORRECTNESS_PROOFS],
)
def test_cfrg_correctness_typechecks_in_easycrypt(
    proof_path: Path, tmp_path: Path
) -> None:
    """Each CFRG correctness proof type-checks in EasyCrypt with 0 admits.

    The full clean guarantee. Marked ``slow`` — the seedbased combiners are
    large multi-hop ``.ec`` files that take minutes to compile; deselect with
    ``-m 'not slow'`` for the fast inner loop.
    """
    output = exporter.export_proof_file(str(proof_path))
    assert (
        "admit." not in output
    ), f"{proof_path.name} export contains admit; clean baseline regressed."
    ec_file = tmp_path / f"{proof_path.stem}.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected {proof_path.name} (exit {result.returncode}); "
        f"the CFRG correctness clean baseline has regressed.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout[-2000:]}"
    )
