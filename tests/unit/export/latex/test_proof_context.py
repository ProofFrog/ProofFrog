from proof_frog import frog_ast
from proof_frog.export.latex.proof_context import ProofContext, StepRender  # noqa: E402

DDH = "examples/Proofs/Group/DDH_implies_CDH.proof"
# TriplingPRG has explicit `let: PRG G = PRG(...); TriplingPRG T = TriplingPRG(G);`
# bindings that resolve to imported Primitive/Scheme objects.
TRIPLING = "examples/Proofs/PRG/TriplingPRG_PRGSecurity.proof"
CPRG = "examples/Proofs/PRG/CounterPRG_PRGSecurity.proof"
# ElGamal's theorem game INDCPA_MultiChal.Initialize destructures
# `[pk, sk] = E.KeyGen();` -- an *imported* security game (Definitions section).
ELGAMAL = "examples/Proofs/PubKeyEnc/ElGamal_INDCPA_MultiChal.proof"
# GHP18's let `KEMCombiner KC = KEMCombiner(...);` destructures inside its own
# Encaps body -- an instantiated *construction* (Construction section).
GHP18 = "examples/applications/KEMCombiner-GHP18/GHP18_INDCPA_First.proof"


def _has_destructuring(block: frog_ast.Block) -> bool:
    return any(isinstance(s, frog_ast.DestructuringBinding) for s in block.statements)


def _has_tup_temp(block: frog_ast.Block) -> bool:
    return any(
        isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name.startswith("_tup")
        for s in block.statements
    )


def test_security_game_files_are_resolved_and_deduped():
    ctx = ProofContext(DDH)
    names = {gf.get_export_name() for gf in ctx.security_game_files()}
    # assume: DDH, RandomTargetGuessing; theorem: CDH; all are .game imports
    assert {"DDH", "CDH", "RandomTargetGuessing"} <= names


def test_let_constructions_returns_schemes_and_primitives():
    ctx = ProofContext(TRIPLING)
    kinds = [type(root).__name__ for _name, root in ctx.let_constructions()]
    # TriplingPRG lets `PRG G = PRG(lambda, lambda);` -> Primitive
    # and `TriplingPRG T = TriplingPRG(G);` -> Scheme
    assert "Primitive" in kinds
    assert "Scheme" in kinds


def test_assumptions_and_theorem_exposed():
    ctx = ProofContext(DDH)
    assert len(ctx.assumptions()) == 2
    assert isinstance(ctx.theorem(), frog_ast.ParameterizedGame)


def test_resolve_inlined_returns_game():
    ctx = ProofContext(DDH)
    step = ctx.game_steps()[1]
    game = ctx.resolve_inlined(step)
    assert isinstance(game, frog_ast.Game)
    assert game.methods


def test_resolve_symbolic_reduction_step_has_novel_reduction():
    ctx = ProofContext(DDH)
    step = ctx.game_steps()[1]  # DDH.Left compose R
    sr = ctx.resolve_symbolic(step)
    assert sr.novel is not None
    assert isinstance(sr.novel, frog_ast.Reduction)


def test_resolve_symbolic_start_step_has_no_novel():
    ctx = ProofContext(DDH)
    sr = ctx.resolve_symbolic(ctx.game_steps()[0])  # CDH.Left, no reduction
    assert sr.novel is None


def test_hop_kinds_align_with_games():
    ctx = ProofContext(DDH)
    kinds = ctx.hop_kinds()
    # one entry per hop between consecutive game steps
    assert len(kinds) == len(ctx.game_steps()) - 1
    assert all(k.kind in {"interchangeable", "assumption"} for k in kinds)


def test_hop_kinds_detects_side_flip_assumption_hops():
    # DDH proof hops: 0->1 interchange, 1->2 by DDH (side flip),
    # 2->3 interchange, 3->4 by RandomTargetGuessing (side flip),
    # 4->5 interchange.
    ctx = ProofContext(DDH)
    kinds = ctx.hop_kinds()
    assert [k.kind for k in kinds] == [
        "interchangeable",
        "assumption",
        "interchangeable",
        "assumption",
        "interchangeable",
    ]
    assert kinds[1].assumption is not None and kinds[1].assumption.name == "DDH"
    assert (
        kinds[3].assumption is not None
        and kinds[3].assumption.name == "RandomTargetGuessing"
    )


def test_security_game_files_render_destructuring_not_desugared():
    # Part 2.5: imported security games used in Definitions must keep
    # tuple-destructuring bindings, not the engine's desugared _tup temporaries.
    ctx = ProofContext(ELGAMAL)
    indcpa = next(
        gf
        for gf in ctx.security_game_files()
        if gf.get_export_name() == "INDCPA_MultiChal"
    )
    for game in indcpa.games:
        init = next(m for m in game.methods if m.signature.name == "Initialize")
        assert _has_destructuring(init.block)
        assert not _has_tup_temp(init.block)


def test_let_constructions_render_destructuring_not_desugared():
    # Part 2.5: instantiated constructions used in Construction must keep
    # tuple-destructuring bindings inside their own method bodies.
    ctx = ProofContext(GHP18)
    kc = next(root for name, root in ctx.let_constructions() if name == "KC")
    encaps = next(m for m in kc.methods if m.signature.name == "Encaps")
    assert _has_destructuring(encaps.block)
    assert not _has_tup_temp(encaps.block)
