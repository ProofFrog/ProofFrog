"""resolve_step_game is the public seam shared by prover, web, and export."""
from proof_frog.web_server import _setup_engine_for_proof


def test_resolve_step_game_matches_private_get_game_ast():
    engine, proof_file = _setup_engine_for_proof(
        "examples/Proofs/Group/DDH_implies_CDH.proof"
    )
    step = proof_file.steps[1]  # a reduction-composed step
    public = engine.resolve_step_game(step.challenger, step.reduction)
    # pylint: disable=protected-access
    private = engine._get_game_ast(step.challenger, step.reduction)
    # pylint: enable=protected-access
    assert str(public) == str(private)


def test_resolve_step_game_no_reduction():
    engine, proof_file = _setup_engine_for_proof(
        "examples/Proofs/Group/DDH_implies_CDH.proof"
    )
    step = proof_file.steps[0]  # start game, no reduction
    game = engine.resolve_step_game(step.challenger)
    assert game.methods  # resolved to a real game with methods
