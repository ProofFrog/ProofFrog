"""Generic EC-expression text utilities.

String-level helpers for rendered EasyCrypt expression text: safe
parenthesization and top-level argument splitting. Construction-free by
design (the ratified architecture's R9: the exporter knows languages,
not cryptography).
"""

from __future__ import annotations


def paren(expr: str) -> str:
    """Wrap ``expr`` in parens for use as a space-separated op argument."""
    e = expr.strip()
    if e.startswith("(") and e.endswith(")"):
        return e
    return f"({e})" if " " in e else e


def split_top_args(args: str) -> list[str]:
    """Split a rendered ``args`` string on top-level commas (nesting-aware)."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out
