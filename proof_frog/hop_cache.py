"""On-disk cache of verified equivalence hops (opt-in).

A user iterating on a proof re-runs ``prove`` after each edit, and most
equivalence hops are unchanged from the previous run. This module remembers
which hops the engine has already verified so a re-run can skip their
canonicalization.

What is stored is a set of SHA-256 digests, one per verified hop: no ASTs, no
pickles. A digest covers everything the equivalence check reads:

- the two inlined games, in order (current, next);
- the step assumptions of the hop;
- every field of the :class:`PipelineContext` (let types, proof namespace,
  subset/equality constraints, requirements, the query cap, ...);
- the engine itself: the bytes of every ``proof_frog`` source file and the
  Python, Z3 and SymPy versions.

SOUNDNESS: a hit replaces the canonicalize-and-compare step with "verified",
so a digest that omits something the verdict depends on would be a false
accept. Two rules keep the digest complete:

- The serialization is structural and FAIL-CLOSED: a value of a type it does
  not know raises :class:`Uncacheable` and the hop is checked normally. A new
  ``PipelineContext`` field is therefore either covered automatically or
  disables caching; it can never be silently left out.
- Only successes are stored. A failing hop is always re-checked, so
  diagnostics are never served from the cache.

The cache file is trusted: whoever can write to it can make a hop report as
verified. It is therefore off unless requested, never used by the test suite,
and cached hops are marked in the ``prove`` output.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import sympy
import z3

from . import frog_ast
from .transforms._base import PipelineContext
from .visitors import NameTypeMap, NameTypePair

# Bump when the digest layout changes.
_FORMAT_VERSION = 2

# Environment variables: opt in, and override the cache location.
ENV_ENABLE = "PROOFFROG_HOP_CACHE"
ENV_DIR = "PROOFFROG_CACHE_DIR"

# Files for older engine fingerprints are pruned beyond this many.
_MAX_CACHE_FILES = 8

# A cache file above _MAX_ENTRIES lines (about 3.3 MB, ~75 ms to load) is
# rewritten keeping its newest _TRIM_TO entries. Dropping entries is always
# safe: a dropped hop is simply checked again.
_MAX_ENTRIES = 50_000
_TRIM_TO = 25_000

# PipelineContext fields that are not inputs of the equivalence check:
# `sort_game_fn` is the engine's bound `sort_game`, whose only state is the
# proof namespace (digested as its own field) and whose code is covered by
# the engine fingerprint; `near_misses` is an output, reset for every game.
_CONTEXT_FIELDS_NOT_INPUTS = frozenset({"sort_game_fn", "near_misses"})

_NON_SEMANTIC = frog_ast.ASTNode._NON_SEMANTIC  # pylint: disable=protected-access


class Uncacheable(Exception):
    """A value the structural digest does not know how to serialize."""


def _digest_of(obj: object) -> bytes:
    sub = hashlib.sha256()
    _feed(sub, obj)
    return sub.digest()


def _feed_str(h: Any, tag: bytes, text: str) -> None:
    data = text.encode("utf-8")
    h.update(tag + str(len(data)).encode() + b":")
    h.update(data)


def _feed_unordered(h: Any, tag: bytes, items: Iterable[object]) -> None:
    digests = sorted(_digest_of(item) for item in items)
    h.update(tag + str(len(digests)).encode() + b":")
    for digest in digests:
        h.update(digest)


def _feed(h: Any, obj: object) -> None:  # pylint: disable=too-many-branches
    """Write an unambiguous, order- and type-tagged encoding of *obj* to *h*.

    Every composite is length-prefixed and every value type-tagged, so two
    different values never produce the same byte stream. Unknown types raise
    :class:`Uncacheable`.
    """
    if obj is None:
        h.update(b"N;")
    elif isinstance(obj, enum.Enum):
        _feed_str(h, b"E", f"{type(obj).__qualname__}.{obj.name}")
    elif isinstance(obj, bool):
        h.update(b"B1;" if obj else b"B0;")
    elif isinstance(obj, int):
        h.update(b"I" + str(obj).encode() + b";")
    elif isinstance(obj, str):
        _feed_str(h, b"S", obj)
    elif isinstance(obj, frog_ast.ASTNode):
        # The same view of a node that `ASTNode.__eq__` compares: its class
        # and every attribute except source positions.
        _feed_str(h, b"A", f"{type(obj).__module__}.{type(obj).__qualname__}")
        items = sorted(
            (key, value) for key, value in vars(obj).items() if key not in _NON_SEMANTIC
        )
        h.update(str(len(items)).encode() + b":")
        for key, value in items:
            _feed_str(h, b"k", key)
            _feed(h, value)
    elif isinstance(obj, NameTypeMap):
        h.update(b"M")
        _feed(h, obj.type_map)
    elif isinstance(obj, NameTypePair):
        h.update(b"P")
        _feed(h, obj.name)
        _feed(h, obj.type)
    elif isinstance(obj, (list, tuple)):
        h.update((b"L" if isinstance(obj, list) else b"T") + str(len(obj)).encode())
        h.update(b":")
        for item in obj:
            _feed(h, item)
    elif isinstance(obj, (set, frozenset)):
        _feed_unordered(h, b"U", obj)
    elif isinstance(obj, dict):
        _feed_unordered(h, b"D", obj.items())
    elif isinstance(obj, sympy.Basic):
        _feed_str(h, b"Y", sympy.srepr(obj))
    else:
        raise Uncacheable(type(obj).__qualname__)


_ENGINE_FINGERPRINT: Optional[str] = None


def engine_fingerprint() -> str:
    """A digest of the running engine: its sources and solver versions.

    Hashing the source files (not the version string) means a development
    checkout that changes without a version bump still gets a fresh cache.
    Computed once per process, as close as possible to when the process
    imported the engine; :meth:`HopCache.add` re-reads the sources to catch a
    change made while a proof runs. Raises ``OSError`` if the sources cannot
    be read.
    """
    global _ENGINE_FINGERPRINT  # pylint: disable=global-statement
    if _ENGINE_FINGERPRINT is None:
        _ENGINE_FINGERPRINT = _fingerprint_sources()
    return _ENGINE_FINGERPRINT


def _fingerprint_sources() -> str:
    """The engine fingerprint as the files on disk are now (uncached)."""
    h = hashlib.sha256()
    _feed(
        h,
        [
            _FORMAT_VERSION,
            list(sys.version_info[:3]),
            z3.get_version_string(),
            sympy.__version__,
        ],
    )
    package_dir = Path(__file__).resolve().parent
    for path in sorted(package_dir.rglob("*.py")):
        _feed_str(h, b"F", path.relative_to(package_dir).as_posix())
        data = path.read_bytes()
        h.update(str(len(data)).encode() + b":")
        h.update(data)
    return h.hexdigest()


def default_cache_dir() -> Path:
    """``$PROOFFROG_CACHE_DIR``, else the user cache directory."""
    override = os.environ.get(ENV_DIR)
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "prooffrog"


def enabled_by_environment() -> bool:
    """True only for an explicit yes: ``1``, ``true``, ``yes`` or ``on``."""
    return os.environ.get(ENV_ENABLE, "").strip().lower() in ("1", "true", "yes", "on")


def _is_digest(line: str) -> bool:
    return len(line) == 64 and all(c in "0123456789abcdef" for c in line)


class HopCache:
    """The set of hop digests verified by this exact engine.

    One text file per engine fingerprint, one hex digest per line. Reading
    and writing are best-effort: an unreadable or unwritable cache behaves as
    an empty one and never fails a proof.
    """

    def __init__(self, directory: Optional[Path] = None) -> None:
        self._fingerprint = engine_fingerprint()
        directory = directory if directory is not None else default_cache_dir()
        self._path = directory / f"hops-{self._fingerprint[:16]}.txt"
        self._known: set[str] = set()
        # Lines in the file, counted to decide when to trim it.
        self._lines = 0
        # Set once the engine sources on disk no longer match the fingerprint
        # this run started with; from then on nothing is recorded.
        self._stale = False
        self.hits = 0
        try:
            entries = self._read_entries()
        except (OSError, UnicodeDecodeError):
            entries = []
        self._known = set(entries)
        self._lines = len(entries)

    def _read_entries(self) -> list[str]:
        """The well-formed digests in the file, oldest first."""
        with open(self._path, encoding="ascii") as f:
            return [line for line in (raw.strip() for raw in f) if _is_digest(line)]

    def key(
        self,
        ctx: PipelineContext,
        current_game: frog_ast.Game,
        next_game: frog_ast.Game,
        step_assumptions: list[Any],
    ) -> Optional[str]:
        """The digest of one equivalence hop, or None if it is uncacheable."""
        h = hashlib.sha256()
        try:
            _feed_str(h, b"V", self._fingerprint)
            for field in dataclasses.fields(ctx):
                if field.name in _CONTEXT_FIELDS_NOT_INPUTS:
                    continue
                _feed_str(h, b"c", field.name)
                _feed(h, getattr(ctx, field.name))
            _feed(h, current_game)
            _feed(h, next_game)
            _feed(h, list(step_assumptions))
        except (Uncacheable, RecursionError):
            return None
        return h.hexdigest()

    @property
    def fingerprint(self) -> str:
        """The engine fingerprint this cache stores verdicts for."""
        return self._fingerprint

    def __contains__(self, key: object) -> bool:
        return key in self._known

    def lookup(self, key: Optional[str]) -> bool:
        """True (and counted as a hit) if the hop *key* is known verified."""
        if key is not None and key in self._known:
            self.hits += 1
            return True
        return False

    def add(self, key: Optional[str], verified_by: Optional[str] = None) -> None:
        """Record a hop the engine has just verified.

        *verified_by* is the fingerprint of the process that checked the hop
        (a pool worker imports the engine afresh, possibly after the sources
        changed); a hop checked by any other engine is not recorded. Before
        writing, the sources are hashed again: if they changed since this run
        started, the code that verified the hop is not the code this cache
        is keyed on, so nothing more is recorded in this run.
        """
        if key is None or key in self._known or self._stale:
            return
        if verified_by is not None and verified_by != self._fingerprint:
            return
        try:
            if _fingerprint_sources() != self._fingerprint:
                self._stale = True
                return
        except OSError:
            self._stale = True
            return
        self._known.add(key)
        try:
            created = not self._path.exists()
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # One short line per append: atomic under O_APPEND, so concurrent
            # `prove` runs cannot interleave within a digest.
            with open(self._path, "a", encoding="ascii") as f:
                f.write(key + "\n")
            self._lines += 1
            if created:
                self._prune()
            if self._lines > _MAX_ENTRIES:
                self._trim()
        except (OSError, UnicodeDecodeError):
            pass

    def _trim(self) -> None:
        """Rewrite the file keeping only its newest _TRIM_TO distinct entries.

        The file is append-ordered, so the newest entries are the most
        recently verified hops. The rewrite goes through a temporary file and
        an atomic rename, so a concurrent reader never sees a partial file; an
        append racing the rewrite may be lost, which only costs a re-check.
        Entries this run already knows stay usable in memory.
        """
        newest: list[str] = []
        seen: set[str] = set()
        for entry in reversed(self._read_entries()):
            if entry not in seen:
                seen.add(entry)
                newest.append(entry)
                if len(newest) == _TRIM_TO:
                    break
        newest.reverse()
        temporary = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text("".join(e + "\n" for e in newest), encoding="ascii")
            os.replace(temporary, self._path)
        finally:
            temporary.unlink(missing_ok=True)
        self._lines = len(newest)

    def _prune(self) -> None:
        """Drop the files of the least recently used engine fingerprints."""
        files = sorted(
            self._path.parent.glob("hops-*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in files[_MAX_CACHE_FILES:]:
            if stale != self._path:
                stale.unlink(missing_ok=True)


def open_hop_cache(requested: Optional[bool] = None) -> Optional[HopCache]:
    """The cache to use for a run, or None when caching is off.

    *requested* is the command-line choice (``--cache`` / ``--no-cache``);
    None defers to ``PROOFFROG_HOP_CACHE``. Any failure to set the cache up
    (e.g. unreadable engine sources) turns it off.
    """
    if requested is None:
        requested = enabled_by_environment()
    if not requested:
        return None
    try:
        return HopCache()
    except OSError:
        return None
