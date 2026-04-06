"""Tests for the LocalRFToUniform transform pass."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.random_functions import LocalRFToUniformTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: local RF sampled then called once -> uniform sample
        (
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z <- BitString<16>;
                return z;
            }
            """,
        ),
        # RF call inside a branch: still replaced (one syntactic call)
        (
            """
            BitString<16> f(BitString<8> x, Int count) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                if (count == 1) {
                    BitString<16> z = RF(x);
                    return z;
                } else {
                    BitString<16> r <- BitString<16>;
                    return r;
                }
            }
            """,
            """
            BitString<16> f(BitString<8> x, Int count) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                if (count == 1) {
                    BitString<16> z <- BitString<16>;
                    return z;
                } else {
                    BitString<16> r <- BitString<16>;
                    return r;
                }
            }
            """,
        ),
        # RF called twice: should NOT simplify
        (
            """
            [BitString<16>, BitString<16>] f(BitString<8> x, BitString<8> y) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z1 = RF(x);
                BitString<16> z2 = RF(y);
                return [z1, z2];
            }
            """,
            """
            [BitString<16>, BitString<16>] f(BitString<8> x, BitString<8> y) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z1 = RF(x);
                BitString<16> z2 = RF(y);
                return [z1, z2];
            }
            """,
        ),
        # RF used in non-call context (RF.domain): should NOT simplify
        (
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
        ),
        # RF call inside a for loop: should NOT simplify (multiple dynamic calls)
        (
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = RF(x);
                for (Int i = 0 to 5) {
                    z = RF(x);
                }
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = RF(x);
                for (Int i = 0 to 5) {
                    z = RF(x);
                }
                return z;
            }
            """,
        ),
    ],
)
def test_local_rf_to_uniform(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = method_ast
    while True:
        new_ast = LocalRFToUniformTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
