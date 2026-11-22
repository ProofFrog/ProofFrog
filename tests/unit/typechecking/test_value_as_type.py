"""A name that denotes a value may not stand where a type is expected (F-423).

``frog_ast.Variable`` models both a value reference and a type name, and the
type checker read a value name in a type position as that value's type: with
``BitString<8>? c``, a parameter ``c y`` had type ``BitString<8>?`` and
``Set K = c;`` made ``K`` stand for ``BitString<8>?``. The engine reads such
a name as an abstract type, whose values are never None, so ``y == None``
folded to ``false`` while the adversary could pass ``None``. A value name is
now refused as a declared type (of a parameter, field or local), as the
value of a ``Set`` alias (``let:``, game, scheme or primitive), and as the
argument for a ``Set`` parameter. A name declared with the bare kind ``Set``
(a ``Set K`` parameter, a ``Set K = ...;`` alias, a ``let:`` ``Set K;``), a
member alias ``E.Key`` and a primitive, scheme or game name remain types;
a value inside a length, modulus or group (``BitString<n>``,
``GroupElem<G>``) is an expression and is unaffected.
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_CHECKER = """
Primitive Checker(Set K) {
    Set Elem = K;
    Bool Check(Elem x);
}
"""

_NONE_CHECK = """
import 'Checker.primitive';

Scheme NoneCheck(Set K) extends Checker {
    Set Elem = K;

    Bool Check(Elem x) {
        return this.IsNone(x);
    }

    Bool IsNone(Elem? v) {
        return v == None;
    }
}
"""

_OPT_PAIR = """
Game Left(BitString<8>? y) {
    Bool Test() {
        return y == None;
    }
}

Game Right(BitString<8>? y) {
    Bool Test() {
        return false;
    }
}

export as OptPair;
"""


def _check(tmp_path: Path, files: dict[str, str], main: str) -> None:
    for name, source in files.items():
        (tmp_path / name).write_text(source)
    path = str(tmp_path / main)
    semantic_analysis.check_well_formed(frog_parser.parse_file(path), path)


def _game_pair(header: str, fields: str, test_signature: str) -> str:
    return (
        f"Game Left({header}) {{ {fields} Bool {test_signature} "
        "{ return y == None; } }\n"
        f"Game Right({header}) {{ {fields} Bool {test_signature} "
        "{ return false; } }\n"
        "export as P;\n"
    )


@pytest.mark.parametrize(
    "files, main, message",
    [
        # A game parameter's value as a method parameter's type.
        (
            {"p.game": _game_pair("BitString<8>? c", "", "Test(c y)")},
            "p.game",
            "c is a value of type BitString<8>?, not a type",
        ),
        # A game's Set alias of a value.
        (
            {"p.game": _game_pair("BitString<8>? c", "Set F = c;", "Test(F y)")},
            "p.game",
            "The set F is defined as c: c is a value of type BitString<8>?, "
            "not a type",
        ),
        # A let: Set alias of a value.
        (
            {
                "OptPair.game": _OPT_PAIR,
                "t.proof": "import 'OptPair.game';\nproof:\nlet:\n"
                "    BitString<8>? c;\n    Set K = c;\n    K d;\n"
                "theorem:\n    OptPair(d);\ngames:\n"
                "    OptPair(d).Left against OptPair(d).Adversary;\n"
                "    OptPair(d).Right against OptPair(d).Adversary;\n",
            },
            "t.proof",
            "The set K is defined as c: c is a value of type BitString<8>?, "
            "not a type",
        ),
        # A primitive's member alias of a value parameter.
        (
            {
                "OptP.primitive": "Primitive OptP(BitString<8>? c) "
                "{ Set Elem = c; Elem Pick(); }"
            },
            "OptP.primitive",
            "The set Elem is defined as c: c is a value of type BitString<8>?, "
            "not a type",
        ),
        # A scheme's member alias of a value parameter.
        (
            {
                "Checker.primitive": _CHECKER,
                "V.scheme": "import 'Checker.primitive';\n"
                "Scheme V(BitString<8>? c) extends Checker {\n"
                "    Set Elem = c;\n"
                "    Bool Check(Elem x) { return x == x; }\n"
                "}\n",
            },
            "V.scheme",
            "The set Elem is defined as c: c is a value of type BitString<8>?, "
            "not a type",
        ),
        # A value as the argument for a Set parameter.
        (
            {
                "Checker.primitive": _CHECKER,
                "NoneCheck.scheme": _NONE_CHECK,
                "OptPair.game": _OPT_PAIR,
                "t.proof": "import 'Checker.primitive';\n"
                "import 'NoneCheck.scheme';\nimport 'OptPair.game';\n"
                "proof:\nlet:\n"
                "    BitString<8> c;\n    NoneCheck C = NoneCheck(c);\n"
                "theorem:\n    OptPair(c);\ngames:\n"
                "    OptPair(c).Left against OptPair(c).Adversary;\n"
                "    OptPair(c).Right against OptPair(c).Adversary;\n",
            },
            "t.proof",
            "Argument c for the Set parameter 'K' of NoneCheck is a value of "
            "type BitString<8>, not a type",
        ),
        # A game parameter's value as a local's type.
        (
            {
                "p.game": "Game Left(Int n) { Bool Test() { n x = 5; return true; } }\n"
                "Game Right(Int n) { Bool Test() { return true; } }\n"
                "export as P;\n"
            },
            "p.game",
            "n is a value of type Int, not a type",
        ),
    ],
)
def test_value_as_type_is_refused(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    files: dict[str, str],
    main: str,
    message: str,
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(tmp_path, files, main)
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "files, main",
    [
        # A game's Set parameter and an alias of it as types.
        (
            {
                "p.game": _game_pair("Set K", "Set F = K;", "Test(F y)").replace(
                    "y == None", "y == y"
                )
            },
            "p.game",
        ),
        # let: Set entries, an alias of one, a value of it.
        (
            {
                "OptPair.game": _OPT_PAIR,
                "t.proof": "import 'OptPair.game';\nproof:\nlet:\n"
                "    Set K;\n    Set D = K;\n    D d;\n"
                "    BitString<8>? e;\n"
                "theorem:\n    OptPair(e);\ngames:\n"
                "    OptPair(e).Left against OptPair(e).Adversary;\n"
                "    OptPair(e).Right against OptPair(e).Adversary;\n",
            },
            "t.proof",
        ),
        # A member alias of a Set parameter, and a member alias as a type.
        (
            {
                "Checker.primitive": _CHECKER,
                "NoneCheck.scheme": _NONE_CHECK,
            },
            "NoneCheck.scheme",
        ),
        # Values inside a length and a group.
        (
            {
                "p.game": "Game Left(Int n, Group G) { Bool Test(BitString<n> y, "
                "GroupElem<G> g) { return y == y && g == g; } }\n"
                "Game Right(Int n, Group G) { Bool Test(BitString<n> y, "
                "GroupElem<G> g) { return true; } }\n"
                "export as P;\n"
            },
            "p.game",
        ),
    ],
)
def test_types_are_accepted(tmp_path: Path, files: dict[str, str], main: str) -> None:
    _check(tmp_path, files, main)
