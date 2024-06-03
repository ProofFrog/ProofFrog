import pytest
from sympy import Symbol
from proof_frog import visitors, frog_parser


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

    transformed_ast = visitors.SimplifySpliceTransformer(
        {"lambda": Symbol("lambda")}
    ).transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
