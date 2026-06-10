from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

CFRG = REPO / "examples/applications/cfrg-hybrid-kems/primitives"
KDF = str(CFRG / "KDF.primitive")
KEM = str(CFRG / "KEM.primitive")


def _export(path: str) -> str:
    from proof_frog.export.latex.exporter import export_file

    return export_file(path)


def _itemize_body(out: str) -> str:
    start = out.index(r"\begin{itemize}")
    return out[start : out.index(r"\end{itemize}", start)]


def test_render_symenc_primitive() -> None:
    out = _export(str(REPO / "examples/Primitives/SymEnc.primitive"))
    assert r"\providecommand{\SymEnc}" in out
    assert r"\KeyGen" in out
    assert r"\Enc" in out
    assert r"\Dec" in out
    # Primitive renders as a typed-signature definition list, not a procedure block.
    assert r"\procedure" not in out


def test_parameters_are_an_itemize_item() -> None:
    # Parameters belong in the bullet list, not on the heading line.
    out = _export(KDF)
    assert r"\item Parameters" in _itemize_body(out)
    assert r"\textit{Parameters:}" not in out


def test_parameter_types_use_set_membership() -> None:
    # Show types mathematically: `Nin \in \mathbb{Z}`, not `Nin : \mathbb{Z}`.
    out = _export(KDF)
    assert r"\in \mathbb{Z}" in out
    assert r"Nin : " not in out


def test_kdf_has_no_sets_line() -> None:
    # KDF's only fields are the Int lengths Nin/Nout -- not sets, so there is
    # no "Sets:" entry (those lengths already appear under Parameters).
    out = _export(KDF)
    assert "Sets:" not in out


def test_signature_has_no_owner_suffix() -> None:
    # The redundant "(in KDF)" trailer on every method signature is gone.
    out = _export(KDF)
    assert "(in $" not in out
    assert r"\evaluate" in out


def test_kem_sets_line_lists_only_set_fields() -> None:
    out = _export(KEM)
    sets_items = [ln for ln in out.splitlines() if "Sets:" in ln]
    assert len(sets_items) == 1
    line = sets_items[0]
    # The four Set fields appear; the Int length fields do not.
    for s in ("SharedSecret", "Ciphertext", "EncapsKey", "DecapsKey"):
        assert s in line
    for n in ("Nseed", "Nct", "Nek"):
        assert n not in line


def test_kem_set_names_render_upright_via_macro() -> None:
    # Set names must be set consistently (upright \mathsf via the algorithm
    # macro), the same way they render in method signatures -- not bare italic.
    out = _export(KEM)
    sets_items = [ln for ln in out.splitlines() if "Sets:" in ln]
    assert r"\SharedSecret" in sets_items[0]
