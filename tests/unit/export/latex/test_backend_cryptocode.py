from proof_frog.export.latex import ir
from proof_frog.export.latex.backends.cryptocode import CryptocodeBackend


def test_render_simple_procedure() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(
        title=r"\Enc(k, m)",
        lines=[
            ir.Sample(lhs="r", rhs=r"\{0,1\}^\lambda"),
            ir.Assign(lhs="c", rhs=r"\PRF(k, r) \oplus m"),
            ir.Return(expr="(r, c)"),
        ],
    )
    out = b.render_procedure(p)
    assert r"\procedure" in out
    assert r"\Enc(k, m)" in out
    assert r"r \getsr \{0,1\}^\lambda" in out
    assert r"c \gets \PRF(k, r) \oplus m" in out
    assert r"\pcreturn (r, c)" in out


def test_render_empty_procedure_no_blank_body() -> None:
    # A procedure with no rendered lines must emit an empty body "{}", not a
    # whitespace-only "{\n    \n}".  The blank line is a LaTeX \par which breaks
    # cryptocode's \procedure ("Paragraph ended before \@pseudocode was
    # complete").
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\Foo()", lines=[])
    out = b.render_procedure(p)
    assert "{\n    \n}" not in out
    assert out.endswith("{}")


def test_render_vstack_boxed() -> None:
    b = CryptocodeBackend()
    p = ir.ProcedureBlock(title=r"\KeyGen()", lines=[ir.Return(expr="k")])
    out = b.render_vstack(ir.VStack(blocks=[p], boxed=True))
    assert r"\begin{pcvstack}[boxed]" in out
    assert r"\end{pcvstack}" in out


def test_required_packages() -> None:
    b = CryptocodeBackend()
    pkgs = b.required_packages()
    names = {p.name for p in pkgs}
    assert "cryptocode" in names


def test_preamble_extras_defines_getsr() -> None:
    # \getsr is emitted in the body for sampling, but is not a built-in
    # cryptocode command (cryptocode 3.x uses \sample).  The preamble must
    # define \getsr as a providecommand alias so generated documents compile
    # with pdflatex without "Undefined control sequence" errors.
    b = CryptocodeBackend()
    extras = b.preamble_extras()
    assert r"\providecommand{\getsr}{\sample}" in extras
