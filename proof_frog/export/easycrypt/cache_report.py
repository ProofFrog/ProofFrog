"""Sidecar tactic-cache orphan/miss reporter.

For each ``.proof`` file under ``examples/``, exports it in per-transform
mode, harvests the set of canonical cache keys the export consulted, and
diffs the result against the proof's ``.tactics.toml`` sidecar (if any).

Output is a per-proof report:

    examples/joy/Proofs/Ch2/OTPSecure.proof
      cache: ./OTPSecure.proof.tactics.toml (0 entries)
      used: 0, orphan: 0, missing: 0
      OK.

* **used**   — sidecar entries whose ``(transform, before, after)`` key
              was requested by the current export.
* **orphan** — entries in a WRITABLE layer (the sidecar or the project
              store) that no current micro-lemma asks for. Retained for
              fuzzy-hint purposes; flagged so a human can curate them. The
              packaged store is excluded: it is a shared library, and an
              entry of it that this one proof does not need is not an
              orphan.
* **missing** — keys the export requested but the sidecar lacked. Each
              one corresponds to an ``admit-*`` resolution in the EC file.

Exit code is always 0 (the report is a status surface, not a CI gate),
unless ``--strict`` is passed — then a nonzero exit indicates at least
one missing entry exists somewhere in the corpus.

Run via ``make check-tactic-cache``.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass

from .tactic_cache import (
    SYNTHESIZER_CANDIDATE_THRESHOLD,
    load_layered,
    relative_sidecar_path,
    synthesizer_candidates,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


@dataclass
class _Report:
    proof_path: pathlib.Path
    sidecar_path: pathlib.Path
    used: int
    orphan: int
    missing: int
    error: str | None = None


def _harvest_keys(proof_path: pathlib.Path) -> set[tuple[str, str, str]]:
    """Run the export and return every cache key consulted.

    The exporter publishes the list as
    ``easycrypt.exporter._last_requested_cache_keys`` after each call;
    we read it immediately after invoking the export.
    """
    # pylint: disable=import-outside-toplevel
    from . import exporter as ec_exporter

    ec_exporter.export_proof_file(str(proof_path))
    return set(getattr(ec_exporter, "_last_requested_cache_keys", []))


def _build_report(proof_path: pathlib.Path) -> _Report:
    sidecar_path = relative_sidecar_path(proof_path)
    # Every layer the export itself would consult, so `used` and `missing`
    # answer the question the export actually asks.
    cache = load_layered(proof_path)
    writable = {
        (e.transform, e.game_before, e.game_after)
        for e in cache.entries
        if e.source != "packaged"
    }
    try:
        requested = _harvest_keys(proof_path)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _Report(
            proof_path=proof_path,
            sidecar_path=sidecar_path,
            used=0,
            orphan=len(writable),
            missing=0,
            error=f"{type(exc).__name__}: {exc}",
        )
    live_keys = {(e.transform, e.game_before, e.game_after) for e in cache.entries}
    used = len(live_keys & requested)
    # An orphan is an entry in a WRITABLE layer that nothing asks for; a
    # packaged-library entry this proof does not need is not an orphan.
    orphan = len(writable - requested)
    missing = len(requested - live_keys)
    return _Report(
        proof_path=proof_path,
        sidecar_path=sidecar_path,
        used=used,
        orphan=orphan,
        missing=missing,
    )


def _format_report(report: _Report) -> str:
    rel_sidecar = (
        report.sidecar_path.relative_to(report.proof_path.parent)
        if report.sidecar_path.parent == report.proof_path.parent
        else report.sidecar_path
    )
    sidecar_state = (
        f"./{rel_sidecar}" if report.sidecar_path.exists() else "<not present>"
    )
    try:
        rel_proof = report.proof_path.resolve().relative_to(REPO_ROOT)
        proof_display = str(rel_proof)
    except ValueError:
        proof_display = str(report.proof_path)
    lines = [proof_display]
    if report.error is not None:
        lines.append(f"  EXPORT FAILED: {report.error}")
        return "\n".join(lines)
    lines.append(f"  cache: {sidecar_state}")
    lines.append(
        f"  used: {report.used}, orphan: {report.orphan}, missing: {report.missing}"
    )
    if report.missing > 0:
        lines.append(
            f"  MISS: {report.missing} micro-lemmas need derivation "
            f"(see EC export comments)."
        )
    elif report.orphan > 0:
        lines.append(
            f"  ORPHAN: {report.orphan} sidecar entries no longer match "
            f"any current micro-lemma."
        )
    else:
        lines.append("  OK.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report per-transform tactic-cache used/orphan/missing counts."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if any proof has missing cache entries.",
    )
    parser.add_argument(
        "--examples-dir",
        type=pathlib.Path,
        default=REPO_ROOT / "examples",
        help="Directory to scan for .proof files (default: ./examples).",
    )
    args = parser.parse_args(argv)

    proof_files = sorted(args.examples_dir.rglob("*.proof"))
    if not proof_files:
        print(f"No .proof files found under {args.examples_dir}")
        return 0

    any_missing = False
    all_entries: list[object] = []
    for proof_path in proof_files:
        report = _build_report(proof_path)
        print(_format_report(report))
        print()
        if report.missing > 0:
            any_missing = True
        all_entries.extend(load_layered(proof_path).entries)

    _print_escalation(all_entries)

    if args.strict and any_missing:
        return 1
    return 0


def _print_escalation(entries: list) -> None:  # type: ignore[type-arg]
    """The escalation report: shapes captured often enough to be worth a
    synthesizer.

    Entries are clustered by a LOOSER key than the one lookups use (every
    identifier masked, not just variable names), so a cluster means several
    distinct sites needed the same shape -- the mechanical replacement for a
    human noticing the fifth identical fill. Nothing is REUSED on this
    basis; the stored key stays tight.
    """
    candidates = synthesizer_candidates(entries)  # type: ignore[arg-type]
    print(
        "synthesizer candidates "
        f"(shapes captured at >= {SYNTHESIZER_CANDIDATE_THRESHOLD} distinct sites)"
    )
    if not candidates:
        print("  none — no shape is captured that often yet.")
        return
    for transform, sites in candidates:
        print(f"  {sites:3d} sites  {transform}")


if __name__ == "__main__":
    sys.exit(main())
