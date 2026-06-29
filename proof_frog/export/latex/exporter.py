"""Top-level entry points for LaTeX export."""

from __future__ import annotations

from pathlib import Path

from ... import frog_parser
from .backends.cryptocode import CryptocodeBackend
from .backends.base import Backend
from .document import assemble
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer

_BACKENDS: dict[str, type[Backend]] = {"cryptocode": CryptocodeBackend}  # type: ignore[type-abstract]


def _make_backend(name: str, diff_style: str = "box") -> Backend:
    if name not in _BACKENDS:
        raise ValueError(f"Unknown LaTeX backend: {name}")
    return _BACKENDS[name](diff_style=diff_style)  # type: ignore[abstract,call-arg]


def export_file(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
