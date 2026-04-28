"""Top-level entry points for LaTeX export."""

from __future__ import annotations

from pathlib import Path

from ... import frog_parser
from .backends.cryptocode import CryptocodeBackend
from .backends.base import Backend
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer

_BACKENDS: dict[str, type[Backend]] = {"cryptocode": CryptocodeBackend}  # type: ignore[type-abstract]


def _make_backend(name: str) -> Backend:
    if name not in _BACKENDS:
        raise ValueError(f"Unknown LaTeX backend: {name}")
    return _BACKENDS[name]()  # type: ignore[abstract]


def _document(backend: Backend, macros: MacroRegistry, body: str) -> str:
    pkg_lines = []
    for spec in backend.required_packages():
        if spec.options:
            pkg_lines.append(rf"\usepackage[{','.join(spec.options)}]{{{spec.name}}}")
        else:
            pkg_lines.append(rf"\usepackage{{{spec.name}}}")
    extras = backend.preamble_extras()
    parts = [
        r"\documentclass{article}",
        *pkg_lines,
        *([extras] if extras else []),
        macros.preamble().rstrip(),
        r"\begin{document}",
        body,
        r"\end{document}",
        "",
    ]
    return "\n".join(parts)


def export_file(path: str, backend_name: str = "cryptocode") -> str:
    """Dispatch on file extension. Returns rendered LaTeX as a string."""
    suffix = Path(path).suffix
    backend = _make_backend(backend_name)
    macros = MacroRegistry()
    renderer = ModuleRenderer(backend, macros)

    if suffix == ".primitive":
        ast = frog_parser.parse_primitive_file(path)
        body = renderer.render_primitive(ast)
        return _document(backend, macros, body)
    if suffix == ".scheme":
        ast_s = frog_parser.parse_scheme_file(path)
        body = renderer.render_scheme(ast_s)
        return _document(backend, macros, body)
    if suffix == ".game":
        game_file = frog_parser.parse_game_file(path)
        chunks = []
        for game in game_file.games:
            chunks.append(renderer.render_game(game, experiment_name=game_file.name))
        body = "\n\n".join(chunks)
        return _document(backend, macros, body)
    if suffix == ".proof":
        # pylint: disable=import-outside-toplevel
        from .proof_renderer import render_proof

        return render_proof(path, backend, macros, renderer)
    raise ValueError(f"Unsupported file type for LaTeX export: {suffix}")
