"""Unit tests for the per-transform tactic-cache sidecar I/O."""

from __future__ import annotations

import pathlib

from proof_frog.export.easycrypt.tactic_cache import (
    CacheEntry,
    SCHEMA_VERSION,
    TacticCache,
    relative_sidecar_path,
)


def _sample_entry(
    transform: str = "Topological Sorting", description: str | None = "hop 2"
) -> CacheEntry:
    # Multi-line fields are stored with trailing newlines (matches the
    # TOML literal-block round-trip).
    return CacheEntry(
        transform=transform,
        game_before="proc enc(m : M) : C = {\n  return m;\n}\n",
        game_after="proc enc(m : M) : C = {\n  return m;\n}\n",
        tactic="proc.\nswap{1} 2 2.\nrnd{1}; auto => />.\nsim.\n",
        description=description,
        added="2026-05-23",
    )


def test_load_missing_file_returns_empty_cache(tmp_path: pathlib.Path) -> None:
    cache = TacticCache.load(tmp_path / "absent.toml")
    assert cache.entries == []
    assert cache.stale_entries == []
    assert cache.schema_version == SCHEMA_VERSION


def test_round_trip_preserves_entries(tmp_path: pathlib.Path) -> None:
    cache = TacticCache(entries=[_sample_entry()])
    path = tmp_path / "x.tactics.toml"
    cache.save(path)
    reloaded = TacticCache.load(path)
    assert reloaded.entries == cache.entries
    assert reloaded.schema_version == SCHEMA_VERSION


def test_round_trip_is_byte_stable(tmp_path: pathlib.Path) -> None:
    """Saving the same cache twice produces byte-identical files —
    needed for git-diff-friendly sidecars."""
    cache = TacticCache(entries=[_sample_entry(), _sample_entry(transform="Other")])
    path1 = tmp_path / "a.toml"
    path2 = tmp_path / "b.toml"
    cache.save(path1)
    cache.save(path2)
    assert path1.read_bytes() == path2.read_bytes()


def test_lookup_hit(tmp_path: pathlib.Path) -> None:
    entry = _sample_entry()
    cache = TacticCache(entries=[entry])
    hit = cache.lookup(entry.transform, entry.game_before, entry.game_after)
    assert hit == entry


def test_lookup_miss(tmp_path: pathlib.Path) -> None:
    entry = _sample_entry()
    cache = TacticCache(entries=[entry])
    assert cache.lookup("Other", entry.game_before, entry.game_after) is None
    assert cache.lookup(entry.transform, "different", entry.game_after) is None


def test_schema_version_mismatch_demotes_entries(tmp_path: pathlib.Path) -> None:
    """A sidecar with a future schema_version returns no live entries,
    but retains the entries as stale hints."""
    path = tmp_path / "future.toml"
    path.write_text(
        "schema_version = 999\n\n"
        "[[entry]]\n"
        'transform = "Topological Sorting"\n'
        "game_before = '''\nx\n'''\n"
        "game_after = '''\ny\n'''\n"
        "tactic = '''\nadmit.\n'''\n",
        encoding="utf-8",
    )
    cache = TacticCache.load(path)
    assert cache.entries == []
    assert len(cache.stale_entries) == 1
    assert cache.lookup("Topological Sorting", "x\n", "y\n") is None


def test_relative_sidecar_path() -> None:
    p = pathlib.Path("examples/foo/Bar.proof")
    assert relative_sidecar_path(p) == pathlib.Path(
        "examples/foo/Bar.proof.tactics.toml"
    )


def test_serialize_omits_optional_fields_when_none(tmp_path: pathlib.Path) -> None:
    entry = CacheEntry(
        transform="X",
        game_before="a",
        game_after="b",
        tactic="admit.",
        description=None,
        added=None,
    )
    path = tmp_path / "c.toml"
    TacticCache(entries=[entry]).save(path)
    text = path.read_text(encoding="utf-8")
    assert "description =" not in text
    assert "added =" not in text
    assert "transform =" in text
