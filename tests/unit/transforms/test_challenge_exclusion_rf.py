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


# --------------------------------------------------------------------------
# RC3 determinism / purity guards (verdict vectors a, c, d).
# --------------------------------------------------------------------------


def _fired(source: str) -> bool:
    """True if the pass rewrote the Initialize RF call (single pass)."""
    game = frog_parser.parse_game(source)
    return ChallengeExclusionRFToUniformTransformer().transform(game) != game


def test_known_function_not_simplified() -> None:
    """Vector (a): a function field bound by ``H = F`` (a known / standard-
    model function) is NOT a sampled random function, so ``H(cf)`` is a fixed
    value and must NOT be rewritten to a uniform sample."""
    source = """
    Game G(Int n, Function<BitString<n>, BitString<n>> F) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {
            H = F;
            cf <- BitString<n>;
            field = H(cf);
            return cf;
        }
        BitString<n>? Query(BitString<n> param) {
            if (param == cf) {
                return None;
            }
            return H(param);
        }
    }
    """
    assert not _fired(source)


def test_sampled_function_positive_control_fires() -> None:
    """Positive control for vector (a): an otherwise identical game whose
    function is genuinely SAMPLED (``H <- Function<...>``) still fires."""
    source = """
    Game G(Int n) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            field = H(cf);
            return cf;
        }
        BitString<n>? Query(BitString<n> param) {
            if (param == cf) {
                return None;
            }
            return H(param);
        }
    }
    """
    assert _fired(source)


def test_aliased_rf_call_not_simplified() -> None:
    """Vector (c): an RF reachable only through a local alias ``G = H`` is
    invisible to the by-name call-site scan, so the rewrite must decline."""
    source = """
    Game G(Int n) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            field = H(cf);
            return cf;
        }
        BitString<n> Query(BitString<n> param) {
            Function<BitString<n>, BitString<n>> Galias = H;
            return Galias(param);
        }
    }
    """
    assert not _fired(source)


def test_embedded_second_init_call_not_simplified() -> None:
    """Vector (d): a second RF evaluation embedded in a larger Initialize
    expression (``leak = H(cf) || cf;``) would survive the rewrite and stay
    correlated with the sampled field, so the pass must decline."""
    source = """
    Game G(Int n) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<2 * n> leak;
        BitString<n> Initialize() {
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            field = H(cf);
            leak = H(cf) || cf;
            return cf;
        }
        BitString<n>? Query(BitString<n> param) {
            if (param == cf) {
                return None;
            }
            return H(param);
        }
    }
    """
    assert not _fired(source)


def test_challenge_field_mutation_not_simplified() -> None:
    """Vector F-013: a `Mutate(v){ cf = v; }` oracle reassigns the challenge
    field, so the exclusion guard later protects a different value and H(cf)
    becomes observable; the pass must decline."""
    source = """
    Game G(Int n) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            field = H(cf);
            return cf;
        }
        Void Mutate(BitString<n> v) {
            cf = v;
        }
        BitString<n>? Query(BitString<n> param) {
            if (param == cf) {
                return None;
            }
            return H(param);
        }
    }
    """
    assert not _fired(source)


def test_guard_var_reassigned_to_challenge_not_simplified() -> None:
    """Vector F-014: reassigning the guard variable to the challenge after the
    guard (`param = cf; return H(param);`) re-queries the excluded point; the
    pass must decline."""
    source = """
    Game G(Int n) {
        Function<BitString<n>, BitString<n>> H;
        BitString<n> cf;
        BitString<n> field;
        BitString<n> Initialize() {
            H <- Function<BitString<n>, BitString<n>>;
            cf <- BitString<n>;
            field = H(cf);
            return cf;
        }
        BitString<n>? Query(BitString<n> param) {
            if (param == cf) {
                return None;
            }
            param = cf;
            return H(param);
        }
    }
    """
    assert not _fired(source)
