from pathlib import Path

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
