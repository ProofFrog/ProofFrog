"""Tests for proof_renderer helpers added in Task 4."""

from proof_frog import frog_ast, frog_parser
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.module_renderer import ModuleRenderer
from proof_frog.export.latex.proof_context import GameRef, Hop, ProofContext
from proof_frog.export.latex import proof_renderer as pr

DDH = "examples/Proofs/Group/DDH_implies_CDH.proof"
MULTICHAL = "examples/Proofs/PubKeyEnc/INDCPA_implies_INDCPA_MultiChal.proof"
CFRG_LEAK = (
    "examples/applications/cfrg-hybrid-kems/proofs/CG/"
    "CG_expanded_LEAK_BIND_K_CT_DIFFKEY.proof"
)
HASHED_ELGAMAL = "examples/Proofs/KEM/HashedElGamalKEM_INDCCA.proof"
RFRP = "examples/Proofs/PRP/RFRP_Switching.proof"
FIXTURES = "tests/unit/export/latex/fixtures"
HYBRID = f"{FIXTURES}/hybrid_threshold.proof"
STEP_ASSUMPTION = f"{FIXTURES}/step_assumption.proof"


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


def test_claimed_bound_negation_keeps_operand_parentheses():
    _b, _m, mr = _renderer()
    assert pr._render_claimed_bound(_claim("-(a + b)"), mr) == "-(a + b)"
    assert pr._render_claimed_bound(_claim("-(a * b)"), mr) == r"-(a \cdot b)"
    assert pr._render_claimed_bound(_claim("-a ^ 2"), mr) == "-a^{2}"


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
    assert r"\Adv{\LEAKBINDKCTDIFFKEY(\KEMPQ)}{\RPQBind}" in out
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
    loss_hop = pr._hop_annotation(_make_assumption_hop(), mr, loss=_make_adv_term())
    # Prose names the assumption and states the advantage bound inequality.
    assert r"\DDH(\G)" in loss_hop
    assert r"\le" in loss_hop
    assert r"\Adv{" in loss_hop
    assert r"\Pr[G_{0} = 1]" in loss_hop
    # An invisible author-commentary placeholder follows (a LaTeX comment).
    assert "% commentary (author)" in loss_hop
    # An equivalence hop states perfect indistinguishability, with no bound.
    plain = pr._hop_annotation(_make_interchangeable_hop(), mr, loss=None)
    assert "perfectly indistinguishable" in plain
    assert r"\le" not in plain
    assert r"\Pr[G_{0} = 1] = \Pr[G_{1} = 1]" in plain


def _make_assumption_hop():
    return Hop(
        "assumption",
        frog_ast.ParameterizedGame("DDH", [frog_ast.Variable("G")]),
        GameRef(0),
        GameRef(1),
    )


def _make_interchangeable_hop():
    return Hop("interchangeable", None, GameRef(0), GameRef(1))


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


def _symbolic(path):
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    return pr.render_proof(ProofContext(path), backend, macros, mr)


def test_plain_proof_prose_unchanged():
    # A proof with no induction, step assumption or lemma keeps its prose.
    out = _symbolic(DDH)
    assert (
        r"If indistinguishability holds for $\DDH(\G)$ and "
        r"$\RandomTargetGuessing(\G)$, then indistinguishability holds for "
        r"$\CDH(\G)$. Concretely,"
    ) in out
    hops = [line for line in out.splitlines() if line.startswith("Games $G_")]
    assert hops == [
        r"Games $G_{0}$ and $G_{1}$ are perfectly indistinguishable: "
        r"$\Pr[G_{0} = 1] = \Pr[G_{1} = 1]$.",
        r"Games $G_{1}$ and $G_{2}$ differ only in the $\DDH(\G)$ challenger; "
        r"the reduction turns any distinguisher into an adversary "
        r"$\mathcal{B}_{1}$ with $\lvert \Pr[G_{1} = 1] - \Pr[G_{2} = 1] \rvert "
        r"\le \Adv{\DDH(\G)}{\mathcal{B}_{1}}$.",
        r"Games $G_{2}$ and $G_{3}$ are perfectly indistinguishable: "
        r"$\Pr[G_{2} = 1] = \Pr[G_{3} = 1]$.",
        r"Games $G_{3}$ and $G_{4}$ differ only in the "
        r"$\RandomTargetGuessing(\G)$ challenger; the reduction turns any "
        r"distinguisher into an adversary $\mathcal{B}_{2}$ with "
        r"$\lvert \Pr[G_{3} = 1] - \Pr[G_{4} = 1] \rvert "
        r"\le \Adv{\RandomTargetGuessing(\G)}{\mathcal{B}_{2}}$.",
        r"Games $G_{4}$ and $G_{5}$ are perfectly indistinguishable: "
        r"$\Pr[G_{4} = 1] = \Pr[G_{5} = 1]$.",
    ]
    assert "% commentary (author): explain the intuition for the G_0 -> G_1 hop" in out


def test_induction_renders_as_hybrid():
    out = _symbolic(MULTICHAL)
    assert (
        "Games $G_{1,i}$ and $G_{2,i}$ form a hybrid over $i$ from $1$ to $q$." in out
    )
    assert r"$G_{1,i} = \INDCPA(\E).\Left \circ \R(\E, i)$" in out
    assert (
        r"For each $1 \le i \le q$, games $G_{1,i}$ and $G_{2,i}$ differ only in "
        r"the $\INDCPA(\E)$ challenger, and are indistinguishable under that "
        "assumption."
    ) in out
    # The rollover runs i -> i + 1 below the upper bound.
    assert r"For each $1 \le i < q$, assuming" in out
    assert r"games $G_{2,i}$ and $G_{1,i + 1}$ are perfectly indistinguishable" in out
    assert r"Chained over $i$, these hops connect $G_{1,1}$ to $G_{2,q}$." in out
    assert r"(reduction as in $G_{1,i}$)" in out
    assert out.count(r"\begin{center}") == 4
    assert "explain the intuition for the G_2,i -> G_1,i + 1 hop" in out


def test_step_assumption_renders_as_condition():
    out = _symbolic(STEP_ASSUMPTION)
    assert (
        r"Assuming $n \ge 1$, games $G_{2}$ and $G_{3}$ are perfectly "
        "indistinguishable"
    ) in out
    assert r"$n \ge 1$ challenger" not in out
    assert r"and $n \ge 1$, then indistinguishability holds for" in out


def test_induction_step_assumptions_are_not_challengers():
    out = _symbolic(MULTICHAL)
    assert r"\mathit{count} = 1$ challenger" not in out
    assert (
        r"Assuming $\R(\E, q).\mathit{count} < q + 1$ and "
        r"$\INDCPA(\E).\Right.\mathit{count} = 1$, games $G_{2,q}$ and $G_{3}$"
    ) in out
    # Each distinct step assumption is a theorem premise.
    theorem = out[out.find(r"\begin{theorem}") : out.find(r"\end{theorem}")]
    assert (
        r"$\R(\E, 1).\mathit{count} \ge 1$, $\INDCPA(\E).\Left.\mathit{count} = 1$, "
        r"$\INDCPA(\E).\Right.\mathit{count} = 1$, and "
        r"$\R(\E, q).\mathit{count} < q + 1$ hold, then"
    ) in theorem


def test_indexed_assumption_is_quantified_in_theorem():
    out = _symbolic(HYBRID)
    theorem = out[out.find(r"\begin{theorem}") : out.find(r"\end{theorem}")]
    assert (
        r"If indistinguishability holds for $\IndexedThreshold(j)$ for each "
        r"$1 \le j \le q$, and $q \ge 1$, then indistinguishability holds for "
        r"$\Threshold(q)$."
    ) in theorem
    assert (
        r"For each $1 \le j \le q$, games $G_{1,j}$ and $G_{2,j}$ differ only in "
        r"the $\IndexedThreshold(j)$ challenger"
    ) in out
    assert r"Assuming $q \ge 1$, games $G_{2,q}$ and $G_{3}$" in out


def test_lemma_hop_names_lemma_file():
    out = _symbolic(HASHED_ELGAMAL)
    lemma = r"\texttt{GapCDH\_implies\_GapCDH\_NZ.proof}"
    assert (
        rf"and indistinguishability holds for $\GapCDHNZ(\G)$ (proved in {lemma}), "
        "then"
    ) in out
    assert (
        rf"differ only in the $\GapCDHNZ(\G)$ challenger, whose sides the lemma "
        rf"in {lemma} proves indistinguishable; the reduction"
    ) in out
    # The assumed ROMProgramming hop still reads as an assumption hop.
    assert r"$\ROMProgramming(\G, \{0,1\}^{n})$ challenger; the reduction" in out


def test_lemma_hop_without_bound_cites_lemma():
    hop = Hop(
        "lemma",
        frog_ast.ParameterizedGame("PRFSecurity", [frog_ast.Variable("F")]),
        GameRef(1),
        GameRef(2),
        lemma_path="../PRF/PRF_lemma.proof",
    )
    out = pr._hop_annotation(hop, _renderer()[2])
    assert out.startswith(
        r"Games $G_{1}$ and $G_{2}$ differ only in the $\PRFSecurity(\F)$ "
        r"challenger, and are indistinguishable by the lemma in "
        r"\texttt{PRF\_lemma.proof}."
    )


def test_event_lemma_is_a_theorem_premise():
    out = _symbolic(RFRP)
    lemma = r"\texttt{RFRP\_Switching\_Event.proof}"
    assert (
        r"If $\Pr[\mathit{bad} \text{ in } \RFvsRP(\X) \text{ against } "
        rf"\mathcal{{A}}]$ is small (proved in {lemma}), then"
    ) in out
    assert f"which is bounded by the event lemma in {lemma}." in out
