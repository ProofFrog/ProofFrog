from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def test_render_tripling_prg_scheme() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Schemes/PRG/TriplingPRG.scheme"))
    assert r"\providecommand{\TriplingPRG}" in out
    assert r"\begin{pcvstack}[boxed]" in out
    assert r"\procedure" in out
    assert r"\TriplingPRG.\evaluate" in out


def test_scheme_body_wrapped_to_fit_width() -> None:
    # A wide scheme procedure must shrink to the text width (A1).
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Schemes/PRG/TriplingPRG.scheme"))
    assert r"\adjustbox{max width=\textwidth}{" in out
    assert out.index(r"\adjustbox") < out.index(r"\begin{pcvstack}")
