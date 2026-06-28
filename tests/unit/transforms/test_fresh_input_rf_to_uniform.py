"""Tests for the FreshInputRFToUniform transform pass.

The transform replaces ``RF(v)`` with a uniform sample when ``v`` is a
``<-uniq[S]`` single-use input.  The replacement is sound ONLY when the
exclusion set ``S`` provably covers the RF's queried domain (in the relevant
projection).  Two regimes are accepted:

  (A) ``S`` is the called RF's own ``RF.domain``; or
  (B) ``S`` is a persistent, never-reset game field into which every RF call
      site inserts its argument's matching component (projection-tracking).

The transform must NOT fire when neither holds -- in particular when ``S`` is
an own-outputs-only set that ignores an adversary oracle's queries to the same
RF (which would make ``RF(v)`` not actually fresh).
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import FreshInputRFToUniform
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


def test_fires_projection_tracking_tuple() -> None:
    # Challenge samples c <-uniq[seen] and queries H([c, x]); the Eval oracle
    # inserts y[0] into seen before its own H(y) -- so every H query's first
    # component is in seen, and H([c, x]) is fresh.
    _assert_game(
        """
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
        """,
        """
        Game G() {
            Function<[BitString<8>, BitString<8>], BitString<16>> H;
            Set<BitString<8>> seen;
            Void Initialize() {
                H <- Function<[BitString<8>, BitString<8>], BitString<16>>;
            }
            BitString<16> Challenge(BitString<8> x) {
                BitString<16> __fresh_rf_c__ <- BitString<16>;
                BitString<16> z = __fresh_rf_c__;
                return z;
            }
            BitString<16> Eval([BitString<8>, BitString<8>] y) {
                seen = seen union {y[0]};
                return H(y);
            }
        }
        """,
    )


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


def test_f001_unconditional_tracking_add_still_fires() -> None:
    """Positive control: an unconditional top-level `seen = seen union {x}`
    records every RF query, so the fresh-input rewrite still fires."""
    transformed, _ = _apply(
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
    src = str(transformed)
    assert "<- BitString<m>" in src and "RF(v)" not in src
