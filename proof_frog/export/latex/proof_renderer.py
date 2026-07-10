"""Render a ``.proof`` file to a self-contained LaTeX document."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ... import frog_ast
from . import ir
from .backends.base import Backend
from .document import assemble
from .expr_renderer import _looks_like_algorithm_name
from .macros import MacroRegistry
from .module_renderer import ModuleRenderer

if TYPE_CHECKING:
    from ...advantage import AdvTerm, AdvantageBound
    from .proof_context import Hop, ProofContext


@dataclass
class _SymbolicHeading:
    """Structured pieces of a symbolic game heading ``G_i = challenger [o R]``.

    Kept alongside each figure so adjacent headings can be diffed component-wise
    (challenger / reduction) and the changed part highlighted -- the symbolic
    analogue of the body-line diff used in inlined mode.
    """

    index: int
    challenger_tex: str
    reduction_tex: str | None
    sections_ref: bool  # start/end step: heading-only, references shared sections


def render_proof(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    ctx: "ProofContext",
    backend: Backend,
    macros: MacroRegistry,
    renderer: ModuleRenderer,
    composition: str = "symbolic",
    standalone: bool = True,
    diff: bool = True,
) -> str:
    """Render a proof file to LaTeX.

    ``ctx`` is a ``ProofContext`` that exposes game steps and resolution.
    ``composition`` is either ``"symbolic"`` (default) or ``"inlined"``.
    ``standalone`` selects a full document (default) or an ``\\input`` fragment.
    ``diff`` (default True) highlights, in each game, the lines that changed
    relative to the previous game (D1).

    The body is rendered first so macro registration populates the preamble,
    then the document (or fragment) is assembled.
    """
    # Make proof-level let types visible to operand disambiguation (`+`/`||`)
    # inside reduction / intermediate-game bodies.
    renderer.base_name_types = ctx.let_types()
    body_parts = [
        _definitions_section(ctx, renderer),
        _construction_section(ctx, renderer),
        _theorem_section(ctx, renderer),
        _games_sequence(ctx, renderer, backend, composition, diff),
    ]
    body = "\n\n".join(p for p in body_parts if p)
    return assemble(backend, macros, body, standalone)


def _definitions_section(ctx: "ProofContext", renderer: ModuleRenderer) -> str:
    parts = [r"\section*{Definitions}"]
    for game_file in ctx.security_game_files():
        parts.append(
            renderer.render_game_file_games(
                game_file.games, experiment_name=game_file.get_export_name()
            )
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


def _adversary_tex(name: str) -> str:
    """Render an adversary label (``B1``, ``A``) as ``\\mathcal{B}_{1}`` etc."""
    letter, rest = name[0], name[1:]
    base = rf"\mathcal{{{letter}}}"
    return base + (rf"_{{{rest}}}" if rest else "")


def _render_adv_term(term: "AdvTerm", renderer: ModuleRenderer) -> str:
    notion = _render_game_ref(term.notion, renderer, as_notion=True)
    return rf"\Adv{{{notion}}}{{{_adversary_tex(term.adversary)}}}"


def _bound_terms(bound: "AdvantageBound", renderer: ModuleRenderer) -> list[str]:
    """The synthesized bound's summands, each as its own LaTeX string.

    Split on a sentinel joiner (rather than ``" + "``) so a term that itself
    contains ``+`` internally is not split. One summand per element, in the
    order ``render`` emits them.
    """
    joined = bound.render(
        term_renderer=lambda t: _render_adv_term(t, renderer),
        mul=r" \cdot ",
        joiner="\x00",
    )
    return [part for part in joined.split("\x00") if part]


def _render_advantage_reference(
    ref: frog_ast.AdvantageReference, renderer: ModuleRenderer
) -> str:
    """Render an ``advantage(notion compose reduction)`` atom as ``\\Adv``.

    The notion renders as a security-notion macro; the reduction (a bare name
    in a claimed bound) as an algorithm macro. A reference with no reduction is
    played directly by the adversary ``A``.
    """
    notion = _render_game_ref(ref.notion, renderer, as_notion=True)
    if ref.reduction is None:
        adversary = r"\mathcal{A}"
    else:
        adversary = _render_game_ref(ref.reduction, renderer, as_notion=False)
    return rf"\Adv{{{notion}}}{{{adversary}}}"


# Numeric operators a claimed bound may use, and their infix LaTeX (``/`` and
# ``^`` are handled specially -- fraction and superscript -- so are absent).
_CLAIM_INFIX: dict[frog_ast.BinaryOperators, str] = {
    frog_ast.BinaryOperators.ADD: "+",
    frog_ast.BinaryOperators.SUBTRACT: "-",
    frog_ast.BinaryOperators.MULTIPLY: r"\cdot",
}


def _render_claimed_bound(
    expr: frog_ast.Expression, renderer: ModuleRenderer, parent_prec: int = 0
) -> str:
    """Render a claimed ``bound:`` expression to LaTeX math.

    Precedence-aware (the shared ``ExprRenderer`` is not, so it is used only for
    leaves): ``/`` becomes a ``\\frac``, ``^`` a braced superscript, and ``+``
    ``-`` ``*`` are parenthesized by operator precedence. ``advantage(...)``
    atoms become ``\\Adv`` terms and ``count_<Oracle>`` a query-count symbol
    ``q_{<Oracle>}``; any other leaf defers to the expression renderer.
    """
    if isinstance(expr, frog_ast.AdvantageReference):
        return _render_advantage_reference(expr, renderer)
    if isinstance(expr, frog_ast.BinaryOperation) and expr.operator in (
        *_CLAIM_INFIX,
        frog_ast.BinaryOperators.DIVIDE,
        frog_ast.BinaryOperators.EXPONENTIATE,
    ):
        op = expr.operator
        left, right = expr.left_expression, expr.right_expression
        if op == frog_ast.BinaryOperators.DIVIDE:
            num = _render_claimed_bound(left, renderer, 0)
            den = _render_claimed_bound(right, renderer, 0)
            return rf"\frac{{{num}}}{{{den}}}"
        if op == frog_ast.BinaryOperators.EXPONENTIATE:
            base = _render_claimed_bound(left, renderer, 99)
            if isinstance(left, frog_ast.BinaryOperation):
                base = f"({base})"
            return f"{base}^{{{_render_claimed_bound(right, renderer, 0)}}}"
        prec = op.precedence()
        # The right operand of a left-associative subtraction needs a tighter
        # threshold so ``a - (b + c)`` keeps its parentheses.
        right_prec = prec + (1 if op == frog_ast.BinaryOperators.SUBTRACT else 0)
        rendered = (
            f"{_render_claimed_bound(left, renderer, prec)} {_CLAIM_INFIX[op]} "
            f"{_render_claimed_bound(right, renderer, right_prec)}"
        )
        return f"({rendered})" if prec < parent_prec else rendered
    if isinstance(expr, frog_ast.UnaryOperation):
        if expr.operator == frog_ast.UnaryOperators.SIZE:
            return (
                rf"\left|{_render_claimed_bound(expr.expression, renderer, 0)}\right|"
            )
        if expr.operator == frog_ast.UnaryOperators.MINUS:
            return f"-{_render_claimed_bound(expr.expression, renderer, 5)}"
    if isinstance(expr, frog_ast.Variable) and expr.name.startswith("count_"):
        oracle = expr.name[len("count_") :]
        return rf"q_{{\mathsf{{{oracle}}}}}"
    return renderer.expr.render(expr)


def _flatten_sum(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """Split a top-level ``+`` chain into its summands (left to right)."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.ADD
    ):
        return _flatten_sum(expr.left_expression) + _flatten_sum(expr.right_expression)
    return [expr]


def _claimed_bound_terms(
    expr: frog_ast.Expression, renderer: ModuleRenderer
) -> list[str]:
    """The claimed bound's summands, each as its own LaTeX string."""
    return [_render_claimed_bound(term, renderer) for term in _flatten_sum(expr)]


def _claimed_bound_reductions(
    expr: frog_ast.Expression,
) -> list[frog_ast.ParameterizedGame]:
    """Distinct reductions named by ``advantage(... compose R)`` atoms, in order."""
    found: list[frog_ast.ParameterizedGame] = []
    seen: set[str] = set()

    def walk(node: frog_ast.ASTNode) -> None:
        if isinstance(node, frog_ast.AdvantageReference):
            if node.reduction is not None and node.reduction.name not in seen:
                seen.add(node.reduction.name)
                found.append(node.reduction)
            return
        for attr in vars(node):
            value = getattr(node, attr)
            for child in value if isinstance(value, (list, tuple)) else [value]:
                if isinstance(child, frog_ast.ASTNode):
                    walk(child)

    walk(expr)
    return found


def _bound_display(lhs: str, terms: list[str]) -> str:
    """Render ``lhs <= t1 + t2 + ...`` as a broken ``align*`` display.

    The summands go one per line (broken at each ``+``), continuation lines
    aligned just past the ``\\le``. Breaking the sum keeps even a many-term
    bound within the text width, where a single inline or displayed line would
    overflow.
    """
    rows = [rf"{lhs} &\le {terms[0]}"]
    rows += [rf"&\quad + {term}" for term in terms[1:]]
    body = " \\\\\n".join(rows)
    return "\\begin{align*}\n" + body + "\n\\end{align*}"


def _bound_sentence(lhs: str, terms: list[str], adversaries: list[str]) -> str:
    """The concrete-security statement appended to the theorem.

    The bound renders as a displayed ``align*`` so a long sum wraps cleanly.
    ``adversaries`` is the list of already-``$``-wrapped constructed-adversary
    names, named in a trailing "runs in approximately the time of A" clause when
    present (the usual case; a purely directly-played bound has none).
    """
    sentence = (
        r" Concretely, for every adversary $\mathcal{A}$,"
        + "\n"
        + _bound_display(lhs, terms)
    )
    if adversaries:
        names = ", ".join(adversaries)
        sentence += (
            f"\nwhere each of {names} runs in approximately the time of "
            r"$\mathcal{A}$."
        )
    return sentence


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
    lhs = rf"\Adv{{{concl}}}{{\mathcal{{A}}}}"
    claimed = ctx.claimed_bound()
    if claimed is not None:
        # The author stated the bound explicitly: display it (the intended,
        # human-readable form) rather than the synthesized one.
        terms = _claimed_bound_terms(claimed, renderer)
        adversaries = [
            f"${_render_game_ref(r, renderer, as_notion=False)}$"
            for r in _claimed_bound_reductions(claimed)
        ]
        body += _bound_sentence(lhs, terms, adversaries)
    else:
        bound = ctx.advantage_bound()
        if bound.supported:
            adversaries = [
                f"${_adversary_tex(t.adversary)}$"
                for t in bound.terms.values()
                if t.adversary != "A"
            ]
            body += _bound_sentence(lhs, _bound_terms(bound, renderer), adversaries)
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
    diff: bool,
) -> str:
    """Render the full game sequence with hop annotations between figures.

    Figures are built as IR first so the diff pass (D1) can run before the
    backend turns the IR into LaTeX. Both modes highlight changed *body lines*
    (``mark_diff``); symbolic mode adds two things, because there the delta also
    lives in the heading and a reduction is often repeated verbatim:

    * **inlined** -- each step is a full game; only the changed body lines are
      highlighted.
    * **symbolic** -- the body is a reduction (or intermediate game). Changed
      body lines are still highlighted (``R`` vs ``Rprime`` genuinely differ),
      *and* the changed heading component (which security game the reduction is
      composed with) is highlighted. A reduction body that repeats the previous
      game's verbatim is not redrawn -- its assumption-hop twin points back to
      it (``_apply_symbolic_diff``).
    """
    # pylint: disable=import-outside-toplevel
    from .diff import mark_diff

    steps = ctx.game_steps()
    hops = ctx.hop_kinds()
    bound = ctx.advantage_bound()
    # Per-hop loss terms align 1:1 with `hops` (both are one-per-transition in
    # game-step order) when the bound synthesized; otherwise annotate without a
    # loss term.
    hop_terms: list["AdvTerm | None"] = (
        bound.hop_terms
        if bound.supported and len(bound.hop_terms) == len(hops)
        else [None] * len(hops)
    )
    built = [
        _step_figure_ir(ctx, step, renderer, i, composition)
        for i, step in enumerate(steps)
    ]
    figures = [fig for fig, _ in built]
    headings = [head for _, head in built]
    if composition == "symbolic":
        _apply_symbolic_diff(figures, headings, backend, diff)
    elif diff:
        for i in range(1, len(figures)):
            mark_diff(figures[i - 1].body, figures[i].body)
    chunks: list[str] = []
    for i, fig in enumerate(figures):
        if i > 0:
            chunks.append(_hop_annotation(i, hops[i - 1], renderer, hop_terms[i - 1]))
        chunks.append(backend.render_figure(fig))
    return "\n\n".join(chunks)


def _apply_symbolic_diff(
    figures: list[ir.Figure],
    headings: list["_SymbolicHeading | None"],
    backend: Backend,
    diff: bool,
) -> None:
    """Highlight changed body lines + heading deltas, and de-dup repeats.

    Mutates ``figures`` in place. For each game (against its predecessor):

    * if the body repeats the predecessor's verbatim, drop it and point back
      (the assumption-hop twin: same reduction, different composed challenger);
    * otherwise highlight the body lines that changed (``mark_diff``) -- e.g.
      ``R`` vs ``Rprime`` differ line by line;
    * (re)assemble the heading, highlighting the challenger/reduction component
      that changed.

    The body comparison uses the predecessor's *original* body, so a game still
    diffs against the reduction drawn above it even when the intervening twin
    was collapsed. Figures with no structured heading (the error fallback) are
    left untouched. Skipped entirely when ``diff`` is off, so ``--no-diff``
    draws every game in full with no highlighting.
    """
    if not diff:
        return
    # pylint: disable=import-outside-toplevel
    from .diff import bodies_equal, mark_diff

    original_bodies = [fig.body for fig in figures]
    for i, head in enumerate(headings):
        if head is None:
            continue
        prev = headings[i - 1] if i > 0 else None
        prev_body = original_bodies[i - 1] if i > 0 else None
        deduped_from: int | None = None
        if figures[i].body is not None and prev_body is not None:
            if bodies_equal(prev_body, figures[i].body):
                figures[i].body = None
                deduped_from = i - 1
            else:
                mark_diff(prev_body, figures[i].body)
        figures[i].heading = _symbolic_heading_tex(head, prev, backend, deduped_from)


def _symbolic_heading_tex(
    head: "_SymbolicHeading",
    prev: "_SymbolicHeading | None",
    backend: Backend,
    deduped_from: int | None,
) -> str:
    """Assemble the ``$G_i = ...$`` heading, highlighting changed components."""
    challenger = head.challenger_tex
    if prev is not None and prev.challenger_tex != challenger:
        challenger = backend.highlight(challenger)
    body_tex = challenger
    if head.reduction_tex is not None:
        reduction = head.reduction_tex
        if prev is not None and prev.reduction_tex != reduction:
            reduction = backend.highlight(reduction)
        body_tex = rf"{body_tex} \circ {reduction}"
    math = rf"$G_{{{head.index}}} = {body_tex}$"
    if head.sections_ref:
        return math + r"\\\textit{(see Definitions and Construction)}"
    if deduped_from is not None:
        return math + rf"\\\textit{{(reduction as in $G_{{{deduped_from}}}$)}}"
    return math


def _hop_annotation(
    i: int,
    hop: "Hop",
    renderer: ModuleRenderer,
    loss: "AdvTerm | None" = None,
) -> str:
    """Render the paragraph annotation for a hop between G_{i-1} and G_i.

    When the hop contributes a loss term to the advantage bound (a
    reduction/assumption hop), it is appended as ``losing $\\Adv{...}$``.
    """
    if hop.kind == "assumption" and hop.assumption is not None:
        ref = _render_game_ref(hop.assumption, renderer, as_notion=True)
        reason = f"by assumption ${ref}$"
    else:
        reason = "interchangeable"
    if loss is not None:
        reason += f", losing ${_render_adv_term(loss, renderer)}$"
    return (
        rf"\paragraph{{Game $G_{{{i-1}}} \to G_{{{i}}}$.}} "
        rf"({reason}) \todo{{commentary}}"
    )


def _step_figure_ir(
    ctx: "ProofContext",
    step: frog_ast.Step,
    renderer: ModuleRenderer,
    index: int,
    composition: str,
) -> tuple[ir.Figure, "_SymbolicHeading | None"]:
    """Build the IR ``Figure`` for one game step, plus its symbolic heading.

    Returning IR rather than a LaTeX string lets the caller run the diff pass
    over adjacent games before the backend renders them. Macro registration
    still happens here (during body construction), so the preamble is populated
    regardless of when rendering occurs.

    In symbolic mode the returned ``_SymbolicHeading`` carries the heading's
    structured pieces; ``_apply_symbolic_diff`` assembles the final
    ``figure.heading`` from it. In inlined mode (and on the error fallback) the
    second element is ``None``.

    On any resolution or render failure, prints a warning to stderr and emits
    the raw step text in a ``\\pccomment`` fallback block so partial proofs
    still export.
    """
    caption = f"Game $G_{{{index}}}$"
    label = f"fig:G{index}"
    try:
        if composition == "inlined":
            game = ctx.resolve_inlined(step)
            block = renderer._method_blocks_vstack(  # pylint: disable=protected-access
                game
            )
            return ir.Figure(body=block, caption=caption, label=label), None
        # symbolic mode
        sr = ctx.resolve_symbolic(step)
        challenger_ref = _render_game_ref(sr.challenger, renderer, as_notion=True)
        reduction_ref: str | None = None
        if sr.reduction_ref is not None:
            reduction_ref = _render_game_ref(
                sr.reduction_ref, renderer, as_notion=False
            )
        head = _SymbolicHeading(
            index=index,
            challenger_tex=challenger_ref,
            reduction_tex=reduction_ref,
            sections_ref=sr.novel is None,
        )
        if sr.novel is not None:
            vstack = renderer._method_blocks_vstack(  # pylint: disable=protected-access
                sr.novel
            )
            # heading is assembled later by _apply_symbolic_diff from `head`.
            return ir.Figure(body=vstack, caption=caption, label=label), head
        # start/end step: heading only, referencing the shared sections.
        return ir.Figure(body=None, caption=caption, label=label), head
    except Exception as exc:  # pylint: disable=broad-exception-caught
        import sys  # pylint: disable=import-outside-toplevel

        print(f"latex-export: could not render step {index}: {exc}", file=sys.stderr)
        return (
            ir.Figure(
                body=ir.ProcedureBlock(
                    title=caption,
                    lines=[ir.Comment(text=_latex_escape(str(step).rstrip(";")))],
                ),
                caption=caption,
                label=label,
            ),
            None,
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
