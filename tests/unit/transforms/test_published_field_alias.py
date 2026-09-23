"""Tests for PublishedFieldAlias (proof_frog.transforms.control_flow)."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import PublishedFieldAliasTransformer

BASE = """
Game G(Int n, Function<BitString<n>, BitString<n>> H) {
    BitString<n> sHid;
    BitString<n> sStar;
    Bool challenged;
    Bool askH;
    Int count;
    Void Initialize() {
        sHid <- BitString<n>;
        sStar = 0^n;
        challenged = false;
        askH = false;
        count = 0;
    }
    BitString<n>? Challenge() {
        BitString<n>? result = None;
        count = count + 1;
        if (count == 1) {
            sStar = sHid;
            challenged = true;
            result = H(sHid);
        }
        return result;
    }
    BitString<n> HashH(BitString<n> x) {
        if (challenged && x == sStar) {
            askH = true;
        }
        return H(x);
    }
}
"""


def _apply(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(PublishedFieldAliasTransformer(game).transform(game))


def test_guarded_read_uses_the_stable_source() -> None:
    expected = BASE.replace(
        "if (challenged && x == sStar) {", "if (challenged && x == sHid) {"
    )
    assert _apply(BASE) == str(frog_parser.parse_game(expected))


@pytest.mark.parametrize(
    "old,new",
    [
        # unguarded read
        ("if (challenged && x == sStar) {", "if (x == sStar) {"),
        # flag raised a second time elsewhere
        (
            "        return H(x);\n    }\n}",
            "        challenged = true;\n        return H(x);\n    }\n}",
        ),
        # source rewritten after Initialize
        (
            "            sStar = sHid;",
            "            sHid = x0;\n            sStar = sHid;",
        ),
        # publication after the flag
        (
            "            sStar = sHid;\n            challenged = true;",
            "            challenged = true;\n            sStar = sHid;",
        ),
    ],
)
def test_declines(old: str, new: str) -> None:
    assert old in BASE, old
    src = BASE.replace(old, new).replace(
        "Challenge() {", "Challenge(BitString<n> x0) {"
    )
    assert _apply(src) == str(frog_parser.parse_game(src))
