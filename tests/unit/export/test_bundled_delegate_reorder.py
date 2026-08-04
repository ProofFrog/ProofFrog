"""Unit tests for the bundled-delegate init-reorder planner in ``chain_emitter``.

The synthesizer (``_synth_bundled_delegate_reorder``) closes the CFRG `_PQ`
IND-CCA `initialize` hops where one endpoint gets ``keygen; encaps`` bundled
inside a delegate ``Challenger.initialize()`` while the other splits them
around its own sampling chain. Its two pure planners are covered here:

* ``_bundled_reorder_swaps`` -- the block-move ``swap`` computation, including
  the travel block (feeding + unpacking assignments) and the independence gate;
* ``_sample_drop_alignment`` -- the one-sided-sample alignment, including the
  distribution granularity that keeps a seed draw from being coupled to a
  shared-secret draw.

End-to-end rendering + EC compilation is covered by the pinned template
``ec_templates/bundled_delegate_encaps_reorder.ec`` and by compiling the real
`CG_expanded_INDCCA_PQ` export.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _bd_events,
    _bd_sample_dead,
    _bundled_reorder_swaps,
    _ec_local_vars,
    _sample_drop_alignment,
    _stmt_travel_block,
)


def _explicit_side() -> list[ec_ast.EcStmt]:
    """The EXPLICIT endpoint: ``encaps`` sits after the first sampling chain.

    ``pq_keys <@ K.keygen(); seed <$ d; s <@ N.randomscalar(seed);
    g <@ N.generator(); e <@ N.exp(g, s); ek <- pq_keys.`1;
    t <@ K.encaps(ek); ss <- t.`1; ct <- t.`2``
    """
    return [
        ec_ast.Call("pq_keys", "K.keygen", ""),
        ec_ast.Sample("seed", "dSeed"),
        ec_ast.Call("s", "N.randomscalar", "seed"),
        ec_ast.Call("g", "N.generator", ""),
        ec_ast.Call("e", "N.exp", "g, s"),
        ec_ast.Assign("ek", "pq_keys.`1"),
        ec_ast.Call("t", "K.encaps", "ek"),
        ec_ast.Assign("ss", "t.`1"),
        ec_ast.Assign("ct", "t.`2"),
    ]


def _bundled_side() -> list[ec_ast.EcStmt]:
    """The BUNDLED endpoint: the inlined delegate ran ``keygen; encaps`` first."""
    return [
        ec_ast.Call("pq_keys", "K.keygen", ""),
        ec_ast.Assign("ek", "pq_keys.`1"),
        ec_ast.Call("t", "K.encaps", "ek"),
        ec_ast.Assign("ct", "t.`2"),
        ec_ast.Sample("seed", "dSeed"),
        ec_ast.Call("s", "N.randomscalar", "seed"),
        ec_ast.Call("g", "N.generator", ""),
        ec_ast.Call("e", "N.exp", "g, s"),
    ]


# ---------------------------------------------------------------------------
# _stmt_travel_block
# ---------------------------------------------------------------------------


def test_travel_block_takes_feeder_and_unpackers() -> None:
    body = _explicit_side()
    local = _ec_local_vars(body)
    # index 6 is `t <@ K.encaps(ek)`; it must travel with `ek <- pq_keys.`1`
    # (its argument) and with both `t.`i` unpackers.
    assert _stmt_travel_block(body, 6, local) == (5, 8)


def test_travel_block_stops_at_a_sample() -> None:
    body = _explicit_side()
    local = _ec_local_vars(body)
    # index 2 is `s <@ N.randomscalar(seed)`; `seed` comes from a SAMPLE, which
    # is not an assignment, so the block does not extend backwards over it.
    assert _stmt_travel_block(body, 2, local) == (2, 2)


# ---------------------------------------------------------------------------
# _bundled_reorder_swaps
# ---------------------------------------------------------------------------


def test_reorder_hoists_the_encaps_block_over_the_chain() -> None:
    body = _explicit_side()
    target = [c.callee for c in _bundled_side() if isinstance(c, ec_ast.Call)]
    got = _bundled_reorder_swaps(body, target, 1)
    assert got is not None
    swaps, moved = got
    # 1-based [6..9] moved back 4, i.e. to sit immediately after `keygen`.
    assert swaps == ["swap{1} [6..9] -4."]
    assert [c.callee for c in moved if isinstance(c, ec_ast.Call)] == target


def test_reorder_is_a_noop_when_the_call_order_already_matches() -> None:
    body = _bundled_side()
    target = [c.callee for c in body if isinstance(c, ec_ast.Call)]
    got = _bundled_reorder_swaps(body, target, 2)
    assert got is not None
    assert got[0] == []


def test_reorder_declines_when_the_target_call_is_absent() -> None:
    body = _explicit_side()
    assert _bundled_reorder_swaps(body, ["K.keygen", "K.decaps"], 1) is None


def test_reorder_declines_when_a_move_would_cross_a_dependency() -> None:
    # Moving `K.encaps` UP past `K.keygen` is rejected: they share `glob K`,
    # and `encaps` reads the key `keygen` produced.
    body = _explicit_side()
    target = ["K.encaps", "K.keygen", "N.randomscalar", "N.generator", "N.exp"]
    assert _bundled_reorder_swaps(body, target, 1) is None


# ---------------------------------------------------------------------------
# _sample_drop_alignment
# ---------------------------------------------------------------------------

_C = ("call", "K.keygen")
_E = ("call", "K.encaps")
_SEED = ("sample", "dSeed")
_SS = ("sample", "dSharedSecret")


def test_alignment_drops_one_dead_sample_per_side() -> None:
    # The hop_10 shape: the KDF challenger draws a key on the left, the KEM
    # challenger draws a shared secret on the right, and neither has a
    # counterpart.
    left = [_SS, _C, _E, _SEED]
    right = [_C, _E, _SS, _SEED]
    ops = _sample_drop_alignment(left, right)
    assert ops == [
        ("dropL", 0, -1),
        ("match", 1, 0),
        ("match", 2, 1),
        ("dropR", -1, 2),
        ("match", 3, 3),
    ]


def test_alignment_never_couples_two_different_distributions() -> None:
    # The bug this granularity exists to prevent: matching by "is a sample"
    # pairs the left's SEED draw with the right's SHARED-SECRET draw, emitting
    # an `rnd` whose distribution-equality side condition is false. With
    # distribution tags the only alignment drops both.
    left = [_C, _SEED]
    right = [_C, _SS]
    ops = _sample_drop_alignment(left, right)
    assert ops is not None
    assert ("match", 1, 1) not in ops
    assert ("dropL", 1, -1) in ops and ("dropR", -1, 1) in ops


def test_alignment_declines_on_a_one_sided_call() -> None:
    # A one-sided CALL needs a glob-preservation drop this route does not do.
    assert _sample_drop_alignment([_C, _E], [_C]) is None


def test_alignment_of_equal_backbones_is_all_matches() -> None:
    both = [_C, _E, _SEED]
    ops = _sample_drop_alignment(both, both)
    assert ops == [("match", 0, 0), ("match", 1, 1), ("match", 2, 2)]


def test_bd_events_tags_samples_by_distribution() -> None:
    assert _bd_events(_explicit_side()) == [
        ("call", "K.keygen"),
        ("sample", "dSeed"),
        ("call", "N.randomscalar"),
        ("call", "N.generator"),
        ("call", "N.exp"),
        ("call", "K.encaps"),
    ]


# ---------------------------------------------------------------------------
# _bd_sample_dead -- the soundness gate of the one-sided drop
# ---------------------------------------------------------------------------


def _delegate_repack() -> list[ec_ast.EcStmt]:
    """The bundled delegate's repack: one dead draw inside a whole-result tuple.

    ``ssStar`` is dead, but it is packed with the LIVE `ek` and `ct` into one
    tuple that the reduction then projects component by component.
    """
    return [
        ec_ast.Call("kp", "K.keygen", ""),
        ec_ast.Assign("ek", "kp.`1"),
        ec_ast.Call("t", "K.encaps", "ek"),
        ec_ast.Assign("ct", "t.`2"),
        ec_ast.Sample("ssStar", "dSharedSecret"),
        ec_ast.Assign("_tup", "(ek, ssStar, ct)"),
        ec_ast.Assign("ek_PQ", "_tup.`1"),
        ec_ast.Assign("ss_PQ", "_tup.`2"),
        ec_ast.Assign("kem_ct", "_tup.`3"),
    ]


def test_sample_dead_sees_through_a_tuple_repack() -> None:
    # Whole-variable taint would mark `ssStar` as reaching `ek_PQ`/`kem_ct` and
    # decline every genuine case; per-component taint reaches only `ss_PQ`.
    body = _delegate_repack()
    assert _bd_sample_dead(body, 4, "((ek_PQ, ekT), ss, kem_ct)", "R.kem_ct{2}")


def test_sample_live_through_a_tuple_component_is_not_dead() -> None:
    body = _delegate_repack()
    # Now the goal observes the component the draw feeds.
    assert not _bd_sample_dead(body, 4, "((ek_PQ, ekT), ss_PQ, kem_ct)", "")


def test_sample_feeding_the_return_is_not_dead() -> None:
    # The CK_expanded_INDCCA_T hop_9 shape: the "dead" draw is really the same
    # draw the other side makes, reordered, and it feeds the KDF input.
    body = [
        ec_ast.Sample("ss_T_star", "dbs_kem_t_nss"),
        ec_ast.Assign("kdf_in", "concat ss_T_star lbl"),
        ec_ast.Call("ss", "H.evaluate", "kdf_in"),
    ]
    assert not _bd_sample_dead(body, 0, "(pk, ss, ct)", "")


def test_sample_observed_only_through_the_coupling_is_not_dead() -> None:
    body = [
        ec_ast.Sample("k", "dKey"),
        ec_ast.Assign("stored", "k"),
    ]
    assert _bd_sample_dead(body, 0, "(pk, ss)", "")
    assert not _bd_sample_dead(body, 0, "(pk, ss)", "R.stored{2} = G.stored{1}")
