"""LocalizeInitOnlyField, single-block case: a field written at the top of one
block of one oracle and read only later in that block becomes a local."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _localize_single_block_field_assignments

BASE = """
Game G(TDP F, Int n, Function<BitString<n>, BitString<n>> H) {
    PK pk;
    BitString<n> sStar;
    Int count;
    PK Initialize() {
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        sStar = 0^n;
        count = 0;
        return pk;
    }
    BitString<n>? Challenge(BitString<n> m) {
        BitString<n>? result = None;
        count = count + 1;
        if (count == 1) {
            sStar = m + H(m);
            result = F.evaluate(pk, sStar || H(sStar));
        }
        return result;
    }
}
"""

EXPECTED = """
Game G(TDP F, Int n, Function<BitString<n>, BitString<n>> H) {
    PK pk;
    Int count;
    PK Initialize() {
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        count = 0;
        return pk;
    }
    BitString<n>? Challenge(BitString<n> m) {
        BitString<n>? result = None;
        count = count + 1;
        if (count == 1) {
            BitString<n> sStar = m + H(m);
            result = F.evaluate(pk, sStar || H(sStar));
        }
        return result;
    }
}
"""


def _apply(src: str) -> str:
    return str(_localize_single_block_field_assignments(frog_parser.parse_game(src)))


def test_localizes_block_scoped_field() -> None:
    assert _apply(BASE) == str(frog_parser.parse_game(EXPECTED))


@pytest.mark.parametrize(
    "old,new",
    [
        # read in another oracle: the value crosses invocations
        (
            "        return result;\n    }\n}",
            "        return result;\n    }\n    BitString<n> Peek() {\n        return sStar;\n    }\n}",
        ),
        # read before the write in the same block
        (
            "            sStar = m + H(m);",
            "            BitString<n> old = sStar;\n            sStar = m + H(m);",
        ),
        # read outside the block that writes it
        (
            "        return result;\n    }\n}",
            "        return result + sStar;\n    }\n}",
        ),
    ],
)
def test_declines(old: str, new: str) -> None:
    assert old in BASE
    src = BASE.replace(old, new)
    assert _apply(src) == str(frog_parser.parse_game(src))
