"""Typechecker rules for the RC2 uniq/minus split.

`x <-uniq[S] T` is the stateful freshness form: it implicitly inserts the draw
into S, so S must be a mutable Set lvalue (a Set variable/field) or a sampled
Function's `.domain`. `x <- T \\ E` is the pure one-shot exclusion draw: E may
be any set-valued expression (literal, view, computed) and there is no
insertion. See `proof_frog/semantic_analysis.py::leave_unique_sample`.
"""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)


# --- uniq form: accepted lvalues ------------------------------------------


def test_uniq_set_field_accepted() -> None:
    _check_game("""
        Game G() {
            Set<BitString<8>> seen;
            Void Initialize() {
                BitString<8> a <-uniq[seen] BitString<8>;
            }
        }
        """)


def test_uniq_rf_domain_accepted() -> None:
    _check_game("""
        Game G() {
            Function<BitString<8>, BitString<8>> H;
            Void Initialize() {
                BitString<8> a <-uniq[H.domain] BitString<8>;
            }
        }
        """)


# --- uniq form: rejected non-lvalues --------------------------------------


def test_uniq_literal_set_rejected() -> None:
    _check_game_fails("""
        Game G() {
            Void Initialize() {
                BitString<8> a <-uniq[{0b00000000}] BitString<8>;
            }
        }
        """)


def test_uniq_map_keys_view_rejected() -> None:
    _check_game_fails("""
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            Void Initialize() {
                BitString<8> a <-uniq[M.keys] BitString<8>;
            }
        }
        """)


def test_uniq_computed_set_expression_rejected() -> None:
    _check_game_fails("""
        Game G() {
            Set<BitString<8>> S;
            Set<BitString<8>> T;
            Void Initialize() {
                BitString<8> a <-uniq[S union T] BitString<8>;
            }
        }
        """)


# --- minus form: any set-valued exclusion accepted -------------------------


def test_minus_literal_accepted() -> None:
    _check_game("""
        Game G() {
            Void Initialize() {
                BitString<8> a <- BitString<8> \\ {0b00000000};
            }
        }
        """)


def test_minus_map_keys_view_accepted() -> None:
    _check_game("""
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            Void Initialize() {
                BitString<8> a <- BitString<8> \\ M.keys;
            }
        }
        """)


def test_minus_set_field_accepted() -> None:
    _check_game("""
        Game G() {
            Set<BitString<8>> S;
            Void Initialize() {
                BitString<8> a <- BitString<8> \\ S;
            }
        }
        """)
