"""F-391: a field initializer that makes a call the inliner inlines.

The initializers run once, in declaration order, before ``Initialize``, and a
method call in one is made once. Since F-384 a field initialized by a method
call stays a field, and the inliner, reaching its initializer, had no block
to put the callee's body in: ``prove`` crashed with "pop from empty list"
(a game field ``k = S.Draw()``, a reduction field ``y = challenger.Bump()``).

Now the inliner leaves field initializers alone, and before inlining
``ProofEngine.resolve_step_game`` runs such an initializer as an assignment
at the start of ``Initialize`` (``run_call_initializers_in_initialize``),
the field starting at its type's default as any field without an
initializer does. A reduction's field initializer runs before its
``Initialize``, hence before ``challenger.Initialize``: one that calls
``challenger.Initialize``, or calls the challenger when the challenger has an
``Initialize``, is refused.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser, upto, visitors
from proof_frog.proof_engine import (
    UnsupportedFieldInitializerError,
    run_call_initializers_in_initialize,
)

_DRAW = frog_parser.parse_method(
    "BitString<8> Draw() { BitString<8> r <- BitString<8>; return r; }"
)
_LOOKUP = {("S", "Draw"): _DRAW}


def _game(source: str) -> frog_ast.Game:
    return frog_parser.parse_game(source)


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    return next(m for m in game.methods if m.signature.name == name)


def _field(game: frog_ast.Game, name: str) -> frog_ast.Field:
    return next(f for f in game.fields if f.name == name)


class TestInlinerSkipsFieldInitializers:
    def test_field_initializer_call_is_left_alone(self) -> None:
        game = _game("""
            Game G() {
                BitString<8> k = S.Draw();
                BitString<8> Get() { return k; }
            }""")
        # Used to raise IndexError ("pop from empty list").
        result = visitors.InlineTransformer(_LOOKUP).transform(game)
        assert result == game

    def test_method_calls_are_still_inlined(self) -> None:
        game = _game("""
            Game G() {
                BitString<8> k = S.Draw();
                BitString<8> Get() { return S.Draw(); }
            }""")
        result = visitors.InlineTransformer(_LOOKUP).transform(game)
        assert _field(result, "k").value == frog_parser.parse_expression("S.Draw()")
        assert "S.Draw()" not in str(_method(result, "Get"))


class TestRunInInitialize:
    def test_creates_initialize_when_absent(self) -> None:
        game = _game("""
            Game G() {
                BitString<8> k = S.Draw();
                BitString<8> Get() { return k; }
            }""")
        result = run_call_initializers_in_initialize(game, _LOOKUP)
        assert _field(result, "k").value is None
        assert result.methods[0] == frog_parser.parse_method(
            "Void Initialize() { k = S.Draw(); }"
        )
        assert _method(result, "Get") == _method(game, "Get")

    def test_prepends_to_existing_initialize(self) -> None:
        game = _game("""
            Game G() {
                BitString<8> k = S.Draw();
                Int c;
                Void Initialize() { c = 0; }
                BitString<8> Get() { return k; }
            }""")
        result = run_call_initializers_in_initialize(game, _LOOKUP)
        assert _method(result, "Initialize") == frog_parser.parse_method(
            "Void Initialize() { k = S.Draw(); c = 0; }"
        )
        assert len(result.methods) == len(game.methods)

    def test_later_initializer_reading_a_moved_field_moves_after_it(self) -> None:
        # j must read k's drawn value, not k's default.
        game = _game("""
            Game G(Int n) {
                BitString<8> k = S.Draw();
                Int m = n;
                BitString<8> j = k;
                BitString<8> Get() { return j; }
            }""")
        result = run_call_initializers_in_initialize(game, _LOOKUP)
        assert _field(result, "k").value is None
        assert _field(result, "j").value is None
        # m reads no moved field and keeps its initializer.
        assert _field(result, "m").value == frog_ast.Variable("n")
        assert _method(result, "Initialize") == frog_parser.parse_method(
            "Void Initialize() { k = S.Draw(); j = k; }"
        )

    def test_unchanged_without_an_inlinable_call(self) -> None:
        # P.Sample is not in the lookup (an opaque primitive method).
        game = _game("""
            Game G(Int n) {
                Int m = n;
                BitString<8> k = P.Sample();
                BitString<8> Get() { return k; }
            }""")
        assert run_call_initializers_in_initialize(game, _LOOKUP) is game

    def test_initialize_parameter_does_not_capture_a_moved_name(self) -> None:
        # The parameter k of Initialize would capture the field k written by
        # the moved assignment, and t, read by the moved initializer of j.
        game = _game("""
            Game G() {
                BitString<8> t;
                BitString<8> k = S.Draw();
                BitString<8> j = t + k;
                BitString<8> Initialize(BitString<8> k, BitString<8> t) {
                    return k + t;
                }
                BitString<8> Get() { return j; }
            }""")
        result = run_call_initializers_in_initialize(game, _LOOKUP)
        initialize = _method(result, "Initialize")
        names = [param.name for param in initialize.signature.parameters]
        assert "k" not in names and "t" not in names
        first, second = names
        moved = frog_parser.parse_method("Void f() { k = S.Draw(); j = t + k; }")
        assert initialize.block.statements[:2] == moved.block.statements
        assert initialize.block.statements[2:] == [
            frog_ast.ReturnStatement(
                frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.ADD,
                    frog_ast.Variable(first),
                    frog_ast.Variable(second),
                )
            )
        ]

    def test_moved_field_named_in_a_type_is_refused(self) -> None:
        lookup = {("S", "Len"): frog_parser.parse_method("Int Len() { return 8; }")}
        game = _game("""
            Game G() {
                Int n = S.Len();
                BitString<n> Get() { return 0^n; }
            }""")
        with pytest.raises(UnsupportedFieldInitializerError, match="'n'"):
            run_call_initializers_in_initialize(game, lookup)


_REDUCTION = """
Reduction R(Int n) compose Ctr(n) against Probe(n).Adversary {{
    {field}
    Int Get() {{ return challenger.Get(); }}
}}"""


def _reduction(field: str) -> frog_ast.Reduction:
    return frog_parser.parse_reduction(_REDUCTION.format(field=field))


class TestChallengerCallsInReductionFields:
    def test_challenger_call_allowed_when_challenger_has_no_initialize(
        self,
    ) -> None:
        red = _reduction("Int y = challenger.Bump();")
        assert upto.challenger_call_in_field_initializer(red, False) is None
        assert upto.check_challenger_init_placement(red, False) is None

    def test_challenger_call_refused_before_challenger_initialize(self) -> None:
        red = _reduction("Int y = challenger.Bump();")
        message = upto.check_challenger_init_placement(red, True)
        assert message is not None
        assert "R.y calls the challenger before challenger.Initialize" in message

    @pytest.mark.parametrize("has_initialize", [False, True])
    def test_challenger_initialize_in_a_field_is_refused(
        self, has_initialize: bool
    ) -> None:
        red = _reduction("Void y = challenger.Initialize();")
        message = upto.check_challenger_init_placement(red, has_initialize)
        assert message is not None
        assert "R.y calls challenger.Initialize" in message

    def test_other_field_initializers_are_unaffected(self) -> None:
        red = _reduction("Int y = n + 1;")
        assert upto.check_challenger_init_placement(red, True) is None
