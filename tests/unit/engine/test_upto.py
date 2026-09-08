"""Unit tests for the structural checks behind up-to-bad hops (proof_frog.upto)."""

from proof_frog import frog_ast, frog_parser, upto

PAIR = """
Game Left(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Eq(S c) {{
        if (c == target) {{
            bad = true;
            return true;
        }}
        return false;
    }}
}}

Game Right(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Eq(S c) {{
        if (c == target) {{
            bad = true;
        }}
        return {right_tail};
    }}
}}

export as Pair;
"""

FLAG = """
Game Real(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Eq(S c) {{
        if (c == target) {{
            bad = true;
        }}
        return false;
    }}

    Bool Reveal() {{
        return {real_reveal};
    }}
}}

Game Ideal(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Eq(S c) {{
        if (c == target) {{
            bad = true;
        }}
        return false;
    }}

    Bool Reveal() {{
        return {ideal_reveal};
    }}
}}

export as Flag;
"""


def _game_file(src: str) -> frog_ast.GameFile:
    ast = frog_parser.parse_string(src, frog_ast.FileType.GAME)
    assert isinstance(ast, frog_ast.GameFile)
    return ast


def _pair(right_tail: str = "false") -> frog_ast.GameFile:
    return _game_file(PAIR.format(right_tail=right_tail))


def _flag(real_reveal: str = "bad", ideal_reveal: str = "false") -> frog_ast.GameFile:
    return _game_file(FLAG.format(real_reveal=real_reveal, ideal_reveal=ideal_reveal))


class TestIdenticalUntilBad:
    def test_accepts_pair_differing_only_after_bad(self) -> None:
        assert upto.identical_until_bad(_pair()) is None

    def test_rejects_difference_outside_flagged_block(self) -> None:
        reason = upto.identical_until_bad(_pair(right_tail="true"))
        assert reason is not None
        assert "Eq" in reason

    def test_rejects_missing_marker_on_one_side(self) -> None:
        src = PAIR.format(right_tail="false").replace(
            "        if (c == target) {\n            bad = true;\n            return true;",
            "        if (c == target) {\n            return true;",
        )
        assert upto.identical_until_bad(_game_file(src)) is not None

    def test_rejects_bad_read_outside_reveal(self) -> None:
        src = PAIR.format(right_tail="bad")
        assert upto.identical_until_bad(_game_file(src)) is not None

    def test_rejects_missing_bad_field(self) -> None:
        src = PAIR.format(right_tail="false").replace("    Bool bad;\n", "")
        src = src.replace("        bad = false;\n", "")
        assert upto.identical_until_bad(_game_file(src)) is not None


class TestFlagGameOf:
    def test_accepts_derived_flag_game(self) -> None:
        assert upto.flag_game_mismatch(_pair(), _flag()) is None

    def test_rejects_ideal_that_reveals(self) -> None:
        assert upto.flag_game_mismatch(_pair(), _flag(ideal_reveal="bad")) is not None

    def test_rejects_real_that_hides(self) -> None:
        assert upto.flag_game_mismatch(_pair(), _flag(real_reveal="false")) is not None

    def test_rejects_body_drift(self) -> None:
        assert upto.flag_game_mismatch(_pair(right_tail="true"), _flag()) is not None
