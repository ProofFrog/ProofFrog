"""Tests for the LazyMapPairToSampledFunction transform pass (design §4)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import LazyMapPairToSampledFunction
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(game_src: str) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return LazyMapPairToSampledFunction().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapPairToSampledFunction().apply(original, _ctx())
    assert got == original


def test_declines_missing_disjointness_guard() -> None:
    # The write to M1 is not guarded by "!in M2".
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_mismatched_value_types() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<32>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_cardinality_read() -> None:
    # P2-1: a cardinality read on one map disqualifies the pass.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Int Count() { return |M1|; }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_declines_initialize_touches_map() -> None:
    # P2-2: a map assignment in Initialize disqualifies the pass.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Void Initialize() { M1[0b00000000] = 0b0000000000000000; }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_basic_two_map_merge() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> QueryA(BitString<8> k) {
                return F(k);
            }
            BitString<16> QueryB(BitString<8> k) {
                return F(k);
            }
        }
        """,
    )


# ---------------------------------------------------------------------------
# Disjointness-invariant fixtures
#
# Soundness of LazyMapPairToSampledFunction relies on the inductive
# invariant  dom(M1) ∩ dom(M2) = ∅  (see
# extras/docs/transforms/random_functions/LazyMapPairToSampledFunction.md).
# The invariant is preserved because (a) maps start empty (Initialize must
# not touch them -- P2-2), (b) hit-branches do not mutate, and (c)
# miss-branches write a key that was just verified (by the cascading guard)
# to be absent from both maps.  The tests below exercise every possible
# `writes_to` configuration across methods and confirm the rewrite
# uniformly produces `return F(k);` -- this is semantically correct
# *only* under the disjointness invariant, since the rewrite erases the
# distinction between the two maps.
# ---------------------------------------------------------------------------


def test_invariant_all_writes_to_m1() -> None:
    """Every matching method writes to M1; M2 is read but never written.
    Semantically M2 remains empty forever (its guard is always false),
    so the pair reduces to a single-map lazy RF on M1. The rewrite to a
    single sampled Function is still sound because F(k) uniformly
    represents the same lazy-RF distribution."""
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> QueryA(BitString<8> k) {
                return F(k);
            }
            BitString<16> QueryB(BitString<8> k) {
                return F(k);
            }
        }
        """,
    )


def test_invariant_all_writes_to_m2() -> None:
    """Symmetric converse: every matching method writes to M2."""
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> QueryA(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
            BitString<16> QueryB(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> QueryA(BitString<8> k) {
                return F(k);
            }
            BitString<16> QueryB(BitString<8> k) {
                return F(k);
            }
        }
        """,
    )


def test_invariant_three_oracle_mixed_writes() -> None:
    """Three oracles with a mixed writes_to configuration (M1, M2, M1).
    All must rewrite identically to `return F(k);` -- the transform
    discards the writes_to bit because under the disjointness invariant
    the choice of which map to memoize into is unobservable."""
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            BitString<16> A(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
            BitString<16> B(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
            BitString<16> C(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> A(BitString<8> k) { return F(k); }
            BitString<16> B(BitString<8> k) { return F(k); }
            BitString<16> C(BitString<8> k) { return F(k); }
        }
        """,
    )


def test_invariant_violation_direct_m2_write_without_guard() -> None:
    """Adversarial AST: if a method wrote directly to M2 *without* a
    preceding guard on both maps, the disjointness invariant could be
    violated (the same key could end up in both M1 and M2 simultaneously,
    after which the ordering of `if (k in M1)` vs. `if (k in M2)` becomes
    observable). The matcher requires the full cascading guard; a naked
    write elsewhere is caught by P2-1 and the transform declines."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Void Poison(BitString<8> k, BitString<16> v) {
                M2[k] = v;
            }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M1[k] = s;
                return s;
            }
        }
        """,
    )


def test_invariant_violation_initialize_populates_m1() -> None:
    """Adversarial AST: a non-empty Initialize for M1 could seed a key
    that is later also written to M2 on a miss (if the Initialize-seeded
    key is not in M2 at miss time), violating disjointness. The P2-2
    precondition rejects any Initialize reference to either map."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M1;
            Map<BitString<8>, BitString<16>> M2;
            Void Initialize() {
                M1[0b00000000] = 0b0000000000000000;
            }
            BitString<16> Query(BitString<8> k) {
                if (k in M1) { return M1[k]; }
                else if (k in M2) { return M2[k]; }
                BitString<16> s <- BitString<16>;
                M2[k] = s;
                return s;
            }
        }
        """,
    )
