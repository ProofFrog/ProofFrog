"""A sampling domain must be a finite type.

Registering ``Bool``/``Int``/``T?`` in the AST type map (so they can appear
as tuple components) also makes them reachable as the right-hand side of a
sample. ``Bool`` is a legitimate uniform domain; ``Int`` is unbounded and an
optional type has no natural weight for ``None``, so both stay rejected on
either sampling form."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)


class TestSamplableDomains:
    def test_bool_is_samplable(self) -> None:
        _check_game("""
            Game G() {
                Bool Run() {
                    Bool b <- Bool;
                    return b;
                }
            }
            """)

    def test_bit_string_is_samplable(self) -> None:
        _check_game("""
            Game G(Int n) {
                Bool Run() {
                    BitString<n> r <- BitString<n>;
                    return r == r;
                }
            }
            """)

    def test_mod_int_is_samplable(self) -> None:
        _check_game("""
            Game G(Int q) {
                Bool Run() {
                    ModInt<q> x <- ModInt<q>;
                    return x == x;
                }
            }
            """)

    def test_uniq_sample_from_finite_type(self) -> None:
        _check_game("""
            Game G(Int n) {
                Set<BitString<n>> seen;
                Bool Run() {
                    BitString<n> r <-uniq[seen] BitString<n>;
                    return r == r;
                }
            }
            """)


class TestUnsamplableDomains:
    def test_int_is_not_samplable(self) -> None:
        _check_game_fails("""
            Game G() {
                Bool Run() {
                    Int n <- Int;
                    return n == 0;
                }
            }
            """)

    def test_int_is_not_samplable_with_uniq(self) -> None:
        _check_game_fails("""
            Game G() {
                Set<Int> seen;
                Bool Run() {
                    Int n <-uniq[seen] Int;
                    return n == 0;
                }
            }
            """)

    def test_int_is_not_samplable_with_exclusion(self) -> None:
        """The one-shot ``x <- T \\ E`` form is checked too."""
        _check_game_fails("""
            Game G() {
                Set<Int> seen;
                Bool Run() {
                    Int n <- Int \\ seen;
                    return n == 0;
                }
            }
            """)

    def test_optional_bool_is_not_samplable(self) -> None:
        _check_game_fails("""
            Game G() {
                Bool Run() {
                    Bool? b <- Bool?;
                    return b == None;
                }
            }
            """)

    def test_optional_bit_string_is_not_samplable(self) -> None:
        _check_game_fails("""
            Game G(Int n) {
                Bool Run() {
                    BitString<n>? r <- BitString<n>?;
                    return r == None;
                }
            }
            """)

    def test_optional_is_not_samplable_with_uniq(self) -> None:
        _check_game_fails("""
            Game G(Int n) {
                Set<BitString<n>?> seen;
                Bool Run() {
                    BitString<n>? r <-uniq[seen] BitString<n>?;
                    return r == None;
                }
            }
            """)
