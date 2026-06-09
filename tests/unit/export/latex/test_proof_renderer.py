"""Tests for proof_renderer helpers added in Task 4."""

from proof_frog import frog_ast
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.module_renderer import ModuleRenderer
from proof_frog.export.latex.proof_context import ProofContext
from proof_frog.export.latex import proof_renderer as pr

DDH = "examples/Proofs/Group/DDH_implies_CDH.proof"


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


def test_render_proof_inlined_runs_clean():
    backend = CryptocodeBackend()
    macros = MacroRegistry()
    mr = ModuleRenderer(backend, macros)
    ctx = ProofContext(DDH)
    out = pr.render_proof(ctx, backend, macros, mr, composition="inlined")
    assert out.count(r"\begin{figure}") == len(ctx.game_steps())
    assert r"\end{document}" in out
