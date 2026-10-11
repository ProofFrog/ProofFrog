"""End-to-end checks that FreshInputRFToUniform keeps ``H(v)`` for
``v <-uniq[seen]`` when a method changes a value it inserted into ``seen``
before querying ``H`` on it.

``seen`` then misses a point ``H`` was queried on, and ``v`` may draw it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine

_PRIMITIVE = """
Primitive P() {
    BitString<2> G();
}
"""

_PROOF = """
import 'P.primitive';
import 'Pair.game';

proof:

let:
    P S;

assume:

theorem:
    Pair(S);

games:
    Pair(S).Left against Pair(S).Adversary;
    Pair(S).Right against Pair(S).Adversary;
"""


def _side(name: str, fresh: str) -> str:
    return f"""
Game {name}(P S) {{
    Function<BitString<2>, BitString<2>> H;
    Set<BitString<2>> seen;
    Void Initialize() {{
        H <- Function<BitString<2>, BitString<2>>;
    }}
    BitString<2> Hash(BitString<2> x) {{
        seen = seen union {{x}};
        x = 0b00;
        return H(x);
    }}
    BitString<2> Fresh() {{
        {fresh}
    }}
}}
"""


def test_rewritten_insertion_pair_fails(tmp_path: Path) -> None:
    """After Hash(0b01), Fresh may draw 0b00 and return Hash's answer."""
    (tmp_path / "P.primitive").write_text(_PRIMITIVE, encoding="utf-8")
    (tmp_path / "Pair.game").write_text(
        "import 'P.primitive';\n"
        + _side("Left", "BitString<2> v <-uniq[seen] BitString<2>; return H(v);")
        + _side("Right", "BitString<2> z <- BitString<2>; return z;")
        + "\nexport as Pair;\n",
        encoding="utf-8",
    )
    (tmp_path / "pair.proof").write_text(_PROOF, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(tmp_path / "pair.proof")],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "Proof Failed!" in output


def _game(initialize: str, fresh: str) -> str:
    # Only Initialize and Fresh query H, so a later query never meets v.
    return f"""
        Game G() {{
            Function<BitString<2>, BitString<2>> H;
            Set<BitString<2>> seen;
            BitString<2> y;
            Void Initialize() {{
                H <- Function<BitString<2>, BitString<2>>;
                {initialize}
            }}
            BitString<2> Reveal() {{
                return y;
            }}
            BitString<2> Fresh() {{
                {fresh}
            }}
        }}
        """


def _equal(initialize: str) -> bool:
    real = _game(initialize, "BitString<2> v <-uniq[seen] BitString<2>; return H(v);")
    ideal = _game(initialize, "BitString<2> z <- BitString<2>; return z;")
    return (
        ProofEngine()
        .check_equivalent(frog_parser.parse_game(real), frog_parser.parse_game(ideal))
        .valid
    )


@pytest.mark.parametrize(
    "initialize",
    [
        "BitString<2> u = 0b00; seen = seen union {u}; u = 0b11; y = H(u);",
        "BitString<2> u = 0b00; seen = seen union {u}; "
        "if (u == 0b00) { u = 0b11; } y = H(u);",
    ],
)
def test_rewritten_insertion_in_initialize_rejected(initialize: str) -> None:
    """Initialize records 0b00 and queries 0b11, so Fresh may return y."""
    assert not _equal(initialize)


def test_recorded_value_accepted() -> None:
    assert _equal("BitString<2> u = 0b00; seen = seen union {u}; y = H(u);")
