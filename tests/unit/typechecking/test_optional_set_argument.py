"""A ``Set`` parameter may not be instantiated with an optional type (F-417).

The type checker refuses ``x == None`` for ``x`` of an abstract set ``K``, and
Dead Null Guard Elimination reads a value of an abstract set as never None.
Instantiating a ``Set`` parameter with ``T?`` broke both: a lemma proved for an
abstract ``K`` held only for sets without None, and a parent used it at
``K = BitString<8>?``. The type checker now refuses an argument for a bare
``Set`` parameter (of a scheme, primitive, game or reduction) that is, or
stands for through a ``let:`` alias or a member alias, an optional type."""

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

_HOLDER = """
Primitive Holder() {
    Set Elem = BitString<8>?;
    Elem Get();
}
"""

_CHECK_PAIR = """
import 'Checker.primitive';

Game Real(Checker C) {
    Bool Test(C.Elem x) {
        return C.Check(x);
    }
}

Game Ideal(Checker C) {
    Bool Test(C.Elem x) {
        return false;
    }
}

export as CheckPair;
"""

_SET_PAIR = """
Game Real(Set K) {
    Bool Test(K x) {
        return true;
    }
}

Game Ideal(Set K) {
    Bool Test(K x) {
        return false;
    }
}

export as SetPair;
"""

_CHECK_PROOF = """
import 'Checker.primitive';
import 'NoneCheck.scheme';
import 'Holder.primitive';
import 'CheckPair.game';

proof:

let:
{lets}

assume:

theorem:
    CheckPair(C);

games:
    CheckPair(C).Real against CheckPair(C).Adversary;
    CheckPair(C).Ideal against CheckPair(C).Adversary;
"""

_SET_PROOF = """
import 'SetPair.game';

proof:

let:
{lets}

assume:

theorem:
    SetPair({arg});

games:
    SetPair({arg}).Real against SetPair({arg}).Adversary;
    SetPair({arg}).Ideal against SetPair({arg}).Adversary;
"""


def _write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def _check_proof(tmp_path: Path, content: str) -> None:
    for name, source in [
        ("Checker.primitive", _CHECKER),
        ("NoneCheck.scheme", _NONE_CHECK),
        ("Holder.primitive", _HOLDER),
        ("CheckPair.game", _CHECK_PAIR),
        ("SetPair.game", _SET_PAIR),
    ]:
        _write(tmp_path, name, source)
    path = _write(tmp_path, "test.proof", content)
    semantic_analysis.check_well_formed(frog_parser.parse_file(path), path)


def _indent(lets: str) -> str:
    return "\n".join(f"    {line}" for line in lets.splitlines())


_OPTIONAL = "a Set parameter may not be instantiated with an optional type"


@pytest.mark.parametrize(
    "lets, message",
    [
        pytest.param(
            "NoneCheck C = NoneCheck(BitString<8>?);",
            "Argument BitString<8>? for the Set parameter 'K' of NoneCheck is"
            f" the optional type BitString<8>?: {_OPTIONAL}",
            id="scheme_direct",
        ),
        pytest.param(
            "Set K = BitString<8>?;\nNoneCheck C = NoneCheck(K);",
            "Argument K for the Set parameter 'K' of NoneCheck is the optional"
            f" type BitString<8>?: {_OPTIONAL}",
            id="scheme_let_alias",
        ),
        pytest.param(
            "Set J = BitString<8>?;\nSet K = J;\nNoneCheck C = NoneCheck(K);",
            "Argument K for the Set parameter 'K' of NoneCheck is the optional"
            f" type BitString<8>?: {_OPTIONAL}",
            id="scheme_chained_alias",
        ),
        pytest.param(
            "Holder H = Holder();\nNoneCheck C = NoneCheck(H.Elem);",
            "Argument H.Elem for the Set parameter 'K' of NoneCheck is the"
            f" optional type BitString<8>?: {_OPTIONAL}",
            id="scheme_member_alias",
        ),
        pytest.param(
            "Set K;\nNoneCheck C = NoneCheck(K?);",
            "Argument K? for the Set parameter 'K' of NoneCheck is the optional"
            f" type K?: {_OPTIONAL}",
            id="scheme_optional_of_abstract",
        ),
        pytest.param(
            "Checker C = Checker(BitString<8>?);",
            "Argument BitString<8>? for the Set parameter 'K' of Checker is the"
            f" optional type BitString<8>?: {_OPTIONAL}",
            id="primitive_direct",
        ),
        pytest.param(
            "Set K = BitString<8>?;\nChecker C = Checker(K);",
            "Argument K for the Set parameter 'K' of Checker is the optional"
            f" type BitString<8>?: {_OPTIONAL}",
            id="primitive_let_alias",
        ),
    ],
)
def test_optional_argument_for_a_set_parameter_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], lets: str, message: str
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_proof(tmp_path, _CHECK_PROOF.format(lets=_indent(lets)))
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "lets, arg",
    [
        pytest.param("", "BitString<8>?", id="direct"),
        pytest.param("Set K = BitString<8>?;", "K", id="let_alias"),
    ],
)
def test_optional_argument_for_a_game_set_parameter_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], lets: str, arg: str
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_proof(tmp_path, _SET_PROOF.format(lets=_indent(lets), arg=arg))
    assert (
        f"Argument {arg} for the Set parameter 'K' of Real is the optional type"
        f" BitString<8>?: {_OPTIONAL}" in capsys.readouterr().err
    )


@pytest.mark.parametrize(
    "lets",
    [
        pytest.param("NoneCheck C = NoneCheck(BitString<8>);", id="concrete"),
        pytest.param("Set K;\nNoneCheck C = NoneCheck(K);", id="abstract"),
        pytest.param(
            "Set K = BitString<8>;\nNoneCheck C = NoneCheck(K);",
            id="alias_of_non_optional",
        ),
        pytest.param("Checker C = Checker(Bool);", id="primitive_concrete"),
    ],
)
def test_non_optional_argument_for_a_set_parameter_is_accepted(
    tmp_path: Path, lets: str
) -> None:
    _check_proof(tmp_path, _CHECK_PROOF.format(lets=_indent(lets)))


def test_optional_value_for_an_optional_parameter_is_accepted(
    tmp_path: Path,
) -> None:
    """The rule is about Set parameters only: a parameter of type ``T?``
    still takes an optional value."""
    _write(
        tmp_path,
        "OptPair.game",
        """
Game Left(BitString<8>? c) {
    Bool Test() {
        return c == None;
    }
}

Game Right(BitString<8>? c) {
    Bool Test() {
        return false;
    }
}

export as OptPair;
""",
    )
    path = _write(
        tmp_path,
        "opt.proof",
        """
import 'OptPair.game';

proof:

let:
    Set K = BitString<8>?;
    K c;

assume:

theorem:
    OptPair(c);

games:
    OptPair(c).Left against OptPair(c).Adversary;
    OptPair(c).Right against OptPair(c).Adversary;
""",
    )
    semantic_analysis.check_well_formed(frog_parser.parse_file(path), path)
