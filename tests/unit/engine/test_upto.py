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


SPLIT_PAIR = """
Game Left(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    S Dec(S a, S b) {{
        if (a == target) {{
            return b;
        }}
        bad = true;
        return {left_tail};
    }}
}}

Game Right(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    S Dec(S a, S b) {{
        if (a == target) {{
            return b;
        }}
        bad = true;
        return b;
    }}
}}

export as Split;
"""


class TestTopLevelBadSplit:
    def test_accepts_divergence_after_top_level_bad(self) -> None:
        assert (
            upto.identical_until_bad(_game_file(SPLIT_PAIR.format(left_tail="a")))
            is None
        )

    def test_rejects_divergence_before_top_level_bad(self) -> None:
        src = SPLIT_PAIR.format(left_tail="a").replace(
            "        if (a == target) {\n            return b;\n        }\n        bad = true;\n        return a;",
            "        if (a == target) {\n            return a;\n        }\n        bad = true;\n        return a;",
        )
        assert upto.identical_until_bad(_game_file(src)) is not None


MISMATCH_PAIR = """
Game Left(Set S) {{
    Bool bad;

    Void Initialize() {{
        bad = false;
    }}

    S Dec(S a, S b) {{
        if ({guard}) {{
            bad = true;{extra}
        }}
        return {left_ret};
    }}
}}

Game Right(Set S) {{
    Bool bad;

    Void Initialize() {{
        bad = false;
    }}

    S Dec(S a, S b) {{
        if ({guard}) {{
            bad = true;{extra}
        }}
        return b;
    }}
}}

export as Mismatch;
"""


class TestFlagOnMismatchThenReturn:
    def test_accepts_return_of_either_compared_operand(self) -> None:
        src = MISMATCH_PAIR.format(guard="a != b", extra="", left_ret="a")
        assert upto.identical_until_bad(_game_file(src)) is None

    def test_accepts_negated_equality_guard(self) -> None:
        src = MISMATCH_PAIR.format(guard="!(a == b)", extra="", left_ret="a")
        assert upto.identical_until_bad(_game_file(src)) is None

    def test_rejects_return_of_an_uncompared_value(self) -> None:
        src = MISMATCH_PAIR.format(guard="a != b", extra="", left_ret="b + a")
        assert upto.identical_until_bad(_game_file(src)) is not None

    def test_rejects_extra_work_inside_the_guard(self) -> None:
        src = MISMATCH_PAIR.format(
            guard="a != b", extra="\n            b = a;", left_ret="a"
        )
        assert upto.identical_until_bad(_game_file(src)) is not None

    def test_rejects_unrelated_guard(self) -> None:
        src = MISMATCH_PAIR.format(guard="a == b", extra="", left_ret="a")
        assert upto.identical_until_bad(_game_file(src)) is not None


GUARDED_PAIR = """
Game Left(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Mark(S c) {{
        if (c == target) {{
            bad = true;
        }}
        return false;
    }}

    S Dec(S a, S b) {{
        if (bad) {{
            return a;
        }}
        return b;
    }}
}}

Game Right(Set S) {{
    S target;
    Bool bad;

    Void Initialize() {{
        target <- S;
        bad = false;
    }}

    Bool Mark(S c) {{
        if (c == target) {{
            bad = true;
        }}
        return false;
    }}

    S Dec(S a, S b) {{{right_guard}
        return b;
    }}
}}

export as Guarded;
"""


class TestPostBadGuards:
    def test_if_bad_block_may_exist_on_one_side_only(self) -> None:
        src = GUARDED_PAIR.format(right_guard="")
        assert upto.identical_until_bad(_game_file(src)) is None

    def test_if_bad_blocks_may_differ(self) -> None:
        src = GUARDED_PAIR.format(
            right_guard="\n        if (bad) {\n            return b;\n        }"
        )
        assert upto.identical_until_bad(_game_file(src)) is None

    def test_bad_read_outside_a_guard_is_rejected(self) -> None:
        src = GUARDED_PAIR.format(
            right_guard="\n        if (bad && a == b) {\n            return a;\n        }"
        )
        assert upto.identical_until_bad(_game_file(src)) is not None

    def test_if_bad_with_else_is_not_a_post_bad_guard(self) -> None:
        """The ``else`` of ``if (bad)`` runs exactly when the flag is down, so
        the guard must not be skipped: differing else-bodies distinguish the
        games on runs that never raise the flag."""
        src = GUARDED_PAIR.format(
            right_guard=(
                "\n        if (bad) {\n            return b;\n        }"
                " else {\n            return a;\n        }"
            )
        )
        assert upto.identical_until_bad(_game_file(src)) is not None


def test_flag_game_reveal_oracle_may_have_any_name() -> None:
    flag = _flag()
    for game in flag.games:
        for method in game.methods:
            if method.signature.name == "Reveal":
                method.signature.name = "RevealBad"
    assert upto.flag_game_mismatch(_pair(), flag) is None
