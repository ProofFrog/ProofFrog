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


def test_side_by_side_games_wrapped_to_fit_width() -> None:
    # The side-by-side pair is the widest content the exporter emits; it must
    # be wrapped so an over-wide pair shrinks to the text block (A1).
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Games/PRG/PRGSecurity.game"))
    assert r"\adjustbox{max width=\textwidth}{" in out
    assert out.index(r"\adjustbox") < out.index(r"\begin{pchstack}")


def test_two_game_file_renders_side_by_side() -> None:
    # A two-game (Real/Random) file is the pair of sides of a security
    # definition; they render in one horizontal stack, not stacked vertically.
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Games/PRG/PRGSecurity.game"))
    assert out.count(r"\begin{pchstack}") == 1
    # two columns, each an outer (title) pcvstack wrapping a boxed inner one
    assert out.count(r"\begin{pcvstack}[boxed]") == 2
    assert out.count(r"\begin{pcvstack}") == 4
