"""Unit tests for proof_frog/upto.py: flag discipline, flag-game construction
and the identical-until-bad lockstep check."""

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, upto

PAIR_TEMPLATE = """
Game Left(Set S) {{
{left}
}}

Game Right(Set S) {{
{right}
}}

export as P;
"""


def pair(
    tmp_path: Path, left: str, right: str, name: str = "P.game"
) -> frog_ast.GameFile:
    path = tmp_path / name
    path.write_text(PAIR_TEMPLATE.format(left=left, right=right))
    return frog_parser.parse_game_file(str(path))


BAD_GUESS_LEFT = """
    S target;
    Bool bad;
    Void Initialize() { target <- S; bad = false; }
    Bool Eq(S c) { if (c == target) { bad = true; return true; } return false; }
"""
BAD_GUESS_RIGHT = """
    S target;
    Bool bad;
    Void Initialize() { target <- S; bad = false; }
    Bool Eq(S c) { if (c == target) { bad = true; } return false; }
"""


# ---------------------------------------------------------------------------
# Flag field and discipline
# ---------------------------------------------------------------------------


def test_flag_field_present(tmp_path: Path) -> None:
    p = pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    assert upto.check_flag_field(p.games[0], "bad") is None
    assert upto.check_flag_field(p.games[0], "nope") is not None


def test_flag_field_must_be_bool(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("Bool bad;", "Int bad;").replace(
        "bad = false;", "bad = 0;"
    )
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    assert upto.check_flag_field(p.games[0], "bad") is not None


def test_flag_discipline_accepts_bad_guess(tmp_path: Path) -> None:
    p = pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    assert upto.check_flag_discipline(p.games[0], "bad") is None
    assert upto.check_flag_discipline(p.games[1], "bad") is None


def test_flag_discipline_allows_reads(tmp_path: Path) -> None:
    body = """
    Bool bad;
    Void Initialize() { bad = false; }
    Bool Peek() { if (bad) { return true; } return bad; }
    """
    p = pair(tmp_path, body, body)
    assert upto.check_flag_discipline(p.games[0], "bad") is None


def test_flag_discipline_rejects_sampling(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("bad = false;", "bad <- Bool;")
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    err = upto.check_flag_discipline(p.games[0], "bad")
    assert err is not None and "Initialize" in err.message


def test_flag_discipline_rejects_shadowing(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("Bool Eq(S c)", "Bool Eq(S c, Bool bad)")
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_rejects_local_shadowing(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("return false; }", "Bool bad = true; return bad; }")
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_rejects_reset_outside_initialize(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("return false; }", "bad = false; return false; }")
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_rejects_reset_after_raise(tmp_path: Path) -> None:
    # A reset after a raise in Initialize would un-raise the flag while the
    # two sides' states already differ.
    body = """
    S x; S y; Bool bad;
    Void Initialize() { x <- S; y <- S; if (x == y) { bad = true; } bad = false; }
    """
    p = pair(tmp_path, body, body)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_rejects_conditional_reset(tmp_path: Path) -> None:
    body = """
    S x; Bool bad;
    Void Initialize() { x <- S; if (x == x) { bad = false; } }
    """
    p = pair(tmp_path, body, body)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_rejects_missing_reset(tmp_path: Path) -> None:
    body = """
    S x; Bool bad;
    Void Initialize() { x <- S; }
    Bool O() { bad = true; return bad; }
    """
    p = pair(tmp_path, body, body)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_flag_discipline_accepts_field_initializer(tmp_path: Path) -> None:
    body = """
    S x; Bool bad = false;
    Void Initialize() { x <- S; }
    Bool O(S c) { if (c == x) { bad = true; } return bad; }
    """
    p = pair(tmp_path, body, body)
    assert upto.check_flag_discipline(p.games[0], "bad") is None


def test_flag_discipline_rejects_other_value(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("bad = true; return true;", "bad = c == c;")
    p = pair(tmp_path, left, BAD_GUESS_RIGHT)
    assert upto.check_flag_discipline(p.games[0], "bad") is not None


def test_raised_only_in_initialize(tmp_path: Path) -> None:
    p = pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    assert not upto.raised_only_in_initialize(p.games[1], "bad")
    init_only = """
    S x; S y; Bool bad;
    Void Initialize() { x <- S; y <- S; bad = false; if (x == y) { bad = true; } }
    Bool Collided() { return bad; }
    """
    q = pair(
        tmp_path,
        init_only,
        init_only.replace("return bad;", "return false;"),
        name="Q.game",
    )
    assert upto.raised_only_in_initialize(q.games[0], "bad")


# ---------------------------------------------------------------------------
# Flag games
# ---------------------------------------------------------------------------


def test_flag_game_appends_reveal(tmp_path: Path) -> None:
    p = pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    fg = upto.flag_game(p, "Right", "bad", "P#event#bad")
    assert fg.name == "P#event#bad"
    assert [g.name for g in fg.games] == ["Real", "Ideal"]
    real_reveal = fg.games[0].get_method(upto.REVEAL)
    ideal_reveal = fg.games[1].get_method(upto.REVEAL)
    assert str(real_reveal.block.statements[0]) == "return bad;"
    assert str(ideal_reveal.block.statements[0]) == "return false;"
    assert [m.signature.name for m in fg.games[0].methods][:-1] == [
        m.signature.name for m in p.games[1].methods
    ]
    # The source pair is untouched.
    assert not p.games[1].has_method(upto.REVEAL)


def test_strip_keeps_only_initialize(tmp_path: Path) -> None:
    body = """
    S x; S y; Bool bad;
    [S, S] Initialize() { x <- S; y <- S; bad = false; if (x == y) { bad = true; } return [x, y]; }
    Bool Collided() { return bad; }
    """
    p = pair(tmp_path, body, body.replace("return bad;", "return false;"))
    sg = upto.strip(p, "Right", "bad", "P#event#bad#init")
    names = [m.signature.name for m in sg.games[0].methods]
    assert names == ["Initialize", upto.REVEAL]
    init = sg.games[0].get_method("Initialize")
    assert isinstance(init.signature.return_type, frog_ast.Void)
    assert "return" not in str(init)
    assert "if (x == y)" in str(init)


def test_strip_rejects_early_return(tmp_path: Path) -> None:
    body = """
    S x; Bool bad;
    S Initialize() { x <- S; bad = false; if (x == x) { return x; } return x; }
    """
    p = pair(tmp_path, body, body)
    with pytest.raises(ValueError, match="early return"):
        upto.strip(p, "Right", "bad", "P#event#bad#init")


def test_with_reveal_appends_oracle(tmp_path: Path) -> None:
    src = _placement_proof(tmp_path, "challenger.Eq(c)")
    red = _reduction(src)
    wrapped = upto.with_reveal(red, frog_ast.Boolean(False))
    assert wrapped.has_method(upto.REVEAL)
    assert not red.has_method(upto.REVEAL)
    assert isinstance(wrapped, frog_ast.Reduction)


# ---------------------------------------------------------------------------
# challenger.Initialize placement
# ---------------------------------------------------------------------------


def _placement_proof(tmp_path: Path, eq_body: str, init_body: str = "") -> Path:
    src = tmp_path / "r.proof"
    src.write_text(f"""
import 'P.game';
proof:
let:
    Set S;
assume:
    P(S);
theorem:
    P(S);
games:
    P(S).Left against P(S).Adversary;
    P(S).Right against P(S).Adversary;

Reduction R(Set S) compose P(S) against P(S).Adversary {{
    Void Initialize() {{ challenger.Initialize(); {init_body} }}
    Bool Eq(S c) {{ return {eq_body}; }}
}}
""")
    pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    return src


def _reduction(src: Path) -> frog_ast.Reduction:
    pf = frog_parser.parse_proof_file(str(src))
    return next(h for h in pf.helpers if isinstance(h, frog_ast.Reduction))


def test_placement_rule_accepts_initialize_only(tmp_path: Path) -> None:
    red = _reduction(_placement_proof(tmp_path, "challenger.Eq(c)"))
    assert upto.check_challenger_init_placement(red) is None


def test_placement_rule_rejects_oracle_call(tmp_path: Path) -> None:
    src = tmp_path / "r.proof"
    src.write_text("""
import 'P.game';
proof:
let:
    Set S;
assume:
    P(S);
theorem:
    P(S);
games:
    P(S).Left against P(S).Adversary;
    P(S).Right against P(S).Adversary;

Reduction R(Set S) compose P(S) against P(S).Adversary {
    Void Initialize() { challenger.Initialize(); }
    Bool Eq(S c) { challenger.Initialize(); return challenger.Eq(c); }
}
""")
    pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT)
    msg = upto.check_challenger_init_placement(_reduction(src))
    assert msg is not None and "Eq" in msg


def test_placement_rule_rejects_double_call(tmp_path: Path) -> None:
    red = _reduction(
        _placement_proof(
            tmp_path, "challenger.Eq(c)", init_body="challenger.Initialize();"
        )
    )
    msg = upto.check_challenger_init_placement(red)
    assert msg is not None and "more than once" in msg
