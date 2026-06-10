"""Fragment (non-standalone) export, for \\input into a larger document."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

SCHEME = str(REPO / "examples/Schemes/PRG/TriplingPRG.scheme")
GAME = str(REPO / "examples/Games/PRG/PRGSecurity.game")
PROOF = str(REPO / "examples/Proofs/Group/DDH_implies_CDH.proof")


def _fragment(path: str) -> str:
    from proof_frog.export.latex.exporter import export_file

    return export_file(path, standalone=False)


def _standalone(path: str) -> str:
    from proof_frog.export.latex.exporter import export_file

    return export_file(path, standalone=True)


def test_default_is_standalone() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(SCHEME)
    assert r"\documentclass" in out
    assert r"\begin{document}" in out


def test_fragment_has_no_document_wrapper() -> None:
    out = _fragment(SCHEME)
    assert r"\documentclass" not in out
    assert r"\begin{document}" not in out
    assert r"\end{document}" not in out


def test_fragment_keeps_body_content() -> None:
    out = _fragment(SCHEME)
    assert r"\procedure" in out
    assert r"\TriplingPRG.\evaluate" in out


def test_fragment_embeds_macros_inline() -> None:
    # The generated \providecommand macros must travel with the fragment so a
    # bare \input works; \providecommand is idempotent and yields to any user
    # redefinition, so inlining them is safe.
    out = _fragment(SCHEME)
    assert r"\providecommand{\TriplingPRG}" in out


def test_fragment_lists_required_packages_as_comments() -> None:
    # Packages and \newtheorem cannot appear in the document body, so the
    # fragment lists them in a comment header for the user to copy to their
    # preamble.
    out = _fragment(SCHEME)
    assert r"% \usepackage" in out
    assert "cryptocode" in out
    # Every emitted preamble line in the header must be commented out.
    for line in out.splitlines():
        if r"\usepackage" in line:
            assert line.lstrip().startswith("%"), line


def test_fragment_comments_preamble_extras() -> None:
    # \newtheorem / \Experiment etc. are preamble material -> commented header.
    out = _fragment(PROOF)
    assert r"% \newtheorem{theorem}{Theorem}" in out


def test_proof_fragment_has_no_document_wrapper() -> None:
    out = _fragment(PROOF)
    assert r"\documentclass" not in out
    assert r"\begin{document}" not in out
    # but the proof body survives
    assert r"\section*{Definitions}" in out
    assert r"\providecommand" in out


def test_game_fragment_round_trips() -> None:
    out = _fragment(GAME)
    assert r"\documentclass" not in out
    assert r"\begin{pchstack}" in out
    assert r"\providecommand{\PRGSecurity}" in out
