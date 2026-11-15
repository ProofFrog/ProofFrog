"""F-371: the method inliner evaluates an argument that calls a method once.

A call evaluates each argument once, before the callee's body. The inliner
used to substitute every argument expression for the callee's parameter,
so an argument that draws was drawn once per read of the parameter, and not
at all when the callee never reads it. An argument with a call is now bound
to a variable of the parameter's type; an argument without calls is still
substituted.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import InlineTransformer, substitutable_argument

_SCHEME = """
Scheme S(Int n) extends P {
    Bool Same(BitString<n> x) {
        return x == x;
    }

    BitString<n> Ignore(BitString<n> x) {
        return 0^n;
    }

    BitString<n> DrawThenRead(BitString<n> x) {
        BitString<n> s <- BitString<n>;
        return s + x;
    }

    BitString<n> Draw() {
        BitString<n> r <- BitString<n>;
        return r;
    }
}
"""

_CHALLENGER = """
Game C(Int n) {
    Int count;

    BitString<n> Inc() {
        count = count + 1;
        return 0^n;
    }
}
"""


def _lookup() -> dict[tuple[str, str], frog_ast.Method]:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    challenger = frog_parser.parse_game(_CHALLENGER)
    lookup.update({("challenger", m.signature.name): m for m in challenger.methods})
    return lookup


def _inline(caller_src: str, steps: int = 10) -> frog_ast.Game:
    lookup = _lookup()
    game = frog_parser.parse_game(caller_src)
    for _ in range(steps):
        new_game = InlineTransformer(lookup).transform(game)
        if new_game == game:
            break
        game = new_game
    return game


def _samples(method: frog_ast.Method) -> int:
    return sum(
        isinstance(statement, frog_ast.Sample) for statement in method.block.statements
    )


@pytest.mark.parametrize(
    "arg, substitutable",
    [
        ("y", True),
        ("5", True),
        ("0^n", True),
        ("y + 1^n", True),
        ("t[0]", True),
        ("[y, t[1]]", True),
        ("S.Draw()", False),
        ("S.Draw() + y", False),
        ("[S.Draw(), y]", False),
        ("H(y)", False),
        ("challenger.Inc()", False),
    ],
)
def test_f371_substitutable_argument(arg: str, substitutable: bool) -> None:
    assert substitutable_argument(frog_parser.parse_expression(arg)) is substitutable


def test_f371_argument_with_call_read_twice_is_drawn_once() -> None:
    game = _inline("Game T(Int n) { Bool O() { return S.Same(S.Draw()); } }")
    text = str(game)
    assert "BitString<n> S.Same@x0 = " in text
    assert "S.Same@x0 == S.Same@x0" in text
    assert _samples(game.get_method("O")) == 1


def test_f371_unread_argument_with_call_is_still_evaluated() -> None:
    """A draw passed to a parameter the callee never reads is still made."""
    game = _inline("Game T(Int n) { BitString<n> O() { return S.Ignore(S.Draw()); } }")
    assert _samples(game.get_method("O")) == 1


def test_f371_unread_challenger_call_keeps_its_effect() -> None:
    """A challenger call in an argument the callee never reads still
    changes the challenger's state."""
    game = _inline(
        "Game T(Int n) { BitString<n> O() { return S.Ignore(challenger.Inc()); } }"
    )
    assert "count = count + 1;" in str(game)


def test_f371_argument_is_evaluated_before_the_callee_body() -> None:
    """The bound argument's draw comes before the callee's own draw."""
    game = _inline(
        "Game T(Int n) { BitString<n> O() { return S.DrawThenRead(S.Draw()); } }"
    )
    statements = game.get_method("O").block.statements
    samples = [s for s in statements if isinstance(s, frog_ast.Sample)]
    assert len(samples) == 2
    assert isinstance(samples[0].var, frog_ast.Variable)
    assert samples[0].var.name.startswith("S.Draw@")
    assert isinstance(samples[1].var, frog_ast.Variable)
    assert samples[1].var.name.startswith("S.DrawThenRead@")


def test_f371_argument_without_call_is_substituted() -> None:
    game = _inline("Game T(Int n) { Bool O(BitString<n> y) { return S.Same(y + y); } }")
    text = str(game)
    assert "@" not in text
    assert "y + y == y + y" in text
