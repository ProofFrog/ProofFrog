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
