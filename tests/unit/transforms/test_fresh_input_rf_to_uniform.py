"""Tests for the FreshInputRFToUniform transform pass.

The transform replaces RF(v) with a uniform sample when v is a <-uniq
sampled variable used only in that one RF call.  It must NOT fire on
plain uniform samples (<-).
"""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.random_functions import _FreshInputRFTransformer

_RF_TYPES: dict[str, frog_ast.FunctionType] = {
    "H": frog_ast.FunctionType(
        frog_ast.BitStringType(frog_ast.Integer(8)),
        frog_ast.BitStringType(frog_ast.Integer(16)),
    ),
}


def _run(method_str: str) -> frog_ast.Method:
    ast = frog_parser.parse_method(method_str)
    while True:
        new_ast = _FreshInputRFTransformer(_RF_TYPES).transform(ast)
        if new_ast == ast:
            return ast
        ast = new_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: <-uniq input, single use in RF call -> replaced with uniform
        (
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<8> v <-uniq[S] BitString<8>;
                BitString<16> z = H(v);
                return z;
            }
            """,
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<16> __fresh_rf_v__ <- BitString<16>;
                BitString<16> z = __fresh_rf_v__;
                return z;
            }
            """,
        ),
        # Plain uniform sample (<-): must NOT fire
        (
            """
            BitString<16> f() {
                BitString<8> v <- BitString<8>;
                BitString<16> z = H(v);
                return z;
            }
            """,
            """
            BitString<16> f() {
                BitString<8> v <- BitString<8>;
                BitString<16> z = H(v);
                return z;
            }
            """,
        ),
        # Variable used more than once: must NOT fire
        (
            """
            [BitString<8>, BitString<16>] f(Set<BitString<8>> S) {
                BitString<8> v <-uniq[S] BitString<8>;
                BitString<16> z = H(v);
                return [v, z];
            }
            """,
            """
            [BitString<8>, BitString<16>] f(Set<BitString<8>> S) {
                BitString<8> v <-uniq[S] BitString<8>;
                BitString<16> z = H(v);
                return [v, z];
            }
            """,
        ),
        # RF call inside a loop: must NOT fire
        (
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<16> z;
                for (Int i = 0 to 3) {
                    BitString<8> v <-uniq[S] BitString<8>;
                    z = H(v);
                }
                return z;
            }
            """,
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<16> z;
                for (Int i = 0 to 3) {
                    BitString<8> v <-uniq[S] BitString<8>;
                    z = H(v);
                }
                return z;
            }
            """,
        ),
        # Non-RF function call (G is not in rf_types): must NOT fire
        (
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<8> v <-uniq[S] BitString<8>;
                BitString<16> z = G(v);
                return z;
            }
            """,
            """
            BitString<16> f(Set<BitString<8>> S) {
                BitString<8> v <-uniq[S] BitString<8>;
                BitString<16> z = G(v);
                return z;
            }
            """,
        ),
        # RF sample (Function type): must NOT fire (handled by LocalRFToUniform)
        (
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = H(RF);
                return z;
            }
            """,
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = H(RF);
                return z;
            }
            """,
        ),
    ],
)
def test_fresh_input_rf_to_uniform(method: str, expected: str) -> None:
    transformed = _run(method)
    expected_ast = frog_parser.parse_method(expected)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed)
    assert expected_ast == transformed
