"""Tests for the FreshInputRFToUniform transform pass.

The transform replaces ``RF(v)`` with a uniform sample when ``v`` is a
``<-uniq[S]`` single-use input.  The replacement is sound ONLY when the
exclusion set ``S`` provably covers the RF's queried domain (in the relevant
projection).  Two regimes are accepted:

  (A) ``S`` is the called RF's own ``RF.domain``; or
  (B) ``S`` is a persistent, never-reset game field, and every RF call
      site's matching component is recorded in ``S`` before the call, with
      the value the call queries: either it is itself a ``<-uniq[S]`` draw,
      or an ``S = S union {..}`` insertion records it and the call is in
      Initialize, before the draw (an oracle may run after any draw).

The transform must NOT fire when neither holds -- in particular when ``S`` is
an own-outputs-only set that ignores an adversary oracle's queries to the same
RF, or when an oracle records its query in ``S`` but may make it after ``v``
is drawn (either would make ``RF(v)`` not actually fresh).
"""

import copy

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import (
    FreshInputRFToUniform,
    _exclusion_adequate,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(game_src: str) -> tuple[frog_ast.Game, PipelineContext]:
    game = frog_parser.parse_game(game_src)
    ctx = _ctx()
    transformed = FreshInputRFToUniform().apply(game, ctx)
    return transformed, ctx


def _assert_game(actual_src: str, expected_src: str) -> frog_ast.Game:
    transformed, _ = _apply(actual_src)
    expected = frog_parser.parse_game(expected_src)
    assert transformed == expected
    return transformed


# ---------------------------------------------------------------------------
# Regime (A): S == RF.domain  ->  fires
# ---------------------------------------------------------------------------


def test_fires_when_exclusion_is_rf_domain() -> None:
    _assert_game(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[H.domain] BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[H.domain] BitString<8>;
                BitString<16> __fresh_rf_c__ <- BitString<16>;
                BitString<16> z = __fresh_rf_c__;
                return z;
            }
        }
        """,
    )


def test_fires_rf_domain_even_with_adversary_oracle() -> None:
    # H is also exposed via Hash. Whether H.domain tracks those plain queries
    # (standard ROM) or only `<-uniq[H.domain]` draws (USER-ATTENTION sec 1.b)
    # is the contested F-002/F-003 ruling; regime A currently trusts the former,
    # which the ROM example corpus relies on. F-002 is ESCALATED, so this stays
    # a positive (fires) test pending the ruling.
    _assert_game(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[H.domain] BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
            BitString<16> Hash(BitString<8> x) {
                return H(x);
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[H.domain] BitString<8>;
                BitString<16> __fresh_rf_c__ <- BitString<16>;
                BitString<16> z = __fresh_rf_c__;
                return z;
            }
            BitString<16> Hash(BitString<8> x) {
                return H(x);
            }
        }
        """,
    )


# ---------------------------------------------------------------------------
# Regime (B): persistent field tracking the projection of every RF call
# ---------------------------------------------------------------------------


def test_fires_projection_tracking_tuple_in_initialize() -> None:
    # Challenge samples c <-uniq[seen] and queries H([c, x]); Initialize
    # inserts k into seen before its own H([k, k]), and runs before every
    # Challenge, so every H query's first component is in seen when c is
    # drawn, and H([c, x]) is fresh.
    _assert_game(
        """
        Game G(BitString<8> k) {
            Function<[BitString<8>, BitString<8>], BitString<16>> H;
            Set<BitString<8>> seen;
            BitString<16> y;
            Void Initialize() {
                H <- Function<[BitString<8>, BitString<8>], BitString<16>>;
                seen = seen union {k};
                y = H([k, k]);
            }
            BitString<16> Challenge(BitString<8> x) {
                BitString<8> c <-uniq[seen] BitString<8>;
                BitString<16> z = H([c, x]);
                return z;
            }
        }
        """,
        """
        Game G(BitString<8> k) {
            Function<[BitString<8>, BitString<8>], BitString<16>> H;
            Set<BitString<8>> seen;
            BitString<16> y;
            Void Initialize() {
                H <- Function<[BitString<8>, BitString<8>], BitString<16>>;
                seen = seen union {k};
                y = H([k, k]);
            }
            BitString<16> Challenge(BitString<8> x) {
                BitString<8> c <-uniq[seen] BitString<8>;
                BitString<16> __fresh_rf_c__ <- BitString<16>;
                BitString<16> z = __fresh_rf_c__;
                return z;
            }
        }
        """,
    )


def test_does_not_fire_projection_tracking_tuple_in_oracle() -> None:
    # The Eval oracle inserts y[0] into seen before its own H(y), but the
    # adversary may call Eval after Challenge drew c: Eval([c', x]) for every
    # c' hits H([c, x]), so H([c, x]) is not fresh.  (This test used to
    # assert the rewrite.)
    _assert_unchanged("""
        Game G() {
            Function<[BitString<8>, BitString<8>], BitString<16>> H;
            Set<BitString<8>> seen;
            Void Initialize() {
                H <- Function<[BitString<8>, BitString<8>], BitString<16>>;
            }
            BitString<16> Challenge(BitString<8> x) {
                BitString<8> c <-uniq[seen] BitString<8>;
                BitString<16> z = H([c, x]);
                return z;
            }
            BitString<16> Eval([BitString<8>, BitString<8>] y) {
                seen = seen union {y[0]};
                return H(y);
            }
        }
        """)


# ---------------------------------------------------------------------------
# UNSOUND shapes: must NOT fire (the gap this gate closes)
# ---------------------------------------------------------------------------


def _assert_unchanged(game_src: str) -> PipelineContext:
    transformed, ctx = _apply(game_src)
    expected = frog_parser.parse_game(game_src)
    assert transformed == expected
    return ctx


def test_does_not_fire_own_outputs_set_with_untracked_adversary_oracle() -> None:
    # S = seen accumulates only the challenge's own c's; the Hash oracle queries
    # H(x) WITHOUT adding x to seen, so H(c) for c<-uniq[seen] is NOT fresh
    # (c can equal an adversary Hash query).  Must not fire.
    ctx = _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Set<BitString<8>> seen;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[seen] BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
            BitString<16> Hash(BitString<8> x) {
                return H(x);
            }
        }
        """)
    assert any(
        nm.transform_name == "Fresh Input RF To Uniform" for nm in ctx.near_misses
    )


def test_does_not_fire_arbitrary_local_exclusion_set() -> None:
    # S is a method parameter (not a field, not RF.domain): cannot guarantee
    # cross-call distinctness / domain coverage.  Must not fire.
    _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge(Set<BitString<8>> S) {
                BitString<8> c <-uniq[S] BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
        }
        """)


def test_does_not_fire_when_set_is_reset() -> None:
    # seen tracks projections, but a reset (seen = {}) mid-stream breaks the
    # accumulation invariant.  Must not fire.
    _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Set<BitString<8>> seen;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <-uniq[seen] BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
            Void Reset() {
                seen = {};
            }
        }
        """)


# ---------------------------------------------------------------------------
# Structural negatives (independent of the exclusion-set gate)
# ---------------------------------------------------------------------------


def test_does_not_fire_on_plain_uniform_sample() -> None:
    # Plain <- (not <-uniq): a real sampling-with-replacement loss that must be
    # accounted for via an assumption hop, never silently simplified.
    _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<8> c <- BitString<8>;
                BitString<16> z = H(c);
                return z;
            }
        }
        """)


def test_does_not_fire_when_input_used_more_than_once() -> None:
    _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            [BitString<8>, BitString<16>] Challenge() {
                BitString<8> c <-uniq[H.domain] BitString<8>;
                BitString<16> z = H(c);
                return [c, z];
            }
        }
        """)


def test_does_not_fire_inside_loop() -> None:
    _assert_unchanged("""
        Game G() {
            Function<BitString<8>, BitString<16>> H;
            Void Initialize() {
                H <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Challenge() {
                BitString<16> z;
                for (Int i = 0 to 3) {
                    BitString<8> c <-uniq[H.domain] BitString<8>;
                    z = H(c);
                }
                return z;
            }
        }
        """)


def test_f001_conditional_tracking_add_not_fresh() -> None:
    """F-001 (attack_a): the tracking-add `seen = seen union {x}` is nested under
    `if (flag)`, so a Probe(x, false) queries RF(x) WITHOUT recording x; a later
    `v <-uniq[seen]` could draw v == x, making RF(v) a stale re-query.  Decline."""
    _assert_unchanged(
        """
        Game G(Int n, Int m) {
            Function<BitString<n>, BitString<m>> RF;
            Set<BitString<n>> seen;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<m>>;
            }
            BitString<m> Probe(BitString<n> x, Bool flag) {
                BitString<m> z = RF(x);
                if (flag) {
                    seen = seen union {x};
                }
                return z;
            }
            BitString<m> Fresh() {
                BitString<n> v <-uniq[seen] BitString<n>;
                return RF(v);
            }
        }
        """
    )


def test_f001_tracking_add_after_early_return_not_fresh() -> None:
    """F-001 (attack_b): the tracking-add is placed AFTER an early return
    `if (flag) return z;`, so on the flag=true path RF(x) ran but x was never
    recorded.  Decline."""
    _assert_unchanged(
        """
        Game G(Int n, Int m) {
            Function<BitString<n>, BitString<m>> RF;
            Set<BitString<n>> seen;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<m>>;
            }
            BitString<m> Probe(BitString<n> x, Bool flag) {
                BitString<m> z = RF(x);
                if (flag) {
                    return z;
                }
                seen = seen union {x};
                return z;
            }
            BitString<m> Fresh() {
                BitString<n> v <-uniq[seen] BitString<n>;
                return RF(v);
            }
        }
        """
    )


def test_f001_unconditional_tracking_add_in_oracle_not_fresh() -> None:
    """An unconditional top-level `seen = seen union {x}` records every RF
    query, but Probe is an oracle the adversary may call after Fresh drew v:
    Probe(v) queries RF(v) again, so RF(v) is not fresh.  Decline.  (This test
    used to assert the rewrite.)"""
    _assert_unchanged(
        """
        Game G(Int n, Int m) {
            Function<BitString<n>, BitString<m>> RF;
            Set<BitString<n>> seen;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<m>>;
            }
            BitString<m> Probe(BitString<n> x) {
                seen = seen union {x};
                BitString<m> z = RF(x);
                return z;
            }
            BitString<m> Fresh() {
                BitString<n> v <-uniq[seen] BitString<n>;
                return RF(v);
            }
        }
        """
    )


# ---------------------------------------------------------------------------
# Regime (B): the call must query the value the insertion recorded.
# ---------------------------------------------------------------------------


def _fired(game_src: str) -> bool:
    transformed, _ = _apply(game_src)
    return "__fresh_rf_" in str(transformed)


def _hash_game(body: str) -> str:
    return f"""
    Game G() {{
        Function<BitString<2>, BitString<2>> H;
        Set<BitString<2>> seen;
        Void Initialize() {{
            H <- Function<BitString<2>, BitString<2>>;
        }}
        BitString<2> Hash(BitString<2> x, Bool c) {{
            {body}
        }}
        BitString<2> Fresh() {{
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }}
    }}
    """


# Hash is an oracle, so the insertions below no longer count in any case (a
# Hash call may follow the draw); the Initialize variants further down keep
# exercising the rewrite checks on insertions that do count.
@pytest.mark.parametrize(
    "body",
    [
        # Hash records x and queries 0b00, so Fresh may draw 0b00.
        "seen = seen union {x}; x = 0b00; return H(x);",
        "seen = seen union {x}; if (c) { x = 0b00; } return H(x);",
        "seen = seen union {x}; if (c) { } else { x = 0b00; } return H(x);",
        "seen = seen union {x}; if (c) { if (c) { x = 0b00; } } return H(x);",
        "seen = seen union {x}; for (Int i = 0 to 1) { x = 0b00; } return H(x);",
        "seen = seen union {x}; x <- BitString<2>; return H(x);",
        "seen = seen union {x}; x = 0b00; if (c) { return H(x); } return 0b00;",
        # The call reads a different binding of x.
        "seen = seen union {x}; if (c) { BitString<2> x = 0b00; return H(x); } "
        "return 0b00;",
        # The insertion follows the call.
        "BitString<2> y = H(x); x = 0b00; seen = seen union {x}; return y;",
        "BitString<2> y = H(x); BitString<2> w <-uniq[seen] BitString<2>; "
        "seen = seen union {x}; return y + H(w);",
        # The draw records w, then w changes.
        "BitString<2> w <-uniq[seen] BitString<2>; w = x; return H(w);",
        # The draw is skipped when c is false.
        "if (c) { x <-uniq[seen] BitString<2>; } return H(x);",
    ],
)
def test_rewritten_insertion_not_simplified(body: str) -> None:
    assert not _fired(_hash_game(body))


def test_call_on_other_expression_not_simplified() -> None:
    assert not _fired(_hash_game("seen = seen union {x}; return H(x + 0b01);"))


@pytest.mark.parametrize(
    "body",
    [
        "seen = seen union {y[0]}; y = [0b00, y[1]]; return H(y);",
        "seen = seen union {y[0]}; y[0] = 0b00; return H(y);",
    ],
)
def test_rewritten_tuple_projection_not_simplified(body: str) -> None:
    assert not _fired(f"""
        Game G() {{
            Function<[BitString<2>, BitString<2>], BitString<2>> H;
            Set<BitString<2>> seen;
            Void Initialize() {{
                H <- Function<[BitString<2>, BitString<2>], BitString<2>>;
            }}
            BitString<2> Challenge(BitString<2> x) {{
                BitString<2> v <-uniq[seen] BitString<2>;
                return H([v, x]);
            }}
            BitString<2> Eval([BitString<2>, BitString<2>] y) {{
                {body}
            }}
        }}
        """)


def _initialize_game(initialize: str) -> str:
    # Only Initialize and Fresh query H, so a later query never meets v.
    return f"""
    Game G(Bool c) {{
        Function<BitString<2>, BitString<2>> H;
        Set<BitString<2>> seen;
        BitString<2> y;
        Void Initialize() {{
            H <- Function<BitString<2>, BitString<2>>;
            {initialize}
        }}
        BitString<2> Reveal() {{
            return y;
        }}
        BitString<2> Fresh() {{
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }}
    }}
    """


@pytest.mark.parametrize(
    "initialize",
    [
        "BitString<2> u = 0b00; seen = seen union {u}; u = 0b11; y = H(u);",
        "BitString<2> u = 0b00; seen = seen union {u}; if (c) { u = 0b11; } "
        "y = H(u);",
    ],
)
def test_rewritten_insertion_in_initialize_not_simplified(initialize: str) -> None:
    assert not _fired(_initialize_game(initialize))


@pytest.mark.parametrize(
    "initialize",
    [
        "BitString<2> u = 0b00; seen = seen union {u}; y = H(u);",
        "BitString<2> u = 0b00; u = 0b01; seen = seen union {u}; y = H(u);",
        "BitString<2> u = 0b00; seen = seen union {u}; BitString<2> t = 0b01; "
        "y = H(u);",
        "BitString<2> u = 0b00; seen = seen union {u}; y = H(u); u = 0b11;",
        "BitString<2> u = 0b00; seen = seen union {u}; if (c) { y = H(u); }",
        "BitString<2> u = 0b00; if (c) { seen = seen union {u}; y = H(u); }",
        "BitString<2> u <-uniq[seen] BitString<2>; y = H(u);",
        "if (c) { BitString<2> u <-uniq[seen] BitString<2>; y = H(u); }",
    ],
)
def test_recorded_value_still_simplified(initialize: str) -> None:
    assert _fired(_initialize_game(initialize))


# ---------------------------------------------------------------------------
# Regime (B): an inserted element that calls a method may differ from the
# queried one, since a method call returns a fresh value each time unless the
# method is annotated deterministic.
# ---------------------------------------------------------------------------

_CALL_PRIMITIVE = """
Primitive P() {
    BitString<2> G();
    BitString<2> f(BitString<2> x);
    deterministic BitString<2> D(BitString<2> x);
    deterministic BitString<2> DG();
}
"""


def _fired_with_primitive(game_src: str) -> bool:
    game = frog_parser.parse_game(game_src)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={"S": frog_parser.parse_primitive_file(_CALL_PRIMITIVE)},
        subsets_pairs=[],
    )
    return "__fresh_rf_" in str(FreshInputRFToUniform().apply(game, ctx))


def _call_game(hash_method: str = "", initialize: str = "") -> str:
    return f"""
    Game G(P S, BitString<2> k) {{
        Function<BitString<2>, BitString<2>> H;
        Set<BitString<2>> seen;
        BitString<2> y;
        Void Initialize() {{
            H <- Function<BitString<2>, BitString<2>>;
            {initialize}
        }}
        BitString<2> Reveal() {{
            return y;
        }}
        {hash_method}
        BitString<2> Fresh() {{
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }}
    }}
    """


@pytest.mark.parametrize(
    "hash_method",
    [
        # Each S.f(x) / S.G() may return a different value, so seen records
        # one value while H is queried on another.
        "BitString<2> Hash(BitString<2> x) "
        "{ seen = seen union {S.f(x)}; return H(S.f(x)); }",
        "BitString<2> Hash() { seen = seen union {S.G()}; return H(S.G()); }",
        "BitString<2> Hash(BitString<2> x) "
        "{ seen = seen union {S.D(S.f(x))}; return H(S.D(S.f(x))); }",
        "BitString<2> Hash(BitString<2> x) "
        "{ seen = seen union {x + S.G()}; return H(x + S.G()); }",
    ],
)
def test_inserted_nondeterministic_call_not_simplified(hash_method: str) -> None:
    assert not _fired_with_primitive(_call_game(hash_method))
    # Without the primitive in scope, no call is known to be deterministic.
    assert not _fired(_call_game(hash_method))


@pytest.mark.parametrize(
    "initialize",
    [
        # As in Hash above, but in Initialize, the only other H caller.
        "seen = seen union {S.f(k)}; y = H(S.f(k));",
        "seen = seen union {S.G()}; y = H(S.G());",
    ],
)
def test_inserted_nondeterministic_call_in_initialize_not_simplified(
    initialize: str,
) -> None:
    assert not _fired_with_primitive(_call_game(initialize=initialize))


# Only Initialize and Fresh query H below, so a later query never meets v.
@pytest.mark.parametrize(
    "initialize",
    [
        "seen = seen union {S.D(k)}; y = H(S.D(k));",
        "seen = seen union {S.DG()}; y = H(S.DG());",
        "seen = seen union {S.D(k + S.DG())}; y = H(S.D(k + S.DG()));",
        # One evaluation of a non-deterministic call, inserted and queried.
        "BitString<2> u = S.f(k); seen = seen union {u}; y = H(u);",
    ],
)
def test_inserted_deterministic_call_still_simplified(initialize: str) -> None:
    assert _fired_with_primitive(_call_game(initialize=initialize))


def test_inserted_deterministic_call_rewritten_argument_not_simplified() -> None:
    assert not _fired_with_primitive(
        _call_game(
            initialize="BitString<2> u = k; seen = seen union {S.D(u)}; "
            "u = 0b00; y = H(S.D(u));"
        )
    )


def test_inserted_deterministic_call_unknown_primitive_not_simplified() -> None:
    # With an empty namespace S.D cannot be resolved, so it is not trusted.
    assert not _fired(
        _call_game(initialize="seen = seen union {S.D(k)}; y = H(S.D(k));")
    )


# ---------------------------------------------------------------------------
# Regime (B): an insertion keeps the queried point away from the draw only
# when the query runs before the draw.  Any oracle may run after any draw, so
# only a query in Initialize, before the draw, counts.
# ---------------------------------------------------------------------------


def _timing_game(initialize: str = "", oracles: str = "", fresh: bool = True) -> str:
    fresh_method = (
        """
        BitString<2> Fresh() {
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }
        """
        if fresh
        else ""
    )
    return f"""
    Game G(Bool c) {{
        Function<BitString<2>, BitString<2>> H;
        Set<BitString<2>> seen;
        BitString<2> y;
        Void Initialize() {{
            H <- Function<BitString<2>, BitString<2>>;
            {initialize}
        }}
        BitString<2> Reveal() {{
            return y;
        }}
        {oracles}
        {fresh_method}
    }}
    """


_HASH = "BitString<2> Hash(BitString<2> x) { seen = seen union {x}; return H(x); }"


@pytest.mark.parametrize(
    "initialize, oracles, fresh",
    [
        # An oracle query on a recorded point: a later Hash(v) hits v.
        ("", _HASH, True),
        # ... on a recorded constant: v may be 0b00.
        (
            "",
            "BitString<2> Hash() { seen = seen union {0b00}; return H(0b00); }",
            True,
        ),
        # ... guarded by a membership test: sound (v is in seen once drawn),
        # but the gate does not read the guard, so it is refused too.
        (
            "",
            "BitString<2> Hash(BitString<2> x) { if (x in seen) { return 0b00; } "
            "seen = seen union {x}; return H(x); }",
            True,
        ),
        # The recorded query precedes the draw in the same oracle, but a
        # later call of that oracle may query v.
        (
            "",
            "BitString<2> Twice(BitString<2> x) { seen = seen union {x}; "
            "BitString<2> a = H(x); BitString<2> v <-uniq[seen] BitString<2>; "
            "return a + H(v); }",
            False,
        ),
        # The recorded query follows the draw in the same call.
        (
            "",
            "BitString<2> Twice(BitString<2> x) { "
            "BitString<2> v <-uniq[seen] BitString<2>; seen = seen union {x}; "
            "BitString<2> a = H(x); return a + H(v); }",
            False,
        ),
        # The draw is in Initialize; every oracle runs after it.
        ("BitString<2> v <-uniq[seen] BitString<2>; y = H(v);", _HASH, False),
        # The draw is in Initialize, the recorded query later in Initialize.
        (
            "BitString<2> v <-uniq[seen] BitString<2>; y = H(v); "
            "BitString<2> u = 0b00; seen = seen union {u}; y = y + H(u);",
            "",
            False,
        ),
        (
            "BitString<2> v <-uniq[seen] BitString<2>; seen = seen union {0b00}; "
            "y = H(v) + H(0b00);",
            "",
            False,
        ),
        # ... or after the branch holding the draw.
        (
            "if (c) { BitString<2> v <-uniq[seen] BitString<2>; y = H(v); } "
            "seen = seen union {0b00}; y = y + H(0b00);",
            "",
            False,
        ),
        # A recorded query in Initialize is fine, but Hash is still an oracle.
        ("seen = seen union {0b00}; y = H(0b00);", _HASH, True),
    ],
)
def test_recorded_query_after_draw_not_simplified(
    initialize: str, oracles: str, fresh: bool
) -> None:
    assert not _fired(_timing_game(initialize, oracles, fresh))


@pytest.mark.parametrize(
    "initialize, oracles, fresh",
    [
        # Every recorded query is in Initialize; the draw is in an oracle.
        ("seen = seen union {0b00}; y = H(0b00);", "", True),
        (
            "if (c) { seen = seen union {0b00}; y = H(0b00); } "
            "else { seen = seen union {0b01}; y = H(0b01); }",
            "",
            True,
        ),
        (
            "for (Int i = 0 to 2) { BitString<2> u = y; seen = seen union {u}; "
            "y = H(u); }",
            "",
            True,
        ),
        # The draw is in Initialize, after the recorded query.
        (
            "seen = seen union {0b00}; BitString<2> a = H(0b00); "
            "BitString<2> v <-uniq[seen] BitString<2>; y = a + H(v);",
            "",
            False,
        ),
        (
            "seen = seen union {0b00}; BitString<2> a = H(0b00); "
            "if (c) { BitString<2> v <-uniq[seen] BitString<2>; y = a + H(v); }",
            "",
            False,
        ),
        # ... in the condition of the if holding the draw.
        (
            "seen = seen union {0b00}; "
            "if (H(0b00) == 0b00) { BitString<2> v <-uniq[seen] BitString<2>; "
            "y = H(v); }",
            "",
            False,
        ),
        # Every other query is itself a <-uniq[seen] draw, wherever it is.
        (
            "",
            "BitString<2> Samp() { BitString<2> x <-uniq[seen] BitString<2>; "
            "return H(x); }",
            True,
        ),
        (
            "BitString<2> v <-uniq[seen] BitString<2>; y = H(v);",
            "BitString<2> Samp() { BitString<2> x <-uniq[seen] BitString<2>; "
            "return H(x); }",
            False,
        ),
    ],
)
def test_recorded_query_before_draw_still_simplified(
    initialize: str, oracles: str, fresh: bool
) -> None:
    assert _fired(_timing_game(initialize, oracles, fresh))


def test_draw_not_found_in_game_not_adequate() -> None:
    """The gate locates the draw by identity to tell which Initialize queries
    precede it; a draw it cannot find there (or finds twice) is refused."""
    game = frog_parser.parse_game(
        _timing_game("seen = seen union {0b00}; y = H(0b00);")
    )
    fresh = next(m for m in game.methods if m.signature.name == "Fresh")
    draw = fresh.block.statements[0]
    assert isinstance(draw, frog_ast.UniqueSample)
    args = (game, "H", "seen", None, {f.name for f in game.fields}, {})
    assert _exclusion_adequate(*args, draw)
    assert not _exclusion_adequate(*args, copy.deepcopy(draw))


@pytest.mark.parametrize(
    "exclusion, oracles",
    [
        ("seen", "Int Size() { return |seen|; }"),
        ("H.domain", ""),
    ],
)
def test_rewrite_keeps_the_draw(exclusion: str, oracles: str) -> None:
    """`v <-uniq[S] T` also inserts v into S, which may be read elsewhere,
    so only the call is replaced; the draw stays for dead-code elimination
    to judge."""
    _assert_game(
        f"""
        Game G() {{
            Function<BitString<2>, BitString<2>> H;
            Set<BitString<2>> seen;
            Void Initialize() {{
                H <- Function<BitString<2>, BitString<2>>;
            }}
            {oracles}
            BitString<2> Fresh() {{
                BitString<2> v <-uniq[{exclusion}] BitString<2>;
                return H(v);
            }}
        }}
        """,
        f"""
        Game G() {{
            Function<BitString<2>, BitString<2>> H;
            Set<BitString<2>> seen;
            Void Initialize() {{
                H <- Function<BitString<2>, BitString<2>>;
            }}
            {oracles}
            BitString<2> Fresh() {{
                BitString<2> v <-uniq[{exclusion}] BitString<2>;
                BitString<2> __fresh_rf_v__ <- BitString<2>;
                return __fresh_rf_v__;
            }}
        }}
        """,
    )


# ---------------------------------------------------------------------------
# Eligibility: H is one sampled function, queried only by direct calls.
# ---------------------------------------------------------------------------


def _eligibility_game(oracles: str, fields: str = "", initialize: str = "") -> str:
    """Fresh draws v <-uniq[seen], which no other H query is recorded in, so
    the rewrite is sound exactly when no other query reaches H."""
    return f"""
    Game G() {{
        Function<BitString<2>, BitString<2>> H;
        Set<BitString<2>> seen;
        {fields}
        Void Initialize() {{
            H <- Function<BitString<2>, BitString<2>>;
            {initialize}
        }}
        {oracles}
        BitString<2> Fresh() {{
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }}
    }}
    """


_FN = "Function<BitString<2>, BitString<2>>"


@pytest.mark.parametrize(
    "oracles, fields, initialize",
    [
        # A local copy queried on an adversary-chosen point.
        (
            f"BitString<2> Hash(BitString<2> x) {{ {_FN} K = H; return K(x); }}",
            "",
            "",
        ),
        # A field copy made in Initialize.
        (
            "BitString<2> Hash(BitString<2> x) { return K(x); }",
            f"{_FN} K;",
            "K = H;",
        ),
        # The function itself handed to the adversary.
        (f"{_FN} Reveal() {{ return H; }}", "", ""),
        # Stored in a tuple.
        (
            f"[{_FN}, Bool] Reveal() {{ return [H, true]; }}",
            "",
            "",
        ),
    ],
)
def test_escaping_rf_not_simplified(oracles: str, fields: str, initialize: str) -> None:
    """A copy of H answers queries the call-site analysis never sees, so
    H(v) may already be known."""
    assert not _fired(_eligibility_game(oracles, fields, initialize))


@pytest.mark.parametrize(
    "oracles, fields, initialize",
    [
        # Replaced by an adversary-chosen function.
        (f"Void Reset({_FN} F) {{ H = F; }}", "", ""),
        # Replaced by another random function the adversary can query.
        (
            "Void Reset() { H = K; } BitString<2> HashK(BitString<2> x) "
            "{ return K(x); }",
            f"{_FN} K;",
            f"K <- {_FN};",
        ),
        # Overwritten in Initialize after its sample.
        (
            "BitString<2> HashK(BitString<2> x) { return K(x); }",
            f"{_FN} K;",
            f"K <- {_FN}; H = K;",
        ),
        # Written under a branch.
        (f"Void Reset(Bool b, {_FN} F) {{ if (b) {{ H = F; }} }}", "", ""),
        # Re-sampled by an oracle.
        (f"Void Reset() {{ H <- {_FN}; }}", "", ""),
    ],
)
def test_reassigned_rf_not_simplified(
    oracles: str, fields: str, initialize: str
) -> None:
    """After any write besides its one sample, H need not be the sampled
    random function the rewrite assumes."""
    assert not _fired(_eligibility_game(oracles, fields, initialize))


@pytest.mark.parametrize(
    "oracles, fields",
    [
        # Draw-recorded queries, called directly.
        (
            "BitString<2> Hash() { BitString<2> u <-uniq[seen] BitString<2>; "
            "return H(u); }",
            "",
        ),
        # Writes to another Function field leave H alone.
        (f"Void Reset({_FN} F) {{ G = F; }}", f"{_FN} G;"),
    ],
)
def test_directly_called_rf_still_simplified(oracles: str, fields: str) -> None:
    assert _fired(_eligibility_game(oracles, fields))


def _let_ctx() -> PipelineContext:
    types = NameTypeMap()
    types.set(
        "H",
        frog_ast.FunctionType(
            frog_ast.BitStringType(frog_ast.Integer(2)),
            frog_ast.BitStringType(frog_ast.Integer(2)),
        ),
    )
    return PipelineContext(
        variables={},
        proof_let_types=types,
        proof_namespace={},
        subsets_pairs=[],
        sampled_let_names={"H"},
    )


def _let_game(oracles: str) -> str:
    return f"""
    Game G() {{
        Set<BitString<2>> seen;
        {oracles}
        BitString<2> Fresh() {{
            BitString<2> v <-uniq[seen] BitString<2>;
            return H(v);
        }}
    }}
    """


@pytest.mark.parametrize(
    "oracles, fires",
    [
        ("", True),
        (f"BitString<2> Hash(BitString<2> x) {{ {_FN} K = H; return K(x); }}", False),
        (f"Void Reset({_FN} F) {{ H = F; }}", False),
    ],
)
def test_sampled_let_function_eligibility(oracles: str, fires: bool) -> None:
    """A sampled let: function is sampled outside the game, so the game may
    neither write it nor copy it."""
    game = frog_parser.parse_game(_let_game(oracles))
    transformed = FreshInputRFToUniform().apply(game, _let_ctx())
    assert ("__fresh_rf_" in str(transformed)) == fires
