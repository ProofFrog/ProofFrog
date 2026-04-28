from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def test_render_prg_security_game() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Games/PRG/PRGSecurity.game"))
    assert r"\begin{pcvstack}[boxed]" in out
    assert r"\Real" in out
    assert r"\Random" in out
    assert r"\Query" in out
    assert r"\Experiment{\PRGSecurity}{\Real}{\G}" in out
    assert r"\Experiment{\PRGSecurity}{\Random}{\G}" in out
