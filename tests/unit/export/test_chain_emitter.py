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
