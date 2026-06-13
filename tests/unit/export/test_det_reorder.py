"""Unit tests for the deterministic-reorder synthesizer.

Covers the gate ``_needs_det_functional_reorder`` (fires on a same-module
deterministic-call reorder, declines on cross-module-only reorders, non-reorders,
and probabilistic-call reorders), the ``_ec_functionalize`` call->ev rewrite, and
the end-to-end ``_synth_det_reorder`` structure (two ev-functional twin modules
plus a 3-leg transitivity). End-to-end EC compilation is exercised by the
integration sweep on ``CK_expanded_Correctness``.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _calls_only_alignment_invalid,
    _det_reorder_leg,
    _ec_full_perm_swaps,
    _ec_functionalize,
    _needs_det_functional_reorder,
    _synth_det_reorder,
)

_T = ec_ast.EcType("T")
# keygen is probabilistic; f, g (KEM_T-style) and h (other module) are det.
_DET = {("M", "f"), ("M", "g"), ("N", "h")}


def _det_pred(module: str, method: str) -> bool:
    return (module, method) in _DET


def _clone_of(module: str) -> str:
    return module + "_c"


def _module(name: str, body: list[ec_ast.EcStmt]) -> ec_ast.Module:
    params = [ec_ast.ModuleParam("M", "M_c.Scheme"), ec_ast.ModuleParam("N", "N_c.Scheme")]
    return ec_ast.Module(
        name=name,
        procs=[ec_ast.Proc("compute", [], _T, body)],
        params=params,
    )


def _same_module_pair() -> tuple[list[ec_ast.EcStmt], list[ec_ast.EcStmt]]:
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Call("c", "M.g", "a"),
        ec_ast.Return("(b, c)"),
    ]
    right = [  # same multiset, M.f and M.g transposed (same declared module)
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("c", "M.g", "a"),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(b, c)"),
    ]
    return left, right


def test_gate_fires_on_same_module_det_reorder() -> None:
    left, right = _same_module_pair()
    assert _needs_det_functional_reorder(left, right, _det_pred, True)


def test_gate_declines_cross_module_only_reorder() -> None:
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Call("d", "N.h", "a"),
        ec_ast.Return("(b, d)"),
    ]
    right = [  # N.h moved before M.f: each module's own order is unchanged
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("d", "N.h", "a"),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(b, d)"),
    ]
    assert not _needs_det_functional_reorder(left, right, _det_pred, True)


def test_gate_declines_identity() -> None:
    left, _ = _same_module_pair()
    assert not _needs_det_functional_reorder(left, list(left), _det_pred, True)


def test_gate_declines_probabilistic_reorder() -> None:
    # Two probabilistic calls transposed: the F_left ~ F_right leg cannot align
    # them, so the route must decline.
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("e", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(a, e, b)"),
    ]
    right = [
        ec_ast.Call("e", "M.keygen", ""),
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(a, e, b)"),
    ]
    assert not _needs_det_functional_reorder(left, right, _det_pred, True)


def test_functionalize_rewrites_det_calls_only() -> None:
    body = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
    ]
    out = _ec_functionalize(body, _det_pred, _clone_of)
    assert isinstance(out[0], ec_ast.Call)  # probabilistic kept
    assert isinstance(out[1], ec_ast.Assign)  # det functionalized
    assert out[1].rhs == "M_c.ev_f (a)"


def test_synth_emits_twins_and_three_leg_transitivity() -> None:
    left, right = _same_module_pair()
    syn = _synth_det_reorder(
        _module("S_left", left),
        _module("S_right", right),
        "S_left",
        "S_right",
        "(M, N)",
        "compute",
        "={glob M, glob N}",
        "={res, glob M, glob N}",
        _det_pred,
        _clone_of,
        True,
    )
    assert syn is not None
    assert syn.module_names == ["S_left_fdet", "S_right_fdet"]
    assert len(syn.module_texts) == 2
    joined = "\n".join(syn.tactic)
    # Two transitivity hops through the twin modules, det axiom + functional close.
    assert joined.count("transitivity ") == 2
    assert "S_left_fdet(M, N).compute" in joined
    assert "S_right_fdet(M, N).compute" in joined
    assert "M_f_det" in joined and "M_g_det" in joined
    assert "call (_: true)" in joined  # probabilistic prefix coupling


def test_synth_declines_cross_module_only() -> None:
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Call("d", "N.h", "a"),
        ec_ast.Return("(b, d)"),
    ]
    right = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("d", "N.h", "a"),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(b, d)"),
    ]
    assert (
        _synth_det_reorder(
            _module("S_left", left),
            _module("S_right", right),
            "S_left",
            "S_right",
            "(M, N)",
            "compute",
            "={glob M, glob N}",
            "={res, glob M, glob N}",
            _det_pred,
            _clone_of,
            True,
        )
        is None
    )


def _cross_module_dataflow_pair() -> tuple[
    list[ec_ast.EcStmt], list[ec_ast.EcStmt]
]:
    """A cross-module reorder (the micro_2_right_2_rev shape): ``N.h`` is sunk
    below the ``M.f`` + ``kdf <- r`` pair. Aligning ``right``'s calls to
    ``left``'s order pushes ``M.f`` (which defines ``r``) below the ``kdf <- r``
    assignment that reads it -- a use-before-def. The other direction is valid.
    Per-module call order is unchanged (cross-module), so it is the data-flow,
    not a same-module transposition, that needs the det route.
    """
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("x", "N.h", "a"),
        ec_ast.Call("r", "M.f", "a"),
        ec_ast.Assign("kdf", "r"),
        ec_ast.Return("(x, r, kdf)"),
    ]
    right = [  # N.h sunk past M.f and the kdf assignment that reads r
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("r", "M.f", "a"),
        ec_ast.Assign("kdf", "r"),
        ec_ast.Call("x", "N.h", "a"),
        ec_ast.Return("(x, r, kdf)"),
    ]
    return left, right


def test_alignment_invalid_detects_use_before_def() -> None:
    left, right = _cross_module_dataflow_pair()
    # Aligning right's calls to left's order is a use-before-def.
    assert _calls_only_alignment_invalid(right, left)
    # The other direction is valid (left already runs N.h before the kdf read).
    assert not _calls_only_alignment_invalid(left, right)


def test_gate_fires_cross_module_data_invalid_when_allowed() -> None:
    left, right = _cross_module_dataflow_pair()
    assert _needs_det_functional_reorder(left, right, _det_pred, True)


def test_gate_declines_cross_module_data_invalid_for_tuple_transform() -> None:
    # Same diff, but a tuple-inline transform (allow_cross_module=False) keeps the
    # byte-identical tuple-walk path instead of the det route.
    left, right = _cross_module_dataflow_pair()
    assert not _needs_det_functional_reorder(left, right, _det_pred, False)


def _mixed_reorder_pair() -> tuple[list[ec_ast.EcStmt], list[ec_ast.EcStmt]]:
    """The ``Topological Sorting`` shape: a *cross-module* probabilistic reorder
    (``M.keygen`` <-> ``N.keygen``) bundled with a *same-module* deterministic
    reorder (``M.f`` <-> ``M.g``). Each module's own probabilistic-call order is
    preserved, so the prob reorder is EC-swappable; the same-module det
    transposition forces the functional-twin route.
    """
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("p", "N.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Call("c", "M.g", "a"),
        ec_ast.Call("q", "N.h", "p"),
        ec_ast.Return("(b, c, q)"),
    ]
    right = [  # keygens transposed (cross-module); M.f/M.g transposed (same-module)
        ec_ast.Call("p", "N.keygen", ""),
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("c", "M.g", "a"),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Call("q", "N.h", "p"),
        ec_ast.Return("(b, c, q)"),
    ]
    return left, right


def test_gate_fires_on_mixed_crossmodule_prob_and_samemodule_det_reorder() -> None:
    left, right = _mixed_reorder_pair()
    assert _needs_det_functional_reorder(left, right, _det_pred, True)


def test_gate_declines_samemodule_prob_reorder() -> None:
    # Two *different* same-module probabilistic calls transposed: the middle leg
    # has no EC ``swap`` for them (shared glob) and no functional form, so the
    # per-module probabilistic-order check must decline.
    left = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("e", "M.encaps", "a"),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(a, e, b)"),
    ]
    right = [
        ec_ast.Call("e", "M.encaps", "a"),
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "M.f", "a"),
        ec_ast.Return("(a, e, b)"),
    ]
    assert not _needs_det_functional_reorder(left, right, _det_pred, True)


def test_det_reorder_leg_swaps_then_sim_for_reordered_calls() -> None:
    # When the functionalized twins differ in abstract-call order, the middle leg
    # reorders the left to the right with swap{1} and closes with ``sim``.
    fl = [
        ec_ast.Call("p", "N.keygen", ""),
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Return("(a, p)"),
    ]
    fr = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("p", "N.keygen", ""),
        ec_ast.Return("(a, p)"),
    ]
    leg = _det_reorder_leg(fl, fr)
    assert leg is not None
    assert leg[0] == "proc."
    assert leg[-1] == "sim."
    assert any(s.startswith("swap{1}") for s in leg)


def test_det_reorder_leg_wpcall_for_identical_call_order() -> None:
    # Identical abstract-call order (only the deterministic ``ev`` assignments
    # differ): keep the ``(wp; call)*`` peel, not swaps.
    fl = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Assign("b", "M_c.ev_f (a)"),
        ec_ast.Return("(a, b)"),
    ]
    fr = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Assign("b", "M_c.ev_f (a)"),
        ec_ast.Return("(a, b)"),
    ]
    leg = _det_reorder_leg(fl, fr)
    assert leg is not None
    assert "call (_: true)." in leg
    assert not any(s.startswith("swap{1}") for s in leg)


def test_ec_full_perm_swaps_reorders_to_target() -> None:
    before = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Assign("x", "1"),
        ec_ast.Call("b", "N.keygen", ""),
        ec_ast.Assign("y", "2"),
        ec_ast.Return("(a, b)"),
    ]
    # target: move N.keygen and its assign before M.keygen's assign
    after = [
        ec_ast.Call("a", "M.keygen", ""),
        ec_ast.Call("b", "N.keygen", ""),
        ec_ast.Assign("y", "2"),
        ec_ast.Assign("x", "1"),
        ec_ast.Return("(a, b)"),
    ]
    swaps = _ec_full_perm_swaps(before, after)
    assert swaps is not None and swaps  # non-empty, all swap{1} ... .
    assert all(s.startswith("swap{1} ") and s.endswith(".") for s in swaps)


def test_ec_full_perm_swaps_declines_on_duplicates() -> None:
    # Two statements with identical full signatures cannot be uniquely matched.
    before = [
        ec_ast.Assign("x", "1"),
        ec_ast.Assign("x", "1"),
        ec_ast.Return("x"),
    ]
    after = [
        ec_ast.Assign("x", "1"),
        ec_ast.Assign("x", "1"),
        ec_ast.Return("x"),
    ]
    assert _ec_full_perm_swaps(before, after) is None


def test_ec_full_perm_swaps_declines_on_non_permutation() -> None:
    before = [ec_ast.Call("a", "M.keygen", ""), ec_ast.Return("a")]
    after = [ec_ast.Call("a", "N.keygen", ""), ec_ast.Return("a")]
    assert _ec_full_perm_swaps(before, after) is None
