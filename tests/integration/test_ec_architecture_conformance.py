"""The architecture conformance gate (enforcement contract E2).

Every micro-lemma closure the exporter emits must carry a provenance-
tagged resolution comment — ``(* resolution: <rung> transform="..."
entry="..." *)`` — whose ``(transform, entry)`` pair is registered in
:mod:`proof_frog.export.easycrypt.tactic_registry`. A ``synth-*``
closure with no registered pair is exactly the failure mode the
ratified architecture forbids: a tactic chosen by program shape with
the transform name out of the loop.

The single-oracle chain conforms today and must stay conforming. The
multi-oracle leg dispatcher is not yet wired through the registry; its
test is ``xfail(strict=True)`` so the suite stays green now and fails
loudly the moment the rewiring lands — at which point the marker comes
off and the gate covers both paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter, resolution, tactic_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
MODOTP_INDOT_PROOF = REPO_ROOT / "examples" / "Proofs" / "SymEnc" / "ModOTP_INDOT.proof"
OTP_SECURE_PROOF = REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecure.proof"
GENERIC_HON_PK_PROOF = (
    REPO_ROOT
    / "examples"
    / "applications"
    / "cfrg-hybrid-kems"
    / "proofs"
    / "Generic"
    / "LEAK_implies_HON_BIND_K_PK.proof"
)

_LEMMA_RE = re.compile(r"^\s*(?:local )?lemma (\w+)")


def _micro_tags(ec_text: str) -> list[tuple[str, str, str | None, str | None]]:
    """Collect ``(lemma, rung, transform, entry)`` for micro-lemma tags."""
    current: str | None = None
    tags: list[tuple[str, str, str | None, str | None]] = []
    for line in ec_text.splitlines():
        if lemma_match := _LEMMA_RE.match(line):
            current = lemma_match.group(1)
            continue
        if tag_match := resolution.TAG_RE.search(line):
            if current is not None and current.startswith("micro_"):
                tags.append(
                    (
                        current,
                        tag_match.group(1),
                        tag_match.group(2),
                        tag_match.group(3),
                    )
                )
    return tags


def _assert_conforming(proof_path: Path, minimum_micros: int) -> None:
    output = exporter.export_proof_file(str(proof_path))
    tags = _micro_tags(output)
    assert len(tags) >= minimum_micros, (
        f"selector found only {len(tags)} micro tags in {proof_path.name}; "
        "the lemma-name or tag pattern has drifted"
    )
    violations = [
        (lemma, rung, transform, entry)
        for lemma, rung, transform, entry in tags
        if not tactic_registry.is_conforming_tag(rung, transform, entry)
    ]
    assert not violations, (
        f"{len(violations)} of {len(tags)} micro closures in "
        f"{proof_path.name} are not registry-conforming; first few: "
        f"{violations[:5]}"
    )


def test_single_oracle_micros_conform() -> None:
    """ModOTP_INDOT: every single-oracle micro closure is registered."""
    _assert_conforming(MODOTP_INDOT_PROOF, minimum_micros=20)


def test_single_oracle_textbook_micros_conform() -> None:
    """OTPSecure: the textbook chain is registry-conforming too."""
    _assert_conforming(OTP_SECURE_PROOF, minimum_micros=5)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "the multi-oracle leg dispatcher is not yet wired through the "
        "tactic registry (architecture-pinning plan, Phase 3); when the "
        "rewiring lands this xfail flips loudly and the marker comes off"
    ),
)
def test_multi_oracle_micros_conform() -> None:
    """Generic LEAK=>HON PK: multi-oracle micros must eventually conform."""
    _assert_conforming(GENERIC_HON_PK_PROOF, minimum_micros=20)
