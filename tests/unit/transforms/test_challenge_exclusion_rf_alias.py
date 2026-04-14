from proof_frog import frog_parser
from proof_frog.transforms.random_functions import (
    ChallengeExclusionRFToUniformTransformer,
)


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = ChallengeExclusionRFToUniformTransformer().transform(
        game, proof_namespace={}
    )
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


def test_alias_resolution_in_init_rf_args() -> None:
    """RF argument goes through intermediate variables (aliases) like
    bct = ct_star; result = RF(bct).
    The transform should resolve aliases back to the field and still fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<8> alias = ct_star;
            BitString<16> result = RF(alias);
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
    """
    expected = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<8> alias = ct_star;
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
    """
    _transform_and_compare(source, expected)


def test_no_alias_resolution_without_field_ref() -> None:
    """When the alias chain does NOT resolve to a challenge field,
    the transform should not fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        BitString<8> other;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            other = 99;
            BitString<8> alias = other;
            BitString<16> result = RF(alias);
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
    """
    # Should NOT fire: alias resolves to 'other', not 'ct_star'
    game = frog_parser.parse_game(source)
    result = ChallengeExclusionRFToUniformTransformer().transform(
        game, proof_namespace={}
    )
    assert result == game, "Transform should not fire when alias doesn't resolve to challenge field"
