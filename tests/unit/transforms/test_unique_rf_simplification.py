"""Tests for the UniqueRFSimplification transform pass."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.random_functions import (
    UniqueRFSimplificationTransformer,
)


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: r dead after RF call -> z <- R, UniqueSample removed
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z <- BitString<16>;
                return z;
            }
            """,
        ),
        # r alive after RF call: DOES simplify (all RF calls are guarded)
        (
            """
            [BitString<8>, BitString<16>] f(BitString<16> m) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return [r, m + z];
            }
            """,
            """
            [BitString<8>, BitString<16>] f(BitString<16> m) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z <- BitString<16>;
                return [r, m + z];
            }
            """,
        ),
        # Plain Set as unique set (not RF.domain): DOES simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                Set<BitString<8>> Q;
                BitString<8> r <-uniq[Q] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                Set<BitString<8>> Q;
                BitString<8> r <-uniq[Q] BitString<8>;
                BitString<16> z <- BitString<16>;
                return z;
            }
            """,
        ),
        # RF1.domain guarding RF2 call: should NOT simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF1;
                RandomFunctions<BitString<8>, BitString<16>> RF2;
                RF1 <- RandomFunctions<BitString<8>, BitString<16>>;
                RF2 <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF1.domain] BitString<8>;
                BitString<16> z = RF2(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF1;
                RandomFunctions<BitString<8>, BitString<16>> RF2;
                RF1 <- RandomFunctions<BitString<8>, BitString<16>>;
                RF2 <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF1.domain] BitString<8>;
                BitString<16> z = RF2(r);
                return z;
            }
            """,
        ),
        # Sampled var doesn't match RF arg: should NOT simplify
        (
            """
            BitString<16> f(BitString<8> x) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
        ),
        # Not uniquely sampled (plain sample): should NOT simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <- BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <- BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
        ),
    ],
)
def test_unique_rf_simplification(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = method_ast
    while True:
        new_ast = UniqueRFSimplificationTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
