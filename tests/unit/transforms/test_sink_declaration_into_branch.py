"""Tests for SinkDeclarationIntoBranch.

A typed declaration ``T x = e;`` whose every later mention is inside one
branch of the next ``if`` that mentions it moves to the start of that
branch, when evaluating ``e`` later (and only on paths into the branch)
cannot change its value or anything else: every call in ``e`` touches no
game state, nothing it passes over writes or rebinds a name ``e`` reads, and
nothing it passes over makes a call that may touch state.
"""

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.control_flow import SinkDeclarationIntoBranch
from proof_frog.visitors import NameTypeMap

_PRIMITIVE = """
Primitive P(Int n) {
    Int Samp(Int x);
    deterministic Int det(Int x);
}
"""


def _ctx() -> PipelineContext:
    ctx = PipelineContext(
        variables={}, proof_let_types=NameTypeMap(), proof_namespace={}, subsets_pairs=[]
    )
    ctx.proof_namespace["F"] = frog_parser.parse_primitive_file(_PRIMITIVE)
    return ctx


def _game(body: str, fields: str = "") -> object:
    return frog_parser.parse_game(
        f"Game T() {{\n{fields}\n Int f(Int a, Bool b) {{\n{body}\n}}\n}}"
    )


def _apply(body: str, fields: str = "", ctx: PipelineContext | None = None):
    game = _game(body, fields)
    return game, SinkDeclarationIntoBranch().apply(game, ctx or _ctx())


def test_sinks_into_the_only_branch_that_uses_it() -> None:
    _, result = _apply("Int x = F.det(a);\nif (b) {\nreturn x + 1;\n}\nreturn 0;")
    assert result == _game("if (b) {\nInt x = F.det(a);\nreturn x + 1;\n}\nreturn 0;")


def test_sinks_a_nondeterministic_primitive_call_past_other_statements() -> None:
    """An abstract primitive call touches no game state, so evaluating it
    later, and only when the branch is taken, changes nothing observable."""
    _, result = _apply(
        "Int x = F.Samp(a);\nInt y = a + 1;\nif (b) {\nreturn x;\n}\nreturn y;"
    )
    assert result == _game(
        "Int y = a + 1;\nif (b) {\nInt x = F.Samp(a);\nreturn x;\n}\nreturn y;"
    )


def test_sinks_into_an_else_branch() -> None:
    _, result = _apply(
        "Int x = a + 1;\nif (b) {\nreturn 0;\n} else {\nreturn x;\n}"
    )
    assert result == _game("if (b) {\nreturn 0;\n} else {\nInt x = a + 1;\nreturn x;\n}")


def test_no_sink_when_a_condition_reads_it() -> None:
    game, result = _apply("Int x = a + 1;\nif (x == 2) {\nreturn x;\n}\nreturn 0;")
    assert result == game


def test_no_sink_when_two_branches_use_it() -> None:
    game, result = _apply(
        "Int x = a + 1;\nif (b) {\nreturn x;\n} else {\nreturn x + 1;\n}"
    )
    assert result == game


def test_no_sink_when_used_after_the_if() -> None:
    game, result = _apply("Int x = a + 1;\nif (b) {\nreturn x;\n}\nreturn x;")
    assert result == game


def test_no_sink_when_the_branch_rebinds_it() -> None:
    game, result = _apply(
        "Int x = a + 1;\nif (b) {\nInt y = x;\nInt x = 2;\nreturn x + y;\n}\nreturn 0;"
    )
    assert result == game


def test_no_sink_past_a_write_to_a_name_it_reads() -> None:
    """Moved past `a = 5;`, `e` would read the new value of `a`."""
    game, result = _apply("Int x = a + 1;\na = 5;\nif (b) {\nreturn x;\n}\nreturn a;")
    assert result == game


def test_no_sink_past_a_binder_of_a_name_it_reads() -> None:
    """`e` reads the field `g`; a local `g` declared in between would capture
    the moved read."""
    game, result = _apply(
        "Int x = g + 1;\nInt g = 2;\nif (b) {\nreturn x;\n}\nreturn g;",
        fields="Int g;",
    )
    assert result == game


def test_no_sink_with_a_stateful_call_in_the_value() -> None:
    game, result = _apply(
        "Int x = challenger.Get();\nif (b) {\nreturn x;\n}\nreturn 0;"
    )
    assert result == game


def test_no_sink_past_a_stateful_call() -> None:
    """`challenger.Inc()` may write state that `e` reads."""
    game, result = _apply(
        "Int x = a + 1;\nInt y = challenger.Inc();\nif (b) {\nreturn x;\n}\nreturn y;"
    )
    assert result == game


def test_no_sink_when_a_condition_makes_a_stateful_call() -> None:
    game, result = _apply(
        "Int x = a + 1;\nif (challenger.Test()) {\nreturn x;\n}\nreturn 0;"
    )
    assert result == game


def test_no_sink_into_a_loop() -> None:
    game, result = _apply(
        "Int x = a + 1;\nInt s = 0;\nfor (Int i = 0 to a) {\ns = s + x;\n}\nreturn s;"
    )
    assert result == game


def test_no_sink_of_a_draw() -> None:
    """Draws belong to Sink Uniform Sample, which checks their domains."""
    game, result = _apply("Int x <- Int;\nif (b) {\nreturn x;\n}\nreturn 0;")
    assert result == game


def test_engine_identifies_hoisted_and_sunk_declarations() -> None:
    """Two games that differ only in whether `x` is computed before the if or
    at the start of the only branch using it are the same program. `x` holds
    a non-deterministic primitive call used twice, so no inlining pass can
    remove it (on main the two games stay apart)."""
    left = """
        Game G() {
            Int f(Int a, Bool b) {
                Int x = F.Samp(a);
                Int y = a * 2;
                if (b) {
                    return x + x + y;
                }
                return y;
            }
        }
    """
    right = """
        Game G() {
            Int f(Int a, Bool b) {
                Int y = a * 2;
                if (b) {
                    Int x = F.Samp(a);
                    return x + x + y;
                }
                return y;
            }
        }
    """
    engine = ProofEngine()
    engine.proof_namespace = {"F": frog_parser.parse_primitive_file(_PRIMITIVE)}
    result = engine.check_equivalent(
        frog_parser.parse_game(left), frog_parser.parse_game(right)
    )
    assert result.valid


def test_no_sink_past_a_write_to_a_name_the_type_reads() -> None:
    """F-420's class: inlining can put a written variable in a type
    (`ModInt<c> x = a;` from a scheme's `ModInt<k> x = a;`). Moved past
    `c = c + 1;`, the store would reduce `a` modulo the new value."""
    game, result = _apply(
        "ModInt<g> x = a;\ng = g + 1;\nif (b) {\nreturn 0;\n}\nreturn 1;",
        fields="Int g;",
    )
    game2, result2 = _apply(
        "ModInt<g> x = a;\ng = g + 1;\nif (b) {\nBool t = x == x;\nreturn 0;\n}"
        "\nreturn 1;",
        fields="Int g;",
    )
    assert result == game
    assert result2 == game2
