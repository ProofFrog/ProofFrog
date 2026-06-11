"""Top-level entry points for LaTeX export."""

from __future__ import annotations

from pathlib import Path

from ... import frog_parser
from .backends.cryptocode import CryptocodeBackend
from .backends.base import Backend
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer

_BACKENDS: dict[str, type[Backend]] = {"cryptocode": CryptocodeBackend}  # type: ignore[type-abstract]


def _make_backend(name: str, diff_style: str = "box") -> Backend:
    if name not in _BACKENDS:
        raise ValueError(f"Unknown LaTeX backend: {name}")
    return _BACKENDS[name](diff_style=diff_style)  # type: ignore[abstract,call-arg]


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


def export_file(
    path: str,
    backend_name: str = "cryptocode",
    composition: str = "symbolic",
    standalone: bool = True,
    diff: bool = True,
    diff_style: str = "box",
) -> str:
    """Dispatch on file extension. Returns rendered LaTeX as a string.

    ``standalone`` controls whether the output is a complete document
    (default) or an ``\\input``-able fragment for inclusion in a larger file.
    ``diff`` (proof files only) highlights, in each game, the lines that
    changed relative to the previous game; ``diff_style`` is ``"box"`` (gray
    ``\\gamechange`` box) or ``"color"`` (colored text).
    """
    suffix = Path(path).suffix
    backend = _make_backend(backend_name, diff_style)
    macros = MacroRegistry()
    renderer = ModuleRenderer(backend, macros)

    if suffix == ".primitive":
        ast = frog_parser.parse_primitive_file(path)
        body = renderer.render_primitive(ast)
        return assemble(backend, macros, body, standalone)
    if suffix == ".scheme":
        # desugar=False keeps tuple-destructuring bindings intact for faithful
        # rendering; the module path never reaches the proof engine.
        ast_s = frog_parser.parse_scheme_file(path, desugar=False)
        body = renderer.render_scheme(ast_s)
        return assemble(backend, macros, body, standalone)
    if suffix == ".game":
        game_file = frog_parser.parse_game_file(path, desugar=False)
        body = renderer.render_game_file_games(
            game_file.games, experiment_name=game_file.name
        )
        return assemble(backend, macros, body, standalone)
    if suffix == ".proof":
        # pylint: disable=import-outside-toplevel
        from .proof_renderer import render_proof
        from .proof_context import ProofContext

        ctx = ProofContext(path)
        return render_proof(
            ctx,
            backend,
            macros,
            renderer,
            composition=composition,
            standalone=standalone,
            diff=diff,
        )
    raise ValueError(f"Unsupported file type for LaTeX export: {suffix}")
