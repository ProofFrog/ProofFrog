"""Sidecar I/O for the per-transform EasyCrypt tactic cache.

Each ``.proof`` file may have a sibling ``.proof.tactics.toml`` sidecar
containing cached tactic bodies, keyed by
``(transform_name, canonical_text(game_before), canonical_text(game_after))``.

This module owns reading and writing those sidecars. Reading uses the
stdlib ``tomllib``. Writing uses a small deterministic serializer
(triple-quoted multi-line strings preserved verbatim, fixed key order)
so that round-tripping is byte-stable and ``git diff`` stays readable.

Schema versioning is conservative: a load with an unrecognized
``schema_version`` returns an empty live cache, retaining the stored
entries as hints (addressable via :attr:`TacticCache.stale_entries`) for
the Layer-3 diagnostic to surface but never returned by :meth:`lookup`.
"""

from __future__ import annotations

import logging
import pathlib
import tomllib
from dataclasses import dataclass, field
from typing import Iterable

SCHEMA_VERSION = 1
"""Bumped whenever ``canonical_text`` or this file's serialization shape
changes. Entries written under an older schema are loaded as stale
hints (orphaned) rather than treated as cache hits."""


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheEntry:
    """One cached tactic body, addressed by (transform, before, after)."""

    transform: str
    game_before: str
    game_after: str
    tactic: str
    description: str | None = None
    added: str | None = None


@dataclass
class TacticCache:
    """In-memory view of one sidecar ``.tactics.toml`` file.

    ``entries`` are the live (schema-matching) entries used for
    :meth:`lookup`. ``stale_entries`` are entries from a sidecar whose
    ``schema_version`` does not match :data:`SCHEMA_VERSION` — they are
    retained for the Layer-3 diagnostic to consult as fuzzy hints but
    never returned by :meth:`lookup`.
    """

    schema_version: int = SCHEMA_VERSION
    entries: list[CacheEntry] = field(default_factory=list)
    stale_entries: list[CacheEntry] = field(default_factory=list)

    def lookup(
        self, transform: str, game_before: str, game_after: str
    ) -> CacheEntry | None:
        """Exact-match lookup. Linear scan; n is small in practice."""
        for entry in self.entries:
            if (
                entry.transform == transform
                and entry.game_before == game_before
                and entry.game_after == game_after
            ):
                return entry
        return None

    def append(self, entry: CacheEntry) -> None:
        """Append a new live entry. Caller is responsible for uniqueness."""
        self.entries.append(entry)

    @classmethod
    def load(cls, path: pathlib.Path) -> "TacticCache":
        """Load a sidecar from disk; missing file → empty cache."""
        if not path.exists():
            return cls()
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        return _build_from_toml(data)

    def save(self, path: pathlib.Path) -> None:
        """Serialize the cache deterministically to ``path``."""
        path.write_text(_serialize(self), encoding="utf-8")


# ---------------------------------------------------------------------------
# TOML parsing
# ---------------------------------------------------------------------------


def _build_from_toml(data: dict[str, object]) -> TacticCache:
    raw_version = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(raw_version, int):
        version = raw_version
    else:
        _LOGGER.warning(
            "tactic cache: ignoring non-integer schema_version %r", raw_version
        )
        version = -1
    raw_entries = data.get("entry", [])
    if not isinstance(raw_entries, list):
        _LOGGER.warning("tactic cache: 'entry' is not a list; treating as empty")
        raw_entries = []
    entries = [_entry_from_toml(e) for e in raw_entries if isinstance(e, dict)]
    if version != SCHEMA_VERSION:
        _LOGGER.warning(
            "tactic cache: schema_version %d != expected %d; treating "
            "%d entries as stale hints",
            version,
            SCHEMA_VERSION,
            len(entries),
        )
        return TacticCache(schema_version=version, entries=[], stale_entries=entries)
    return TacticCache(schema_version=version, entries=entries, stale_entries=[])


def _entry_from_toml(d: dict[str, object]) -> CacheEntry:
    def _str(key: str) -> str:
        v = d.get(key, "")
        if not isinstance(v, str):
            raise ValueError(f"tactic cache: entry field {key!r} must be a string")
        return v

    def _optstr(key: str) -> str | None:
        v = d.get(key)
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError(f"tactic cache: entry field {key!r} must be a string")
        return v

    return CacheEntry(
        transform=_str("transform"),
        game_before=_str("game_before"),
        game_after=_str("game_after"),
        tactic=_str("tactic"),
        description=_optstr("description"),
        added=_optstr("added"),
    )


# ---------------------------------------------------------------------------
# Deterministic TOML emission (custom — no tomli-w dependency)
# ---------------------------------------------------------------------------


def _serialize(cache: TacticCache) -> str:
    """Emit a sidecar in a stable, hand-edit-friendly TOML shape.

    Header line gives the schema version. Each entry is an
    ``[[entry]]`` table with fields in a fixed order: ``transform``,
    optional ``description``, optional ``added``, then the three
    multi-line fields ``game_before``, ``game_after``, ``tactic``. The
    multi-line fields are written as triple-quoted strings (``\"\"\"``)
    so they round-trip verbatim through ``tomllib`` regardless of
    embedded quotes or whitespace.
    """
    out: list[str] = []
    out.append(f"schema_version = {cache.schema_version}")
    for entry in cache.entries:
        out.append("")
        out.append("[[entry]]")
        out.append(f"transform = {_inline_string(entry.transform)}")
        if entry.description is not None:
            out.append(f"description = {_inline_string(entry.description)}")
        if entry.added is not None:
            out.append(f"added = {_inline_string(entry.added)}")
        out.append(f"game_before = {_block_string(entry.game_before)}")
        out.append(f"game_after = {_block_string(entry.game_after)}")
        out.append(f"tactic = {_block_string(entry.tactic)}")
    out.append("")
    return "\n".join(out)


def _inline_string(s: str) -> str:
    """Single-line TOML string. Escapes backslashes and double-quotes."""
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _block_string(s: str) -> str:
    """Triple-quoted TOML multi-line string.

    TOML's basic multi-line strings (``\"\"\"...\"\"\"``) strip a single
    leading newline if it immediately follows the opening delimiter and
    treat embedded ``\\`` as an escape character. To round-trip arbitrary
    content (including backslashes from tactic scripts), we use the
    *literal* multi-line form ``'''...'''`` instead — it neither strips
    nor interprets escapes. The one constraint is that the body must
    not contain three consecutive single-quotes; tactic / canonical
    text shouldn't have those, but we defensively fall back to the
    basic form with escaping if encountered.
    """
    if "'''" not in s:
        return "'''\n" + s + ("" if s.endswith("\n") else "\n") + "'''"
    escaped = s.replace("\\", "\\\\").replace('"""', '""\\"')
    return '"""\n' + escaped + ("" if escaped.endswith("\n") else "\n") + '"""'


# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------


def relative_sidecar_path(proof_path: pathlib.Path) -> pathlib.Path:
    """Conventional sidecar location: ``<proof_path>.tactics.toml`` sibling."""
    return proof_path.with_suffix(proof_path.suffix + ".tactics.toml")


def all_entries(cache: TacticCache) -> Iterable[CacheEntry]:
    """Live + stale entries combined; used by the orphan reporter."""
    yield from cache.entries
    yield from cache.stale_entries
