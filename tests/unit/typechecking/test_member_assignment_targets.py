"""The target of an assignment or sample may not be a member access.

Members such as ``M.keys`` or a scheme's field ``T.lambda`` are read-only.
The engine read ``M.keys = S;`` as no write to ``M``, kept a fact about
``M.keys`` across it and deleted a live branch. The type checker rejects a
member access anywhere on a target's spine (``M.keys``, ``T.lambda``,
``M.keys[0]``); element targets such as ``t[0]`` / ``M[k]``, including ones
whose index reads a member, are allowed.
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_PRIMITIVE = """\
Primitive Prim(Int n) {
    Int lambda = n;

    BitString<lambda> Sample();
}
"""

_GAMES = """\
import 'Prim.primitive';

Game Left(Prim T) {
    Map<Int, Int> M;
    [Int, Int] P;
    Map<Int, [Int, Int]> N;
    Int O(Set<Int> S, Int k, Int v) {
        BODY
        return 0;
    }
}

Game Right(Prim T) {
    Map<Int, Int> M;
    [Int, Int] P;
    Map<Int, [Int, Int]> N;
    Int O(Set<Int> S, Int k, Int v) {
        return 0;
    }
}

export as Targets;
"""

_SCHEME = """\
import 'Prim.primitive';

Scheme S(Int n) extends Prim {
    Int lambda = n;

    BitString<lambda> Sample() {
        BODY
        BitString<lambda> r <- BitString<lambda>;
        return r;
    }
}
"""


def _check_game(tmp_path: Path, body: str) -> None:
    (tmp_path / "Prim.primitive").write_text(_PRIMITIVE)
    path = tmp_path / "Targets.game"
    path.write_text(_GAMES.replace("BODY", body))
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


def _check_scheme(tmp_path: Path, body: str) -> None:
    (tmp_path / "Prim.primitive").write_text(_PRIMITIVE)
    path = tmp_path / "S.scheme"
    path.write_text(_SCHEME.replace("BODY", body))
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


@pytest.mark.parametrize(
    "body, message",
    [
        pytest.param(
            "M.keys = S;",
            "Cannot assign to 'M.keys': 'M.keys' is a member access,"
            " and members are read-only",
            id="map_keys_assignment",
        ),
        pytest.param(
            "M.values = S;",
            "Cannot assign to 'M.values'",
            id="map_values_assignment",
        ),
        pytest.param(
            "T.lambda = 5;",
            "Cannot assign to 'T.lambda'",
            id="primitive_field_assignment",
        ),
        pytest.param(
            "Int T.lambda = 5;",
            "Cannot assign to 'T.lambda'",
            id="typed_declaration",
        ),
        pytest.param(
            "M.keys[0] = 1;",
            "Cannot assign to 'M.keys[0]': 'M.keys' is a member access",
            id="element_of_member",
        ),
        pytest.param(
            "T.lambda <- Int;",
            "Cannot assign to 'T.lambda'",
            id="sample",
        ),
        pytest.param(
            "T.lambda <-uniq[S] Int;",
            "Cannot assign to 'T.lambda'",
            id="unique_sample",
        ),
    ],
)
def test_member_access_target_rejected_in_game(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str, message: str
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(tmp_path, body)
    assert message in capsys.readouterr().err


def test_member_access_target_rejected_in_scheme(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_scheme(tmp_path, "this.lambda = 3;")
    assert "Cannot assign to 'this.lambda'" in capsys.readouterr().err


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("M[k] = v;", id="map_element"),
        pytest.param("P[0] = v;", id="tuple_element"),
        pytest.param("N[k][1] = v;", id="nested_element"),
        pytest.param("M[T.lambda] = v;", id="member_in_index"),
        pytest.param("M[|M.keys|] = v;", id="member_read_in_index"),
        pytest.param("Int x = v; x = x + 1;", id="variable"),
        pytest.param("Bool b <- Bool;", id="sample_into_variable"),
    ],
)
def test_variable_and_element_targets_allowed(tmp_path: Path, body: str) -> None:
    _check_game(tmp_path, body)


def test_variable_target_allowed_in_scheme(tmp_path: Path) -> None:
    _check_scheme(tmp_path, "Int x = lambda;")
