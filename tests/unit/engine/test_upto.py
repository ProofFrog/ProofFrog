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


# ---------------------------------------------------------------------------
# The lockstep check (identical until bad)
# ---------------------------------------------------------------------------


def ok(p: frog_ast.GameFile) -> None:
    err = upto.identical_until_bad(p, "bad")
    assert err is None, str(err)


def fails(p: frog_ast.GameFile, text: str) -> None:
    err = upto.identical_until_bad(p, "bad")
    assert err is not None and text in str(err), err


def test_accept_bad_guess(tmp_path: Path) -> None:
    ok(pair(tmp_path, BAD_GUESS_LEFT, BAD_GUESS_RIGHT))


def test_accept_compare_then_return(tmp_path: Path) -> None:
    # The RAISED arm learns !(e != m); the leaf m == e is then entailed.
    left = """
    S m; S e; Bool bad;
    Void Initialize() { bad = false; m <- S; e <- S; }
    S Get() { if (e != m) { bad = true; } return m; }
    """
    right = left.replace("return m;", "return e;")
    ok(pair(tmp_path, left, right))


def test_accept_if_bad_guard_pruned(tmp_path: Path) -> None:
    left = """
    S m; S e; Bool bad;
    Void Initialize() { bad = false; m <- S; e <- S; }
    Void Raise() { bad = true; }
    S Get() { if (bad) { return m; } return e; }
    """
    right = left.replace("if (bad) { return m; } return e;", "return e;")
    ok(pair(tmp_path, left, right))


def test_accept_if_bad_else_pruned_to_else(tmp_path: Path) -> None:
    left = """
    S m; S e; Bool bad;
    Void Initialize() { bad = false; m <- S; e <- S; }
    Void Raise() { bad = true; }
    S Get() { if (bad) { return m; } else { return e; } }
    """
    right = left.replace("if (bad) { return m; } else { return e; }", "return e;")
    ok(pair(tmp_path, left, right))


def test_accept_flag_leaf(tmp_path: Path) -> None:
    # Collided returns the flag on one side and false on the other.
    left = """
    S x; S y; Bool bad;
    Void Initialize() { bad = false; x <- S; y <- S; if (x == y) { bad = true; } }
    Bool Collided() { return bad; }
    """
    ok(pair(tmp_path, left, left.replace("return bad;", "return false;")))


def test_accept_assignment_learns_equality(tmp_path: Path) -> None:
    left = """
    S a; Bool bad;
    Void Initialize() { bad = false; a <- S; }
    S O() { S t = a; return t; }
    """
    ok(pair(tmp_path, left, left.replace("return t;", "return a;")))


def test_reject_flag_at_different_positions(tmp_path: Path) -> None:
    left = """
    Int x; Bool bad;
    Void Initialize() { bad = false; x = 0; }
    Void O(Bool c) { if (c) { x = 1; bad = true; } }
    """
    right = left.replace("x = 1; bad = true;", "bad = true; x = 1;")
    fails(pair(tmp_path, left, right), "flag raised at different points")


def test_reject_fact_killed_by_reassignment(tmp_path: Path) -> None:
    left = """
    S a; S b; Bool bad;
    Void Initialize() { bad = false; a <- S; b <- S; }
    S Get() { if (a != b) { bad = true; } a <- S; return a; }
    """
    right = left.replace("a <- S; return a;", "a <- S; return b;")
    fails(pair(tmp_path, left, right), "Get")


def test_reject_learned_fact_killed_by_other_arm(tmp_path: Path) -> None:
    # The fact a == b learned from the raising arm describes the state on
    # entry; the else arm resamples a, so it must not survive the join.
    left = """
    S a; S b; Bool bad;
    Void Initialize() { bad = false; a <- S; b <- S; }
    S Get() { if (a != b) { bad = true; } else { a <- S; } return a; }
    """
    right = left.replace("return a;", "return b;")
    fails(pair(tmp_path, left, right), "Get")


def test_reject_different_assignment_targets(tmp_path: Path) -> None:
    # a == b holds, but writing a and writing b are different effects.
    left = """
    S a; S b; Bool bad;
    Void Initialize() { bad = false; a <- S; b <- S; }
    S Get(S v) { if (a != b) { bad = true; } a = v; return a; }
    """
    right = left.replace("a = v; return a;", "b = v; return a;")
    fails(pair(tmp_path, left, right), "Get")


def test_accept_map_index_by_entailment(tmp_path: Path) -> None:
    left = """
    S a; S b; Map<S, S> M; Bool bad;
    Void Initialize() { bad = false; a <- S; b <- S; }
    Void Put(S v) { if (a != b) { bad = true; } M[a] = v; }
    """
    ok(pair(tmp_path, left, left.replace("M[a] = v;", "M[b] = v;")))


def test_reject_call_in_leaf_not_sent_to_z3(tmp_path: Path) -> None:
    # F(bad) vs F(false) is a syntactic mismatch, never decided by Z3.
    left = """
    Bool bad;
    Void Initialize() { bad = false; }
    Bool O(Function<Bool, Bool> F) { return F(bad); }
    """
    right = left.replace("F(bad)", "F(false)")
    fails(pair(tmp_path, left, right), "O")


def test_reject_differing_pre_bad_code(tmp_path: Path) -> None:
    left = BAD_GUESS_LEFT.replace("target <- S; bad = false;", "bad = false; target <- S;")
    right = BAD_GUESS_RIGHT.replace(
        "target <- S; bad = false;", "bad = false; S u <- S; target <- S;"
    )
    fails(pair(tmp_path, left, right), "Initialize")


def test_reject_read_before_reset_not_pruned(tmp_path: Path) -> None:
    # Before the reset in Initialize the flag's value is not known to be false.
    left = """
    S m; Bool bad;
    S Initialize() { S e <- S; if (bad) { return e; } bad = false; m <- S; return m; }
    """
    right = left.replace("if (bad) { return e; } ", "")
    fails(pair(tmp_path, left, right), "Initialize")


def test_loops_compared_bodywise(tmp_path: Path) -> None:
    left = """
    Set<S> seen; Bool bad;
    Void Initialize() { bad = false; }
    Void O(S c) { for (S s in seen) { if (s == c) { bad = true; } } seen = seen union c; }
    """
    ok(pair(tmp_path, left, left))
    fails(
        pair(tmp_path, left, left.replace("seen = seen union c;", "")),
        "extra statement",
    )


def test_w1_w2_errors(tmp_path: Path) -> None:
    fails(
        pair(
            tmp_path,
            BAD_GUESS_LEFT,
            BAD_GUESS_RIGHT.replace("S target;", "S target; Int n;"),
        ),
        "different fields",
    )
    fails(
        pair(
            tmp_path,
            BAD_GUESS_LEFT,
            BAD_GUESS_RIGHT.replace("Bool Eq(S c)", "Bool Eq2(S c)"),
        ),
        "oracle",
    )


def test_undecided_is_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upto, "_entails", lambda *args: None)
    left = """
    S m; S e; Bool bad;
    Void Initialize() { bad = false; m <- S; e <- S; }
    S Get() { if (e != m) { bad = true; } return m; }
    """
    fails(pair(tmp_path, left, left.replace("return m;", "return e;")), "could not decide")


def test_entails_does_not_collapse_concatenation_to_bool() -> None:
    # `||` is also bitstring concatenation; encoding it as Boolean OR would
    # make three pairwise-distinct concatenations unsatisfiable and so
    # entail anything.
    v = frog_ast.Variable
    ops = frog_ast.BinaryOperators

    def cat(a: str, b: str) -> frog_ast.Expression:
        return frog_ast.BinaryOperation(ops.OR, v(a), v(b))

    def ne(x: frog_ast.Expression, y: frog_ast.Expression) -> frog_ast.Expression:
        return frog_ast.BinaryOperation(ops.NOTEQUALS, x, y)

    phi = [ne(cat("a", "b"), cat("c", "d")), ne(cat("a", "b"), cat("e", "f")),
           ne(cat("c", "d"), cat("e", "f"))]
    goal = frog_ast.BinaryOperation(ops.EQUALS, v("x"), v("y"))
    assert upto._entails(phi, goal) is False  # pylint: disable=protected-access
