"""Tests for GenericFor over Map (via .keys/.values/.entries) and Array."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)


class TestArrayIteration:
    def test_iterate_array_of_int(self) -> None:
        _check_game(
            """
            Game G() {
                Array<Int, 4> arr;
                Int Sum() {
                    Int total = 0;
                    for (Int x in arr) {
                        total = total + x;
                    }
                    return total;
                }
            }
            """
        )

    def test_iterate_array_wrong_element_type_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Array<Int, 4> arr;
                Void Initialize() {
                    for (Bool x in arr) {
                    }
                }
            }
            """
        )


class TestMapKeysValues:
    def test_iterate_map_keys(self) -> None:
        _check_game(
            """
            Game G() {
                Map<Int, Bool> M;
                Int Count() {
                    Int n = 0;
                    for (Int k in M.keys) {
                        n = n + 1;
                    }
                    return n;
                }
            }
            """
        )

    def test_iterate_map_values(self) -> None:
        _check_game(
            """
            Game G() {
                Map<Int, Bool> M;
                Bool AnyTrue() {
                    for (Bool v in M.values) {
                        if (v) { return true; }
                    }
                    return false;
                }
            }
            """
        )

    def test_map_keys_wrong_element_type_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Bool k in M.keys) {
                    }
                }
            }
            """
        )

    def test_map_unknown_field_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M.keyz) {
                    }
                }
            }
            """
        )


class TestMapEntries:
    def test_iterate_map_entries(self) -> None:
        _check_game(
            """
            Game G() {
                Map<Int, Bool> M;
                Int CountTrue() {
                    Int n = 0;
                    for ([Int, Bool] e in M.entries) {
                        if (e[1]) { n = n + 1; }
                    }
                    return n;
                }
            }
            """
        )

    def test_map_entries_wrong_tuple_shape_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for ([Bool, Int] e in M.entries) {
                    }
                }
            }
            """
        )


class TestRejections:
    def test_iterate_over_int_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Void Initialize() {
                    Int n = 5;
                    for (Int x in n) {
                    }
                }
            }
            """
        )

    def test_iterate_raw_map_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M) {
                    }
                }
            }
            """
        )

    def test_iterate_map_entries_with_scalar_var_fails(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Map<Int, Bool> M;
                Void Initialize() {
                    for (Int k in M.entries) {
                    }
                }
            }
            """
        )


class TestIntegration:
    def test_decaps_iter_fragment(self) -> None:
        _check_game(
            """
            Game G() {
                Map<Int, Bool> HashTable;
                Bool Lookup(Int query) {
                    for ([Int, Bool] entry in HashTable.entries) {
                        if (entry[0] == query) {
                            return entry[1];
                        }
                    }
                    return false;
                }
            }
            """
        )
