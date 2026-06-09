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
    assert out.count(r"\begin{figure}") >= 1


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
