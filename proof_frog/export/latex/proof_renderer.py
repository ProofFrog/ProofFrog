"""Render a ``.proof`` file to a self-contained LaTeX document."""

from __future__ import annotations

from ... import frog_ast, frog_parser
from . import ir
from .backends.base import Backend
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer


def render_proof(
    path: str,
    backend: Backend,
    macros: MacroRegistry,
    renderer: ModuleRenderer,
) -> str:
    proof = frog_parser.parse_proof_file(path)

    pkg_lines = []
    for spec in backend.required_packages():
        if spec.options:
            pkg_lines.append(rf"\usepackage[{','.join(spec.options)}]{{{spec.name}}}")
        else:
            pkg_lines.append(rf"\usepackage{{{spec.name}}}")

    body_parts: list[str] = []
    body_parts.append(_construction_section(proof, renderer))
    body_parts.append(_theorem_section(proof, renderer))
    body_parts.append(_games_sequence(proof, renderer, backend))

    parts = [
        r"\documentclass{article}",
        *pkg_lines,
        backend.preamble_extras() or "",
        macros.preamble().rstrip(),
        r"\begin{document}",
        "\n\n".join(s for s in body_parts if s),
        r"\end{document}",
        "",
    ]
    return "\n".join(p for p in parts if p != "")


def _construction_section(proof: frog_ast.ProofFile, renderer: ModuleRenderer) -> str:
    if not proof.lets:
        return ""
    lines = [r"\section*{Construction}", r"\begin{itemize}"]
    for let in proof.lets:
        ty = renderer.types.render(let.type)
        lines.append(rf"  \item ${let.name} : {ty}$")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _theorem_section(proof: frog_ast.ProofFile, renderer: ModuleRenderer) -> str:
    theorem_str = renderer.expr.render(proof.theorem)
    return (
        r"\begin{theorem}"
        + "\n"
        + theorem_str
        + "\n"
        + r"\end{theorem}"
        + "\n\n"
        + r"\noindent\textit{Proof.}"
    )


def _games_sequence(
    proof: frog_ast.ProofFile,
    renderer: ModuleRenderer,
    backend: Backend,
) -> str:
    chunks: list[str] = []
    helpers_by_name = {g.name: g for g in proof.helpers}
    for i, step in enumerate(proof.steps):
        chunks.append(rf"\paragraph{{Game $G_{{{i}}}$.}} \todo{{commentary}}")
        figure = _step_figure(step, helpers_by_name, renderer, backend, i)
        if figure:
            chunks.append(figure)
    return "\n\n".join(chunks)


def _step_figure(
    step: frog_ast.ProofStep,
    helpers_by_name: dict[str, frog_ast.Game],
    renderer: ModuleRenderer,
    backend: Backend,
    index: int,
) -> str:
    game_obj: frog_ast.Game | None = None
    if isinstance(step, frog_ast.Step):
        challenger = step.challenger
        if isinstance(challenger, (frog_ast.ConcreteGame, frog_ast.ParameterizedGame)):
            name = _game_name(challenger)
            if name in helpers_by_name:
                game_obj = helpers_by_name[name]
    if game_obj is None:
        body: ir.VStack | ir.ProcedureBlock = ir.ProcedureBlock(
            title=f"G_{{{index}}}",
            lines=[ir.Comment(text=str(step).rstrip(";"))],
        )
    else:
        method_blocks = [
            renderer._method_block(  # pylint: disable=protected-access
                m, renderer.macros.register_algorithm(game_obj.name)
            )
            for m in game_obj.methods
        ]
        body = ir.VStack(blocks=method_blocks, boxed=True)
    return backend.render_figure(
        ir.Figure(body=body, caption=f"Game $G_{{{index}}}$", label=f"fig:G{index}")
    )


def _game_name(g: frog_ast.Expression) -> str:
    if isinstance(g, frog_ast.ConcreteGame):
        # ConcreteGame has .game (ParameterizedGame) and .which (left/right name)
        inner = getattr(g, "game", None)
        if inner is not None:
            return _game_name(inner)
    if isinstance(g, frog_ast.ParameterizedGame):
        return getattr(g, "name", "")
    return ""
