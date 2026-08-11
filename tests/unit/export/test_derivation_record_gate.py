"""Phase-4 Decision 4: an entry is inadmissible without a derivation record.

Douglas's ruling (2026-08-11) is GRANDFATHER: the entries that predate the
requirement stay admissible, and every entry created after it must carry the
record. The dividing line implemented here is the entry's own ``added`` date,
not the presence of a record field -- keying it on "has no ``derived_on``"
would let a new record-free entry grandfather itself, which is the loophole
the rule exists to close.
"""

import pathlib

from proof_frog.export.easycrypt.tactic_cache import (
    RECORD_REQUIRED_FROM,
    CacheEntry,
    TacticCache,
)

INHERITED = CacheEntry(
    transform="Inline Local Tuple Literal",
    game_before="before",
    game_after="after",
    tactic="proc. auto.",
    added="2026-06-14",
)


def _cache(*entries: CacheEntry) -> TacticCache:
    return TacticCache(entries=list(entries))


def _found(cache: TacticCache) -> bool:
    return cache.lookup("Inline Local Tuple Literal", "before", "after") is not None


def test_inherited_entry_stays_admissible() -> None:
    assert _found(_cache(INHERITED))


def test_new_entry_without_a_record_is_refused() -> None:
    """The whole point of the rule: a tactic that ran is not evidence that it
    did work, so an entry added after the requirement must say what was
    falsified and what EasyCrypt answered."""
    new = CacheEntry(**{**vars(INHERITED), "added": RECORD_REQUIRED_FROM})
    assert not _found(_cache(new))


def test_new_entry_with_a_full_record_is_admissible() -> None:
    new = CacheEntry(
        **{
            **vars(INHERITED),
            "added": "2026-09-01",
            "derived_on": "CG_expanded_LEAK_BIND_K_PK hop_2 | EC r2026 | abc1234",
            "negative_control": "dropped the field9 conjunct -> cannot prove goal",
            "refuted": "sim alone (leaves the goal open)",
            "scope_note": "keyed on the masked changed region only",
        }
    )
    assert _found(_cache(new))


def test_partial_record_is_refused() -> None:
    """Every mandatory field is mandatory; the negative control is the one
    that carries the weight, so a record missing it is not a record."""
    partial = CacheEntry(
        **{
            **vars(INHERITED),
            "added": "2026-09-01",
            "derived_on": "somewhere",
            "scope_note": "a note",
        }
    )
    assert not _found(_cache(partial))


def test_entry_with_no_added_date_must_carry_a_record() -> None:
    """The scaffold does not write ``added``, so an undated entry is a NEW
    one being written now -- never an inherited one, which all carry a date."""
    undated = CacheEntry(**{**vars(INHERITED), "added": None})
    assert not _found(_cache(undated))


def test_every_shipped_sidecar_entry_is_still_admissible() -> None:
    """The grandfather clause is only worth having if it actually keeps the
    thirteen inherited entries: enforcing the rule literally would drop them
    all and turn six currently-clean proofs into admitting ones."""
    root = pathlib.Path(__file__).parents[2].parent / "examples"
    sidecars = sorted(root.rglob("*.tactics.toml"))
    assert sidecars, "no sidecars found -- is the examples submodule checked out?"
    for path in sidecars:
        cache = TacticCache.load(path)
        for entry in cache.entries:
            assert (
                cache.lookup(entry.transform, entry.game_before, entry.game_after)
                is not None
            ), f"{path}: entry for {entry.transform} became inadmissible"
