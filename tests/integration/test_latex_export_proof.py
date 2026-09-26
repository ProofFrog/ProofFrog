from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_export_proof_smoke() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(
        str(REPO / "examples/Proofs/PRG/CounterPRG_PRGSecurity.proof")
    )
    assert r"\documentclass{article}" in out
    assert "cryptocode" in out
    assert r"\begin{document}" in out
    assert r"\end{document}" in out
    assert r"\begin{theorem}" in out
    # The proof body is an amsthm proof environment with non-floating game
    # blocks (no figure floats that would drift out of reading order).
    assert r"\begin{proof}" in out and r"\end{proof}" in out
    assert r"\begin{figure}" not in out
    assert out.count(r"\begin{center}") >= 1


# ---------------------------------------------------------------------------
# Task 8: Three-fixture acceptance sweep (both modes)
# ---------------------------------------------------------------------------

FIXTURES = [
    str(REPO / "examples/Proofs/Group/DDH_implies_CDH.proof"),
    str(REPO / "examples/Proofs/SymEnc/ModOTP_INDOT.proof"),
    str(REPO / "examples/Proofs/PRG/CounterPRG_PRGSecurity.proof"),
    str(REPO / "examples/Proofs/PRG/TriplingPRG_PRGSecurity.proof"),
]


@pytest.mark.parametrize("path", FIXTURES)
@pytest.mark.parametrize("mode", ["symbolic", "inlined"])
def test_proof_exports_clean(path: str, mode: str) -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(path, composition=mode)
    assert r"\documentclass{article}" in out
    assert r"\begin{document}" in out and r"\end{document}" in out
    assert r"\begin{theorem}" in out


@pytest.mark.parametrize("path", FIXTURES)
def test_symbolic_has_no_unsupported_or_rawstep(path: str) -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(path, composition="symbolic")
    assert "% unsupported" not in out
    # No raw-step-text fallback comment for the common step kinds: the
    # fallback wraps the step string "... against ...Adversary".
    assert "against" not in out or r"\circ" in out


def test_symbolic_renders_intermediate_game_body() -> None:
    # ModOTP_INDOT step 1 is the explicit intermediate game Hyb(q); in
    # symbolic mode its body must render as a boxed vstack (the `novel` path),
    # not a heading-only "see Definitions" note.
    from proof_frog.export.latex.exporter import export_file

    out = export_file(
        str(REPO / "examples/Proofs/SymEnc/ModOTP_INDOT.proof"),
        composition="symbolic",
    )
    assert r"\Hyb" in out
    assert r"\begin{pcvstack}" in out


# ---------------------------------------------------------------------------
# Event theorems and identical-until-bad hops
# ---------------------------------------------------------------------------

UPTO = REPO / "tests/integration/upto_fixtures"


@pytest.mark.parametrize("mode", ["symbolic", "inlined"])
def test_upto_hop_exports(mode: str) -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(UPTO / "outer.proof"), composition=mode)
    assert r"\begin{theorem}" in out
    assert "identical until" in out
    assert "fundamental lemma" in out
    assert r"\Pr[" in out and r"\mathit{bad}" in out
    assert "#event" not in out and "silenced" not in out


@pytest.mark.parametrize("mode", ["symbolic", "inlined"])
def test_event_theorem_exports(mode: str) -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(UPTO / "BadGuessEvent.proof"), composition=mode)
    theorem = out[out.index(r"\begin{theorem}") : out.index(r"\end{theorem}")]
    assert r"\Pr[" in theorem and r"\mathit{bad}" in theorem
    # The exporter's AST-only synthesis keeps helper terms as \Adv terms.
    assert r"\Adv{\RandomTargetGuessing" in theorem
    assert "#event" not in out and "silenced" not in out


def test_assumed_event_exports() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(UPTO / "outer_opaque.proof"))
    theorem = out[out.index(r"\begin{theorem}") : out.index(r"\end{theorem}")]
    assert r"\mathit{bad}" in theorem
    assert "#event" not in out and "silenced" not in out


def test_event_claimed_bound_exports() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(UPTO / "outer_claim.proof"))
    theorem = out[out.index(r"\begin{theorem}") : out.index(r"\end{theorem}")]
    assert r"\Pr[" in theorem and r"\mathit{bad}" in theorem
    assert "#event" not in out and "silenced" not in out
