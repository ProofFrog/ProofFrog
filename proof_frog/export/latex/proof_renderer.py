"""Render a ``.proof`` file to a self-contained LaTeX document."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ... import frog_ast
from . import ir
from .backends.base import Backend
from .expr_renderer import _looks_like_algorithm_name
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer

if TYPE_CHECKING:
    from .proof_context import Hop, ProofContext


def render_proof(
    ctx: "ProofContext",
    backend: Backend,
    macros: MacroRegistry,
    renderer: ModuleRenderer,
    composition: str = "symbolic",
) -> str:
    """Render a proof file to a self-contained LaTeX document.

    ``ctx`` is a ``ProofContext`` that exposes game steps and resolution.
    ``composition`` is either ``"symbolic"`` (default) or ``"inlined"``.

    The body is rendered first so macro registration populates the preamble,
    then the full document is assembled.
    """
    # Make proof-level let types visible to operand disambiguation (`+`/`||`)
    # inside reduction / intermediate-game bodies.
    renderer.base_name_types = ctx.let_types()
    body_parts = [
        _definitions_section(ctx, renderer),
        _construction_section(ctx, renderer),
        _theorem_section(ctx, renderer),
        _games_sequence(ctx, renderer, backend, composition),
    ]

    pkg_lines = []
    for spec in backend.required_packages():
        if spec.options:
            pkg_lines.append(rf"\usepackage[{','.join(spec.options)}]{{{spec.name}}}")
        else:
            pkg_lines.append(rf"\usepackage{{{spec.name}}}")

    parts = [
        r"\documentclass{article}",
        *pkg_lines,
        backend.preamble_extras() or "",
        macros.preamble().rstrip(),
        r"\begin{document}",
        "\n\n".join(p for p in body_parts if p),
        r"\end{document}",
        "",
    ]
    return "\n".join(p for p in parts if p != "")


def _definitions_section(ctx: "ProofContext", renderer: ModuleRenderer) -> str:
    parts = [r"\section*{Definitions}"]
    for game_file in ctx.security_game_files():
        for game in game_file.games:
            parts.append(
                renderer.render_game(game, experiment_name=game_file.get_export_name())
            )
    return "\n\n".join(parts)


def _construction_section(ctx: "ProofContext", renderer: ModuleRenderer) -> str:
    parts = [r"\section*{Construction}"]
    construction_names: set[str] = set()
    for name, root in ctx.let_constructions():
        construction_names.add(name)
        if isinstance(root, frog_ast.Scheme):
            parts.append(renderer.render_scheme(root))
        elif isinstance(root, frog_ast.Primitive):
            parts.append(renderer.render_primitive(root))
    # Remaining lets (e.g. `Group G;`, which is a built-in type rather than a
    # scheme/primitive body) are listed as a typed definition list, matching
    # the v1 construction style so identifiers like `\G` still appear.
    others = [let for let in ctx.proof_file.lets if let.name not in construction_names]
    if others:
        lines = [r"\begin{itemize}"]
        for let in others:
            if _looks_like_algorithm_name(let.name):
                name_tex = renderer.macros.register_algorithm(let.name)
            else:
                name_tex = renderer.expr.render(frog_ast.Variable(let.name))
            lines.append(rf"  \item ${name_tex} : {renderer.types.render(let.type)}$")
        lines.append(r"\end{itemize}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _render_game_ref(
    game: frog_ast.Expression,
    renderer: ModuleRenderer,
    *,
    as_notion: bool,
) -> str:
    """Render a ParameterizedGame / ConcreteGame as a LaTeX reference.

    ``as_notion`` registers the head name via the security-notion macro
    (underscores -> hyphens); otherwise via the algorithm macro. Arguments
    may be Expressions or Types, so each is dispatched accordingly.
    """
    if isinstance(game, frog_ast.ConcreteGame):
        head = _render_game_ref(game.game, renderer, as_notion=as_notion)
        side = renderer.macros.register_algorithm(game.which)
        return f"{head}.{side}"
    if isinstance(game, frog_ast.ParameterizedGame):
        if as_notion:
            head = renderer.macros.register_security_notion(game.name)
        else:
            head = renderer.macros.register_algorithm(game.name)
        if not game.args:
            return head
        rendered_args = [_render_game_arg(a, renderer) for a in game.args]
        return f"{head}({', '.join(rendered_args)})"
    return renderer.expr.render(game)


def _render_game_arg(arg: object, renderer: ModuleRenderer) -> str:
    # Algorithm-like variable args (scheme/group instances such as `G`, `E`)
    # are macroified, matching ModuleRenderer._render_param_name, so a game
    # reference reads `\DDH(\G)` rather than `\DDH(G)`.
    # NOTE: Variable multiply-inherits both Expression and Type, so it
    # satisfies both isinstance checks below and must be tested first. A pure
    # Type (e.g. GroupElemType) is not an Expression, so the Type check must
    # precede the Expression check. Order: Variable -> Type -> Expression.
    if isinstance(arg, frog_ast.Variable) and _looks_like_algorithm_name(arg.name):
        return renderer.macros.register_algorithm(arg.name)
    if isinstance(arg, frog_ast.Type):
        return renderer.types.render(arg)
    if isinstance(arg, frog_ast.Expression):
        return renderer.expr.render(arg)
    return str(arg)


def _theorem_section(ctx: "ProofContext", renderer: ModuleRenderer) -> str:
    hyps = [_render_game_ref(a, renderer, as_notion=True) for a in ctx.assumptions()]
    concl = _render_game_ref(ctx.theorem(), renderer, as_notion=True)
    if hyps:
        joined = " and ".join(f"${h}$" for h in hyps)
        body = (
            f"If indistinguishability holds for {joined}, then "
            f"indistinguishability holds for ${concl}$."
        )
    else:
        body = f"Indistinguishability holds for ${concl}$."
    return (
        r"\begin{theorem}"
        + "\n"
        + body
        + "\n"
        + r"\end{theorem}"
        + "\n\n"
        + r"\noindent\textit{Proof.}"
    )


def _games_sequence(
    ctx: "ProofContext",
    renderer: ModuleRenderer,
    backend: Backend,
    composition: str,
) -> str:
    """Render the full game sequence with hop annotations between figures."""
    steps = ctx.game_steps()
    hops = ctx.hop_kinds()
    chunks: list[str] = []
    for i, step in enumerate(steps):
        if i > 0:
            chunks.append(_hop_annotation(i, hops[i - 1], renderer))
        chunks.append(_step_figure(ctx, step, renderer, backend, i, composition))
    return "\n\n".join(chunks)


def _hop_annotation(i: int, hop: "Hop", renderer: ModuleRenderer) -> str:
    """Render the paragraph annotation for a hop between G_{i-1} and G_i."""
    if hop.kind == "assumption" and hop.assumption is not None:
        ref = _render_game_ref(hop.assumption, renderer, as_notion=True)
        reason = f"by assumption ${ref}$"
    else:
        reason = "interchangeable"
    return (
        rf"\paragraph{{Game $G_{{{i-1}}} \to G_{{{i}}}$.}} "
        rf"({reason}) \todo{{commentary}}"
    )


def _step_figure(
    ctx: "ProofContext",
    step: frog_ast.Step,
    renderer: ModuleRenderer,
    backend: Backend,
    index: int,
    composition: str,
) -> str:
    """Render a single game-step figure in the requested composition mode.

    On any resolution or render failure, prints a warning to stderr and emits
    the raw step text in a ``\\pccomment`` fallback block so partial proofs
    still export.
    """
    caption = f"Game $G_{{{index}}}$"
    label = f"fig:G{index}"
    try:
        if composition == "inlined":
            game = ctx.resolve_inlined(step)
            block = renderer._method_blocks_vstack(
                game
            )  # pylint: disable=protected-access
            body: ir.VStack | ir.ProcedureBlock = block
            return backend.render_figure(
                ir.Figure(body=body, caption=caption, label=label)
            )
        # symbolic mode
        sr = ctx.resolve_symbolic(step)
        challenger_ref = _render_game_ref(sr.challenger, renderer, as_notion=True)
        if sr.reduction_ref is not None:
            comp = _render_game_ref(sr.reduction_ref, renderer, as_notion=False)
            heading = rf"$G_{{{index}}} = {challenger_ref} \circ {comp}$"
        else:
            heading = rf"$G_{{{index}}} = {challenger_ref}$"
        if sr.novel is not None:
            vstack = renderer._method_blocks_vstack(
                sr.novel
            )  # pylint: disable=protected-access
            return backend.render_figure(
                ir.Figure(body=vstack, heading=heading, caption=caption, label=label)
            )
        # start/end step: heading only, referencing the shared sections.
        heading_only = heading + r"\\\textit{(see Definitions and Construction)}"
        return backend.render_figure(
            ir.Figure(body=None, heading=heading_only, caption=caption, label=label)
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        import sys  # pylint: disable=import-outside-toplevel

        print(f"latex-export: could not render step {index}: {exc}", file=sys.stderr)
        return backend.render_figure(
            ir.Figure(
                body=ir.ProcedureBlock(
                    title=caption,
                    lines=[ir.Comment(text=_latex_escape(str(step).rstrip(";")))],
                ),
                caption=caption,
                label=label,
            )
        )


_LATEX_ESC = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(s: str) -> str:
    return "".join(_LATEX_ESC.get(c, c) for c in s)
