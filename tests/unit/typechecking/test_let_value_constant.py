"""A proof ``let:`` value is a constant (ruling Q13, F-389, F-395).

A ``let:`` entry that does not instantiate a primitive or scheme is a value,
read as its expression wherever the entry is used. A value that makes a
non-deterministic call (``c = R.Draw()``, or a draw nested anywhere inside
it) would make the call again at each use, though the entry holds one
value, so a game returning ``[c, c]`` would read as two independent draws.
Such an entry is ill-formed: the type checker refuses it, naming the entry,
and ``ProofEngine.prove`` refuses it as well when called without the type
checker. A call is judged as the passes judge it: a primitive method
declared ``deterministic`` and a ``Function`` are deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, proof_engine, semantic_analysis

_PRIMITIVE = """\
Primitive Drawer() {
    BitString<8> Draw();
    deterministic BitString<8> Fixed();
    deterministic BitString<8> Id(BitString<8> x);
}
"""

_SCHEME = """\
import 'Drawer.primitive';

Scheme DrawWrap(Drawer R) extends Drawer {
    BitString<8> Draw() {
        return R.Draw();
    }

    deterministic BitString<8> Fixed() {
        return R.Fixed();
    }

    deterministic BitString<8> Id(BitString<8> x) {
        return R.Id(x);
    }
}
"""

_GAME = """\
Game Left(BitString<8> c) {
    BitString<8> Get() {
        return c;
    }
}

Game Right(BitString<8> c) {
    BitString<8> Get() {
        return c;
    }
}

export as LetValue;
"""

_FN = "Function<BitString<8>, BitString<8>>"


def _write_proof(tmp_path: Path, lets: str) -> Path:
    (tmp_path / "Drawer.primitive").write_text(_PRIMITIVE)
    (tmp_path / "DrawWrap.scheme").write_text(_SCHEME)
    (tmp_path / "LetValue.game").write_text(_GAME)
    proof_path = tmp_path / "let_value.proof"
    proof_path.write_text(
        "import 'Drawer.primitive';\n"
        "import 'DrawWrap.scheme';\n"
        "import 'LetValue.game';\n"
        "\n"
        "proof:\n"
        "let:\n"
        "    Drawer R;\n"
        f"    {_FN} H <- {_FN};\n"
        f"    {lets}\n"
        "theorem:\n"
        "    LetValue(c);\n"
        "games:\n"
        "    LetValue(c).Left against LetValue(c).Adversary;\n"
        "    LetValue(c).Right against LetValue(c).Adversary;\n"
    )
    return proof_path


def _type_check(proof_path: Path) -> None:
    root = frog_parser.parse_file(str(proof_path))
    semantic_analysis.check_well_formed(root, str(proof_path))


@pytest.mark.parametrize(
    "lets, entry, value",
    [
        # A non-deterministic primitive method.
        ("BitString<8> c = R.Draw();", "c", "R.Draw()"),
        # Nested in a value whose top is not a call.
        ("BitString<8> c = R.Draw() + 0^8;", "c", "R.Draw() + 0^8"),
        ("BitString<8> c = R.Fixed() + R.Draw();", "c", "R.Fixed() + R.Draw()"),
        # In the argument of a deterministic method.
        ("BitString<8> c = R.Id(R.Draw());", "c", "R.Id(R.Draw())"),
        # In the argument of a let: function.
        ("BitString<8> c = H(R.Draw());", "c", "H(R.Draw())"),
        (
            "BitString<8> c = H(R.Fixed() + R.Draw()) + 0^8;",
            "c",
            "H(R.Fixed() + R.Draw()) + 0^8",
        ),
        # A scheme method that draws.
        ("DrawWrap W = DrawWrap(R); BitString<8> c = W.Draw();", "c", "W.Draw()"),
        # The draw in an entry of its own: that entry is refused.
        ("BitString<8> x = R.Draw(); BitString<8> c = H(x);", "x", "R.Draw()"),
    ],
)
def test_let_value_making_nondeterministic_call_is_type_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    lets: str,
    entry: str,
    value: str,
) -> None:
    proof_path = _write_proof(tmp_path, lets)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _type_check(proof_path)
    error = capsys.readouterr().err
    assert f"let: entry '{entry}' = {value} makes a non-deterministic call" in error


@pytest.mark.parametrize(
    "lets",
    [
        # A primitive method declared deterministic.
        "BitString<8> c = R.Fixed();",
        "BitString<8> c = R.Id(R.Fixed()) + 0^8;",
        # A let: function, sampled or known, on a deterministic argument.
        "BitString<8> c = H(R.Fixed());",
        "BitString<8> c = H(0^8);",
        f"{_FN} K; BitString<8> c = K(H(0^8));",
        # No call at all.
        "BitString<8> c = 0^8;",
        # An instantiation is not a value.
        "DrawWrap W = DrawWrap(R); BitString<8> c = R.Fixed();",
    ],
)
def test_let_value_making_only_deterministic_calls_type_checks(
    tmp_path: Path, lets: str
) -> None:
    _type_check(_write_proof(tmp_path, lets))


def _proof_and_definitions(
    tmp_path: Path, lets: str
) -> tuple[frog_ast.ProofFile, dict[str, frog_ast.Root]]:
    proof_path = _write_proof(tmp_path, lets)
    proof = frog_parser.parse_proof_file(str(proof_path))
    definitions: dict[str, frog_ast.Root] = {}
    for imp in proof.imports:
        root = frog_parser.parse_file(
            frog_parser.resolve_import_path(imp.filename, str(proof_path))
        )
        definitions[root.get_export_name()] = root
    return proof, definitions


def test_nondeterministic_let_values_lists_offending_entries_in_order(
    tmp_path: Path,
) -> None:
    proof, definitions = _proof_and_definitions(
        tmp_path,
        "BitString<8> x = R.Draw(); BitString<8> y = R.Fixed(); "
        "DrawWrap W = DrawWrap(R); BitString<8> z = W.Draw(); "
        "BitString<8> c = H(x);",
    )
    refused = proof_engine.nondeterministic_let_values(
        proof.lets, proof.sampled_let_names, definitions
    )
    assert [let.name for let in refused] == ["x", "z"]


def _engine(definitions: dict[str, frog_ast.Root]) -> proof_engine.ProofEngine:
    engine = proof_engine.ProofEngine(verbose=False, parallel=False)
    for name, root in definitions.items():
        engine.add_definition(name, root)
    return engine


def test_prove_without_type_check_refuses_let_value_making_nondeterministic_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``c = R.Draw()`` is no call of a ``let:`` function, so set-up stores it;
    ``prove`` still refuses it before any hop is checked."""
    proof, definitions = _proof_and_definitions(
        tmp_path, "BitString<8> c = R.Draw() + 0^8;"
    )
    engine = _engine(definitions)
    with pytest.raises(proof_engine.FailedProof):
        engine.prove(proof)
    output = capsys.readouterr().out
    assert "let: entry 'c' = R.Draw() + 0^8 makes a non-deterministic call" in output
    assert "Proof Failed! (let: entry 'c' is not supported)" in output


def test_prove_without_type_check_accepts_deterministic_let_value(
    tmp_path: Path,
) -> None:
    proof, definitions = _proof_and_definitions(
        tmp_path, "BitString<8> c = H(R.Fixed()) + 0^8;"
    )
    _engine(definitions).prove(proof)
