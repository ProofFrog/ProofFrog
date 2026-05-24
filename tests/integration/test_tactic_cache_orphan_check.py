"""Smoke test for ``make check-tactic-cache`` / the cache-report module.

Runs the reporter on the OTPSecure/OTPSecureLR/CES corpus and asserts
sensible counts: OTPs hit Layer 1 only (used=0, orphan=0, missing=0);
CES exercises the cache-hit path with sidecar entries for both
Topological Sorting and Merge Product Samples (used>0, missing=0).
"""

from __future__ import annotations

import pathlib

from proof_frog.export.easycrypt import cache_report


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PROOF_DIR = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2"


def test_otpsecure_has_no_cache_misses() -> None:
    """OTPSecure should close every micro-lemma in Layer 1."""
    report = cache_report._build_report(PROOF_DIR / "OTPSecure.proof")
    assert report.error is None, report.error
    assert report.missing == 0
    assert report.used == 0
    assert report.orphan == 0


def test_otpsecurelr_has_no_cache_misses() -> None:
    """OTPSecureLR's per-transform export hits Layer 1 only."""
    report = cache_report._build_report(PROOF_DIR / "OTPSecureLR.proof")
    assert report.error is None, report.error
    assert report.missing == 0


def test_ces_sidecar_is_complete() -> None:
    """CES's sidecar covers every interactive micro-lemma."""
    report = cache_report._build_report(PROOF_DIR / "ChainedEncryptionSecure.proof")
    assert report.error is None, report.error
    # Exercises the cache-hit path: 3x Topological Sorting +
    # 1x Merge Product Samples entries, all picked up by the
    # exporter and zero outstanding misses.
    assert report.used > 0
    assert report.missing == 0
    assert report.orphan == 0


def test_cli_main_returns_zero_by_default() -> None:
    """``cache_report`` is a status surface, not a CI gate, by default."""
    rc = cache_report.main(["--examples-dir", str(PROOF_DIR)])
    assert rc == 0
