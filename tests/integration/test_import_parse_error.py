"""A parse error in an imported file is reported like one in the file itself.

Imports are parsed during type checking (name resolution), outside the
CLI's handler for the checked file's own parse error, so ``prove`` and
``check`` used to print a Python traceback ending in the ParseError (F-402).
They now print the error (file, line and message) and exit 1.

A power in a type size, such as ``BitString<2 ^ k>``, is outside the type
grammar; the parser now names the ``^`` instead of reporting the cascade it
caused ("Game body cannot be empty" at the last closing brace).
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent

_SIZE_POW_GAME = """\
Game Left(Int k) {
    BitString<2 ^ k> Get() {
        BitString<2 ^ k> x <- BitString<2 ^ k>;
        return x;
    }
}
Game Right(Int k) {
    BitString<2 ^ k> Get() {
        BitString<2 ^ k> x <- BitString<2 ^ k>;
        return x;
    }
}
export as SizePow;
"""

_SIZE_POW_PROOF = """\
import 'SizePow.game';
proof:
let:
    Int kl;
theorem:
    SizePow(kl);
games:
    SizePow(kl).Left against SizePow(kl).Adversary;
    SizePow(kl).Right against SizePow(kl).Adversary;
"""

# A primitive missing a ';', imported by a scheme the proof imports.
_BAD_PRIMITIVE = """\
Primitive Bad(Int k) {
    Int lambda = k
    BitString<lambda> F(BitString<lambda> x);
}
"""

_USES_BAD_SCHEME = """\
import 'Bad.primitive';
Scheme UsesBad(Bad B) extends Bad {
    Int lambda = B.lambda;
    BitString<lambda> F(BitString<lambda> x) {
        return B.F(x);
    }
}
"""

_NESTED_PROOF = """\
import 'UsesBad.scheme';
proof:
let:
    Int k;
    Bad B = Bad(k);
    UsesBad S = UsesBad(B);
theorem:
    Foo(S);
games:
    Foo(S).Left against Foo(S).Adversary;
    Foo(S).Right against Foo(S).Adversary;
"""


def _run(command: str, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", command, str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write(directory: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")


@pytest.mark.parametrize("command", ["prove", "check"])
def test_power_in_imported_game_type_is_a_parse_error(
    tmp_path: Path, command: str
) -> None:
    _write(
        tmp_path, {"SizePow.game": _SIZE_POW_GAME, "size_pow.proof": _SIZE_POW_PROOF}
    )
    result = _run(command, tmp_path / "size_pow.proof")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert (
        f"{tmp_path / 'SizePow.game'}:2:16: parse error: '^' is not allowed in "
        "the size of BitString<...>" in result.stderr
    )
    assert "Game body cannot be empty" not in result.stderr


@pytest.mark.parametrize("command", ["prove", "check"])
def test_parse_error_in_file_imported_by_an_import(
    tmp_path: Path, command: str
) -> None:
    _write(
        tmp_path,
        {
            "Bad.primitive": _BAD_PRIMITIVE,
            "UsesBad.scheme": _USES_BAD_SCHEME,
            "nested.proof": _NESTED_PROOF,
        },
    )
    result = _run(command, tmp_path / "nested.proof")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert f"{tmp_path / 'Bad.primitive'}:2:18: parse error: missing ';'" in (
        result.stderr
    )


def test_check_scheme_reports_parse_error_in_its_import(tmp_path: Path) -> None:
    _write(
        tmp_path, {"Bad.primitive": _BAD_PRIMITIVE, "UsesBad.scheme": _USES_BAD_SCHEME}
    )
    result = _run("check", tmp_path / "UsesBad.scheme")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert f"{tmp_path / 'Bad.primitive'}:2:18: parse error: missing ';'" in (
        result.stderr
    )


def test_parse_error_in_the_proof_itself_is_reported_the_same_way(
    tmp_path: Path,
) -> None:
    """The format the import errors above match."""
    proof = tmp_path / "bad.proof"
    proof.write_text(
        _SIZE_POW_PROOF.replace("Int kl;", "BitString<2 ^ kl> s;"), encoding="utf-8"
    )
    result = _run("prove", proof)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert (
        f"{proof}:4:16: parse error: '^' is not allowed in the size of "
        "BitString<...>" in result.stderr
    )
