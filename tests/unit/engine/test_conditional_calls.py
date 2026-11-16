"""F-372: a call evaluated only conditionally keeps its condition.

``&&`` and ``||`` on ``Bool`` short-circuit, and an ``else if`` condition is
evaluated only when every earlier condition is false. The method inliner puts
a callee's statements in front of the statement holding the call, so before
it runs, ``make_conditional_calls_explicit`` gives such a call explicit
control flow when its body has an effect (a draw that may not complete, or a
write to state outside the callee), and leaves every other call alone.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.conditional_calls import (
    UntypedConditionalCallError,
    make_conditional_calls_explicit,
)

_SCHEME = """
Scheme S() extends P {
    Bool Pick(Set<BitString<1>> U) {
        BitString<1> x <- BitString<1> \\ U;
        return true;
    }

    Bool Free(Set<BitString<1>> U) {
        BitString<1> x <- BitString<1>;
        return true;
    }

    Bool Wrap(Set<BitString<1>> U) {
        return S.Pick(U);
    }

    BitString<1> Bits(Set<BitString<1>> U) {
        BitString<1> x <- BitString<1> \\ U;
        return x;
    }

    Key Opaque(Set<BitString<1>> U) {
        BitString<1> x <- BitString<1> \\ U;
        return x;
    }
}
"""

_CHALLENGER = """
Game C() {
    Int c;
    Bool Q() {
        c = c + 1;
        return true;
    }
    Bool Get() {
        return c == 0;
    }
}
"""


def _lookup() -> dict[tuple[str, str], frog_ast.Method]:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    challenger = frog_parser.parse_game(_CHALLENGER)
    lookup.update({("challenger", m.signature.name): m for m in challenger.methods})
    return lookup


def _rewrite(game: frog_ast.Game, times: int = 1) -> frog_ast.Game:
    for _ in range(times):
        game = make_conditional_calls_explicit(game, _lookup(), {})
    return game


def _game(body: str, fields: str = "") -> frog_ast.Game:
    return frog_parser.parse_game(
        f"Game G() {{ {fields} Bool O(Bool a, Bool b, Set<BitString<1>> U, "
        f"BitString<1> y) {{ {body} }} }}"
    )


def _assert_body(game: frog_ast.Game, expected: str) -> None:
    assert game.methods[0].block == _game(expected).methods[0].block, str(game)


def test_f372_and_return_becomes_guarded_if() -> None:
    game = _rewrite(_game("return b && S.Pick(U);"))
    _assert_body(game, "if (b) { return S.Pick(U); } return false;")


def test_f372_or_return_becomes_guarded_if() -> None:
    game = _rewrite(_game("return b || S.Pick(U);"))
    _assert_body(game, "if (b) { return true; } return S.Pick(U);")


def test_f372_else_if_condition_moves_into_else() -> None:
    game = _rewrite(
        _game(
            "if (b) { return false; } else if (S.Pick(U)) { return true; } "
            "else { return a; } return true;"
        )
    )
    _assert_body(
        game,
        "if (b) { return false; } else { if (S.Pick(U)) { return true; } "
        "else { return a; } } return true;",
    )


def test_f372_and_inside_larger_expression_uses_a_temporary() -> None:
    game = _rewrite(_game("Bool r = !(b && S.Pick(U)); return r;"))
    block = game.methods[0].block
    assert [str(s).strip() for s in block.statements] == [
        "Bool S.Pick@cond0 = b;",
        "if (S.Pick@cond0) {\nS.Pick@cond0 = S.Pick(U);\n}",
        "Bool r = !(S.Pick@cond0);",
        "return r;",
    ]


def test_f372_or_inside_if_condition_negates_the_guard() -> None:
    game = _rewrite(_game("if (b || S.Pick(U)) { return a; } return false;"))
    block = game.methods[0].block
    assert [str(s).strip() for s in block.statements[:3]] == [
        "Bool S.Pick@cond0 = b;",
        "if (!(S.Pick@cond0)) {\nS.Pick@cond0 = S.Pick(U);\n}",
        "if (S.Pick@cond0) {\nreturn a;\n}",
    ]


def test_f372_call_argument_position() -> None:
    game = _rewrite(_game("return F.g(b && S.Pick(U));"))
    block = game.methods[0].block
    assert str(block.statements[-1]).strip() == "return F.g(S.Pick@cond0);"
    assert str(block.statements[0]).strip() == "Bool S.Pick@cond0 = b;"


def test_f372_nested_positions_are_rewritten_outermost_first() -> None:
    # One call rewrites the inner position too: the inliner runs before the
    # next call and would take S.Pick(U) out of `return b || S.Pick(U);`.
    once = _rewrite(_game("return a && (b || S.Pick(U));"))
    _assert_body(
        once,
        "if (a) { if (b) { return true; } return S.Pick(U); } return false;",
    )
    assert _rewrite(once) is once


def test_f372_temporary_name_is_fresh() -> None:
    game = _rewrite(
        _game(
            "Bool r = (b && S.Pick(U)) == a; Bool s = (a && S.Pick(U)) == b; "
            "return r && s;"
        ),
        times=2,
    )
    names = [
        s.var.name
        for s in game.methods[0].block.statements
        if isinstance(s, frog_ast.Assignment) and s.the_type is not None
    ]
    assert names[:2] == ["S.Pick@cond0", "r"]
    assert "S.Pick@cond1" in names


def test_f372_effect_through_a_nested_call() -> None:
    game = _rewrite(_game("return b && S.Wrap(U);"))
    _assert_body(game, "if (b) { return S.Wrap(U); } return false;")


def test_f372_challenger_call_that_writes_state() -> None:
    game = _rewrite(_game("return b && challenger.Q();"))
    _assert_body(game, "if (b) { return challenger.Q(); } return false;")


def test_f372_challenger_call_that_only_reads_state_is_left_alone() -> None:
    game = _game("return b && challenger.Get();")
    assert _rewrite(game) is game


def test_f372_call_without_effect_is_left_alone() -> None:
    game = _game("return b && S.Free(U); ")
    assert _rewrite(game) is game


def test_f372_bit_string_concatenation_is_left_alone() -> None:
    # `||` on bit strings is concatenation, which evaluates both operands.
    game = frog_parser.parse_game(
        "Game G() { BitString<2> O(BitString<1> y, Set<BitString<1>> U) "
        "{ return y || S.Bits(U); } }"
    )
    assert _rewrite(game) is game


def test_f372_waits_for_an_earlier_call_in_the_statement() -> None:
    # The inliner takes S.Free(U) first; the && is rewritten only after it,
    # so the two calls keep their order.
    game = _game("Bool r = S.Free(U) == (b && S.Pick(U)); return r;")
    assert _rewrite(game) is game


def test_f372_left_operand_call_moves_with_the_position() -> None:
    game = _rewrite(_game("return S.Free(U) && S.Pick(U);"))
    _assert_body(game, "if (S.Free(U)) { return S.Pick(U); } return false;")


def test_f372_untyped_or_is_refused() -> None:
    # Neither operand's type is known, so the `||` may be either one.
    game = frog_parser.parse_game(
        "Game G() { Key O(Set<BitString<1>> U) { return z || S.Opaque(U); } }"
    )
    with pytest.raises(UntypedConditionalCallError):
        _rewrite(game)


def test_f372_a_shared_node_is_evaluated_where_it_occurs() -> None:
    # The same expression object twice in one statement is two evaluations:
    # only the occurrence found is replaced by the temporary.
    game = _game("return [b, b];")
    site = frog_parser.parse_expression("b && S.Pick(U)")
    statement = game.methods[0].block.statements[0]
    assert isinstance(statement, frog_ast.ReturnStatement)
    statement.expression = frog_ast.Tuple([site, site])
    rewritten = _rewrite(game)
    statements = [str(s).strip() for s in rewritten.methods[0].block.statements]
    assert statements == [
        "Bool S.Pick@cond0 = b;",
        "if (S.Pick@cond0) {\nS.Pick@cond0 = S.Pick(U);\n}",
        "Bool S.Pick@cond1 = b;",
        "if (S.Pick@cond1) {\nS.Pick@cond1 = S.Pick(U);\n}",
        "return [S.Pick@cond0, S.Pick@cond1];",
    ]


def test_f372_nested_positions_with_a_temporary_in_one_call() -> None:
    once = _rewrite(_game("Bool r = a && (b || S.Pick(U)); return r;"))
    assert [str(s).strip() for s in once.methods[0].block.statements] == [
        "Bool S.Pick@cond0 = a;",
        "if (S.Pick@cond0) {\nBool S.Pick@cond1 = b;\n"
        "if (!(S.Pick@cond1)) {\nS.Pick@cond1 = S.Pick(U);\n}\n\n"
        "S.Pick@cond0 = S.Pick@cond1;\n}",
        "Bool r = S.Pick@cond0;",
        "return r;",
    ]
    assert _rewrite(once) is once


def test_f372_if_condition_is_rewritten_after_its_else_if_is_split() -> None:
    # Splitting off the else if leaves `a && S.Pick(U)` in the first
    # condition; the same call rewrites it, before the inliner can take
    # S.Pick(U) out of the condition.
    once = _rewrite(
        _game(
            "if (a && S.Pick(U)) { return true; } else if (S.Pick(U)) "
            "{ return false; } return false;"
        )
    )
    statements = once.methods[0].block.statements
    assert [str(s).strip() for s in statements[:2]] == [
        "Bool S.Pick@cond0 = a;",
        "if (S.Pick@cond0) {\nS.Pick@cond0 = S.Pick(U);\n}",
    ]
    rest = frog_parser.parse_game(
        "Game G() { Bool O(Bool t, Set<BitString<1>> U) { if (t) { return true; } "
        "else { if (S.Pick(U)) { return false; } } return false; } }"
    ).methods[0]
    renamed = visitors.rename_value_references(rest, {"t": "S.Pick@cond0"})
    assert statements[2:] == renamed.block.statements, str(once)


def test_f372_challenger_call_defers_only_once_composed() -> None:
    # While a reduction is resolved alone its challenger calls are not in the
    # lookup: the inliner passes over them, so the && is rewritten at once.
    # Once composed, the inliner takes challenger.Get() first.
    game = _game("return F.h(challenger.Get(), b && S.Pick(U));")
    scheme_only = {
        key: method for key, method in _lookup().items() if key[0] != "challenger"
    }
    alone = make_conditional_calls_explicit(game, scheme_only, {})
    assert str(alone.methods[0].block.statements[-1]).strip() == (
        "return F.h(challenger.Get(), S.Pick@cond0);"
    )
    assert _rewrite(game) is game


def _draw_guards(
    block: frog_ast.Block, guards: tuple[str, ...] = ()
) -> list[tuple[str, ...]]:
    """The conditions under which each draw from `BitString<1> \\ U` (the
    draw in S.Pick whose domain may be empty) runs: the conditions of the
    `if` blocks around it, and the negated condition of each earlier `if`
    whose every branch returns."""
    found: list[tuple[str, ...]] = []
    for statement in block.statements:
        # `x <- T \ U;` parses as a draw from T excluding U.
        if isinstance(statement, frog_ast.UniqueSample):
            found.append(guards)
        elif isinstance(statement, frog_ast.IfStatement):
            earlier: tuple[str, ...] = ()
            for index, inner in enumerate(statement.blocks):
                own: tuple[str, ...] = ()
                if index < len(statement.conditions):
                    own = (str(statement.conditions[index]),)
                found.extend(_draw_guards(inner, guards + earlier + own))
                earlier += tuple(f"not {c}" for c in own)
            returns = all(
                inner.statements
                and isinstance(inner.statements[-1], frog_ast.ReturnStatement)
                for inner in statement.blocks
            )
            if returns and len(statement.blocks) == len(statement.conditions):
                guards += earlier
    return found


def _resolve(
    game: frog_ast.Game,
    lookup: dict[tuple[str, str], frog_ast.Method] | None = None,
) -> frog_ast.Game:
    """Rewrite and inline to a fixed point, as `resolve_step_game` does."""
    lookup = _lookup() if lookup is None else lookup
    for _ in range(50):
        new_game = make_conditional_calls_explicit(game, lookup, {})
        new_game = visitors.InlineTransformer(lookup).transform(new_game)
        if new_game == game:
            return game
        game = new_game
    raise AssertionError("inlining did not converge")


@pytest.mark.parametrize(
    "body, guards",
    [
        ("return a && (b || S.Pick(U));", [("a", "not b")]),
        (
            "Bool r = a && (b || S.Pick(U)); return r;",
            [("S.Pick@cond0", "!(S.Pick@cond1)")],
        ),
        (
            "if (a && S.Pick(U)) { return true; } else if (S.Pick(U)) "
            "{ return false; } return false;",
            [("S.Pick@cond0",), ("not S.Pick@cond0",)],
        ),
        ("return [S.Free(U), b && S.Pick(U)];", [("S.Pick@cond0",)]),
    ],
    ids=["nested_return", "nested_temporary", "else_if_after_site", "deferred"],
)
def test_f372_inlining_keeps_every_draw_guarded(
    body: str, guards: list[tuple[str, ...]]
) -> None:
    # The rewriter and the inliner alternate; a draw that may not complete
    # must stay under the conditions that guard its call.
    resolved = _resolve(_game(body))
    assert _draw_guards(resolved.methods[0].block) == guards, str(resolved)


def test_f372_inlining_keeps_a_draw_guarded_before_composition() -> None:
    scheme_only = {
        key: method for key, method in _lookup().items() if key[0] != "challenger"
    }
    resolved = _resolve(
        _game("return F.h(challenger.Get(), b && S.Pick(U));"), scheme_only
    )
    assert _draw_guards(resolved.methods[0].block) == [("S.Pick@cond0",)], str(resolved)
