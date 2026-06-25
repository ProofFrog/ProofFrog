import pytest
from sympy import Symbol
from proof_frog import frog_parser
from proof_frog.transforms.sampling import SimplifySpliceTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Simple substitution
        (
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();

                BitString<2 * lambda> x = a || b;

                BitString<lambda> a2 = x[0 : lambda];
                BitString<lambda> b2 = x[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();

                BitString<2 * lambda> x = a || b;

                BitString<lambda> a2 = a;
                BitString<lambda> b2 = b;
            }
            """,
        ),
        (
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();
                BitString<2 * lambda> x = a || b;
                BitString<lambda> a2 = x[5 : lambda + 5];
            }
            """,
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();
                BitString<2 * lambda> x = a || b;
                BitString<lambda> a2 = x[5 : lambda + 5];
            }
            """,
        ),
        (
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<2 * lambda> b = g();
                BitString<3 * lambda> x = a || b;
                BitString<lambda> a2 = x[0 : lambda];
                BitString<lambda> b2 = x[lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<2 * lambda> b = g();
                BitString<3 * lambda> x = a || b;
                BitString<lambda> a2 = a;
                BitString<lambda> b2 = b;
            }
            """,
        ),
        (
            """
            Void f() {
                BitString<2 * lambda> a = g();
                BitString<(1/2) * lambda> b = g();

                BitString<(5/2) * lambda> x = a || b;

                BitString<2 * lambda> a2 = x[0 : 2*lambda];
                BitString<(1/2) * lambda> b2 = x[2 * lambda : 5*lambda / 2];
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> a = g();
                BitString<(1/2) * lambda> b = g();

                BitString<(5/2) * lambda> x = a || b;

                BitString<2 * lambda> a2 = a;
                BitString<(1/2) * lambda> b2 = b;

            }
            """,
        ),
        (
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();

                BitString<2 * lambda> x = a || b;

                BitString<lambda> a2 = x[0 : lambda];
                BitString<lambda> b2 = x[lambda + 5 : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> a = g();
                BitString<lambda> b = g();

                BitString<2 * lambda> x = a || b;

                BitString<lambda> a2 = a;
                BitString<lambda> b2 = x[lambda + 5 : 2 * lambda];
            }
            """,
        ),
    ],
)
def test_slice_simplification(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SimplifySpliceTransformer({"lambda": Symbol("lambda")}).transform(
        game_ast
    )
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_stale_length_after_redeclaration_not_simplified() -> None:
    """F-067: a component is redeclared with a different bit length before the
    concatenation. The splice must use the length in effect at the concat (the
    LAST declaration), not the first one found in the block. Here `a` is
    redeclared 2*lambda-wide, so `z[lambda : 2*lambda]` is the second half of
    `a`, NOT `b`; the pass must not rewrite it to `b`."""
    method = """
    BitString<lambda> f(BitString<lambda> b) {
        BitString<lambda> a <- BitString<lambda>;
        BitString<2 * lambda> a <- BitString<2 * lambda>;
        BitString<3 * lambda> z = a || b;
        return z[lambda : 2 * lambda];
    }
    """
    game_ast = frog_parser.parse_method(method)
    transformed = SimplifySpliceTransformer({"lambda": Symbol("lambda")}).transform(
        game_ast
    )
    # The slice must NOT be rewritten to `b` (the stale-length bug); with the
    # correct 2*lambda length for `a`, z[lambda:2*lambda] does not align with a
    # component boundary, so the splice is left intact.
    assert "return b;" not in str(transformed), str(transformed)
