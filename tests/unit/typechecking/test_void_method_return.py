"""A method whose return type is Void contains no ``return`` (F-407, ruling Q18).

FrogLang has no bare ``return;``, but the type checker accepted ``return e;``
in a Void method when ``e`` was a Void call. The method inliner replaces the
statement ``return T.Take(true);`` by ``Take``'s body when that body does not
end in a return, so the early exit disappeared: ``if (b) { return
T.Take(true); } c = c + 1;`` became ``if (b) { } c = c + 1;``, and a game
whose oracle skips the update was proved interchangeable with one that
always makes it. The structural rules now refuse any ``return`` in a Void
method, at any depth, in games, reductions and schemes alike; name
resolution runs them on every parsed file, so the proof's own intermediate
games and reductions are covered too.
"""

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, semantic_analysis, structural_rules

_MESSAGE = (
    "Method Test has return type Void but contains a return statement: a Void"
    " method has no return; it ends at the end of its body"
)


def _messages(root: frog_ast.ASTNode) -> list[str]:
    return [v.message for v in structural_rules.check_structural_rules(root)]


def _game_messages(body: str) -> list[str]:
    return _messages(frog_parser.parse_game(f"""
        Game G(Taker T) {{
            Int c = 0;
            Void Test(Bool b) {{
                {body}
            }}
        }}"""))


class TestRefused:
    @pytest.mark.parametrize(
        "body",
        [
            # The method's last statement.
            "c = c + 1; return T.Take(b);",
            # An early exit at the top level.
            "return T.Take(b); c = c + 1;",
            # Inside a branch: F-407's shape.
            "if (b) { return T.Take(true); } c = c + 1;",
            # In an else-if arm and an else arm.
            "if (b) { c = 1; } else if (!b) { return T.Take(b); }",
            "if (b) { c = 1; } else { return T.Take(b); }",
            # Inside a numeric and a generic loop.
            "for (Int i = 0 to 3) { return T.Take(b); }",
            "Set<Int> S; for (Int e in S) { if (b) { return T.Take(b); } }",
            # A return of a non-call value.
            "if (b) { return c; }",
        ],
    )
    def test_return_anywhere_in_a_void_game_method(self, body: str) -> None:
        assert _MESSAGE in _game_messages(body)

    def test_message(self) -> None:
        assert _game_messages("if (b) { return T.Take(true); } c = c + 1;") == [
            _MESSAGE
        ]

    def test_violation_is_at_the_return(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Taker T) {
                Void Test(Bool b) {
                    if (b) {
                        return T.Take(true);
                    }
                }
            }""")
        (violation,) = structural_rules.check_structural_rules(game)
        assert isinstance(violation.node, frog_ast.ReturnStatement)

    def test_scheme_method(self) -> None:
        scheme = frog_parser.parse_string(
            """
            Scheme S() extends Taker {
                Void Test(Bool b) {
                    if (b) { return this.Other(b); }
                }
                Void Other(Bool b) { }
            }""",
            frog_ast.FileType.SCHEME,
        )
        assert _messages(scheme) == [_MESSAGE]

    def test_reduction_method(self) -> None:
        reduction = frog_parser.parse_reduction("""
            Reduction R() compose Pair() against Pair().Adversary {
                Void Test(Bool b) {
                    for (Int i = 0 to 2) {
                        return challenger.Test(b);
                    }
                }
            }""")
        assert _messages(reduction) == [_MESSAGE]

    def test_void_initialize(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Taker T) {
                Void Initialize() {
                    return T.Take(true);
                }
            }""")
        assert _messages(game) == [
            "Method Initialize has return type Void but contains a return"
            " statement: a Void method has no return; it ends at the end of its"
            " body"
        ]


class TestAccepted:
    @pytest.mark.parametrize(
        "body",
        [
            # No statement at all.
            "",
            # A Void call as a statement, in a branch and a loop.
            "if (b) { T.Take(true); } else { c = c + 1; }",
            "for (Int i = 0 to 3) { T.Take(b); c = c + i; }",
        ],
    )
    def test_void_method_without_return(self, body: str) -> None:
        assert not _game_messages(body)

    def test_early_return_in_a_non_void_method(self) -> None:
        assert not _messages(frog_parser.parse_game("""
            Game G() {
                Int c = 0;
                Int Test(Bool b) {
                    if (b) {
                        return 0;
                    }
                    for (Int i = 0 to 3) {
                        if (i == c) { return i; }
                    }
                    c = c + 1;
                    return c;
                }
                Void Bump() {
                    c = c + 1;
                }
            }"""))

    def test_non_void_initialize_returns(self) -> None:
        assert not _messages(frog_parser.parse_game("""
            Game G() {
                Int c;
                Int Initialize() {
                    c = 1;
                    return c;
                }
            }"""))


# End to end through the type checker: the proof's own intermediate game and
# reduction are checked, not only the imported games.

_TAKER = """\
Primitive Taker() {
    Void Take(Bool b);
}
"""

_COUNT = """\
import 'Taker.primitive';

Game Left(Taker T) {
    Int c = 0;
    Void Test(Bool b) {
        c = c + 1;
    }
    Int Get() {
        return c;
    }
}

Game Right(Taker T) {
    Int c = 0;
    Void Test(Bool b) {
        c = c + 1;
    }
    Int Get() {
        return c;
    }
}

export as Count;
"""

_TRIVIAL = """\
Game Real() {
    Void Initialize() {
    }
}

Game Ideal() {
    Void Initialize() {
    }
}

export as Trivial;
"""

_PROOF = """\
import 'Taker.primitive';
import 'Count.game';
import 'Trivial.game';

Game Mid(Taker T) {
    Int c = 0;
    Void Test(Bool b) {
        MID_TEST
        c = c + 1;
    }
    Int Get() {
        return c;
    }
}

Reduction R(Taker T) compose Trivial() against Count(T).Adversary {
    Int c = 0;
    Void Test(Bool b) {
        R_TEST
        c = c + 1;
    }
    Int Get() {
        return c;
    }
}

proof:

let:
    Taker T;

assume:
    Trivial();

theorem:
    Count(T);

games:
    Count(T).Left against Count(T).Adversary;
    Mid(T) against Count(T).Adversary;
    Trivial().Real compose R(T) against Count(T).Adversary;
    Trivial().Ideal compose R(T) against Count(T).Adversary;
    Count(T).Right against Count(T).Adversary;
"""

_EARLY_EXIT = "if (b) { return T.Take(true); }"


def _write_proof(tmp_path: Path, mid_test: str, r_test: str) -> Path:
    (tmp_path / "Taker.primitive").write_text(_TAKER)
    (tmp_path / "Count.game").write_text(_COUNT)
    (tmp_path / "Trivial.game").write_text(_TRIVIAL)
    path = tmp_path / "count.proof"
    path.write_text(_PROOF.replace("MID_TEST", mid_test).replace("R_TEST", r_test))
    return path


def _check(path: Path) -> None:
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


@pytest.mark.parametrize(
    "mid_test, r_test",
    [(_EARLY_EXIT, ""), ("", _EARLY_EXIT)],
    ids=["intermediate_game", "reduction"],
)
def test_proof_helper_with_return_is_a_type_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mid_test: str, r_test: str
) -> None:
    path = _write_proof(tmp_path, mid_test, r_test)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(path)
    assert _MESSAGE in capsys.readouterr().err


def test_proof_helpers_without_return_type_check(tmp_path: Path) -> None:
    _check(_write_proof(tmp_path, "T.Take(b);", "T.Take(b);"))
