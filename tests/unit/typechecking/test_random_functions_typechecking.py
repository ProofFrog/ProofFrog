"""Tests for RandomFunctions<D, R> and UniqueSample type checking."""

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


class TestRFCallReturnsRangeType:
    def test_rf_call_returns_range_type(self) -> None:
        _check_game(
            """
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                BitString<16> Lookup(BitString<8> x) {
                    BitString<16> z = RF(x);
                    return z;
                }
            }
            """
        )


class TestRFCallWrongArgumentTypeRejected:
    def test_wrong_domain_type(self) -> None:
        _check_game_fails(
            """
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                BitString<16> Lookup(BitString<16> x) {
                    BitString<16> z = RF(x);
                    return z;
                }
            }
            """
        )


class TestRFDomainHasSetType:
    def test_domain_usable_in_set_context(self) -> None:
        _check_game(
            """
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                Bool Lookup(BitString<8> x) {
                    return x in RF.domain;
                }
            }
            """
        )


class TestRFSampleValidInInitialize:
    def test_rf_sample_valid(self) -> None:
        _check_game(
            """
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
            }
            """
        )


class TestUniqueSampleValidWhenSetTypeMatches:
    def test_valid_unique_sample(self) -> None:
        _check_game(
            """
            Game G() {
                Set<BitString<8>> Q;
                Void Initialize() {
                    BitString<8> r <-uniq[Q] BitString<8>;
                }
            }
            """
        )


class TestUniqueSampleRejectsWrongSetType:
    def test_wrong_set_element_type(self) -> None:
        _check_game_fails(
            """
            Game G() {
                Set<BitString<16>> Q;
                Void Initialize() {
                    BitString<8> r <-uniq[Q] BitString<8>;
                }
            }
            """
        )


class TestUniqueSampleRejectsNonSetVariable:
    def test_non_set_type(self) -> None:
        _check_game_fails(
            """
            Game G() {
                BitString<8> Q;
                Void Initialize() {
                    BitString<8> r <-uniq[Q] BitString<8>;
                }
            }
            """
        )


class TestUniqueSampleWithRFDomainValid:
    def test_rf_domain_as_unique_set(self) -> None:
        _check_game(
            """
            Game G() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                Void Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                }
                BitString<16> Lookup(BitString<8> x) {
                    BitString<8> r <-uniq[RF.domain] BitString<8>;
                    BitString<16> z = RF(r);
                    return z;
                }
            }
            """
        )
