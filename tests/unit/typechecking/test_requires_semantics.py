"""Semantic validation of the proof-level ``requires:`` block."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis


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
    (tmp_path / "P.primitive").write_text(_PRIMITIVE)
    (tmp_path / "G.game").write_text(_GAME)
    (tmp_path / "S.scheme").write_text(_SCHEME)


def _make_proof(requires_block: str) -> str:
    return (
        "import 'P.primitive';\n"
        "import 'G.game';\n"
        "import 'S.scheme';\n"
        "\n"
        "proof:\n"
        "let:\n"
        "  Group H;\n"
        "  Int n;\n"
        "  S S1 = S(n);\n"
        "assume:\n"
        f"{requires_block}"
        "theorem:\n"
        "  G(S1, n);\n"
        "games:\n"
        "  G(S1, n).Side1 against G(S1, n).Adversary;\n"
        "  G(S1, n).Side2 against G(S1, n).Adversary;\n"
    )


def test_requires_prime_on_group_order_accepted(tmp_path: Path) -> None:
    _write_fixtures(tmp_path)
    content = _make_proof("requires:\n  H.order is prime;\n")
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    # Should not raise.
    semantic_analysis.check_well_formed(root, str(proof_path))


def test_requires_prime_on_int_let_accepted(tmp_path: Path) -> None:
    _write_fixtures(tmp_path)
    content = _make_proof("requires:\n  n is prime;\n")
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    semantic_analysis.check_well_formed(root, str(proof_path))


def test_requires_prime_on_bitstring_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Attempt to declare a BitString target prime, which isn't integer-typed.
    # Use a let-bound BitString<n> to exercise the rejection path.
    _write_fixtures(tmp_path)
    content = (
        "import 'P.primitive';\n"
        "import 'G.game';\n"
        "import 'S.scheme';\n"
        "\n"
        "proof:\n"
        "let:\n"
        "  Int n;\n"
        "  S S1 = S(n);\n"
        "  BitString<n> b = 0^n;\n"
        "assume:\n"
        "requires:\n"
        "  b is prime;\n"
        "theorem:\n"
        "  G(S1, n);\n"
        "games:\n"
        "  G(S1, n).Side1 against G(S1, n).Adversary;\n"
        "  G(S1, n).Side2 against G(S1, n).Adversary;\n"
    )
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, str(proof_path))
    err = capsys.readouterr().err.lower()
    assert "prime" in err
