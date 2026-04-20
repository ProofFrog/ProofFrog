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
