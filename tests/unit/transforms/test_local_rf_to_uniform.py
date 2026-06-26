"""Tests for the LocalRFToUniform transform pass."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.random_functions import (
    LocalRFToUniform,
    LocalRFToUniformTransformer,
)
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


@pytest.mark.parametrize(
    "method,expected",
    [
        # F-026: a bare-variable copy of the RF value (`RF2 = RF`) is a second
        # reference that lets the function escape and be evaluated again. The
        # single-evaluation rewrite must DECLINE (expected == input), or the
        # two evaluations `RF(0)` and `RF2(0)` -- equal in the input -- would be
        # made independent.
        (
            """
            [BitString<16>, BitString<16>] f() {
                Function<BitString<8>, BitString<16>> RF <- Function<BitString<8>, BitString<16>>;
                Function<BitString<8>, BitString<16>> RF2 = RF;
                BitString<16> a = RF(0^8);
                BitString<16> b = RF2(0^8);
                return [a, b];
            }
            """,
            """
            [BitString<16>, BitString<16>] f() {
                Function<BitString<8>, BitString<16>> RF <- Function<BitString<8>, BitString<16>>;
                Function<BitString<8>, BitString<16>> RF2 = RF;
                BitString<16> a = RF(0^8);
                BitString<16> b = RF2(0^8);
                return [a, b];
            }
            """,
        ),
        # F-026: the RF value passed as a method argument is likewise a
        # non-call reference that must block the rewrite.
        (
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = RF(x);
                use(RF);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF <- Function<BitString<8>, BitString<16>>;
                BitString<16> z = RF(x);
                use(RF);
                return z;
            }
            """,
        ),
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


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_extract_temp_avoids_parameter_capture() -> None:
    # F-027: the embedded-call extraction mints a temp __rf_extract_N__.
    # Here a method PARAMETER is already named __rf_extract_0__.  Without a
    # fresh-name discipline the minted temp would shadow and discard the
    # parameter, turning the input-dependent output (uniform + p) into the
    # constant 0^lambda (u + u under XOR).  The mint must avoid the param.
    game = frog_parser.parse_game("""
        Game Capture(Int lambda) {
            BitString<lambda> Challenge(BitString<lambda> __rf_extract_0__) {
                Function<BitString<lambda>, BitString<lambda>> RF <- Function<BitString<lambda>, BitString<lambda>>;
                return RF(0^lambda) + __rf_extract_0__;
            }
        }
        """)
    out = LocalRFToUniform().apply(game, _ctx())
    method = next(m for m in out.methods if m.signature.name == "Challenge")

    # The parameter is untouched.
    assert method.signature.parameters[0].name == "__rf_extract_0__"

    # The minted sample must use a name distinct from the parameter.
    minted_samples = [
        stmt
        for stmt in method.block.statements
        if isinstance(stmt, frog_ast.Sample)
        and isinstance(stmt.var, frog_ast.Variable)
        and stmt.var.name.startswith("__rf_extract_")
    ]
    assert minted_samples, "expected the single RF call to become a uniform sample"
    for stmt in minted_samples:
        assert isinstance(stmt.var, frog_ast.Variable)
        assert stmt.var.name != "__rf_extract_0__"

    # The return still adds the (preserved) parameter, so output depends on it.
    ret = method.block.statements[-1]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert "__rf_extract_0__" in str(ret.expression)
