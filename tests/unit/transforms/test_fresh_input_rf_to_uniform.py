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
    # H is also exposed via Hash, but S == H.domain covers those queries too.
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
