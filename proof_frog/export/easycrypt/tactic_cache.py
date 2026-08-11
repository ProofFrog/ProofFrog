"""Sidecar I/O for the per-transform EasyCrypt tactic cache.

Each ``.proof`` file may have a sibling ``.proof.tactics.toml`` sidecar
containing cached tactic bodies, keyed by
``(transform_name, canonical_text(game_before), canonical_text(game_after))``.

Most entries are *per-transform* micro-lemma tactics. A second kind of
entry is *per-hop*: a whole-hop proof body for a hop the chain machinery
cannot decompose (a cross-primitive deterministic-reorder hop). These use
the reserved ``transform`` sentinel :data:`HOP_TRANSFORM` with
``game_before``/``game_after`` set to the canonical text of the hop's two
adjacent (inlined) games. All caching for a proof — per-transform and
per-hop — lives in the single sidecar; the schema is unchanged (a hop
entry is just an ``[[entry]]`` with ``transform = "<hop>"``).

This module owns reading and writing those sidecars. Reading uses the
stdlib ``tomllib``. Writing uses a small deterministic serializer
(triple-quoted multi-line strings preserved verbatim, fixed key order)
so that round-tripping is byte-stable and ``git diff`` stays readable.

Schema versioning is conservative: a load with an unrecognized
``schema_version`` returns an empty live cache, retaining the stored
entries as hints (addressable via :attr:`TacticCache.stale_entries`) for
the admit diagnostic to surface but never returned by :meth:`lookup`.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
import re
import tomllib
from dataclasses import dataclass, field
from typing import Iterable

SCHEMA_VERSION = 2
"""Bumped whenever the KEY or this file's serialization shape changes.
Entries written under an older schema are loaded as stale hints (orphaned)
rather than treated as cache hits.

Version 2 (Phase-4 Decisions 1+2, 2026-08-11): ``game_before``/``game_after``
hold :func:`canonical_form.masked_shape` -- the changed region of the pair
with variable names masked -- instead of :func:`canonical_form.canonical_text`
of two whole games. Version 1's whole-game key made an entry unreachable from
any proof but the one it was derived on."""

RECORD_REQUIRED_FROM = "2026-08-11"
"""Date from which an entry must carry a derivation record to be usable.

Phase-4 Decision 4, as resolved by the maintainer: GRANDFATHER. An entry
written before this date stays admissible; every entry created on or after it
must supply the mandatory fields (see :func:`admissible`). The dividing line
is the entry's own ``added`` date rather than "does it happen to have a
record", because keying it on the record's presence would let a new
record-free entry grandfather itself -- exactly the case the rule exists to
catch. The thirteen inherited entries all carry ``added`` dates in May and
June 2026 and cannot satisfy the requirement retroactively: whether a
goal-falsifying mutation was ever run for them is recorded nowhere, and
inventing one would be the fabrication the rule prevents."""

_RECORD_FIELDS = ("derived_on", "negative_control", "refuted", "scope_note")

HOP_TRANSFORM = "<hop>"
"""Reserved ``transform`` value for a *per-hop* cache entry (a whole-hop
proof body, e.g. for a cross-primitive deterministic-reorder hop). Its
``game_before``/``game_after`` are the canonical text of the hop's two
adjacent games rather than a single transform's before/after."""

ORACLE_TRANSFORM = "<oracle>"
"""Reserved ``transform`` prefix for a *per-oracle* cache entry of a
multi-oracle hop (a whole-oracle proof body the per-oracle chain cannot
decompose, e.g. KEMPRF's transformed ``challenge`` body). The full
``transform`` value is ``f"{ORACLE_TRANSFORM}:{oracle_name}"`` (see
:func:`oracle_transform`) so the init and each post-init oracle of one hop
get distinct keys. As with :data:`HOP_TRANSFORM`, ``game_before``/
``game_after`` are the canonical text of the hop's two adjacent games
rather than a single transform's before/after. Mirrors the ``<hop>``
mechanism exactly: an ordinary ``[[entry]]`` with a reserved ``transform``,
no schema change."""


def oracle_transform(oracle_name: str) -> str:
    """Per-oracle cache ``transform`` sentinel for ``oracle_name``.

    See :data:`ORACLE_TRANSFORM`."""
    return f"{ORACLE_TRANSFORM}:{oracle_name}"


def admissible(entry: "CacheEntry") -> bool:
    """Whether ``entry`` may close a goal.

    Phase-4 Decision 4 with the maintainer's grandfather clause. An entry
    ``added`` before :data:`RECORD_REQUIRED_FROM` is admissible as it stands.
    Any other entry -- including one with no ``added`` date at all, which the
    derivation scaffold does not write and an inherited entry always has --
    must carry every field of the derivation record.

    The negative control is the load-bearing one: without a goal-falsifying
    mutation that EasyCrypt REJECTED, "the tactic closed" only says the tactic
    ran, and a tactic that runs without closing its goal is the worst state
    this exporter can be in (a zero-admit file EasyCrypt still rejects).
    """
    if entry.added is not None and entry.added < RECORD_REQUIRED_FROM:
        return True
    return all(getattr(entry, f) for f in _RECORD_FIELDS)


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheEntry:
    """One cached tactic body, addressed by (transform, before, after).

    ``source`` records WHICH layer the entry came from (see
    :func:`load_layered`). It is provenance for diagnostics only: it is
    never serialized, never part of the key, and never affects a lookup
    beyond the order the layers are concatenated in.
    """

    transform: str
    game_before: str
    game_after: str
    tactic: str
    description: str | None = None
    added: str | None = None
    source: str = "sidecar"
    # --- derivation record (Phase-4 Decision 4) --------------------------
    # Provenance a reader needs to trust an entry they did not derive. The
    # negative control is the load-bearing one: without a goal-falsifying
    # mutation that EasyCrypt rejected, "the tactic closed" only says the
    # tactic ran. An entry added on or after RECORD_REQUIRED_FROM is REFUSED
    # by lookup without all four (see admissible); entries older than that
    # are grandfathered, since the 13 inherited ones cannot satisfy the
    # requirement retroactively.
    derived_on: str | None = None
    negative_control: str | None = None
    refuted: str | None = None
    scope_note: str | None = None


@dataclass
class TacticCache:
    """In-memory view of one sidecar ``.tactics.toml`` file.

    ``entries`` are the live (schema-matching) entries used for
    :meth:`lookup`. ``stale_entries`` are entries from a sidecar whose
    ``schema_version`` does not match :data:`SCHEMA_VERSION` — they are
    retained for the admit diagnostic to consult as fuzzy hints but
    never returned by :meth:`lookup`.
    """

    schema_version: int = SCHEMA_VERSION
    entries: list[CacheEntry] = field(default_factory=list)
    stale_entries: list[CacheEntry] = field(default_factory=list)

    def lookup(
        self, transform: str, game_before: str, game_after: str
    ) -> CacheEntry | None:
        """Exact-match lookup. Linear scan; n is small in practice.

        An entry that is not :func:`admissible` is skipped as though it were
        not there, so the leg declines to an honest admit rather than closing
        on a tactic nobody can check. Refusing here rather than at load time
        keeps the entry visible to the orphan report and to the admit
        diagnostic's fuzzy hints.
        """
        for entry in self.entries:
            if (
                entry.transform == transform
                and entry.game_before == game_before
                and entry.game_after == game_after
            ):
                if not admissible(entry):
                    _LOGGER.warning(
                        "tactic-cache entry for %r matched but has no derivation "
                        "record (added=%s); skipping it. Fill the mandatory "
                        "fields (%s) or the leg will keep admitting.",
                        transform,
                        entry.added,
                        ", ".join(_RECORD_FIELDS),
                    )
                    continue
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
        derived_on=_optstr("derived_on"),
        negative_control=_optstr("negative_control"),
        refuted=_optstr("refuted"),
        scope_note=_optstr("scope_note"),
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
        if entry.derived_on is not None:
            out.append(f"derived_on = {_inline_string(entry.derived_on)}")
        if entry.scope_note is not None:
            out.append(f"scope_note = {_inline_string(entry.scope_note)}")
        if entry.negative_control is not None:
            out.append(f"negative_control = {_block_string(entry.negative_control)}")
        if entry.refuted is not None:
            out.append(f"refuted = {_block_string(entry.refuted)}")
        out.append(f"game_before = {_block_string(entry.game_before)}")
        out.append(f"game_after = {_block_string(entry.game_after)}")
        out.append(f"tactic = {_block_string(entry.tactic)}")
    out.append("")
    return "\n".join(out)


def derivation_scaffold(
    transform: str, before_key: str, after_key: str, site: str
) -> list[str]:
    """The skeleton of an admissible entry, ready to paste into a store file.

    Phase-4 Decision 4. What a filler must supply is stated as fields rather
    than as prose they have to remember, and the two key halves are the ones
    the export just looked up -- so an entry built from this scaffold is
    found by the next export instead of being subtly mis-keyed.

    ``negative_control`` is mandatory in substance, not decoration: a tactic
    that runs proves nothing on its own, and the mutation that EasyCrypt
    REJECTED is the evidence that the tactic is doing work. A type error does
    not count -- it fails at parse time, before any goal is attempted.
    """
    lines = [
        "[[entry]]",
        f"transform = {_inline_string(transform)}",
        f'derived_on = "{site} | EC <version> | exporter <commit>"',
        'scope_note = "why this key is masked as it is"',
        'negative_control = """',
        "  mutation: <the load-bearing conjunct you falsified>",
        "  EasyCrypt said: <its rejection message>",
        '"""',
        'refuted = """',
        "  <approaches that did NOT work, so the next filler skips them>",
        '"""',
        f"game_before = {_block_string(before_key)}",
        f"game_after = {_block_string(after_key)}",
        'tactic = """',
        "  <the tactic, without the trailing qed.>",
        '"""',
    ]
    return lines


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
# The three-layer store (Phase-4 Decision 3)
# ---------------------------------------------------------------------------

PROJECT_STORE_DIRNAME = ".prooffrog"
"""Project-root marker directory holding a transferable tactic store."""

PROJECT_STORE_SUBDIR = "tactic-cache"
"""Subdirectory of :data:`PROJECT_STORE_DIRNAME` holding the entry files."""

TACTIC_CACHE_ENV = "PROOFFROG_TACTIC_CACHE"
"""Environment override naming a project store directory outright (for CI)."""


def packaged_store_dir() -> pathlib.Path:
    """The read-only, maintainer-curated store that ships in the wheel.

    Writes NEVER go here: it changes only by maintainer promotion, so its
    entries stay in lockstep with the canonical basis and exporter version
    they were validated against.
    """
    return pathlib.Path(__file__).parent / "tactic_store"


def find_project_store(
    proof_path: pathlib.Path, override: str | pathlib.Path | None = None
) -> pathlib.Path | None:
    """The project store for ``proof_path``, or ``None`` if there is none.

    ``override`` (the ``--tactic-cache`` flag) wins; then the
    :data:`TACTIC_CACHE_ENV` environment variable; otherwise walk up from
    the proof file looking for ``.prooffrog/tactic-cache/``. Walking up --
    rather than assuming one fixed location -- is what lets an external
    user keep a transferable store next to their own proofs, and makes our
    own corpus a plain instance of the same mechanism rather than a special
    case.
    """
    explicit = override if override is not None else os.environ.get(TACTIC_CACHE_ENV)
    if explicit:
        path = pathlib.Path(explicit)
        return path if path.is_dir() else None
    start = proof_path.resolve()
    for parent in [start] + list(start.parents):
        candidate = parent / PROJECT_STORE_DIRNAME / PROJECT_STORE_SUBDIR
        if candidate.is_dir():
            return candidate
    return None


def load_store_dir(directory: pathlib.Path, source: str) -> list[CacheEntry]:
    """Every live entry in a store directory, in a deterministic order.

    One TOML file per entry is the intended layout, but a file may hold
    several ``[[entry]]`` blocks -- the parser is the sidecar's, so the two
    layouts read identically. Files are visited in sorted order so a lookup
    never depends on directory iteration order. A file whose
    ``schema_version`` does not match is skipped exactly as a stale sidecar
    is (its entries are hints, not hits).

    Only ``source`` is rewritten. It used to be rebuilt field by field, which
    silently DROPPED the whole derivation record on the way in -- the record
    round-trips through the serializer perfectly and then vanished here, so it
    was invisible to every consumer. Caught by the admissibility gate
    (:func:`admissible`), which refused store entries that had a complete
    record on disk.
    """
    if not directory.is_dir():
        return []
    out: list[CacheEntry] = []
    for path in sorted(directory.glob("*.toml")):
        loaded = TacticCache.load(path)
        out.extend(dataclasses.replace(e, source=source) for e in loaded.entries)
    return out


def load_layered(
    proof_path: pathlib.Path, override: str | pathlib.Path | None = None
) -> TacticCache:
    """Load the sidecar, the project store and the packaged store as one cache.

    Lookup precedence is sidecar -> project -> packaged, and it falls out of
    the ORDER the layers are concatenated in: :meth:`TacticCache.lookup`
    returns the first exact match. Writes are unaffected -- they still go to
    the sidecar (or, later, to the project store); the packaged layer is
    read-only by construction.

    Stale entries from every layer are kept together so the admit
    diagnostic can still surface them as fuzzy hints.
    """
    sidecar = TacticCache.load(relative_sidecar_path(proof_path))
    entries = list(sidecar.entries)
    project_dir = find_project_store(proof_path, override)
    if project_dir is not None:
        entries.extend(load_store_dir(project_dir, "project"))
    entries.extend(load_store_dir(packaged_store_dir(), "packaged"))
    return TacticCache(
        schema_version=SCHEMA_VERSION,
        entries=entries,
        stale_entries=list(sidecar.stale_entries),
    )


# ---------------------------------------------------------------------------
# Escalation report — synthesizer-candidate clusters
# ---------------------------------------------------------------------------

SYNTHESIZER_CANDIDATE_THRESHOLD = 5
"""Distinct entries sharing a shape before the cluster is worth reporting.

Matches the project's standing bar for promoting a recurring cached recipe
to a synthesizer (>= 5 distinct proofs hitting the same shape), so the
report replaces a human noticing the fifth identical fill rather than
inventing a second, softer bar."""


def _shape_of(text: str) -> str:
    """Every identifier run replaced by ``ID``.

    Strictly LOOSER than the stored key, which masks variable names only and
    keeps types (see :func:`canonical_form.masked_shape`). Two entries with
    the same shape but different keys are two sites a single synthesizer
    might cover -- which is what makes them worth reporting -- while the
    stored key stays tight so nothing is REUSED on this basis.
    """
    return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", "ID", text)


def cluster_by_shape(
    entries: Iterable[CacheEntry],
) -> dict[tuple[str, str, str], list[CacheEntry]]:
    """Group entries by ``(transform, shape(before), shape(after))``.

    Only groups with more than one DISTINCT key are returned: several
    entries that share a key are one site captured in several layers, not
    several sites.
    """
    groups: dict[tuple[str, str, str], list[CacheEntry]] = {}
    for entry in entries:
        shape = (
            entry.transform,
            _shape_of(entry.game_before),
            _shape_of(entry.game_after),
        )
        groups.setdefault(shape, []).append(entry)
    return {
        shape: members
        for shape, members in groups.items()
        if len({(m.transform, m.game_before, m.game_after) for m in members}) > 1
    }


def synthesizer_candidates(
    entries: Iterable[CacheEntry], threshold: int = SYNTHESIZER_CANDIDATE_THRESHOLD
) -> list[tuple[str, int]]:
    """``(transform, distinct-site count)`` for clusters at or above
    ``threshold``, largest first -- the mechanical version of noticing that
    the same fill has been written five times."""
    out: list[tuple[str, int]] = []
    for shape, members in cluster_by_shape(entries).items():
        sites = len({(m.transform, m.game_before, m.game_after) for m in members})
        if sites >= threshold:
            out.append((shape[0], sites))
    return sorted(out, key=lambda pair: (-pair[1], pair[0]))


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
