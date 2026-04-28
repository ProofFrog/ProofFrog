"""Top-level entry points for LaTeX export."""

from __future__ import annotations

from pathlib import Path


def export_file(path: str, backend_name: str = "cryptocode") -> str:
    """Dispatch on file extension. Returns rendered LaTeX as a string."""
    suffix = Path(path).suffix
    if suffix not in {".primitive", ".scheme", ".game", ".proof"}:
        raise ValueError(f"Unsupported file type for LaTeX export: {suffix}")
    # Per-suffix dispatch is filled in by later tasks.
    _ = backend_name
    return ""
