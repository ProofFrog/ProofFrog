import pytest
from proof_frog import frog_parser
from proof_frog.transforms.random_functions import (
    ChallengeExclusionRFToUniformTransformer,
)


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = ChallengeExclusionRFToUniformTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # 1. Basic: RF called in Initialize with field arg, oracle calls RF
        #    with local arg behind guard -> Initialize call replaced
        (
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result = RF(ct_star);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    if (ct == ct_star) {
                        return 0;
                    }
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result <- BitString<16>;
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    if (ct == ct_star) {
                        return 0;
                    }
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
        ),
        # 2. Tuple + concatenation args: RF called with [a, field1 || field2]
        #    in Init, [b, v1 || v2] in oracle behind tuple guard
        (
            """
            Game Test() {
                BitString<8> field1;
                BitString<8> field2;
                Function<[BitString<8>, BitString<16>], BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<[BitString<8>, BitString<16>], BitString<16>>;
                    field1 = 1;
                    field2 = 2;
                    BitString<16> result = RF([field1, field1 || field2]);
                    return result;
                }
                BitString<16> Query(BitString<8> v1, BitString<8> v2) {
                    if ([v1, v2] == [field1, field2]) {
                        return 0;
                    }
                    BitString<16> result = RF([v1, v1 || v2]);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> field1;
                BitString<8> field2;
                Function<[BitString<8>, BitString<16>], BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<[BitString<8>, BitString<16>], BitString<16>>;
                    field1 = 1;
                    field2 = 2;
                    BitString<16> result <- BitString<16>;
                    return result;
                }
                BitString<16> Query(BitString<8> v1, BitString<8> v2) {
                    if ([v1, v2] == [field1, field2]) {
                        return 0;
                    }
                    BitString<16> result = RF([v1, v1 || v2]);
                    return result;
                }
            }
            """,
        ),
        # 3. No guard: RF called in Init and oracle without guard -> NOT replaced
        (
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result = RF(ct_star);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result = RF(ct_star);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
        ),
        # 4. RF call BEFORE guard in oracle -> NOT replaced
        (
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result = RF(ct_star);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    BitString<16> early = RF(ct);
                    if (ct == ct_star) {
                        return 0;
                    }
                    return early;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> ct_star;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    BitString<16> result = RF(ct_star);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    BitString<16> early = RF(ct);
                    if (ct == ct_star) {
                        return 0;
                    }
                    return early;
                }
            }
            """,
        ),
        # 5. No challenge field overlap: Init RF arg doesn't contain any
        #    challenge fields -> NOT replaced
        (
            """
            Game Test() {
                BitString<8> ct_star;
                BitString<8> other_field;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    other_field = 99;
                    BitString<16> result = RF(other_field);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    if (ct == ct_star) {
                        return 0;
                    }
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> ct_star;
                BitString<8> other_field;
                Function<BitString<8>, BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<BitString<8>, BitString<16>>;
                    ct_star = 42;
                    other_field = 99;
                    BitString<16> result = RF(other_field);
                    return result;
                }
                BitString<16> Query(BitString<8> ct) {
                    if (ct == ct_star) {
                        return 0;
                    }
                    BitString<16> result = RF(ct);
                    return result;
                }
            }
            """,
        ),
        # 6. Swapped argument positions: oracle RF arg has guard variables
        #    at different positions than the guard comparison -> NOT replaced
        (
            """
            Game Test() {
                BitString<8> field_A;
                BitString<8> field_B;
                Function<[BitString<8>, BitString<8>], BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<[BitString<8>, BitString<8>], BitString<16>>;
                    field_A = 1;
                    field_B = 2;
                    BitString<16> result = RF([field_A, field_B]);
                    return result;
                }
                BitString<16> Query(BitString<8> v1, BitString<8> v2) {
                    if (v1 == field_A) {
                        return 0;
                    }
                    BitString<16> result = RF([v2, v1]);
                    return result;
                }
            }
            """,
            """
            Game Test() {
                BitString<8> field_A;
                BitString<8> field_B;
                Function<[BitString<8>, BitString<8>], BitString<16>> RF;
                BitString<16> Initialize() {
                    RF <- Function<[BitString<8>, BitString<8>], BitString<16>>;
                    field_A = 1;
                    field_B = 2;
                    BitString<16> result = RF([field_A, field_B]);
                    return result;
                }
                BitString<16> Query(BitString<8> v1, BitString<8> v2) {
                    if (v1 == field_A) {
                        return 0;
                    }
                    BitString<16> result = RF([v2, v1]);
                    return result;
                }
            }
            """,
        ),
    ],
)
def test_challenge_exclusion_rf(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


def test_rf_call_inside_guard_block_not_replaced() -> None:
    """If the guard block (return-early branch) contains an RF call before
    returning, the Init RF call should NOT be replaced with a uniform sample.

    The guard fires when ct == ct_star, and the RF call inside uses ct
    (== ct_star), so the RF input matches the Initialize RF input.
    Replacing the Init call with a uniform sample would break RF consistency.
    """
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result = RF(ct_star);
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                BitString<16> leaked = RF(ct);
                return leaked;
            }
            BitString<16> result = RF(ct);
            return result;
        }
    }
    """
    game = frog_parser.parse_game(source)
    result = ChallengeExclusionRFToUniformTransformer().transform(game)
    assert (
        result == game
    ), "Init RF call should not be replaced when guard block contains RF call"
