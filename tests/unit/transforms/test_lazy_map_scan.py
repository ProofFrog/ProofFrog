"""Tests for the LazyMapScan transform pass (design spec §5.2)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_iteration import LazyMapScan
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
    return LazyMapScan().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapScan().apply(original, _ctx())
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"


def test_basic_scan_to_direct_lookup() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )


def test_equality_reversed_order() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (arg == e[0]) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )


def test_body_returns_e0() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<8> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<8> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return arg;
                }
                return 0b00000000;
            }
        }
        """,
    )


def test_trailing_statements_preserved() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """,
    )


def test_two_maps_only_one_iterated() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Map<BitString<8>, BitString<16>> N;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """,
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Map<BitString<8>, BitString<16>> N;
            BitString<16> Oracle(BitString<8> arg) {
                if (arg in M) {
                    return M[arg];
                }
                return 0b0000000000000000;
            }
        }
        """,
    )


def test_body_has_multiple_statements_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                    BitString<16> z <- BitString<16>;
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_if_has_else_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    } else {
                        return 0b0000000000000000;
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_non_equality_predicate_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Set<BitString<8>> S;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] in S) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )


def test_key_references_loop_var_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Oracle() {
                for ([BitString<8>, BitString<8>] e in M.entries) {
                    if (e[0] == e[1]) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )


def test_bare_loop_var_in_body_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            [BitString<8>, BitString<16>] Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e;
                    }
                }
                return [0b00000000, 0b0000000000000000];
            }
        }
        """
    )


def test_iteration_over_keys_not_entries_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Bool Oracle(BitString<8> arg) {
                for (BitString<8> k in M.keys) {
                    if (k == arg) {
                        return true;
                    }
                }
                return false;
            }
        }
        """
    )


def test_iteration_over_non_map_field_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Set<BitString<8>> S;
            Bool Oracle(BitString<8> arg) {
                for (BitString<8> k in S) {
                    if (k == arg) {
                        return true;
                    }
                }
                return false;
            }
        }
        """
    )


def test_integration_via_core_pipeline() -> None:
    """Run the full CORE_PIPELINE over a game with the scan pattern; confirm
    the GenericFor is eliminated after canonicalization."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.transforms._base import run_pipeline
    from proof_frog.transforms.pipelines import CORE_PIPELINE
    from proof_frog.visitors import SearchVisitor

    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    result = run_pipeline(game, CORE_PIPELINE, _ctx())
    found = SearchVisitor(
        lambda n: isinstance(n, frog_ast.GenericFor)
    ).visit(result)
    assert found is None, f"GenericFor should be eliminated, got:\n{result}"
