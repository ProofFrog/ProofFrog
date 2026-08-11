"""The same-callee argument crossing the calls-alignment cannot see.

``_calls_only_align_swaps`` aligns calls by CALLEE and, by its own
documentation, "leaves interchangeable same-callee results for the walker".
Two calls to the same callee are interchangeable only when their ARGUMENTS
agree; when they do not, the alignment pairs the wrong ones and the peel built
on top of it emits a FALSE obligation.

Measured on ``CG_expanded_LEAK_BIND_K_PK`` ``micro_2_challenge_left_39``,
whose residual goal (read in EasyCrypt after the peel) demands
``(v7_L, field9{1}).`1 = (v10{2}, field10{2}).`1`` -- i.e. that the oracle's
two input ciphertexts be equal -- from a precondition offering only
``={ct0, ct1}``. EC's ``swap`` refuses to reorder two abstract-module calls,
so the crossing cannot be repaired with more swaps either: the only honest
answer is to decline and let the oracle take its admit.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _calls_only_align_swaps,
    _same_callee_arg_crossing,
)


def _crossing_pair() -> tuple[list[ec_ast.EcStmt], list[ec_ast.EcStmt]]:
    """The measured shape: two ``NG.exp`` calls run in opposite orders."""
    left: list[ec_ast.EcStmt] = [
        ec_ast.Assign("v7", "ct0.`2"),
        ec_ast.Assign("v10", "ct1.`2"),
        ec_ast.Call("_r0", "NG.exp", "v7, field9"),
        ec_ast.Call("_r1", "NG.exp", "v10, field10"),
        ec_ast.Return("(_r0, _r1)"),
    ]
    right: list[ec_ast.EcStmt] = [
        ec_ast.Assign("v7", "ct0.`2"),
        ec_ast.Assign("v10", "ct1.`2"),
        ec_ast.Call("_r0", "NG.exp", "v10, field10"),
        ec_ast.Call("_r1", "NG.exp", "v7, field9"),
        ec_ast.Return("(_r1, _r0)"),
    ]
    return left, right


def test_detects_the_measured_crossing() -> None:
    left, right = _crossing_pair()
    assert _same_callee_arg_crossing(left, right)
    assert _same_callee_arg_crossing(right, left)


def test_alignment_declines_the_crossing() -> None:
    """The gate's whole point: no swap list, so every route above it admits."""
    left, right = _crossing_pair()
    assert _calls_only_align_swaps(left, right) is None
    assert _calls_only_align_swaps(right, left) is None


def test_same_callee_same_order_is_not_a_crossing() -> None:
    """Two calls on one callee are only a crossing when their ARGUMENTS move;
    the ordinary repeated-call shape must stay on the alignment path."""
    left, _ = _crossing_pair()
    assert not _same_callee_arg_crossing(left, list(left))
    assert _calls_only_align_swaps(left, list(left)) == []


def test_renamed_locals_do_not_trip_the_gate() -> None:
    """Deliberately narrow: a leg whose two sides merely rename their locals
    has mismatched argument multisets, so the gate stays silent rather than
    declining a leg it has no evidence against."""
    left, _ = _crossing_pair()
    renamed: list[ec_ast.EcStmt] = [
        ec_ast.Assign("w7", "ct0.`2"),
        ec_ast.Assign("w10", "ct1.`2"),
        ec_ast.Call("_r0", "NG.exp", "w7, field9"),
        ec_ast.Call("_r1", "NG.exp", "w10, field10"),
        ec_ast.Return("(_r0, _r1)"),
    ]
    assert not _same_callee_arg_crossing(left, renamed)


def test_cross_module_reorder_still_aligns() -> None:
    """The control the gate must not break: distinct callees reordered is the
    shape the alignment exists for, and it still produces swaps."""
    left: list[ec_ast.EcStmt] = [
        ec_ast.Call("s", "K.decaps", "dk0, ct0"),
        ec_ast.Call("x", "N.exp", "e0, dk0"),
        ec_ast.Return("(s, x)"),
    ]
    right: list[ec_ast.EcStmt] = [
        ec_ast.Call("x", "N.exp", "e0, dk0"),
        ec_ast.Call("s", "K.decaps", "dk0, ct0"),
        ec_ast.Return("(s, x)"),
    ]
    assert not _same_callee_arg_crossing(left, right)
    swaps = _calls_only_align_swaps(left, right)
    assert swaps and all(s.startswith("swap{1}") for s in swaps)
