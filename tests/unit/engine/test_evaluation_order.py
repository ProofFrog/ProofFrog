"""F-397 and F-372's second review: the parts of a statement keep their order.

The method inliner puts a callee's statements in front of the statement
holding the call (and leaves the callee's returned expression in place), and
the conditional-call rewrite puts the operands of a ``&&`` there. A part of
the statement evaluated before that code and touching state it touches is
bound to a variable in front of the statement first; every other part stays
where it is.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.conditional_calls import make_conditional_calls_explicit
from proof_frog.evaluation_order import UnorderedCallError, order_calls_for_inlining

_FIXTURES = Path(__file__).parents[2] / "integration" / "soundness_regression_fixtures"

_SCHEME = """
Scheme S() extends P {
    Bool Pick(Set<BitString<1>> U) {
        BitString<1> x <- BitString<1> \\ U;
        return true;
    }

    Bool Id(Bool v) {
        return v;
    }

    Int IdI(Int v) {
        return v;
    }

    Bool PickCond(Set<BitString<1>> U) {
        Bool cond = false;
        BitString<1> x <- BitString<1> \\ U;
        return cond;
    }
}
"""

_CHALLENGER = """
Game C() {
    Int c;
    Int d;
    Int e;
    Function<Int, Int> F;
    Bool Inc() {
        c = c + 1;
        return true;
    }
    Int Bump() {
        c = c + 1;
        return 0;
    }
    Bool Zero() {
        return c == 0;
    }
    Int Read() {
        return c;
    }
    Int Copy() {
        d = c;
        return 0;
    }
    Int ReadD() {
        return d;
    }
    Bool DZero() {
        return d == 0;
    }
    Int ReadE() {
        return e;
    }
    Function<Int, Int> BumpGetF() {
        c = c + 1;
        return F;
    }
}
"""

Lookup = dict[tuple[str, str], frog_ast.Method]


def _scheme_lookup() -> Lookup:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    return {("S", m.signature.name): m for m in scheme.methods}


def _challenger() -> frog_ast.Game:
    return frog_parser.parse_game(_CHALLENGER)


def _composed_lookup() -> Lookup:
    lookup = _scheme_lookup()
    lookup.update({("challenger", m.signature.name): m for m in _challenger().methods})
    return lookup


def _game(body: str, returns: str = "Bool") -> frog_ast.Game:
    return frog_parser.parse_game(
        "Game G() { Int c; Map<Int, Bool> M; "
        f"{returns} O(Bool a, Bool b, Set<BitString<1>> U) {{ {body} }} }}"
    )


def _statements(game: frog_ast.Game) -> list[str]:
    return [str(s).strip() for s in game.methods[0].block.statements]


def _resolve(
    game: frog_ast.Game,
    lookup: Lookup,
    challenger: frog_ast.Game | None = None,
) -> frog_ast.Game:
    """Rewrite, order and inline to a fixed point, as `resolve_step_game`
    does."""
    for _ in range(50):
        new_game = make_conditional_calls_explicit(game, lookup, {}, None, challenger)
        new_game = order_calls_for_inlining(new_game, lookup, {}, None, challenger)
        new_game = visitors.InlineTransformer(lookup).transform(new_game)
        if new_game == game:
            return game
        game = new_game
    raise AssertionError("inlining did not converge")


def test_f397_returned_expression_is_read_before_a_later_call() -> None:
    # Read's returned `c` stays in the statement; Bump's body goes in front
    # of it, so `c` is bound before the increment.
    resolved = _resolve(
        _game("return challenger.Read() + challenger.Bump();", "Int"),
        _composed_lookup(),
    )
    assert _statements(resolved) == [
        "Int challenger.Bump@prior@0 = c;",
        "c = c + 1;",
        "return challenger.Bump@prior@0 + 0;",
    ]


def test_f397_part_bound_only_when_the_callee_writes_what_it_reads() -> None:
    conflict = order_calls_for_inlining(
        _game("return [c == 0, challenger.Inc()];", "[Bool, Bool]"),
        _composed_lookup(),
        {},
    )
    assert _statements(conflict) == [
        "Int challenger.Inc@prior@0 = c;",
        "return [challenger.Inc@prior@0 == 0, challenger.Inc()];",
    ]
    # S.Pick touches no `c`: nothing is bound.
    game = _game("return [c == 0, S.Pick(U)];", "[Bool, Bool]")
    assert order_calls_for_inlining(game, _composed_lookup(), {}) is game


def test_f397_element_write_index_is_bound() -> None:
    # The index of an element write is evaluated before the value stored.
    ordered = order_calls_for_inlining(
        _game("M[c] = challenger.Inc(); return true;"), _composed_lookup(), {}
    )
    assert _statements(ordered) == [
        "Int challenger.Inc@prior@0 = c;",
        "M[challenger.Inc@prior@0] = challenger.Inc();",
        "return true;",
    ]


def test_f397_argument_call_stays_behind_an_earlier_challenger_call() -> None:
    # While the reduction is resolved alone the inliner takes S.Id first and
    # puts the binding of its argument, a challenger call, in front of the
    # statement: the earlier challenger.Inc() is bound ahead of it.
    ordered = order_calls_for_inlining(
        _game("return F.h(challenger.Inc(), S.Id(challenger.Zero()));"),
        _scheme_lookup(),
        {},
        challenger=_challenger(),
    )
    assert _statements(ordered) == [
        "Bool S.Id@prior@0 = challenger.Inc();",
        "return F.h(S.Id@prior@0, S.Id(challenger.Zero()));",
    ]


def test_f397_unknown_challenger_call_cannot_be_bound() -> None:
    # Without the challenger its calls' types are unknown: refuse rather than
    # reorder them.
    game = _game("return F.h(challenger.Inc(), S.Id(challenger.Zero()));")
    with pytest.raises(UnorderedCallError):
        order_calls_for_inlining(game, _scheme_lookup(), {})


def test_f397_conditionally_evaluated_call_is_not_bound() -> None:
    game = _game("return b && F.h(challenger.Inc(), S.Id(challenger.Zero()));")
    # Unknown challenger: the && is not made explicit, and binding Inc in
    # front of the statement would run it when b is false.
    with pytest.raises(UnorderedCallError):
        order_calls_for_inlining(game, _scheme_lookup(), {})
    # Known challenger: Inc has an effect, so the && is made explicit first
    # and Inc is bound inside the guard.
    rewritten = make_conditional_calls_explicit(
        game, _scheme_lookup(), {}, None, _challenger()
    )
    ordered = order_calls_for_inlining(
        rewritten, _scheme_lookup(), {}, challenger=_challenger()
    )
    guard = ordered.methods[0].block.statements[0]
    assert isinstance(guard, frog_ast.IfStatement)
    assert [str(s).strip() for s in guard.blocks[0].statements] == [
        "Bool S.Id@prior@0 = challenger.Inc();",
        "return F.h(S.Id@prior@0, S.Id(challenger.Zero()));",
    ]


def test_f397_short_circuit_part_is_bound_whole() -> None:
    # Binding challenger.Zero() alone would evaluate it when a is false.
    ordered = order_calls_for_inlining(
        _game("return F.h(a && challenger.Zero(), S.Id(challenger.Inc()));"),
        _scheme_lookup(),
        {},
        challenger=_challenger(),
    )
    assert _statements(ordered) == [
        "Bool S.Id@prior@0 = a && challenger.Zero();",
        "return F.h(S.Id@prior@0, S.Id(challenger.Inc()));",
    ]


def test_f397_else_if_condition_is_split_rather_than_bound() -> None:
    # The first condition runs only before the else if: it cannot be bound
    # in front of the whole if, so the else if moves into an else block.
    game = _game(
        "if (challenger.Inc()) { return true; } "
        "else if (S.Id(challenger.Zero())) { return false; } return true;"
    )
    challenger = _challenger()
    rewritten = make_conditional_calls_explicit(
        game, _scheme_lookup(), {}, None, challenger
    )
    assert rewritten is game
    ordered = order_calls_for_inlining(
        game, _scheme_lookup(), {}, challenger=challenger
    )
    expected = _game(
        "if (challenger.Inc()) { return true; } "
        "else { if (S.Id(challenger.Zero())) { return false; } } return true;"
    )
    assert ordered.methods[0].block == expected.methods[0].block, str(ordered)


def test_f372_hoisted_operand_stays_behind_an_earlier_challenger_call() -> None:
    # The second review's case: while the reduction is resolved alone, the
    # rewrite would move Zero (in the left operand) in front of Inc.
    rewritten = make_conditional_calls_explicit(
        _game("return F.h(challenger.Inc(), challenger.Zero() && S.Pick(U));"),
        _scheme_lookup(),
        {},
        None,
        _challenger(),
    )
    assert _statements(rewritten) == [
        "Bool S.Pick@prior@0 = challenger.Inc();",
        "Bool S.Pick@cond@0 = challenger.Zero();",
        "if (S.Pick@cond@0) {\nS.Pick@cond@0 = S.Pick(U);\n}",
        "return F.h(S.Pick@prior@0, S.Pick@cond@0);",
    ]


def test_f372_hoisted_operand_moves_past_an_unrelated_call() -> None:
    # Read touches only `c`, which neither operand touches: it stays put.
    rewritten = make_conditional_calls_explicit(
        _game("return F.h(challenger.Read(), b && S.Pick(U));"),
        _scheme_lookup(),
        {},
        None,
        _challenger(),
    )
    assert _statements(rewritten) == [
        "Bool S.Pick@cond@0 = b;",
        "if (S.Pick@cond@0) {\nS.Pick@cond@0 = S.Pick(U);\n}",
        "return F.h(challenger.Read(), S.Pick@cond@0);",
    ]


def test_f372_temporary_is_apart_from_a_callee_local() -> None:
    # PickCond's local `cond`, inlined at index 0, is `S.PickCond@cond0`; the
    # rewrite's temporary must not be that name, or the inlined declaration
    # would shadow it and the temporary would keep `b`.
    resolved = _resolve(
        _game("Bool r = !(b && S.PickCond(U)); return r;"), _scheme_lookup()
    )
    statements = resolved.methods[0].block.statements
    assert str(statements[0]).strip() == "Bool S.PickCond@cond@0 = b;"
    guard = statements[1]
    assert isinstance(guard, frog_ast.IfStatement)
    assert str(guard.blocks[0].statements[-1]).strip() == (
        "S.PickCond@cond@0 = S.PickCond@cond0;"
    )


def test_f397_part_conflicting_with_a_bound_part_is_bound_too() -> None:
    # The review of S36's retry: ReadD (moved with S.IdI) conflicts only with
    # Copy, but binding Copy moves it in front of Bump, which writes the `c`
    # Copy reads, so Bump is bound too, ahead of it. ReadE touches nothing
    # either of them touches and stays where it is.
    ordered = order_calls_for_inlining(
        _game(
            "return F.h(challenger.ReadE(), challenger.Bump(), challenger.Copy(), "
            "S.IdI(challenger.ReadD()));",
            "Int",
        ),
        _scheme_lookup(),
        {},
        challenger=_challenger(),
    )
    assert _statements(ordered) == [
        "Int S.IdI@prior@0 = challenger.Bump();",
        "Int S.IdI@prior@1 = challenger.Copy();",
        "return F.h(challenger.ReadE(), S.IdI@prior@0, S.IdI@prior@1, "
        "S.IdI(challenger.ReadD()));",
    ]


def test_f372_part_conflicting_with_a_bound_part_is_bound_too() -> None:
    # The same through the rewrite: the hoisted DZero conflicts only with
    # Copy, and Copy with the earlier Bump.
    rewritten = make_conditional_calls_explicit(
        _game(
            "return F.h(challenger.Bump(), challenger.Copy(), "
            "challenger.DZero() && S.Pick(U));"
        ),
        _scheme_lookup(),
        {},
        None,
        _challenger(),
    )
    assert _statements(rewritten) == [
        "Int S.Pick@prior@0 = challenger.Bump();",
        "Int S.Pick@prior@1 = challenger.Copy();",
        "Bool S.Pick@cond@0 = challenger.DZero();",
        "if (S.Pick@cond@0) {\nS.Pick@cond@0 = S.Pick(U);\n}",
        "return F.h(S.Pick@prior@0, S.Pick@prior@1, S.Pick@cond@0);",
    ]


def test_f397_call_in_the_callee_position_is_an_earlier_part() -> None:
    # The second review of S36: the callee expression of a call runs before
    # its arguments, and the inliner takes a call there first. The `c` read
    # ahead of it is bound before BumpGetF's increment moves in front.
    ordered = order_calls_for_inlining(
        _game("return [c, challenger.BumpGetF()(5)];", "[Int, Int]"),
        _composed_lookup(),
        {},
    )
    assert _statements(ordered) == [
        "Int challenger.BumpGetF@prior@0 = c;",
        "return [challenger.BumpGetF@prior@0, challenger.BumpGetF()(5)];",
    ]


def test_f397_callee_position_call_is_bound_in_order() -> None:
    # While the reduction is resolved alone, S.IdI's argument Read moves in
    # front; BumpGetF() in the callee position writes the `c` Read reads, so
    # it is bound, and with it the earlier Read() it would otherwise pass.
    ordered = order_calls_for_inlining(
        _game(
            "return [challenger.Read(), challenger.BumpGetF()(5), "
            "S.IdI(challenger.Read())];",
            "[Int, Int, Int]",
        ),
        _scheme_lookup(),
        {},
        challenger=_challenger(),
    )
    assert _statements(ordered) == [
        "Int S.IdI@prior@0 = challenger.Read();",
        "Function<Int, Int> S.IdI@prior@1 = challenger.BumpGetF();",
        "return [S.IdI@prior@0, S.IdI@prior@1(5), S.IdI(challenger.Read())];",
    ]


def test_f372_callee_position_call_stays_ahead_of_a_hoisted_operand() -> None:
    # The guarded Inc moves in front of the statement; BumpGetF() in the
    # callee position of an earlier part writes the same `c`, so it is bound
    # ahead of it.
    rewritten = make_conditional_calls_explicit(
        _game(
            "return [challenger.BumpGetF()(5) == 0, b && challenger.Inc()];",
            "[Bool, Bool]",
        ),
        _scheme_lookup(),
        {},
        None,
        _challenger(),
    )
    assert _statements(rewritten) == [
        "Function<Int, Int> challenger.Inc@prior@0 = challenger.BumpGetF();",
        "Bool challenger.Inc@cond@0 = b;",
        "if (challenger.Inc@cond@0) {\nchallenger.Inc@cond@0 = challenger.Inc();\n}",
        "return [challenger.Inc@prior@0(5) == 0, challenger.Inc@cond@0];",
    ]


def test_f372_step_detail_shows_the_reduction_resolved_alone() -> None:
    # The step-detail display resolves a step's reduction alone; it now does
    # so as the prover does, with the challenger's methods known.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "proof_frog",
            "step-detail",
            str(_FIXTURES / "F_372" / "reorder.proof"),
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    reduction = json.loads(result.stdout)["reduction"]
    assert reduction.index("challenger.Inc()") < reduction.index(
        "challenger.Zero()"
    ), reduction
