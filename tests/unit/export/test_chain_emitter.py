"""Unit tests for the dead-sample-drop synthesizer in ``chain_emitter``.

Cover the pure structural planner ``_dead_sample_drop_plan`` directly: it
must fire on a subsequence drop of dead samples, decline on genuine
permutations (which ``_permutation_swaps`` owns), decline on non-subsequence
diffs, and decline when a dropped statement is live, non-sample, or untyped.
The end-to-end EC rendering + compilation is covered by the integration
tests (``test_easycrypt_export.py``) and the pinned template
(``ec_templates/dead_sample_drop.ec``).
"""

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _dead_sample_drop_plan,
    _ec_perm_swaps,
    _has_tuple_repack,
    _is_tuple_literal,
    _same_det_structure,
    _synth_isuv_walk,
)


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _call_assign(name: str, obj: str, method: str, *args: str) -> frog_ast.Assignment:
    call = frog_ast.FuncCall(
        frog_ast.FieldAccess(_var(obj), method), [_var(a) for a in args]
    )
    return frog_ast.Assignment(None, _var(name), call)


def _sample(name: str, type_name: str) -> frog_ast.Sample:
    return frog_ast.Sample(_var(type_name), _var(name), _var(type_name))


def _ret(expr_name: str) -> frog_ast.ReturnStatement:
    return frog_ast.ReturnStatement(_var(expr_name))


def _game(statements: list[frog_ast.Statement]) -> frog_ast.Game:
    sig = frog_ast.MethodSignature("foo", _var("C"), [])
    method = frog_ast.Method(sig, frog_ast.Block(statements))
    return frog_ast.Game(("G", [], [], [method]))


# A faithful 2_14/7_13-shaped pair: the long side samples a dead ``mPrime``
# the short side never had.
def _long_lead() -> frog_ast.Game:
    return _game(
        [
            _sample("mPrime", "MessageSpace"),
            _call_assign("k", "E", "keygen"),
            _call_assign("c", "E", "enc", "k", "m"),
            _ret("c"),
        ]
    )


def _short() -> frog_ast.Game:
    return _game(
        [
            _call_assign("k", "E", "keygen"),
            _call_assign("c", "E", "enc", "k", "m"),
            _ret("c"),
        ]
    )


def test_fires_forward_leading_drop() -> None:
    plan = _dead_sample_drop_plan(_long_lead(), _short(), reversed_dir=False)
    assert plan is not None
    assert plan.side == 1  # extra sample on the left
    assert [s.var.name for s in plan.drops] == ["mPrime"]


def test_fires_reversed_leading_drop() -> None:
    # Reversed micro: the chain emitter passes the SAME (before=long,
    # after=short) args as the forward micro, flipping only reversed_dir.
    # The lemma is then ``short ~ long``, so the extra sample is on the
    # right and side == 2.
    plan = _dead_sample_drop_plan(_long_lead(), _short(), reversed_dir=True)
    assert plan is not None
    assert plan.side == 2
    assert [s.var.name for s in plan.drops] == ["mPrime"]


def test_fires_non_leading_drop() -> None:
    long = _game(
        [
            _call_assign("k", "E", "keygen"),
            _sample("mPrime", "MessageSpace"),
            _call_assign("c", "E", "enc", "k", "m"),
            _ret("c"),
        ]
    )
    plan = _dead_sample_drop_plan(long, _short(), reversed_dir=False)
    assert plan is not None
    assert plan.side == 1
    assert [s.var.name for s in plan.drops] == ["mPrime"]


def test_fires_two_drops() -> None:
    long = _game(
        [
            _sample("mPrime", "MessageSpace"),
            _call_assign("k", "E", "keygen"),
            _sample("mPrime2", "MessageSpace"),
            _call_assign("c", "E", "enc", "k", "m"),
            _ret("c"),
        ]
    )
    plan = _dead_sample_drop_plan(long, _short(), reversed_dir=False)
    assert plan is not None
    assert plan.side == 1
    assert [s.var.name for s in plan.drops] == ["mPrime", "mPrime2"]


def test_declines_equal_length_permutation() -> None:
    # Same length, reordered: a true reorder owned by _permutation_swaps.
    g1 = _game(
        [
            _call_assign("k", "E", "keygen"),
            _sample("r", "MessageSpace"),
            _ret("k"),
        ]
    )
    g2 = _game(
        [
            _sample("r", "MessageSpace"),
            _call_assign("k", "E", "keygen"),
            _ret("k"),
        ]
    )
    assert _dead_sample_drop_plan(g1, g2, reversed_dir=False) is None


def test_declines_when_dropped_sample_is_live() -> None:
    # The extra sample's result IS used downstream -> not a dead drop.
    long = _game(
        [
            _sample("r", "MessageSpace"),
            _call_assign("k", "E", "keygen"),
            _call_assign("c", "E", "enc", "k", "r"),  # uses r
            _ret("c"),
        ]
    )
    short = _game(
        [
            _call_assign("k", "E", "keygen"),
            _call_assign("c", "E", "enc", "k", "r"),
            _ret("c"),
        ]
    )
    assert _dead_sample_drop_plan(long, short, reversed_dir=False) is None


def test_declines_when_dropped_statement_is_not_a_sample() -> None:
    # The extra statement is a (dead) deterministic assignment, not a <$ .
    long = _game(
        [
            _call_assign("dead", "E", "keygen"),
            _call_assign("k", "E", "keygen"),
            _call_assign("c", "E", "enc", "k", "m"),
            _ret("c"),
        ]
    )
    assert _dead_sample_drop_plan(long, _short(), reversed_dir=False) is None


def test_declines_non_subsequence_diff() -> None:
    long = _game(
        [
            _sample("mPrime", "MessageSpace"),
            _call_assign("k", "E", "keygen"),
            _ret("k"),
        ]
    )
    # short is not a subsequence of long (different call).
    short = _game(
        [
            _call_assign("k", "E", "decaps"),
            _ret("k"),
        ]
    )
    assert _dead_sample_drop_plan(long, short, reversed_dir=False) is None


def test_declines_multiple_methods() -> None:
    sig = frog_ast.MethodSignature("foo", _var("C"), [])
    m1 = frog_ast.Method(sig, frog_ast.Block([_ret("m")]))
    m2 = frog_ast.Method(sig, frog_ast.Block([_ret("m")]))
    multi = frog_ast.Game(("G", [], [], [m1, m2]))
    assert _dead_sample_drop_plan(multi, _short(), reversed_dir=False) is None


# ---------------------------------------------------------------------------
# Rendered-state swap synthesis (B3 blocker B): the call-past-sample reorder.
#
# ``_rendered_state_swaps`` builds the two flat-state EC modules and delegates
# the swap computation to ``_ec_perm_swaps`` over the rendered bodies. These
# tests pin that delegate on the exact 2_14_Forward micro shape (an abstract
# ``E.keygen()`` reordered past an independent ``mPrime <$ d`` sample), which is
# invisible to ``_permutation_swaps`` run on the raw transform-application
# ASTs. The end-to-end rendering + EC compilation is covered by the integration
# tests and the pinned template (``ec_templates/call_past_sample_swap.ec``).
# ---------------------------------------------------------------------------

_KS = ec_ast.EcType("KeySpace")
_MS = ec_ast.EcType("MessageSpace")
_CS = ec_ast.EcType("CiphertextSpace")


def _state0_body() -> list[ec_ast.EcStmt]:
    """``k <@ E.keygen(); mPrime <$ d; c <@ E.enc(k, mPrime); return c``."""
    return [
        ec_ast.VarDecl("k", _KS),
        ec_ast.VarDecl("mPrime", _MS),
        ec_ast.VarDecl("c", _CS),
        ec_ast.Call("k", "E.keygen", ""),
        ec_ast.Sample("mPrime", "dMessageSpace"),
        ec_ast.Call("c", "E.enc", "k, mPrime"),
        ec_ast.Return("c"),
    ]


def _state1_body() -> list[ec_ast.EcStmt]:
    """``mPrime <$ d; _r0 <@ E.keygen(); _r1 <@ E.enc(_r0, mPrime); return _r1``."""
    return [
        ec_ast.VarDecl("mPrime", _MS),
        ec_ast.VarDecl("_r0", _KS),
        ec_ast.VarDecl("_r1", _CS),
        ec_ast.Sample("mPrime", "dMessageSpace"),
        ec_ast.Call("_r0", "E.keygen", ""),
        ec_ast.Call("_r1", "E.enc", "_r0, mPrime"),
        ec_ast.Return("_r1"),
    ]


def test_ec_perm_swaps_forward_call_past_sample() -> None:
    # state_0 ~ state_1: move the sample (exec pos 2) to the front.
    assert _ec_perm_swaps(_state0_body(), _state1_body()) == ["swap{1} 2 -1"]


def test_ec_perm_swaps_reversed_call_past_sample() -> None:
    # state_1 ~ state_0: move keygen (exec pos 2) to the front.
    assert _ec_perm_swaps(_state1_body(), _state0_body()) == ["swap{1} 2 -1"]


def test_ec_perm_swaps_identity_returns_empty() -> None:
    # Same order on both sides: no swap needed (distinct from ``None``).
    assert _ec_perm_swaps(_state0_body(), _state0_body()) == []


def test_ec_perm_swaps_declines_non_permutation() -> None:
    # A length mismatch (would be a drop, not a reorder) is not our case.
    short = [
        ec_ast.Call("k", "E.keygen", ""),
        ec_ast.Call("c", "E.enc", "k, m"),
        ec_ast.Return("c"),
    ]
    assert _ec_perm_swaps(_state0_body(), short) is None


# ---------------------------------------------------------------------------
# Inline-Single-Use-Variables swap-aligned call-walker (``_synth_isuv_walk``).
#
# ``Inline Single-Use Variables`` removes deterministic single-use assignments,
# so before/after differ in statement *count* and the whole-statement
# permutation checks decline; when the inlining also exposed an independent
# different-module call reorder, the canned ``proc; sp; wp; sim`` silently
# leaves ``={res}`` open. The walker aligns the calls (only) with ``swap{2}``
# then peels them bottom-up. The end-to-end EC compilation is covered by the
# cluster correctness proofs (CK_expanded micro_0_left_2 etc).
# ---------------------------------------------------------------------------


def _isuv_module(body: list[ec_ast.EcStmt]) -> ec_ast.Module:
    proc = ec_ast.Proc("compute", [], ec_ast.EcType("T"), body)
    return ec_ast.Module("S", [proc], [], None, [])


def test_isuv_walk_fires_on_cross_module_reorder() -> None:
    # Two independent different-module calls (M.f, N.g) in opposite order on the
    # two sides; the walker aligns the right side's calls to the left's order.
    left = _isuv_module(
        [
            ec_ast.Call("a", "M.f", ""),
            ec_ast.Call("b", "N.g", ""),
            ec_ast.Return("(a, b)"),
        ]
    )
    right = _isuv_module(
        [
            ec_ast.Call("b", "N.g", ""),
            ec_ast.Call("a", "M.f", ""),
            ec_ast.Return("(a, b)"),
        ]
    )
    tactic = _synth_isuv_walk(left, right)
    assert tactic is not None
    # proc + one alignment swap on side 2, then a (wp; call) per call + close.
    assert "proc." in tactic
    assert "swap{2} 2 -1." in tactic
    assert tactic.count("call (_: true).") == 2
    assert tactic[-1] == "skip => /#."


def test_isuv_walk_declines_when_already_aligned() -> None:
    # No reorder -> the canned ``sim`` route handles it; the walker must decline
    # so it never preempts a working static tactic.
    body = [
        ec_ast.Call("a", "M.f", ""),
        ec_ast.Call("b", "N.g", ""),
        ec_ast.Return("(a, b)"),
    ]
    assert _synth_isuv_walk(_isuv_module(body), _isuv_module(body)) is None


def test_isuv_walk_declines_without_calls() -> None:
    body = [ec_ast.Assign("x", "y"), ec_ast.Return("x")]
    assert _synth_isuv_walk(_isuv_module(body), _isuv_module(body)) is None


# --- init backbone peel gate (wall 6): tuple-repack discriminator -----------


def test_is_tuple_literal_recognizes_top_level_tuple() -> None:
    assert _is_tuple_literal("(ek0, K_c.LEAK.dk0, ek1, K_c.LEAK.dk1)")
    assert _is_tuple_literal("(a, b)")


def test_is_tuple_literal_rejects_projection_and_paren_single() -> None:
    # A projection ``t.`1`` is not a tuple constructor.
    assert not _is_tuple_literal("_tup.`1")
    # A parenthesized single expression has no top-level comma.
    assert not _is_tuple_literal("(a.`1)")
    # A comma nested inside an inner call must not count as top-level.
    assert not _is_tuple_literal("(f (a, b)).`1")


def _reduction_init_repack_body() -> list[ec_ast.EcStmt]:
    # A field-holding reduction's inlined Initialize: two keygens, then the
    # inner challenger's 4-tuple return packed and unpacked into own globals.
    return [
        ec_ast.Call("_tup0", "K.keygen", ""),
        ec_ast.Assign("ek00", "_tup0.`1"),
        ec_ast.Assign("C.dk0", "_tup0.`2"),
        ec_ast.Call("_tup_0", "K.keygen", ""),
        ec_ast.Assign("ek10", "_tup_0.`1"),
        ec_ast.Assign("C.dk1", "_tup_0.`2"),
        ec_ast.Assign("_tup", "(ek00, C.dk0, ek10, C.dk1)"),
        ec_ast.Assign("R.dk0", "_tup.`2"),
        ec_ast.Return("(ek00, ek10)"),
    ]


def _direct_keygen_body() -> list[ec_ast.EcStmt]:
    # A direct-keygen init (HON side, or R_MultiPRF): no tuple constructor.
    return [
        ec_ast.Call("_tup", "K.keygen", ""),
        ec_ast.Assign("ek0", "_tup.`1"),
        ec_ast.Assign("dk0", "_tup.`2"),
        ec_ast.Return("ek0"),
    ]


def test_has_tuple_repack_detects_reduction_pack() -> None:
    assert _has_tuple_repack(_reduction_init_repack_body())


def test_has_tuple_repack_false_for_direct_keygen() -> None:
    # The byte-identical ``sim`` case: no repack literal, so the peel declines.
    assert not _has_tuple_repack(_direct_keygen_body())


def test_same_det_structure_true_for_identical_bodies() -> None:
    assert _same_det_structure(_direct_keygen_body(), _direct_keygen_body())


def test_same_det_structure_false_for_repack_vs_direct() -> None:
    # The reduction repack carries extra assignments absent on the direct side.
    assert not _same_det_structure(
        _direct_keygen_body(), _reduction_init_repack_body()
    )
