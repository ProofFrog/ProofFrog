"""Unit tests for the per-transform tactic-cache sidecar I/O."""

from __future__ import annotations

import pathlib

from proof_frog.export.easycrypt import tactic_cache as tc
from proof_frog.export.easycrypt.tactic_cache import (
    CacheEntry,
    ORACLE_TRANSFORM,
    SCHEMA_VERSION,
    TacticCache,
    oracle_transform,
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


def test_oracle_transform_sentinel() -> None:
    """The per-oracle sentinel is the reserved prefix plus the oracle name,
    so init and each post-init oracle of one hop get distinct keys."""
    assert oracle_transform("challenge") == f"{ORACLE_TRANSFORM}:challenge"
    assert oracle_transform("initialize") != oracle_transform("challenge")


def test_oracle_entry_round_trips_byte_stably(tmp_path: pathlib.Path) -> None:
    """An ``<oracle>:challenge`` entry is an ordinary [[entry]] with a
    reserved transform -- it round-trips and looks up like any other (no
    schema change)."""
    entry = _sample_entry(transform=oracle_transform("challenge"), description="hop 0")
    cache = TacticCache(entries=[entry])
    path = tmp_path / "oracle.tactics.toml"
    cache.save(path)
    reloaded = TacticCache.load(path)
    assert reloaded.entries == [entry]
    hit = reloaded.lookup(entry.transform, entry.game_before, entry.game_after)
    assert hit == entry
    # Byte-stable second write.
    path2 = tmp_path / "oracle2.tactics.toml"
    reloaded.save(path2)
    assert path.read_bytes() == path2.read_bytes()


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


# ---------------------------------------------------------------------------
# The three-layer store (Phase-4 Decision 3)
# ---------------------------------------------------------------------------


def _write_store_entry(directory: pathlib.Path, name: str, tactic: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    cache = tc.TacticCache()
    cache.append(
        tc.CacheEntry(transform="T", game_before="B", game_after="A", tactic=tactic)
    )
    cache.save(directory / f"{name}.toml")


def test_layered_lookup_prefers_the_most_specific_layer(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """Sidecar beats project store beats packaged store. Precedence is the
    ORDER the layers are concatenated in, since ``lookup`` returns the first
    exact match."""
    proj = tmp_path / "proj"
    proof = proj / "p.proof"
    proj.mkdir()
    proof.write_text("", encoding="utf-8")
    store = proj / tc.PROJECT_STORE_DIRNAME / tc.PROJECT_STORE_SUBDIR
    _write_store_entry(store, "e", "project tactic")
    packaged = tmp_path / "packaged"
    _write_store_entry(packaged, "e", "packaged tactic")
    monkeypatch.setattr(tc, "packaged_store_dir", lambda: packaged)

    # project + packaged only -> the project entry wins. The key is read back
    # off a loaded entry so the test does not depend on how the serializer
    # round-trips multi-line fields.
    cache = tc.load_layered(proof)
    first = cache.entries[0]
    hit = cache.lookup(first.transform, first.game_before, first.game_after)
    assert hit is not None and hit.tactic.strip() == "project tactic"
    assert hit.source == "project"
    assert [e.source for e in cache.entries] == ["project", "packaged"]

    # add a sidecar entry -> it wins over both
    side = tc.TacticCache()
    side.append(
        tc.CacheEntry(
            transform="T", game_before="B", game_after="A", tactic="sidecar tactic"
        )
    )
    side.save(tc.relative_sidecar_path(proof))
    cache2 = tc.load_layered(proof)
    hit2 = cache2.lookup(first.transform, first.game_before, first.game_after)
    assert hit2 is not None and hit2.tactic.strip() == "sidecar tactic"
    assert hit2.source == "sidecar"


def test_layered_load_with_no_stores_is_just_the_sidecar(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """The corpus today has neither a project nor a packaged store, so the
    layered load must be exactly the old sidecar load -- that is what makes
    this change byte-identical."""
    monkeypatch.setattr(tc, "packaged_store_dir", lambda: tmp_path / "absent")
    monkeypatch.delenv(tc.TACTIC_CACHE_ENV, raising=False)
    proof = tmp_path / "q.proof"
    proof.write_text("", encoding="utf-8")
    assert tc.load_layered(proof).entries == []
    side = tc.TacticCache()
    side.append(
        tc.CacheEntry(transform="T", game_before="B", game_after="A", tactic="t")
    )
    side.save(tc.relative_sidecar_path(proof))
    layered = tc.load_layered(proof).entries
    sidecar_only = tc.TacticCache.load(tc.relative_sidecar_path(proof)).entries
    assert [(e.transform, e.game_before, e.game_after, e.tactic) for e in layered] == [
        (e.transform, e.game_before, e.game_after, e.tactic) for e in sidecar_only
    ]


def test_project_store_is_discovered_by_walking_up(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    monkeypatch.delenv(tc.TACTIC_CACHE_ENV, raising=False)
    root = tmp_path / "root"
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    store = root / tc.PROJECT_STORE_DIRNAME / tc.PROJECT_STORE_SUBDIR
    store.mkdir(parents=True)
    assert tc.find_project_store(deep / "p.proof") == store
    # No marker anywhere -> no store.
    other = tmp_path / "other"
    other.mkdir()
    assert tc.find_project_store(other / "p.proof") is None


def test_explicit_override_and_env_beat_discovery(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    deep = root / "a"
    deep.mkdir(parents=True)
    (root / tc.PROJECT_STORE_DIRNAME / tc.PROJECT_STORE_SUBDIR).mkdir(parents=True)
    elsewhere = tmp_path / "ci-store"
    elsewhere.mkdir()
    assert tc.find_project_store(deep / "p.proof", override=elsewhere) == elsewhere
    monkeypatch.setenv(tc.TACTIC_CACHE_ENV, str(elsewhere))
    assert tc.find_project_store(deep / "p.proof") == elsewhere
    # A path that is not a directory is ignored rather than crashing.
    monkeypatch.setenv(tc.TACTIC_CACHE_ENV, str(tmp_path / "nope"))
    assert tc.find_project_store(deep / "p.proof") is None
