import pytest
from sympy import Symbol
from proof_frog import frog_parser
from proof_frog.transforms.sampling import SplitUniformSampleTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic split: two slices covering the full range
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # Three-way split
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                BitString<lambda> c = z[2 * lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> z_2 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                BitString<lambda> c = z_2;
            }
            """,
        ),
        # Different sized slices
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<2 * lambda> z_1 <- BitString<2 * lambda>;
                BitString<lambda> a = z_0;
                BitString<2 * lambda> b = z_1;
            }
            """,
        ),
        # Partial split: slices don't cover the full range (gaps allowed)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # No split: variable used in non-slice context
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z;
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z;
            }
            """,
        ),
        # Slices used directly in return
        (
            """
            BitString<2 * lambda> f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                return a || b;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                return a || b;
            }
            """,
        ),
        # Duplicate slices: same bounds are deduplicated and split
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[0 : lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_0;
            }
            """,
        ),
        # No split: truly overlapping slices (different bounds that overlap)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<2 * lambda> a = z[0 : 2 * lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<2 * lambda> a = z[0 : 2 * lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
        ),
        # Partial split: gap at the start (only use tail of sample)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[lambda : 2 * lambda];
                BitString<lambda> b = z[2 * lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # No split: non-uniform sample (type != sampled_from)
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
        ),
        # Slice used directly in an expression (not just assignment)
        (
            """
            BitString<lambda> f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                return z[lambda : 2 * lambda];
            }
            """,
            """
            BitString<lambda> f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                return z_1;
            }
            """,
        ),
        # Partial split: single slice (only one part used)
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> a = z_0;
            }
            """,
        ),
        # Coexisting slice of an UNRELATED variable: the _SliceReplacer must
        # leave non-target slices unchanged. Previously transform_slice
        # returned None for non-matching slices, which the Transformer's
        # specific-method dispatch propagated as the new value, corrupting
        # the AST (None ended up where the unrelated Slice should be).
        (
            """
            BitString<lambda> f(BitString<2 * lambda> w) {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                return w[0 : lambda] || a || b;
            }
            """,
            """
            BitString<lambda> f(BitString<2 * lambda> w) {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                return w[0 : lambda] || a || b;
            }
            """,
        ),
    ],
)
def test_split_uniform_samples(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SplitUniformSampleTransformer(
        {"lambda": Symbol("lambda")}
    ).transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
