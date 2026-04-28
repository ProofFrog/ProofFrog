from proof_frog.export.latex import ir


def test_procedure_block_holds_lines() -> None:
    p = ir.ProcedureBlock(
        title="Enc(k, m)",
        lines=[
            ir.Sample(lhs="r", rhs=r"\{0,1\}^\lambda"),
            ir.Assign(lhs="c", rhs=r"\PRF(k, r) \oplus m"),
            ir.Return(expr="(r, c)"),
        ],
    )
    assert len(p.lines) == 3
    assert isinstance(p.lines[0], ir.Sample)


def test_vstack_holds_procedures() -> None:
    p = ir.ProcedureBlock(title="A", lines=[])
    v = ir.VStack(boxed=True, blocks=[p])
    assert v.boxed is True
    assert v.blocks == [p]
