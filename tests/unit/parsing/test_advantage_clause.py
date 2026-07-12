"""Parsing and semantic checks for the game-file `advantage <= ...` clause."""

import pytest

from proof_frog import frog_ast, frog_parser, semantic_analysis

_GAMES = """
Game Replacement(Set S) {
    S Samp() { S val <- S; return val; }
}
Game NoReplacement(Set S) {
    Set<S> seen;
    S Samp() { S val <-uniq[seen] S; return val; }
}
"""


def _game_file(tail: str) -> frog_ast.GameFile:
    return frog_parser.parse_game_file(_GAMES + tail)


class TestParsing:
    def test_clause_parses_into_ast(self) -> None:
        gf = _game_file(
            "advantage <= count_Samp * (count_Samp - 1) / (2 * |S|);\nexport as D;"
        )
        assert gf.advantage is not None
        assert str(gf.advantage.bound) == "count_Samp * (count_Samp - 1) / (2 * |S|)"

    def test_absent_clause_is_none(self) -> None:
        gf = _game_file("export as D;")
        assert gf.advantage is None

    def test_zero_bound(self) -> None:
        gf = _game_file("advantage <= 0;\nexport as D;")
        assert gf.advantage is not None
        assert str(gf.advantage.bound) == "0"

    def test_roundtrips_through_str(self) -> None:
        gf = _game_file("advantage <= count_Samp / |S|;\nexport as D;")
        reparsed = frog_parser.parse_game_file(str(gf))
        assert reparsed.advantage is not None
        assert str(reparsed.advantage.bound) == "count_Samp / |S|"


class TestSemantics:
    def _check(self, tail: str) -> None:
        semantic_analysis.check_well_formed(_game_file(tail), "<test>")

    def test_valid_clause_accepted(self) -> None:
        self._check("advantage <= count_Samp * (count_Samp - 1) / (2 * |S|);\nexport as D;")

    def test_unknown_oracle_count_rejected(self) -> None:
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            self._check("advantage <= count_Nope / |S|;\nexport as D;")

    def test_unknown_free_variable_rejected(self) -> None:
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            self._check("advantage <= count_Samp / |T|;\nexport as D;")

    def test_non_numeric_operator_rejected(self) -> None:
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            self._check("advantage <= count_Samp union count_Samp;\nexport as D;")

    def test_bound_decreasing_in_count_rejected(self) -> None:
        # A bound that shrinks as queries grow would make the count
        # over-approximation / calls pin unsound.
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            self._check("advantage <= 1 / (count_Samp + 1);\nexport as D;")
