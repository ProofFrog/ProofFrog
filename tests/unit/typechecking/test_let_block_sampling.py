"""Tests that let-block sampling in proof files is validated correctly.

Function types can be sampled in let blocks (e.g.
``Function<BitString<8>, BitString<16>> H <- Function<...>;``), but
non-Function types (e.g. ``BitString<8> x <- BitString<8>;``) must be
rejected by the type checker.
"""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

# A minimal primitive and game so the proof file can reference them.
_PRIMITIVE = """\
Primitive P(Int n) {
    BitString<n> f(BitString<n> x);
}
"""

_GAME = """\
import 'P.primitive';

Game Side1(P F, Int n) {
    Bool Initialize() {
        return true;
    }
}

Game Side2(P F, Int n) {
    Bool Initialize() {
        return true;
    }
}

export as G;
"""

_SCHEME = """\
import 'P.primitive';

Scheme S(Int n) extends P {
    BitString<n> f(BitString<n> x) {
        return x;
    }
}
"""


def _write_fixtures(tmp_path: Path) -> None:
    """Write supporting files that the proof imports."""
    (tmp_path / "P.primitive").write_text(_PRIMITIVE)
    (tmp_path / "G.game").write_text(_GAME)
    (tmp_path / "S.scheme").write_text(_SCHEME)


def _make_proof(let_line: str) -> str:
    """Build a minimal proof file with the given let-block entry."""
    return (
        "import 'P.primitive';\n"
        "import 'G.game';\n"
        "import 'S.scheme';\n"
        "\n"
        "proof:\n"
        "let:\n"
        f"  {let_line}\n"
        "  Int n;\n"
        "  S S1 = S(n);\n"
        "assume:\n"
        "theorem:\n"
        "  G(S1, n);\n"
        "games:\n"
        "  G(S1, n).Side1 against G(S1, n).Adversary;\n"
        "  G(S1, n).Side2 against G(S1, n).Adversary;\n"
    )


def test_function_sample_in_let_accepted(tmp_path: Path) -> None:
    """A Function type sampled in the let block should parse and type-check."""
    _write_fixtures(tmp_path)
    content = _make_proof(
        "Function<BitString<8>, BitString<16>> H "
        "<- Function<BitString<8>, BitString<16>>;"
    )
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    # Should not raise
    semantic_analysis.check_well_formed(root, str(proof_path))


def test_non_function_sample_in_let_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-Function type sampled in the let block should be rejected."""
    _write_fixtures(tmp_path)
    content = _make_proof("BitString<8> x <- BitString<8>;")
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, str(proof_path))
    assert "only function types can be sampled" in capsys.readouterr().err.lower()
