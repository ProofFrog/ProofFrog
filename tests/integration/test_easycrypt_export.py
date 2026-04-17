"""Integration test: export OTPSecure.proof and verify EasyCrypt accepts it."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter


REPO_ROOT = Path(__file__).resolve().parents[2]
OTP_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecure.proof"
OTP_LR_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecureLR.proof"
EC_SCRIPT = REPO_ROOT / "scripts" / "easycrypt.sh"


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


def test_export_otpsecure_produces_nonempty_output() -> None:
    """Smoke test: exporter runs and produces a file with some EC constructs."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    assert "require import" in output
    assert "module" in output
    assert "lemma" in output


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecure_typechecks_in_easycrypt(tmp_path: Path) -> None:
    """End-to-end: exported .ec file must type-check in EasyCrypt."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    ec_file = tmp_path / "otpsecure.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_otpsecurelr_produces_expected_structure() -> None:
    """Smoke test for the reductions/multi-game proof."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    # Two game files -> two oracle module types.
    assert "module type OneTimeSecrecy_Oracle" in output
    assert "module type OneTimeSecrecyLR_Oracle" in output
    # Both game sides per game file.
    assert "module OneTimeSecrecy_Real" in output
    assert "module OneTimeSecrecy_Random" in output
    assert "module OneTimeSecrecyLR_Left" in output
    assert "module OneTimeSecrecyLR_Right" in output
    # Two reductions as parameterized modules.
    assert "module R1" in output
    assert "module R2" in output
    # Inlining hops emit an equiv lemma; assumption hops do not (their
    # two sides are genuinely non-equivalent). Plus one _pr lemma per hop.
    # OTPSecureLR: 3 inlining + 2 assumption hops -> 3 equiv + 5 pr = 8.
    assert output.count("lemma hop_") == 8


@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; cannot run EasyCrypt.",
)
def test_export_otpsecurelr_typechecks_in_easycrypt(tmp_path: Path) -> None:
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    ec_file = tmp_path / "otpsecurelr.ec"
    ec_file.write_text(output)
    result = subprocess.run(
        ["bash", str(EC_SCRIPT), str(ec_file)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"EasyCrypt rejected exported file.\n"
        f"Exported file:\n{output}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}\n"
    )


def test_export_otpsecure_lemma_has_no_admit() -> None:
    """OTPSecure's one hop must be discharged with real tactics."""
    output = exporter.export_proof_file(str(OTP_PROOF))
    assert "admit" not in output, (
        f"OTPSecure export still contains admit:\n{output}"
    )


def test_export_otpsecurelr_no_admit() -> None:
    """OTPSecureLR has 5 hops; after Phase 4a, all are discharged in probability form."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "admit" not in output, (
        f"OTPSecureLR export still contains admit:\n{output}"
    )


def test_export_otpsecurelr_emits_advantage_axiom() -> None:
    """The exported file declares the Style B assumption axiom."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "op eps_OneTimeSecrecy : real." in output
    assert "axiom eps_OneTimeSecrecy_pos" in output
    assert "axiom OneTimeSecrecy_advantage" in output


def test_export_otpsecurelr_emits_pr_lemmas() -> None:
    """One probability corollary per hop (5 hops -> 5 _pr lemmas)."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    # 3 inlining-hop equiv lemmas + 5 _pr lemmas = 8. Assumption hops get
    # no equiv lemma (their two sides are genuinely non-equivalent).
    assert output.count("lemma hop_") == 8
    for i in range(5):
        assert f"lemma hop_{i}_pr" in output


def test_export_otpsecurelr_emits_main_theorem() -> None:
    """The exported file declares a chained main_theorem lemma."""
    output = exporter.export_proof_file(str(OTP_LR_PROOF))
    assert "lemma main_theorem" in output
    # Bound: two assumption hops, each contributing eps_OneTimeSecrecy.
    assert "eps_OneTimeSecrecy + eps_OneTimeSecrecy" in output
    # Endpoints: step_0 (Game_OTSLR_Left) and step_5 (Game_OTSLR_Right).
    assert "Pr[Game_step_0(A).main() @ &m : res]" in output
    assert "Pr[Game_step_5(A).main() @ &m : res] |" in output
