"""F-404: a game whose calls the engine did not finish inlining is refused.

The engine inlines one method call per round, for at most
``_MAX_FIXED_POINT_ITERATIONS`` rounds. Past the cap it used to warn and go
on with the calls left in the game, where the passes read them as calls to
an opaque method, which always completes and changes no state: an unused
call to a scheme method whose body draws from a set that may be empty was
dropped. Such a game is now not resolved, and a hop that needs it fails
with a message naming the cap.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine
from proof_frog.proof_engine import (
    FailedProof,
    InliningLimitError,
    ProofEngine,
    inline_calls,
)
from proof_frog.web_server import _setup_engine_for_proof

_SCHEME = """
Scheme S() extends P {
    Bool Id(Bool b) {
        return b;
    }
}
"""

_FIXTURES = "tests/integration/soundness_regression_fixtures/F_404"


def _lookup() -> dict[tuple[str, str], frog_ast.Method]:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    return {("S", m.signature.name): m for m in scheme.methods}


def _game(calls: int) -> frog_ast.Game:
    body = "".join(f"        Bool t{k} = S.Id(a);\n" for k in range(calls))
    return frog_parser.parse_game(
        f"Game G() {{\n    Bool Test(Bool a) {{\n{body}        return a;\n    }}\n}}"
    )


def _calls_left(game: frog_ast.Game) -> int:
    return str(game).count("S.Id(")


def test_inline_calls_inlines_every_call() -> None:
    game = inline_calls(_game(3), _lookup(), max_rounds=10)
    assert _calls_left(game) == 0


def test_inline_calls_needs_one_round_per_call() -> None:
    # Three calls take exactly three rounds: the cap is not hit.
    game = inline_calls(_game(3), _lookup(), max_rounds=3)
    assert _calls_left(game) == 0


def test_inline_calls_refuses_a_game_with_calls_left() -> None:
    with pytest.raises(InliningLimitError) as info:
        inline_calls(_game(3), _lookup(), max_rounds=2)
    message = str(info.value)
    assert "inlining did not finish within 2 rounds" in message
    assert "S.Id(a) is still a call" in message
    assert info.value.rounds == 2


def test_inline_calls_does_not_count_a_field_initializer() -> None:
    # A field initializer has no block to inline into (a reduction resolved
    # before it is composed keeps such a call), so it does not block.
    game = frog_parser.parse_game(
        "Game G() {\n    Bool f = S.Id(true);\n"
        "    Bool Test(Bool a) {\n        return a;\n    }\n}"
    )
    assert inline_calls(game, _lookup(), max_rounds=0) == game


def test_inline_calls_default_cap_is_the_fixed_point_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proof_engine, "_MAX_FIXED_POINT_ITERATIONS", 1)
    with pytest.raises(InliningLimitError, match="within 1 rounds"):
        inline_calls(_game(2), _lookup())


def test_hop_with_a_game_not_inlined_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # few.proof's Left makes 6 calls; with a cap of 3 rounds it is not
    # resolved, and the hop fails with the cap's message instead of raising.
    monkeypatch.setattr(proof_engine, "_MAX_FIXED_POINT_ITERATIONS", 3)
    engine, proof_file = _setup_engine_for_proof(f"{_FIXTURES}/few.proof")
    with pytest.raises(FailedProof):
        engine.prove(proof_file, f"{_FIXTURES}/few.proof")
    output = capsys.readouterr().out
    assert "G_few(P).Left: inlining did not finish within 3 rounds" in output
    assert "Proof Failed! (1 step(s) failed: 1)" in output
    [hop] = engine.hop_results
    assert not hop.valid
    assert hop.kind == "equivalent"
    assert "within 3 rounds" in hop.failure_detail


def test_rollover_with_a_game_not_inlined_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # With no inlining at all, every game of this induction proof that makes
    # a call is unresolved, its rollover's included: those hops fail, and
    # none raises.
    monkeypatch.setattr(proof_engine, "_MAX_FIXED_POINT_ITERATIONS", 0)
    path = "examples/Proofs/PRF/PRFSecurity_implies_PRFSecurity_MultiKey.proof"
    engine, proof_file = _setup_engine_for_proof(path)
    with pytest.raises(FailedProof):
        engine.prove(proof_file, path)
    output = capsys.readouterr().out
    assert "[rollover]" in output
    rollovers = [r for r in engine.hop_results if r.kind == "induction_rollover"]
    assert rollovers
    assert all(not r.valid for r in rollovers)
    assert all("within 0 rounds" in r.failure_detail for r in rollovers)


def _unresolved_hop() -> ProofEngine._PreparedHop:
    return ProofEngine._PreparedHop(  # pylint: disable=protected-access
        step_num=1, current_desc="A", next_desc="B", failure="not resolved"
    )


@pytest.mark.parametrize("parallel", [False, True])
def test_unresolved_hop_is_reported_failed(
    parallel: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    # pylint: disable=protected-access
    engine = ProofEngine()
    engine._total_steps = 1
    engine._current_step = 0
    engine.hop_results = []
    if parallel:
        engine._prove_steps_parallel([_unresolved_hop()], 0)
    else:
        engine._prove_steps_sequential([_unresolved_hop()], [], [], 0, None)
    [hop] = engine.hop_results
    assert not hop.valid
    assert hop.failure_detail == "not resolved"
    assert "not resolved" in capsys.readouterr().out
