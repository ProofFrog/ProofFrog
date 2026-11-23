"""F-420: a callee parameter read in a type of the callee's body is bound
when its argument reads a variable the game writes.

A type is read when its declaration runs: after ``ModInt<k> v;`` every store
into ``v`` reduces modulo the value ``k`` had at the declaration. The
inliner used to substitute the argument for ``k`` (``ModInt<c> v;``), and
when the game writes ``c`` (``c = c + 1;`` after the call), passes that
reorder or merge statements see the later store ``v = a;`` read nothing of
``c``: Topological Sorting moved the write between the declaration and the
store, and Merge Bare Declaration then made ``ModInt<c> v = a;`` after the
write, reducing ``a`` modulo the new ``c``. Bound to ``Int k0 = c;``, a
variable nothing writes, the type keeps the value of ``c`` at the call.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import InlineTransformer

_SCHEME = """
Scheme S() extends P {
    Bool Test(Int k, Int a) {
        ModInt<k> v;
        v = a;
        return v == v + v;
    }

    Bool Plus(Int k, Int a) {
        return k + a == a;
    }

    Bool Draw(Int k) {
        BitString<k> x <- BitString<k>;
        return x == x;
    }
}
"""


def _inline(caller_src: str, steps: int = 10) -> frog_ast.Game:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    game = frog_parser.parse_game(caller_src)
    for _ in range(steps):
        new_game = InlineTransformer(lookup).transform(game)
        if new_game == game:
            break
        game = new_game
    return game


def _method_text(game: frog_ast.Game, name: str) -> str:
    return str(next(m for m in game.methods if m.signature.name == name))


@pytest.mark.parametrize(
    "caller, binding, declaration",
    [
        # The caller writes c after the call.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ Bool r = S.Test(c, a); c = c + 1; return r; } }",
            "Int S.Test@k0 = c;",
            "ModInt<S.Test@k0> S.Test@v0;",
        ),
        # The argument reads c inside an expression.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ Bool r = S.Test(c + 1, a); c = c + 1; return r; } }",
            "Int S.Test@k0 = c + 1;",
            "ModInt<S.Test@k0> S.Test@v0;",
        ),
        # Another method writes c: still bound (conservative, game-wide).
        (
            "Game T() { Int c = 2; Void Initialize() { c = 3; } "
            "Bool f(Int a) { return S.Test(c, a); } }",
            "Int S.Test@k0 = c;",
            "ModInt<S.Test@k0> S.Test@v0;",
        ),
        # An element write counts as a write.
        (
            "Game T() { Array<Int, 2> A; Bool f(Int a) "
            "{ Bool r = S.Test(A[0], a); A[0] = 5; return r; } }",
            "Int S.Test@k0 = A[0];",
            "ModInt<S.Test@k0> S.Test@v0;",
        ),
        # A sampled length.
        (
            "Game T() { Int c = 2; Bool f() "
            "{ Bool r = S.Draw(c); c = c + 1; return r; } }",
            "Int S.Draw@k0 = c;",
            "BitString<S.Draw@k0> S.Draw@x0 <- BitString<S.Draw@k0>;",
        ),
    ],
)
def test_type_parameter_with_written_argument_is_bound(
    caller: str, binding: str, declaration: str
) -> None:
    text = _method_text(_inline(caller), "f")
    assert binding in text, text
    assert declaration in text, text


@pytest.mark.parametrize(
    "caller, declaration",
    [
        # c is a field nothing writes.
        (
            "Game T() { Int c = 2; Bool f(Int a) { return S.Test(c, a); } }",
            "ModInt<c> S.Test@v0;",
        ),
        # A literal.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ Bool r = S.Test(5, a); c = c + 1; return r; } }",
            "ModInt<5> S.Test@v0;",
        ),
        # A game parameter nothing writes.
        (
            "Game T(Int n) { Int c = 2; Bool f(Int a) "
            "{ Bool r = S.Test(n, a); c = c + 1; return r; } }",
            "ModInt<n> S.Test@v0;",
        ),
    ],
)
def test_type_parameter_with_unwritten_argument_is_substituted(
    caller: str, declaration: str
) -> None:
    text = _method_text(_inline(caller), "f")
    assert declaration in text, text
    assert "S.Test@k0" not in text, text


def test_parameter_read_only_in_expressions_is_substituted() -> None:
    """``k`` appears in no type of ``Plus``: an expression reads the
    argument where the callee reads the parameter, and nothing between the
    call and that read writes the caller's variables."""
    text = _method_text(
        _inline(
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ Bool r = S.Plus(c, a); c = c + 1; return r; } }"
        ),
        "f",
    )
    assert "S.Plus@k0" not in text, text
    assert "Bool r = c + a == a;" in text, text


def test_write_in_a_method_of_the_lookup_counts() -> None:
    """A reduction's challenger calls are inlined one per round, and the
    write to a challenger field can sit in a method not yet inlined
    (``challenger.Inc()`` after ``challenger.Test(...)``): the inliner also
    looks for writes in the bodies of the methods it inlines."""
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    challenger = frog_parser.parse_game("Game C() { Void Inc() { cc = cc + 1; } }")
    lookup[("challenger", "Inc")] = challenger.methods[0]
    game = frog_parser.parse_game(
        "Game T() { Bool f(Int a) "
        "{ Bool r = S.Test(cc, a); challenger.Inc(); return r; } }"
    )
    first = InlineTransformer(lookup).transform(game)
    text = _method_text(first, "f")
    assert "Int S.Test@k0 = cc;" in text, text
    assert "ModInt<S.Test@k0> S.Test@v0;" in text, text


def test_written_scope_is_searched_for_writes() -> None:
    """``apply_reduction`` inlines ``challenger.Initialize`` into the
    reduction's Initialize alone; the writes in the other methods are found
    through ``written_scope``."""
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    game = frog_parser.parse_game(
        "Game T() { Int c = 2; Void Initialize(Int a) { Bool r = S.Test(c, a); } "
        "Void Bump() { c = c + 1; } }"
    )
    initialize = game.methods[0]
    result = InlineTransformer(lookup, written_scope=game).transform(initialize)
    assert "Int S.Test@k0 = c;" in str(result), str(result)


def test_hop_with_a_changing_name_in_a_type_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The fail-closed check after inlining: with the binding disabled, the
    inlined Left has `ModInt<c> v;` with `c` written later. The passes'
    guard (`apply_pass`) only refuses an output that adds such a name, and a
    pass that moves the declaration adds none, so a game that comes out of
    inlining with one is not resolved and the hop fails."""
    # pylint: disable=import-outside-toplevel
    from proof_frog import visitors
    from proof_frog.proof_engine import FailedProof
    from proof_frog.web_server import _setup_engine_for_proof

    monkeypatch.setattr(
        visitors.InlineTransformer, "_reads_written_name", lambda self, arg: False
    )
    path = (
        "tests/integration/soundness_regression_fixtures/F_420/attack_merge_flat.proof"
    )
    engine, proof_file = _setup_engine_for_proof(path)
    with pytest.raises(FailedProof):
        engine.prove(proof_file, path)
    output = capsys.readouterr().out
    assert "ModPair(E).Left: after inlining, a type names c" in output, output
    [hop] = engine.hop_results
    assert not hop.valid
