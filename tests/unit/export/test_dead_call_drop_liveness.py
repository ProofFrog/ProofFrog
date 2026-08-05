"""Unit tests for the one-sided call drop's LIVENESS gate.

`_dead_call_drop_tags` licenses dropping a one-sided call with the
glob-preserving `<M>_<m>_pres` axiom. Determinism alone is not enough: `_pres`
says nothing about the call's RESULT, so dropping a call whose result is still
read leaves that result universally quantified in the goal and the closing `/#`
cannot discharge it. The peel then runs to completion WITHOUT CLOSING -- the one
failure mode admit-counting cannot see, since no `admit` marks it. Six CFRG
seedbased IND-CCA exports sat in exactly that state and were EC-rejected because
of it.

Getting the predicate right took three wrong versions, and each test below pins
one of them so it cannot come back:

* a textual "does the name appear later" scan calls a DEAD STORE live;
* a one-step dead-store check misses TRANSITIVE deadness (call -> assign ->
  overwritten);
* whole-variable liveness calls a result live when it is packed into a tuple
  whose OTHER component is live -- the same per-component trap the bundled
  delegate's sample-drop gate hit earlier.

The third is what the PRF-random `KEMPRF_INDCCA` init hop actually looks like,
so every wrong version regressed a hop the peel closes correctly.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import _drop_result_dead


def _events(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    return [s for s in body if isinstance(s, (ec_ast.Call, ec_ast.Sample))]


def _dead(body: list[ec_ast.EcStmt], index: int) -> bool:
    return _drop_result_dead(body, _events(body), index)


def test_a_result_feeding_the_return_is_live() -> None:
    """The `CG_seedbased` / `UG_seedbased` shape: the dropped `NG.exp` feeds the
    returned `ctStar`, so `_pres` cannot characterize it."""
    body = [
        ec_ast.Call("e", "NG.exp", "g, x"),
        ec_ast.Assign("ctStar", "(c, e)"),
        ec_ast.Return("(pk, ss, ctStar)"),
    ]
    assert not _dead(body, 0)


def test_a_result_overwritten_before_use_is_dead() -> None:
    """A DEAD STORE. A textual scan sees `ss` after the call and wrongly calls it
    live; the write in between kills it."""
    body = [
        ec_ast.Call("ss", "F.evaluate", "k, c"),
        ec_ast.Sample("ss", "dbs"),
        ec_ast.Return("(pk, ss)"),
    ]
    assert _dead(body, 0)


def test_deadness_through_a_tuple_is_component_accurate() -> None:
    """The real `KEMPRF_INDCCA` PRF-random init shape, and the subtlest of the
    three: the dropped result is packed into `_tup_0` whose SECOND component is
    genuinely live, while the first is projected into a variable nothing reads.

    Whole-variable liveness marks the result live here and declines a hop the
    peel closes, which is how this was caught -- by an integration test, not by
    review.
    """
    body = [
        ec_ast.Call("ss3", "F.evaluate", "k3, c3"),
        ec_ast.Assign("_tup_0", "(ss3, c3)"),
        ec_ast.Assign("ssReal", "_tup_0.`1"),
        ec_ast.Assign("ctStar", "_tup_0.`2"),
        ec_ast.Sample("ss", "dbs"),
        ec_ast.Return("(pk, ss, ctStar)"),
    ]
    assert _dead(body, 0)


def test_a_live_tuple_component_keeps_its_source_live() -> None:
    """The mirror of the previous test: when it is the FIRST component that is
    read, the same call's result is live. A gate that always answered `dead`
    through a tuple would be unsound in exactly this case."""
    body = [
        ec_ast.Call("ss3", "F.evaluate", "k3, c3"),
        ec_ast.Assign("_tup_0", "(ss3, c3)"),
        ec_ast.Assign("out", "_tup_0.`1"),
        ec_ast.Return("(pk, out)"),
    ]
    assert not _dead(body, 0)


def test_a_result_less_call_is_trivially_dead() -> None:
    body = [ec_ast.Call("", "L.get", ""), ec_ast.Return("pk")]
    assert _dead(body, 0)


def test_a_dead_pure_assignment_keeps_nothing_alive() -> None:
    """A pure assignment whose target is dead can be deleted, so its reads must
    not revive anything. Without this the transitive chain above never breaks."""
    body = [
        ec_ast.Call("r", "K.f", "x"),
        ec_ast.Assign("unused", "r"),
        ec_ast.Return("pk"),
    ]
    assert _dead(body, 0)


def test_only_the_projected_component_stays_live() -> None:
    """Reading `t.`2` revives the SECOND component's source and not the first.

    Stated over two calls so the conclusion is the one the gate actually draws:
    with `keep = t.`2` the first call's result is droppable and the second's is
    not. This is the property every per-component conclusion above rests on.
    """
    body = [
        ec_ast.Call("a", "K.f", ""),
        ec_ast.Call("b", "K.g", ""),
        ec_ast.Assign("t", "(a, b)"),
        ec_ast.Assign("keep", "t.`2"),
        ec_ast.Return("keep"),
    ]
    assert _dead(body, 0)
    assert not _dead(body, 1)
