"""Each game of an equivalence hop is canonicalized independently.

A field pinned while canonicalizing the current game (``ctx.pinned_fields``)
used to stay pinned while canonicalizing the next one, so a game's canonical
form could depend on the game it was paired with and on which side of the hop
it sat.
"""

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine
from proof_frog.transforms._base import PipelineContext

GAME = frog_parser.parse_game("Game G() { Int f() { return 1; } }")


@pytest.mark.parametrize("worker", [False, True])
def test_pinned_fields_do_not_carry_from_current_to_next_game(
    worker: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[set[str]] = []

    def fake_run_pipeline(
        game: frog_ast.Game, _pipeline: object, ctx: PipelineContext, **_kw: object
    ) -> frog_ast.Game:
        seen.append(set(ctx.pinned_fields))
        ctx.pinned_fields.add("_hoisted_0")
        return game

    monkeypatch.setattr(proof_engine, "run_pipeline", fake_run_pipeline)
    engine = proof_engine.ProofEngine(False)
    if worker:
        # pylint: disable=protected-access
        task = proof_engine._EquivalenceTask(
            current_game_ast=GAME,
            next_game_ast=GAME,
            step_assumptions=[],
            ctx=engine._build_context(),
            verbosity=proof_engine.Verbosity.QUIET,
            no_diagnose=True,
            proof_let_types=engine.proof_let_types,
        )
        result = proof_engine._check_equivalent_worker(task)
    else:
        result = engine.check_equivalent(GAME, GAME)
    assert result.valid
    assert seen == [set(), set()]
