import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import ForwardExpressionAliasTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Core case: array access alias is reused
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v1[0];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v3;
            }
            """,
        ),
        # Multiple duplicates replaced one at a time (recursive)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                Int a = v1[0];
                return a + v1[0];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                Int a = v3;
                return a + v3;
            }
            """,
        ),
        # Should NOT transform: expr contains a function call
        (
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """,
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """,
        ),
        # Should NOT transform: free variable in expr is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v1[0];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v1[0];
            }
            """,
        ),
        # Should NOT transform: alias variable is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3 + v1[0];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3 + v1[0];
            }
            """,
        ),
        # Should NOT transform: plain variable copy (handled by RedundantCopy)
        (
            """
            Int f(Int a) {
                Int b = a;
                return b + a;
            }
            """,
            """
            Int f(Int a) {
                Int b = a;
                return b + a;
            }
            """,
        ),
        # Binary operation alias
        (
            """
            Int f(Int a, Int b) {
                Int c = a + b;
                return c * (a + b);
            }
            """,
            """
            Int f(Int a, Int b) {
                Int c = a + b;
                return c * c;
            }
            """,
        ),
        # No duplicate exists — no change
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v1[1];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v1[1];
            }
            """,
        ),
        # Duplicate inside nested expression (function call argument)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return G.evaluate(v1[0]);
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return G.evaluate(v3);
            }
            """,
        ),
    ],
)
def test_forward_expression_alias(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = ForwardExpressionAliasTransformer().transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
