import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import RedundantCopyTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Simple substitution
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Shouldn't be transformed (both variables used)
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = a + 1;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = a + 1;
                return b;
            }
            """,
        ),
        # Douglas' test case
        (
            """
            BitString<lambda + stretch> Eval(BitString<lambda> k, BitString<lambda + stretch> m) { 
                BitString<lambda + stretch> v1 = G.evaluate(k);
                BitString<lambda + stretch> v2 = v1;
                BitString<lambda + stretch> v3 = v2 + m;
                return v1 + v3;
            }
            """,
            """
            BitString<lambda + stretch> Eval(BitString<lambda> k, BitString<lambda + stretch> m) { 
                BitString<lambda + stretch> v1 = G.evaluate(k);
                BitString<lambda + stretch> v3 = v1 + m;
                return v1 + v3;
            }
            """,
        ),
        # Many chained together
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                Int c = b;
                Int d = c;
                Int e = d;
                Int f = e;
                return f;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Works in if-statements too
        (
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    Int b = a;
                    x = b;
                } else {
                    Int a = 2;
                    Int b = a;
                    x = b;
                }
            }
            """,
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    x = a;
                } else {
                    Int a = 2;
                    x = a;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a = a + 1;
                }
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a = a + 1;
                }
                return b;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                if (True) {
                    Int b = a;
                    b = b + 1;
                }
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                if (True) {
                    Int b = a;
                    b = b + 1;
                }
                return a;
            }
            """,
        ),
        # F-179 positive: an array copy with no mutation still folds.
        (
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                return v[0];
            }
            """,
            """
            Int f(Array<Int, 2> w) {
                return w[0];
            }
            """,
        ),
        # F-179 decline: an element write to the original (`w[0] = 2`, an
        # ArrayAccess l-value) after the copy `v = w` must block the
        # substitution -- otherwise `return v[0]` would read post-mutation
        # state. The scan now peels the l-value via `lvalue_base_name`.
        (
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = 2;
                return v[0];
            }
            """,
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = 2;
                return v[0];
            }
            """,
        ),
    ],
)
def test_redundant_copies(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = RedundantCopyTransformer().transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
