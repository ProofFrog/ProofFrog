"""Tests for LocalizeInitOnlyField (proof_frog.transforms.sampling)."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _localize_init_only_field_assignments

BASE = """
Game Test(TDP F) {
    PK pk;
    BitString<n> y;
    Int count;
    PK Initialize() {
        count = 0;
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        BitString<n> s <- BitString<n>;
        y = F.evaluate(pk, s);
        return pk;
    }
    BitString<n>? Challenge(BitString<n> msg) {
        count = count + 1;
        BitString<n>? result = None;
        if (count == 1) {
            result = y;
        }
        return result;
    }
}
"""

EXPECTED = """
Game Test(TDP F) {
    BitString<n> y;
    Int count;
    PK Initialize() {
        count = 0;
        [PK, SK] kp = F.KeyGen();
        PK pk = kp[0];
        BitString<n> s <- BitString<n>;
        y = F.evaluate(pk, s);
        return pk;
    }
    BitString<n>? Challenge(BitString<n> msg) {
        count = count + 1;
        BitString<n>? result = None;
        if (count == 1) {
            result = y;
        }
        return result;
    }
}
"""


def _apply(src: str) -> str:
    return str(_localize_init_only_field_assignments(frog_parser.parse_game(src)))


def test_localizes_init_only_computed_field() -> None:
    assert _apply(BASE) == str(frog_parser.parse_game(EXPECTED))


@pytest.mark.parametrize(
    "old,new",
    [
        # used by an oracle
        ("            result = y;", "            result = F.evaluate(pk, y);"),
        # written twice in Initialize
        ("        return pk;", "        pk = kp[0];\n        return pk;"),
        # read before it is assigned
        (
            "        [PK, SK] kp = F.KeyGen();",
            "        PK q = pk;\n        [PK, SK] kp = F.KeyGen();",
        ),
    ],
)
def test_declines(old: str, new: str) -> None:
    assert old in BASE
    src = BASE.replace(old, new)
    assert _apply(src) == str(frog_parser.parse_game(src))
