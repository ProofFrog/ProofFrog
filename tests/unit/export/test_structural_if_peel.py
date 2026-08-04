"""Unit tests for the same-shape post-init oracle peel in ``chain_emitter``.

``_synth_structural_if_peel`` closes the CFRG `_PQ` `decaps` hops whose two
bodies are statement-for-statement identical and differ only in the field
references the hop's coupling equates (the reduction reads its packed
``corr.`k`` where the game reads a separate field). ``sim`` cannot relate those
-- it matches globals by NAME -- so the peel walks the shared skeleton instead.

Covered here are its pure planners:

* ``_same_shape``   -- the structural predicate that admits the route;
* ``_shape_peel``   -- the emitted tactic, including the ``seq``/``#pre`` split
  before a branch and the ``auto`` terminator for a call-free branch;
* ``_differing_tokens`` -- what the closing ``smt`` has to bridge, which is also
  what the arrow-typed-field gate is applied to.

End-to-end rendering + EC compilation is covered by the pinned template
``ec_templates/decaps_packed_coupling.ec`` and by compiling the real
`CG_expanded_INDCCA_PQ` export.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _differing_tokens,
    _same_shape,
    _shape_peel,
)


def _decaps_body(guard_ref: str, ss_ref: str, dk_ref: str) -> list[ec_ast.EcStmt]:
    """The real `decaps` skeleton: outer guard, shared prefix, inner branch."""
    return [
        ec_ast.If(
            "ct = ctStar",
            [ec_ast.Assign("r", "None")],
            [
                ec_ast.Call("dk_T", "NG.randomscalar", "seed_T"),
                ec_ast.Assign("ct_PQ", "ct.`1"),
                ec_ast.Call("e0", "NG.exp", "ct_PQ, dk_T"),
                ec_ast.If(
                    f"ct_PQ = {guard_ref}",
                    [
                        ec_ast.Call("s8", "K.encodesharedsecret", ss_ref),
                        ec_ast.Assign("r", "Some (s8)"),
                    ],
                    [
                        ec_ast.Call("dsp", "K.decaps", f"{dk_ref}, ct_PQ"),
                        ec_ast.Assign("r", "Some (dsp)"),
                    ],
                ),
            ],
        ),
        ec_ast.Return("r"),
    ]


_RED = _decaps_body("corr.`3", "corr.`5", "corr.`2")
_GAME = _decaps_body("kem_ct", "ss_PQ", "pq_keys.`2")


# ---------------------------------------------------------------------------
# _same_shape
# ---------------------------------------------------------------------------


def test_same_shape_ignores_differing_expressions() -> None:
    assert _same_shape(_RED, _GAME)


def test_same_shape_rejects_a_different_callee() -> None:
    other = _decaps_body("kem_ct", "ss_PQ", "pq_keys.`2")
    inner = other[0].else_body[3]
    assert isinstance(inner, ec_ast.If)
    inner.then_body[0] = ec_ast.Call("s8", "H.evaluate", "ss_PQ")
    assert not _same_shape(_RED, other)


def test_same_shape_rejects_a_missing_statement() -> None:
    other = _decaps_body("kem_ct", "ss_PQ", "pq_keys.`2")
    other[0].else_body.pop(1)
    assert not _same_shape(_RED, other)


def test_same_shape_rejects_a_different_distribution() -> None:
    a = [ec_ast.Sample("x", "dA")]
    b = [ec_ast.Sample("x", "dB")]
    assert not _same_shape(a, b)


# ---------------------------------------------------------------------------
# _shape_peel
# ---------------------------------------------------------------------------


def _peel() -> list[str]:
    got = _shape_peel(
        [s for s in _RED if not isinstance(s, ec_ast.Return)],
        [s for s in _GAME if not isinstance(s, ec_ast.Return)],
    )
    assert got is not None
    return got


def test_peel_opens_with_the_outer_guard_and_discharges_it_by_smt() -> None:
    # The outer guard is `ct = ctStar`, a coupled reference on both sides.
    assert _peel()[0] == "if; 1: smt()."


def test_peel_closes_a_call_free_branch_with_auto() -> None:
    # `r <- None` has no call, so no round's leading `wp` exists to absorb it
    # and `skip` would hit a non-empty statement list.
    assert _peel()[1] == "auto."


def test_peel_splits_the_shared_prefix_with_seq_and_pre() -> None:
    # Three statements precede the inner `if`, and the invariant names ONLY the
    # prefix-bound locals the branch actually reads -- `ct_PQ` (the guard), not
    # `dk_T`/`e0`, which the prefix consumes itself.
    line = next(s for s in _peel() if s.startswith("seq "))
    assert line == "seq 3 3 : (#pre /\\ ={ct_PQ})."


def test_peel_couples_every_call_and_closes_each_branch() -> None:
    peel = _peel()
    assert peel.count("wp; call (_: true).") == 2 + 1 + 1
    assert peel.count("if; 1: smt().") == 2


def test_peel_ends_each_run_with_a_wp_before_skip() -> None:
    # An assignment ABOVE the first call of a run (`ct_PQ <- ct.`1` here) is not
    # absorbed by any round's leading `wp`; without the trailing one EC reports
    # "left instruction list is not empty".
    peel = _peel()
    assert "skip => /#." not in peel
    assert peel.count("wp; skip => /#.") == 3


# ---------------------------------------------------------------------------
# _differing_tokens -- what the closing smt must bridge
# ---------------------------------------------------------------------------


def test_differing_tokens_finds_the_coupled_field_references() -> None:
    diff = _differing_tokens(_RED, _GAME)
    assert {"corr", "kem_ct", "ss_PQ", "pq_keys"} <= diff


def test_differing_tokens_is_empty_for_identical_bodies() -> None:
    assert _differing_tokens(_RED, _RED) == set()


def test_differing_tokens_sees_a_guard_only_difference() -> None:
    a = [ec_ast.If("x = f", [], [])]
    b = [ec_ast.If("x = g", [], [])]
    assert _differing_tokens(a, b) == {"f", "g"}
