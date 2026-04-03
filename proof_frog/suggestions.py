# pylint: disable=duplicate-code
# Type keyword lists necessarily overlap with frog_parser.py
"""Shared utilities for generating error message suggestions.

Used by both frog_parser.py (parse-time heuristics) and
semantic_analysis.py (check-time error messages).
"""

from __future__ import annotations

import os
from collections.abc import Iterable


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)  # pylint: disable=arguments-out-of-order
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(prev_row[j + 1] + 1, curr_row[j] + 1, prev_row[j] + cost)
            )
        prev_row = curr_row
    return prev_row[-1]


# Known FrogLang type names: lowercase -> capitalized
KNOWN_TYPE_NAMES: dict[str, str] = {
    "int": "Int",
    "bool": "Bool",
    "void": "Void",
    "set": "Set",
    "map": "Map",
    "array": "Array",
    "bitstring": "BitString",
    "modint": "ModInt",
    "string": "BitString",
}

# Capitalized type keywords for Levenshtein matching
_TYPE_KEYWORDS = {
    "Int",
    "Bool",
    "Void",
    "Set",
    "Map",
    "BitString",
    "ModInt",
    "Array",
    "RandomFunctions",
}


def suggest_identifier(
    name: str, candidates: Iterable[str], max_distance: int = 2
) -> str | None:
    """Return the closest match to *name* from *candidates*, or None."""
    if len(name) < 3:
        return None
    best: str | None = None
    best_dist = max_distance + 1
    for candidate in candidates:
        if candidate == name:
            continue
        if abs(len(candidate) - len(name)) > max_distance:
            continue
        dist = levenshtein_distance(name, candidate)
        if dist < best_dist:
            best, best_dist = candidate, dist
    return best


def suggest_type(name: str) -> str | None:
    """Suggest a correction for a misspelled or lowercase type name."""
    if len(name) < 3:
        return None
    # Already a valid type keyword — no suggestion needed
    if name in _TYPE_KEYWORDS:
        return None
    # Exact lowercase match
    if name in KNOWN_TYPE_NAMES:
        return KNOWN_TYPE_NAMES[name]
    # Levenshtein against known type keywords.
    # For short names (< 5 chars), require distance 1 to avoid false positives
    # like "Foo" suggesting "Bool" (distance 2).
    max_dist = 2 if len(name) >= 5 else 1
    best: str | None = None
    best_dist = max_dist + 1
    for kw in _TYPE_KEYWORDS:
        if kw == name:
            continue
        if abs(len(kw) - len(name)) > max_dist:
            continue
        dist = levenshtein_distance(name, kw)
        if dist < best_dist:
            best, best_dist = kw, dist
    return best


def suggest_path(failed_path: str) -> str | None:
    """Suggest a corrected path when a file is not found.

    Checks the parent directory for a close match to the filename.
    If the parent doesn't exist, checks one level up for a close
    directory name match.
    """
    if os.path.exists(failed_path):
        return None
    parent = os.path.dirname(failed_path)
    basename = os.path.basename(failed_path)

    # Case 1: parent exists, filename has a typo
    if os.path.isdir(parent):
        siblings = os.listdir(parent)
        suggestion = suggest_identifier(basename, siblings)
        if suggestion:
            return os.path.join(parent, suggestion)
        return None

    # Case 2: parent doesn't exist, directory name has a typo
    grandparent = os.path.dirname(parent)
    parent_name = os.path.basename(parent)
    if os.path.isdir(grandparent):
        sibling_dirs = [
            d
            for d in os.listdir(grandparent)
            if os.path.isdir(os.path.join(grandparent, d))
        ]
        dir_suggestion = suggest_identifier(parent_name, sibling_dirs)
        if dir_suggestion:
            corrected_parent = os.path.join(grandparent, dir_suggestion)
            corrected_path = os.path.join(corrected_parent, basename)
            if os.path.exists(corrected_path):
                return corrected_path
    return None
