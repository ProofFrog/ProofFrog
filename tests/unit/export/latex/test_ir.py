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


def test_lines_default_to_not_highlighted() -> None:
    # The diff pass (D1) flips ``highlight`` to True on changed/added lines;
    # every line defaults to False so non-diffed output is unaffected.
    assert ir.Sample(lhs="r", rhs="R").highlight is False
    assert ir.Assign(lhs="c", rhs="x").highlight is False
    assert ir.Return(expr="c").highlight is False
    assert ir.If(cond="x = 1").highlight is False
    assert ir.For(header="i").highlight is False
    assert ir.Comment(text="c").highlight is False
    assert ir.Raw(latex="x").highlight is False
