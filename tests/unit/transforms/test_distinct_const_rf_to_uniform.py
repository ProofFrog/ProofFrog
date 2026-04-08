"""Tests for the DistinctConstRFToUniform transform pass."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.random_functions import _DistinctConstRFTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: RF called twice on distinct literal constants -> two fresh samples
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(0b1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                BitString<1> __rf_extract_0__ <- BitString<1>;
                BitString<1> __rf_extract_1__ <- BitString<1>;
                return __rf_extract_0__ || __rf_extract_1__;
            }
            """,
        ),
        # Three distinct constants
        (
            """
            BitString<6> f() {
                Function<BitString<2>, BitString<2>> RF;
                RF <- Function<BitString<2>, BitString<2>>;
                BitString<2> a = RF(0b00);
                BitString<2> b = RF(0b01);
                BitString<2> c = RF(0b10);
                return a || b || c;
            }
            """,
            """
            BitString<6> f() {
                Function<BitString<2>, BitString<2>> RF;
                BitString<2> a <- BitString<2>;
                BitString<2> b <- BitString<2>;
                BitString<2> c <- BitString<2>;
                return a || b || c;
            }
            """,
        ),
        # NOT fired: duplicate constants (same num)
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(0b0);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(0b0);
            }
            """,
        ),
        # NOT fired: non-literal argument (variable)
        (
            """
            BitString<2> f(BitString<1> x) {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(x);
            }
            """,
            """
            BitString<2> f(BitString<1> x) {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(x);
            }
            """,
        ),
        # NOT fired: only one call (handled by LocalRFToUniform instead)
        (
            """
            BitString<1> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0);
            }
            """,
            """
            BitString<1> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0);
            }
            """,
        ),
        # NOT fired: RF also accessed via .domain
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                BitString<1> r <-uniq[RF.domain] BitString<1>;
                return RF(0b0) || RF(0b1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                BitString<1> r <-uniq[RF.domain] BitString<1>;
                return RF(0b0) || RF(0b1);
            }
            """,
        ),
        # Fires: concrete-width BinaryNum domain with distinct literals
        (
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                RF <- Function<BitString<2>, BitString<2>>;
                BitString<2> a = RF(0b01);
                BitString<2> b = RF(0b10);
                return a || b;
            }
            """,
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                BitString<2> a <- BitString<2>;
                BitString<2> b <- BitString<2>;
                return a || b;
            }
            """,
        ),
        # Fires: BitStringLiteral arguments with distinct bit values
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0^1) || RF(1^1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                BitString<1> __rf_extract_0__ <- BitString<1>;
                BitString<1> __rf_extract_1__ <- BitString<1>;
                return __rf_extract_0__ || __rf_extract_1__;
            }
            """,
        ),
        # NOT fired: BitStringLiteral with duplicate (bit, length) keys
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0^1) || RF(0^1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0^1) || RF(0^1);
            }
            """,
        ),
        # NOT fired: 0b0 and 0^1 are the same 1-bit zero, so the keys
        # collide and the transform must refuse (regression against a bug
        # where disjoint keys per literal form would erroneously treat
        # these as distinct inputs).
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(0^1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b0) || RF(0^1);
            }
            """,
        ),
        # NOT fired: 0b1 (1-bit, value 1) and 1^1 (all-ones 1-bit) are
        # the same bitstring, so keys collide.
        (
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b1) || RF(1^1);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                return RF(0b1) || RF(1^1);
            }
            """,
        ),
        # Fires: 0b01 (2-bit, value 1) and 0b10 (2-bit, value 2) are
        # distinct.
        (
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                RF <- Function<BitString<2>, BitString<2>>;
                return RF(0b01) || RF(0b10);
            }
            """,
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                BitString<2> __rf_extract_0__ <- BitString<2>;
                BitString<2> __rf_extract_1__ <- BitString<2>;
                return __rf_extract_0__ || __rf_extract_1__;
            }
            """,
        ),
        # Fires: 0b00 (2-bit, value 0) and 1^2 (all-ones 2-bit, value 3)
        # are distinct across literal forms.
        (
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                RF <- Function<BitString<2>, BitString<2>>;
                return RF(0b00) || RF(1^2);
            }
            """,
            """
            BitString<4> f() {
                Function<BitString<2>, BitString<2>> RF;
                BitString<2> __rf_extract_0__ <- BitString<2>;
                BitString<2> __rf_extract_1__ <- BitString<2>;
                return __rf_extract_0__ || __rf_extract_1__;
            }
            """,
        ),
        # NOT fired: literals have structurally-different length expressions
        # (1-bit BinaryNum vs symbolic-length BitStringLiteral).  The
        # transform refuses conservatively even though the method is
        # presumably typechecked such that the lengths coincide.
        (
            """
            BitString<2> f() {
                Function<BitString<lambda>, BitString<1>> RF;
                RF <- Function<BitString<lambda>, BitString<1>>;
                return RF(0b0) || RF(1^lambda);
            }
            """,
            """
            BitString<2> f() {
                Function<BitString<lambda>, BitString<1>> RF;
                RF <- Function<BitString<lambda>, BitString<1>>;
                return RF(0b0) || RF(1^lambda);
            }
            """,
        ),
        # NOT fired: RF call inside a loop body
        (
            """
            BitString<1> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                BitString<1> z = RF(0b1);
                for (Int i = 0 to 5) {
                    z = RF(0b0);
                }
                return z;
            }
            """,
            """
            BitString<1> f() {
                Function<BitString<1>, BitString<1>> RF;
                RF <- Function<BitString<1>, BitString<1>>;
                BitString<1> z = RF(0b1);
                for (Int i = 0 to 5) {
                    z = RF(0b0);
                }
                return z;
            }
            """,
        ),
    ],
)
def test_distinct_const_rf_to_uniform(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = method_ast
    while True:
        new_ast = _DistinctConstRFTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
