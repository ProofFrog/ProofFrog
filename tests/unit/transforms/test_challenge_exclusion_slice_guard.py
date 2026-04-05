"""Tests for the slice guard extension of ChallengeExclusionRFToUniform."""

import pytest
from proof_frog import frog_parser, frog_ast
from proof_frog.transforms._base import NearMiss, PipelineContext
from proof_frog.transforms.random_functions import (
    ChallengeExclusionRFToUniformTransformer,
    ChallengeExclusionRFToUniform,
    _find_challenge_guard,
    _slice_guard_excludes,
    _GuardInfo,
)
from proof_frog.visitors import NameTypeMap


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = ChallengeExclusionRFToUniformTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


def _transform_unchanged(source: str) -> None:
    game = frog_parser.parse_game(source)
    result = ChallengeExclusionRFToUniformTransformer().transform(game)
    assert result == game, f"\nExpected unchanged but got:\n{result}"


# -----------------------------------------------------------------------
# _find_challenge_guard: slice guard detection
# -----------------------------------------------------------------------


class TestFindChallengeGuardSlice:
    """Test detection of slice guard patterns."""

    def test_detects_slice_guard(self):
        """Detect if (m[start:end] == field) { return ...; }."""
        game = frog_parser.parse_game(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> r = RF(challengeField || challengeField || challengeField);
                    return r;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """
        )
        field_names = [f.name for f in game.fields]
        oracle = [m for m in game.methods if m.signature.name == "Oracle"][0]
        result = _find_challenge_guard(oracle, field_names)
        assert result is not None
        assert result.is_slice_guard
        assert result.slice_param == "m"
        assert result.challenge_fields == {"challengeField"}

    def test_direct_guard_not_slice(self):
        """Direct param == field guard is NOT a slice guard."""
        game = frog_parser.parse_game(
            """
            Game Test() {
                BitString<8> ct_star;
                RandomFunctions<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> r = RF(ct_star);
                    return r;
                }
                BitString<16> Query(BitString<8> ct) {
                    if (ct == ct_star) {
                        return 0;
                    }
                    BitString<16> r = RF(ct);
                    return r;
                }
            }
            """
        )
        field_names = [f.name for f in game.fields]
        query = [m for m in game.methods if m.signature.name == "Query"][0]
        result = _find_challenge_guard(query, field_names)
        assert result is not None
        assert not result.is_slice_guard

    def test_slice_guard_with_sample_then_return(self):
        """Slice guard with sample-then-return body is accepted."""
        game = frog_parser.parse_game(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> r = RF(challengeField || challengeField || challengeField);
                    return r;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        BitString<8> r <- BitString<8>;
                        return r;
                    }
                    return RF(m);
                }
            }
            """
        )
        field_names = [f.name for f in game.fields]
        oracle = [m for m in game.methods if m.signature.name == "Oracle"][0]
        result = _find_challenge_guard(oracle, field_names)
        assert result is not None
        assert result.is_slice_guard


# -----------------------------------------------------------------------
# Slice guard transform: positive cases
# -----------------------------------------------------------------------


class TestSliceGuardTransformPositive:
    """Transform correctly replaces RF call when slice guard is valid."""

    def test_basic_slice_guard(self):
        """Slice guard on middle leaf of concatenation enables replacement."""
        _transform_and_compare(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """,
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result <- BitString<8>;
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """,
        )

    def test_slice_guard_first_leaf(self):
        """Slice guard covering the first leaf works."""
        _transform_and_compare(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<8>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<8> m) {
                    if (m[0 : 4] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """,
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<8>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<8>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result <- BitString<8>;
                    return result;
                }
                BitString<8> Oracle(BitString<8> m) {
                    if (m[0 : 4] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """,
        )

    def test_slice_guard_with_sample_abort(self):
        """Slice guard with sample-then-return abort body works."""
        _transform_and_compare(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        BitString<8> r <- BitString<8>;
                        return r;
                    }
                    return RF(m);
                }
            }
            """,
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result <- BitString<8>;
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        BitString<8> r <- BitString<8>;
                        return r;
                    }
                    return RF(m);
                }
            }
            """,
        )

    def test_mixed_direct_and_slice_guards(self):
        """One oracle with direct guard, another with slice guard."""
        _transform_and_compare(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Hash(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
                BitString<8> Decaps(BitString<4> ct) {
                    if (ct == challengeField) {
                        return 0;
                    }
                    BitString<8> result = RF(ct || ct || ct);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result <- BitString<8>;
                    return result;
                }
                BitString<8> Hash(BitString<12> m) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
                BitString<8> Decaps(BitString<4> ct) {
                    if (ct == challengeField) {
                        return 0;
                    }
                    BitString<8> result = RF(ct || ct || ct);
                    return result;
                }
            }
            """,
        )


# -----------------------------------------------------------------------
# Slice guard transform: negative cases
# -----------------------------------------------------------------------


class TestSliceGuardTransformNegative:
    """Transform correctly rejects invalid slice guard patterns."""

    def test_slice_misaligned(self):
        """Slice doesn't align with any single leaf -- not replaced."""
        _transform_unchanged(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[2 : 6] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """
        )

    def test_oracle_rf_arg_not_guarded_param(self):
        """Oracle RF arg is not the guarded parameter -- not replaced."""
        _transform_unchanged(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m, BitString<12> other) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(other);
                }
            }
            """
        )

    def test_slice_guard_on_non_challenge_leaf(self):
        """Slice covers a leaf that is NOT the challenge field -- not replaced."""
        _transform_unchanged(
            """
            Game Test() {
                BitString<4> challengeField;
                BitString<4> otherField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    otherField = 1;
                    BitString<8> result = RF(otherField || challengeField || otherField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m) {
                    if (m[0 : 4] == challengeField) {
                        return 0;
                    }
                    return RF(m);
                }
            }
            """
        )


# -----------------------------------------------------------------------
# Near-miss reporting
# -----------------------------------------------------------------------


class TestSliceGuardNearMiss:
    """Near-miss is reported when slice guard is detected but fails."""

    def test_near_miss_on_slice_guard_failure(self):
        """When slice guard is detected but RF arg isn't guarded param."""
        game = frog_parser.parse_game(
            """
            Game Test() {
                BitString<4> challengeField;
                RandomFunctions<BitString<12>, BitString<8>> RF;
                BitString<8> Initialize() {
                    RF <- RandomFunctions<BitString<12>, BitString<8>>;
                    challengeField = 0;
                    BitString<8> result = RF(challengeField || challengeField || challengeField);
                    return result;
                }
                BitString<8> Oracle(BitString<12> m, BitString<12> other) {
                    if (m[4 : 8] == challengeField) {
                        return 0;
                    }
                    return RF(other);
                }
            }
            """
        )
        ctx = PipelineContext(
            variables={},
            proof_let_types=None,  # type: ignore[arg-type]
            proof_namespace={},
            subsets_pairs=[],
        )
        result = ChallengeExclusionRFToUniform().apply(game, ctx)
        # Transform should not fire
        assert result == game
        # Near-miss should be reported
        slice_misses = [
            nm
            for nm in ctx.near_misses
            if nm.transform_name == "Challenge Exclusion RF To Uniform"
            and "Slice guard" in nm.reason
        ]
        assert len(slice_misses) == 1
        assert "Oracle" in slice_misses[0].reason
