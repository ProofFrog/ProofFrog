"""Smoke test for ``make check-tactic-cache`` / the cache-report module.

Runs the reporter on the OTPSecure/OTPSecureLR/CES corpus and asserts
sensible counts: OTPs hit Layer 1 only (used=0, orphan=0, missing=0)
while CES still has open misses today (the Bucket-2 Topological Sorting
admits) and reports them.
"""

from __future__ import annotations

import pathlib

from proof_frog.export.easycrypt_per_transform import cache_report


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


def test_ces_reports_open_misses_without_sidecar() -> None:
    """CES has Bucket-2 admits today; the reporter must surface them."""
    report = cache_report._build_report(PROOF_DIR / "ChainedEncryptionSecure.proof")
    assert report.error is None, report.error
    # Today's baseline: 4 cache-miss diagnostic blocks (3x Topological
    # Sorting + 1x Merge Product Samples). Bucket-2 closures will
    # reduce this; require >0 so the reporter exercises the
    # missing-counter path.
    assert report.missing > 0


def test_cli_main_returns_zero_by_default() -> None:
    """``cache_report`` is a status surface, not a CI gate, by default."""
    rc = cache_report.main(["--examples-dir", str(PROOF_DIR)])
    assert rc == 0
