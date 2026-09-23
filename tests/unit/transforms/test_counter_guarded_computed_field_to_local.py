"""Tests for CounterGuardedComputedFieldToLocal (proof_frog.transforms.sampling)."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _counter_guarded_computed_field_to_local

POSITIVE = """
Game Test(TDP F, Function<BitString<m>, BitString<k>> H) {
    BitString<n> y;
    BitString<k> r;
    Int count;
    PK pk;
    PK Initialize() {
        r <- BitString<k>;
        count = 0;
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        BitString<m> s <- BitString<m>;
        y = F.evaluate(pk, s || r + H(s));
        return pk;
    }
    BitString<n>? Challenge(BitString<m> msg) {
        count = count + 1;
        BitString<n>? result = None;
        if (count == 1) {
            result = y;
        }
        return result;
    }
    BitString<k> HashH(BitString<m> x) {
        return H(x);
    }
}
"""

POSITIVE_EXPECTED = """
Game Test(TDP F, Function<BitString<m>, BitString<k>> H) {
    Int count;
    PK pk;
    PK Initialize() {
        count = 0;
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        return pk;
    }
    BitString<n>? Challenge(BitString<m> msg) {
        count = count + 1;
        BitString<n>? result = None;
        if (count == 1) {
            BitString<k> r <- BitString<k>;
            BitString<m> s <- BitString<m>;
            BitString<n> y = F.evaluate(pk, s || r + H(s));
            result = y;
        }
        return result;
    }
    BitString<k> HashH(BitString<m> x) {
        return H(x);
    }
}
"""


def _apply(src: str) -> str:
    return str(_counter_guarded_computed_field_to_local(frog_parser.parse_game(src)))


def test_sinks_computed_field_with_its_private_inputs() -> None:
    assert _apply(POSITIVE) == str(frog_parser.parse_game(POSITIVE_EXPECTED))


@pytest.mark.parametrize(
    "mutation",
    [
        # (a) the field is read in a second oracle
        (
            "    BitString<k> HashH(BitString<m> x) {\n        return H(x);\n    }",
            "    BitString<k> HashH(BitString<m> x) {\n        return H(x) + y[0 : k];\n    }",
        ),
        # (c) a referenced field is written by another oracle
        (
            "    BitString<k> HashH(BitString<m> x) {\n        return H(x);\n    }",
            "    BitString<k> HashH(BitString<m> x) {\n        r = x[0 : k];\n        return H(x);\n    }",
        ),
        # (d) the field is read in two different guarded branches
        (
            "        if (count == 1) {\n            result = y;\n        }",
            "        if (count == 1) {\n            result = y;\n        }\n        if (count == 2) {\n            result = y;\n        }",
        ),
        # (e) the read is not counter-guarded at all
        (
            "        if (count == 1) {\n            result = y;\n        }",
            "        result = y;",
        ),
    ],
)
def test_declines_unsound_shapes(mutation: tuple[str, str]) -> None:
    old, new = mutation
    assert old in POSITIVE, "mutation anchor missing"
    src = POSITIVE.replace(old, new)
    assert _apply(src) == str(frog_parser.parse_game(src))


def test_declines_when_initialize_parameter_is_read() -> None:
    src = POSITIVE.replace(
        "PK Initialize() {", "PK Initialize(BitString<k> delta) {"
    ).replace(
        "y = F.evaluate(pk, s || r + H(s));", "y = F.evaluate(pk, s || delta + H(s));"
    )
    assert _apply(src) == str(frog_parser.parse_game(src))


PROMOTE = """
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

PROMOTE_EXPECTED = """
Game Test(TDP F) {
    Int count;
    PK pk;
    PK Initialize() {
        count = 0;
        [PK, SK] kp = F.KeyGen();
        pk = kp[0];
        return pk;
    }
    BitString<n>? Challenge(BitString<n> msg) {
        count = count + 1;
        BitString<n>? result = None;
        if (count == 1) {
            BitString<n> s <- BitString<n>;
            BitString<n> y = F.evaluate(pk, s);
            result = y;
        }
        return result;
    }
}
"""


def test_promotes_shared_init_local_to_field() -> None:
    assert _apply(PROMOTE) == str(frog_parser.parse_game(PROMOTE_EXPECTED))


def test_declines_without_a_moving_sample() -> None:
    """A deterministic function of stable fields stays in Initialize (hoist
    form): here `r` is also read by HashH, so it cannot travel into the
    branch, and no other sample moves."""
    src = (
        POSITIVE.replace("        BitString<m> s <- BitString<m>;\n", "")
        .replace(
            "y = F.evaluate(pk, s || r + H(s));", "y = F.evaluate(pk, r || r + H(r));"
        )
        .replace("        return H(x);", "        return H(x) + r;")
    )
    assert _apply(src) == str(frog_parser.parse_game(src))
