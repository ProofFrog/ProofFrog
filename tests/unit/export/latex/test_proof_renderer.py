"""Tests for proof_renderer helpers added in Task 4."""

from proof_frog import frog_ast, frog_parser
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.module_renderer import ModuleRenderer
from proof_frog.export.latex.proof_context import ProofContext
from proof_frog.export.latex import proof_renderer as pr

DDH = "examples/Proofs/Group/DDH_implies_CDH.proof"
MULTICHAL = "examples/Proofs/PubKeyEnc/INDCPA_implies_INDCPA_MultiChal.proof"
CFRG_LEAK = (
    "examples/applications/cfrg-hybrid-kems/proofs/CG/CG_expanded_LEAK_BIND_K_CT.proof"
)


def _claim(src: str) -> frog_ast.Expression:
    """Parse a ``bound:`` expression via a minimal (parse-only) proof file."""
    pf = frog_parser.parse_proof_file(
        "proof:\ntheorem:\n  Foo(E);\nbound:\n  "
        f"{src};\ngames:\n  Foo(E).Left against Foo(E).Adversary;\n"
    )
    assert pf.claimed_bound is not None
    return pf.claimed_bound.bound


def _renderer():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    return backend, macros, ModuleRenderer(backend, macros)


def test_render_game_ref_parameterized_as_notion():
    _b, macros, mr = _renderer()
    g = frog_ast.ParameterizedGame("DDH", [frog_ast.Variable("G")])
    out = pr._render_game_ref(g, mr, as_notion=True)
    assert out == r"\DDH(\G)"


def test_theorem_combined_hypothesis_form():
    _b, _m, mr = _renderer()
    ctx = ProofContext(DDH)
    out = pr._theorem_section(ctx, mr)
    assert r"\begin{theorem}" in out
    assert "If indistinguishability holds for" in out
    assert r"\DDH(\G)" in out
    assert r"\CDH(\G)" in out
    assert "% unsupported" not in out


def test_theorem_includes_concrete_advantage_bound():
    _b, _m, mr = _renderer()
    ctx = ProofContext(DDH)
    out = pr._theorem_section(ctx, mr)
    # A concrete-security inequality is displayed for the theorem's advantage,
    # broken across lines so a multi-term sum stays within the text width.
    assert "Concretely" in out
    assert r"\begin{align*}" in out
    assert r"\Adv{\CDH(\G)}{\mathcal{A}} &\le" in out
    assert r"&\quad +" in out
    # The two reductions become distinct constructed adversaries.
    assert r"\mathcal{B}_{1}" in out
    assert r"\mathcal{B}_{2}" in out


def test_claimed_bound_renders_advantage_term_with_named_reduction():
    _b, _m, mr = _renderer()
    out = pr._render_claimed_bound(_claim("advantage(PRFSecurity(F) compose R_PRF)"), mr)
    assert out == r"\Adv{\PRFSecurity(\F)}{\RPRF}"


def test_claimed_bound_direct_reference_uses_adversary_A():
    _b, _m, mr = _renderer()
    out = pr._render_claimed_bound(_claim("advantage(DDH(G))"), mr)
    assert out == r"\Adv{\DDH(\G)}{\mathcal{A}}"


def test_claimed_bound_renders_fraction_and_query_count():
    _b, _m, mr = _renderer()
    out = pr._render_claimed_bound(
        _claim("count_CTXT * (count_CTXT - 1) / |BitString<F.in>|"), mr
    )
    # Division becomes a fraction; per-oracle counts become query-count symbols;
    # the subtraction stays parenthesized under the multiplication.
    assert r"\frac{" in out
    assert r"q_{\mathsf{CTXT}}" in out
    assert r"(q_{\mathsf{CTXT}} - 1)" in out
    assert r"\left|" in out


def test_claimed_bound_exponent():
    _b, _m, mr = _renderer()
    out = pr._render_claimed_bound(_claim("2 ^ (1 - lambda)"), mr)
    assert out == r"2^{1 - \lambda}"


def test_claimed_bound_multi_term_breaks_into_align():
    _b, _m, mr = _renderer()
    terms = pr._claimed_bound_terms(
        _claim("advantage(PRFSecurity(F) compose R1) + advantage(PRGSec(G) compose R2)"),
        mr,
    )
    assert len(terms) == 2
    display = pr._bound_display(r"\Adv{\X}{\mathcal{A}}", terms)
    assert display.startswith(r"\begin{align*}")
    assert display.endswith(r"\end{align*}")
    # First summand after `\le`, each further summand on its own `+` line.
    assert r"&\le \Adv{\PRFSecurity(\F)}{\ROne}" in display
    assert display.count(r"&\quad +") == 1
    assert display.count(r"\\") == 1


def test_theorem_prefers_claimed_bound_over_synthesized():
    _b, _m, mr = _renderer()
    ctx = ProofContext(CFRG_LEAK)
    out = pr._theorem_section(ctx, mr)
    assert "Concretely" in out
    assert r"\begin{align*}" in out
    # The claimed bound names its reductions as the constructed adversaries...
    assert r"\Adv{\LEAKBINDKCT(\KEMPQ)}{\RPQBind}" in out
    # ...not the synthesized B1/B2 placeholders.
    assert r"\mathcal{B}_{1}" not in out
    assert "% unsupported" not in out


def test_theorem_falls_back_to_synthesized_without_claim():
    # DDH proof has no bound: clause, so the synthesized B1/B2 form is used.
    _b, _m, mr = _renderer()
    ctx = ProofContext(DDH)
    assert ctx.claimed_bound() is None
    out = pr._theorem_section(ctx, mr)
    assert r"\mathcal{B}_{1}" in out


def test_hop_annotation_assumption_states_prose_bound():
    _b, _m, mr = _renderer()
    loss_hop = pr._hop_annotation(
        1,
        _make_assumption_hop(),
        mr,
        loss=_make_adv_term(),
    )
    # Prose names the assumption and states the advantage bound inequality.
    assert r"\DDH(\G)" in loss_hop
    assert r"\le" in loss_hop
    assert r"\Adv{" in loss_hop
    assert r"\Pr[G_{0} = 1]" in loss_hop
    # An invisible author-commentary placeholder follows (a LaTeX comment).
    assert "% commentary (author)" in loss_hop
    # An equivalence hop states perfect indistinguishability, with no bound.
    plain = pr._hop_annotation(1, _make_interchangeable_hop(), mr, loss=None)
    assert "perfectly indistinguishable" in plain
    assert r"\le" not in plain
    assert r"\Pr[G_{0} = 1] = \Pr[G_{1} = 1]" in plain


def _make_assumption_hop():
    from proof_frog.export.latex.proof_context import Hop

    return Hop(
        "assumption", frog_ast.ParameterizedGame("DDH", [frog_ast.Variable("G")])
    )


def _make_interchangeable_hop():
    from proof_frog.export.latex.proof_context import Hop

    return Hop("interchangeable", None)


def _make_adv_term():
    from proof_frog.advantage import AdvTerm

    return AdvTerm(
        notion=frog_ast.ParameterizedGame("DDH", [frog_ast.Variable("G")]),
        adversary="B1",
    )


def test_definitions_section_renders_both_sides():
    _b, _m, mr = _renderer()
    ctx = ProofContext(DDH)
    out = pr._definitions_section(ctx, mr)
    assert r"\section*{Definitions}" in out
    # CDH game file has two sides; both rendered as games
    assert out.count(r"\begin{pcvstack}") >= 2


def test_construction_section_renders_let_primitive():
    _b, _m, mr = _renderer()
    ctx = ProofContext(DDH)
    out = pr._construction_section(ctx, mr)
    assert r"\section*{Construction}" in out
    assert r"\G" in out


def test_render_proof_symbolic_has_games_and_hops():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(ctx, backend, macros, mr, composition="symbolic")
    assert r"\documentclass{article}" in out
    assert r"\section*{Definitions}" in out
    assert r"\section*{Construction}" in out
    assert r"\begin{theorem}" in out
    # The proof body is an amsthm proof environment, not floating figures.
    assert r"\begin{proof}" in out
    assert r"\end{proof}" in out
    assert r"\begin{figure}" not in out
    # One non-floating, centered game block per game step (reading order).
    assert out.count(r"\begin{center}") == len(ctx.game_steps())
    # symbolic label uses composition
    assert r"\circ" in out
    # prose hop annotations present
    assert ("perfectly indistinguishable" in out) or ("differ only in" in out)
    # The games sequence itself should not have fallback comments (the
    # Definitions section may have % unsupported for exotic types like
    # ModIntType, which is a separate pre-existing limitation).
    games_seq = out[out.find(r"\begin{proof}") :]
    assert "% unsupported" not in games_seq
    # Structural: the symbolic heading must NOT be packed into a procedure
    # title (that would double-wrap it), and a reduction step's novel game must
    # render as a top-level boxed vstack, not nested inside a \procedure body.
    assert "{$Game " not in out
    assert r"\begin{pcvstack}" in out


def test_concrete_game_count_renders_without_unsupported():
    # `INDCPA(E).Left.count == 1` is a FieldAccess on a ConcreteGame; it must
    # not fall through to the `% unsupported` branch (which, placed inside a
    # `$...$` hop annotation, would emit a bare `%` and break pdflatex).
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(MULTICHAL)
    out = pr.render_proof(ctx, backend, macros, mr, composition="symbolic")
    assert "% unsupported" not in out


def test_render_proof_inlined_runs_clean():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined")
    # One non-floating centered game block per step; no floats.
    assert out.count(r"\begin{center}") == len(ctx.game_steps())
    assert r"\begin{figure}" not in out
    assert r"\end{document}" in out


def test_render_proof_diff_highlights_changes_by_default():
    # D1: diff highlighting is on by default in proofs. The inlined game
    # sequence has adjacent full games that differ, so at least one changed
    # line gets a soft \pfhighlight tint.
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(MULTICHAL)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined")
    assert r"\pfhighlight{" in out


def test_render_proof_no_diff_suppresses_highlight():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(MULTICHAL)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined", diff=False)
    assert r"\pfhighlight{" not in out


def _symbolic_ddh(diff=True):
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(ctx, backend, macros, mr, composition="symbolic", diff=diff)
    return ctx, out


def test_symbolic_dedups_repeated_reduction_body():
    # The four-step reduction pattern draws the same reduction R on both sides
    # of the assumption hop. With diff on, the twin (G_2) drops its identical
    # body and instead points back to where the reduction was drawn (G_1).
    _ctx, out = _symbolic_ddh(diff=True)
    assert r"(reduction as in $G_{1}$)" in out
    assert r"(reduction as in $G_{3}$)" in out


def test_symbolic_dedup_reduces_drawn_bodies():
    # The reduction R is drawn for G_1 and repeated for G_2; Rprime for G_3 and
    # repeated for G_4. De-dup drops the two repeats, so two fewer boxed bodies
    # are drawn than with diff off.
    _ctx, on = _symbolic_ddh(diff=True)
    _ctx2, off = _symbolic_ddh(diff=False)
    boxed = r"\begin{pcvstack}[boxed,"
    assert off.count(boxed) - on.count(boxed) == 2


def test_symbolic_heading_not_highlighted():
    # The assumption hop's challenger change (DDH.Left -> DDH.Right) is conveyed
    # by the hop prose, so the heading is no longer highlighted.
    _ctx, out = _symbolic_ddh(diff=True)
    assert r"\pfhighlight{$\DDH(\G).\Right$}" not in out
    assert r"\gamechange" not in out
    # The change is stated in prose instead.
    assert "differ only in the" in out


def test_symbolic_highlights_changed_body_lines():
    # R (G_1) and Rprime (G_3) are different reductions with different source
    # lines; those changed lines are highlighted in G_3's body. G_3's Solve
    # oracle returns challenger.Eq(c), which renders as the bare oracle call
    # \Eq(c), so that changed \pcreturn body line is tinted.
    _ctx, out = _symbolic_ddh(diff=True)
    assert r"\pfhighlight{\pcreturn \Eq(c)}" in out


def test_symbolic_no_diff_keeps_full_sequence():
    # With diff off, every game is drawn in full and nothing is highlighted or
    # deduped.
    _ctx, out = _symbolic_ddh(diff=False)
    assert r"\pfhighlight{" not in out
    assert "(reduction as in" not in out
