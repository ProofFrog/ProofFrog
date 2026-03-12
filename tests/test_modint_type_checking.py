"""Tests for ModInt<q> type checking (Phase 4 semantic analysis)."""

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_game(source: str) -> None:
    """Parse a game string and run CheckTypeVisitor on it."""
    game = frog_parser.parse_game(source)
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.visit(game)


def _check_game_fails(source: str) -> None:
    """Assert that type-checking a game raises FailedTypeCheck."""
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


class TestModIntSampling:
    def test_uniform_sampling(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> r <- ModInt<q>;
                }
            }
            """
        )

    def test_sampling_result_usable(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test() {
                    ModInt<q> r <- ModInt<q>;
                    return r;
                }
            }
            """
        )


# ---------------------------------------------------------------------------
# Integer literal promotion
# ---------------------------------------------------------------------------


class TestModIntLiteralPromotion:
    def test_zero_assignment(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> x = 0;
                }
            }
            """
        )

    def test_one_assignment(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> x = 1;
                }
            }
            """
        )

    def test_literal_return(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test() {
                    return 0;
                }
            }
            """
        )


# ---------------------------------------------------------------------------
# Arithmetic operators
# ---------------------------------------------------------------------------


class TestModIntAddition:
    def test_add_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a, ModInt<q> b) {
                    return a + b;
                }
            }
            """
        )

    def test_add_result_type(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> a <- ModInt<q>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<q> c = a + b;
                }
            }
            """
        )

    def test_add_mismatched_modulus_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int p, Int q) {
                Void Initialize() {
                    ModInt<p> a <- ModInt<p>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<p> c = a + b;
                }
            }
            """
        )

    def test_add_modint_and_int_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> a <- ModInt<q>;
                    Int n = 5;
                    ModInt<q> c = a + n;
                }
            }
            """
        )


class TestModIntSubtraction:
    def test_subtract_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a, ModInt<q> b) {
                    return a - b;
                }
            }
            """
        )

    def test_subtract_result_is_modint(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> a <- ModInt<q>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<q> c = a - b;
                }
            }
            """
        )

    def test_subtract_mismatched_modulus_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int p, Int q) {
                Void Initialize() {
                    ModInt<p> a <- ModInt<p>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<p> c = a - b;
                }
            }
            """
        )

    def test_int_subtract_still_works(self) -> None:
        _check_game(
            """
            Game G() {
                Int Test(Int a, Int b) {
                    return a - b;
                }
            }
            """
        )


class TestModIntMultiplication:
    def test_multiply_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a, ModInt<q> b) {
                    return a * b;
                }
            }
            """
        )

    def test_multiply_result_is_modint(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> a <- ModInt<q>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<q> c = a * b;
                }
            }
            """
        )

    def test_multiply_mismatched_modulus_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int p, Int q) {
                Void Initialize() {
                    ModInt<p> a <- ModInt<p>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<p> c = a * b;
                }
            }
            """
        )


class TestModIntDivision:
    def test_divide_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a, ModInt<q> b) {
                    return a / b;
                }
            }
            """
        )

    def test_divide_mismatched_modulus_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int p, Int q) {
                Void Initialize() {
                    ModInt<p> a <- ModInt<p>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<p> c = a / b;
                }
            }
            """
        )


class TestModIntExponentiation:
    def test_exp_modint_base_int_exponent(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> base, Int exp) {
                    return base ^ exp;
                }
            }
            """
        )

    def test_exp_result_is_modint(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> g <- ModInt<q>;
                    ModInt<q> h = g ^ 3;
                }
            }
            """
        )

    def test_exp_negative_one_inverse(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a) {
                    return a ^ (-1);
                }
            }
            """
        )

    def test_exp_modint_modint_exponent_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int q) {
                Void Initialize() {
                    ModInt<q> a <- ModInt<q>;
                    ModInt<q> b <- ModInt<q>;
                    ModInt<q> c = a ^ b;
                }
            }
            """
        )


# ---------------------------------------------------------------------------
# Unary negation
# ---------------------------------------------------------------------------


class TestModIntNegation:
    def test_negate_modint(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                ModInt<q> Test(ModInt<q> a) {
                    return -a;
                }
            }
            """
        )

    def test_negate_int_still_works(self) -> None:
        _check_game(
            """
            Game G() {
                Int Test(Int a) {
                    return -a;
                }
            }
            """
        )

    def test_negate_bitstring_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int n) {
                Void Initialize() {
                    BitString<n> b <- BitString<n>;
                    BitString<n> c = -b;
                }
            }
            """
        )


# ---------------------------------------------------------------------------
# Equality / inequality
# ---------------------------------------------------------------------------


class TestModIntComparison:
    def test_equals_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Bool Test(ModInt<q> a, ModInt<q> b) {
                    return a == b;
                }
            }
            """
        )

    def test_notequals_same_modulus(self) -> None:
        _check_game(
            """
            Game G(Int q) {
                Bool Test(ModInt<q> a, ModInt<q> b) {
                    return a != b;
                }
            }
            """
        )

    def test_equals_mismatched_modulus_fails(self) -> None:
        _check_game_fails(
            """
            Game G(Int p, Int q) {
                Bool Test(ModInt<p> a, ModInt<q> b) {
                    return a == b;
                }
            }
            """
        )
