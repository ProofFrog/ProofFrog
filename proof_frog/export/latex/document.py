"""Document assembly for LaTeX export.

A leaf module: ``assemble`` wraps a rendered body as a standalone document or
an ``\\input``-able fragment. It lives here (rather than in ``exporter``) so
both ``exporter`` and ``proof_renderer`` can import it without forming an
import cycle.
"""

from __future__ import annotations

from .backends.base import Backend
from .macros import MacroRegistry


def _package_lines(backend: Backend) -> list[str]:
    lines = []
    for spec in backend.required_packages():
        if spec.options:
            lines.append(rf"\usepackage[{','.join(spec.options)}]{{{spec.name}}}")
        else:
            lines.append(rf"\usepackage{{{spec.name}}}")
    return lines


def _fragment(backend: Backend, macros: MacroRegistry, body: str) -> str:
    """Assemble an ``\\input``-able fragment (no document wrapper).

    Packages and ``preamble_extras`` (e.g. ``\\newtheorem``) cannot appear in
    the document body, so they are listed in a commented header for the user
    to copy into their own preamble. The generated ``\\providecommand`` macros
    *can* live in the body and are emitted inline so a bare ``\\input`` works
    without hand-copying them; ``\\providecommand`` yields to any definition the
    user already has, so inlining is safe.
    """
    preamble: list[str] = list(_package_lines(backend))
    extras = backend.preamble_extras()
    if extras:
        preamble.extend(extras.splitlines())
    header = [
        "% --- ProofFrog LaTeX export (fragment; \\input this file) ---",
        "% Add the following lines to your document preamble:",
        *(f"% {line}" for line in preamble),
        "% The \\providecommand macros below may stay inline (they yield to",
        "% any definitions already in your preamble).",
        "% -----------------------------------------------------------",
    ]
    parts = [
        "\n".join(header),
        macros.preamble().rstrip(),
        body,
        "",
    ]
    return "\n".join(p for p in parts if p != "")


def assemble(
    backend: Backend, macros: MacroRegistry, body: str, standalone: bool = True
) -> str:
    """Wrap a rendered ``body`` as a full document or an ``\\input`` fragment."""
    if not standalone:
        return _fragment(backend, macros, body)
    extras = backend.preamble_extras()
    parts = [
        r"\documentclass{article}",
        # Page geometry is document-level, so it lives only in the self-contained
        # build; an \input fragment inherits the host document's margins.
        r"\usepackage[letterpaper,margin=1in]{geometry}",
        *_package_lines(backend),
        *([extras] if extras else []),
        macros.preamble().rstrip(),
        r"\begin{document}",
        body,
        r"\end{document}",
        "",
    ]
    return "\n".join(p for p in parts if p != "")
