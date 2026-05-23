"""Tests for ``proof_frog.transforms._requirements.is_known_nonzero``."""

from proof_frog import frog_parser
from proof_frog.transforms._requirements import is_known_nonzero


def _parse_game(body: str) -> object:
    return frog_parser.parse_game(body)


_UNIQ_GAME = """
Game G(Int q) {
    Int sk = 0;
    Int Initialize() {
        ModInt<q> sk <-uniq[{0}] ModInt<q>;
        return sk;
    }
}
"""

_PLAIN_SAMPLE_GAME = """
Game G(Int q) {
    Int sk = 0;
    Int Initialize() {
        ModInt<q> sk <- ModInt<q>;
        return sk;
    }
}
"""

_UNIQ_EXCLUDES_OTHER_GAME = """
Game G(Int q) {
    Int sk = 0;
    Int x = 0;
    Int Initialize() {
        ModInt<q> x <- ModInt<q>;
        ModInt<q> sk <-uniq[{x}] ModInt<q>;
        return sk;
    }
}
"""


def test_known_nonzero_uniq_sample_with_zero() -> None:
    game = _parse_game(_UNIQ_GAME)
    assert is_known_nonzero("sk", game) is True


def test_known_nonzero_plain_sample() -> None:
    game = _parse_game(_PLAIN_SAMPLE_GAME)
    assert is_known_nonzero("sk", game) is False


def test_known_nonzero_uniq_sample_without_zero() -> None:
    game = _parse_game(_UNIQ_EXCLUDES_OTHER_GAME)
    assert is_known_nonzero("sk", game) is False


def test_known_nonzero_missing_var() -> None:
    game = _parse_game(_UNIQ_GAME)
    assert is_known_nonzero("not_there", game) is False
