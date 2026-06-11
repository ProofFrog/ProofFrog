"""Tests for proof_renderer helpers added in Task 4."""

from proof_frog import frog_ast
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.module_renderer import ModuleRenderer
from proof_frog.export.latex.proof_context import ProofContext
from proof_frog.export.latex import proof_renderer as pr

DDH = "examples/Proofs/Group/DDH_implies_CDH.proof"
MULTICHAL = "examples/Proofs/PubKeyEnc/INDCPA_implies_INDCPA_MultiChal.proof"


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


def test_render_proof_symbolic_has_figures_and_hops():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(ctx, backend, macros, mr, composition="symbolic")
    assert r"\documentclass{article}" in out
    assert r"\section*{Definitions}" in out
    assert r"\section*{Construction}" in out
    assert r"\begin{theorem}" in out
    # one figure per game step
    assert out.count(r"\begin{figure}") == len(ctx.game_steps())
    # symbolic label uses composition
    assert r"\circ" in out
    # hop annotations present
    assert ("interchangeable" in out) or ("by assumption" in out)
    # The games_sequence figures themselves should not have fallback comments
    # (the Definitions section may have % unsupported for exotic types like
    # ModIntType, which is a separate pre-existing limitation)
    games_seq = out[out.find(r"\noindent\textit{Proof.}") :]
    assert "% unsupported" not in games_seq
    # Structural: the symbolic heading must NOT be packed into a procedure
    # title (that would double-wrap the caption as `{$Game $G_0$$}`), and a
    # reduction step's novel game must render as a top-level boxed vstack,
    # not nested inside a \procedure body.
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
    assert out.count(r"\begin{figure}") == len(ctx.game_steps())
    assert r"\end{document}" in out


def test_render_proof_diff_highlights_changes_by_default():
    # D1: diff highlighting is on by default in proofs. The inlined game
    # sequence has adjacent full games that differ, so at least one changed
    # line gets a \gamechange box.
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(MULTICHAL)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined")
    assert r"\gamechange{" in out


def test_render_proof_no_diff_suppresses_highlight():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(MULTICHAL)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined", diff=False)
    assert r"\gamechange{" not in out


def _symbolic_ddh(diff=True):
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(
        ctx, backend, macros, mr, composition="symbolic", diff=diff
    )
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


def test_symbolic_highlights_changed_challenger_in_heading():
    # The assumption hop's real change is the composed challenger
    # (DDH.Left -> DDH.Right); that delta is highlighted in the heading, not in
    # the (identical) body.
    _ctx, out = _symbolic_ddh(diff=True)
    assert r"\gamechange{$\DDH(\G).\Right$}" in out


def test_symbolic_highlights_changed_body_lines():
    # R (G_1) and Rprime (G_3) are different reductions with different source
    # lines; those changed lines are highlighted in G_3's body, not just the
    # heading. G_3's Solve oracle returns challenger.Eq(c) where R returned
    # c = z, so a \pcreturn body line is boxed.
    _ctx, out = _symbolic_ddh(diff=True)
    assert r"\gamechange{$\pcreturn challenger.\Eq(c)$}" in out


def test_symbolic_no_diff_keeps_full_sequence():
    # With diff off, every game is drawn in full and nothing is highlighted or
    # deduped.
    _ctx, out = _symbolic_ddh(diff=False)
    assert r"\gamechange{" not in out
    assert "(reduction as in" not in out
