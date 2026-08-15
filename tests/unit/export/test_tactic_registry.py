"""Unit tests for the transform-keyed tactic registry (R2/R3/E1)."""

from __future__ import annotations

from proof_frog.export.easycrypt import resolution, tactic_registry
from proof_frog.export.easycrypt.transform_buckets import (
    CANNED_TACTIC,
    PARAMETRIC_TACTIC,
)


def test_every_canned_transform_is_registered() -> None:
    for name, body in CANNED_TACTIC.items():
        if body:
            assert tactic_registry.is_registered(name, tactic_registry.ENTRY_CANNED)


def test_every_parametric_transform_is_registered() -> None:
    for name in PARAMETRIC_TACTIC:
        assert tactic_registry.is_registered(
            name, tactic_registry.param_entry_id(name)
        )


def test_unregistered_pair_is_rejected() -> None:
    assert not tactic_registry.is_registered("Alpha Rename", "det-reorder-twin")
    assert not tactic_registry.is_registered("No Such Transform", "canned-static")


def test_conformance_predicate_by_rung() -> None:
    ok = tactic_registry.is_conforming_tag
    # synth rungs need a registered (transform, entry) pair.
    assert ok("synth-static", "Alpha Rename", "canned-static")
    assert not ok("synth-static", "Alpha Rename", None)
    assert not ok("synth-static", None, "canned-static")
    assert not ok("synth-param", "Alpha Rename", "not-an-entry")
    # cached/admit rungs need the transform attribute only.
    assert ok("cached-unguided", "Alpha Rename", None)
    assert ok("admit-unguided", "Alpha Rename", None)
    assert not ok("cached-unguided", None, None)
    assert not ok("admit-guided", None, None)


def test_tag_round_trip_with_and_without_attributes() -> None:
    plain = resolution.tag("synth-static")
    assert plain == "(* resolution: synth-static *)"
    match = resolution.TAG_RE.fullmatch(plain)
    assert match is not None
    assert match.group(1) == "synth-static"
    assert match.group(2) is None and match.group(3) is None

    full = resolution.tag(
        "synth-param", transform="Split Uniform Samples", entry="param:x"
    )
    match = resolution.TAG_RE.fullmatch(full)
    assert match is not None
    assert match.group(1) == "synth-param"
    assert match.group(2) == "Split Uniform Samples"
    assert match.group(3) == "param:x"

    admit = resolution.tag("admit-unguided", transform="Extract RF Calls")
    match = resolution.TAG_RE.fullmatch(admit)
    assert match is not None
    assert match.group(1) == "admit-unguided"
    assert match.group(2) == "Extract RF Calls"
    assert match.group(3) is None
