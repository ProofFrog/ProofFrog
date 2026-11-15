"""The EasyCrypt exporter declines proofs that use event theorems.

An event theorem (``event bad of P(a)``) can be a proof's theorem, an
``assume:`` entry or a ``lemma:`` entry. The exporter has no translation
for identical-until-bad hops or event bounds yet, so such a proof must be
refused up front with a clear message rather than crash later on code that
expects every theorem and assumption to be a game.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proof_frog.export.easycrypt import exporter

REPO_ROOT = Path(__file__).resolve().parents[3]
CFRG = REPO_ROOT / "examples" / "applications" / "cfrg-hybrid-kems" / "proofs"


@pytest.mark.parametrize(
    "rel",
    [
        # the theorem is an event
        "CG/CG_seedbased_TKeyCollisionEvent.proof",
        # an event appears as an assumption or lemma entry
        "CK/CK_seedbased_LEAK_BIND_K_CT_DIFFKEY_std.proof",
    ],
)
def test_event_theorem_proofs_are_declined(rel: str) -> None:
    with pytest.raises(NotImplementedError, match="event theorem"):
        exporter.export_proof_file(str(CFRG / rel))


def test_proofs_without_events_still_export() -> None:
    text = exporter.export_proof_file(
        str(REPO_ROOT / "examples" / "joy" / "Proofs" / "Ch2" / "OTPSecure.proof")
    )
    assert "lemma" in text
