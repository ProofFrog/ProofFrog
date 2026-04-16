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
    assert "admit" in output


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
    # One admit-bodied lemma per hop; 6 steps -> 5 hops.
    assert output.count("lemma hop_") == 5
    assert output.count("admit") >= 5


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
