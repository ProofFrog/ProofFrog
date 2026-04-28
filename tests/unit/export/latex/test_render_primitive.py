from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def test_render_symenc_primitive() -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(REPO / "examples/Primitives/SymEnc.primitive"))
    assert r"\providecommand{\SymEnc}" in out
    assert r"\KeyGen" in out
    assert r"\Enc" in out
    assert r"\Dec" in out
    # Primitive renders as a typed-signature definition list, not a procedure block.
    assert r"\procedure" not in out
