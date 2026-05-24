"""Regression tests for the per-transform bucket map.

Catches name drift between the engine's transform names and the keys in
``TRANSFORM_BUCKET`` / ``CANNED_TACTIC`` / ``PARAMETRIC_TACTIC``. A
mismatch silently demotes a canned-tactic transform to the default
``Bucket.OPEN`` (admit), which was the root cause of multiple "phantom
admits" surfaced during stress-testing on
``ChainedEncryptionSecure.proof``.
"""

from __future__ import annotations

from proof_frog.export.easycrypt.transform_buckets import (
    CANNED_TACTIC,
    PARAMETRIC_TACTIC,
    TRANSFORM_BUCKET,
)
from proof_frog.transforms.pipelines import CORE_PIPELINE, STANDARDIZATION_PIPELINE


def _engine_transform_names() -> set[str]:
    return {p.name for p in CORE_PIPELINE + STANDARDIZATION_PIPELINE}


def test_transform_bucket_keys_match_engine_names() -> None:
    engine = _engine_transform_names()
    unknown = sorted(set(TRANSFORM_BUCKET) - engine)
    assert not unknown, (
        f"TRANSFORM_BUCKET has keys not present as engine transform names: "
        f"{unknown}. Mismatched keys silently fall through to Bucket.OPEN."
    )


def test_canned_tactic_keys_match_engine_names() -> None:
    engine = _engine_transform_names()
    unknown = sorted(set(CANNED_TACTIC) - engine)
    assert not unknown, (
        f"CANNED_TACTIC has keys not present as engine transform names: "
        f"{unknown}. Mismatched keys produce admit instead of the canned "
        f"tactic body."
    )


def test_parametric_tactic_keys_match_engine_names() -> None:
    engine = _engine_transform_names()
    unknown = sorted(set(PARAMETRIC_TACTIC) - engine)
    assert not unknown, (
        f"PARAMETRIC_TACTIC has keys not present as engine transform names: "
        f"{unknown}."
    )


def test_canned_tactic_keys_are_classified_canned() -> None:
    """A transform with a canned tactic body must also be classified CANNED."""
    for name in CANNED_TACTIC:
        bucket = TRANSFORM_BUCKET.get(name)
        assert bucket is not None, f"{name!r} has a canned tactic but no bucket entry."
        assert bucket.value == "canned", (
            f"{name!r} has a canned tactic but is classified as "
            f"{bucket.value!r} in TRANSFORM_BUCKET."
        )
