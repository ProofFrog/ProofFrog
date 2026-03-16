import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineMultiUsePureExpressionTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Expression with ArrayAccess is NOT inlined (contains indexing)
        (
            """
            Int f([Int, Int] v1, [Int, Int] v2) {
                Int v3 = v1[0] + v2[0];
                return v3 + v3;
            }
            """,
            """
            Int f([Int, Int] v1, [Int, Int] v2) {
                Int v3 = v1[0] + v2[0];
                return v3 + v3;
            }
            """,
        ),
        # Pure expression without ArrayAccess IS inlined
        (
            """
            Int f(Int a, Int b) {
                Int v3 = a + b;
                return v3 + v3;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a + b + (a + b);
            }
            """,
        ),
        # Should NOT inline: expression contains function call
        (
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + v;
            }
            """,
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + v;
            }
            """,
        ),
        # Should NOT inline: free variable is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v3;
            }
            """,
        ),
        # Should NOT inline: alias variable is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3;
            }
            """,
        ),
        # Should NOT inline: plain variable (handled by RedundantCopy)
        (
            """
            Int f(Int a) {
                Int b = a;
                return b + b;
            }
            """,
            """
            Int f(Int a) {
                Int b = a;
                return b + b;
            }
            """,
        ),
        # Array access: v3 = v1[0] is NOT inlined (contains ArrayAccess)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                Int a = v3 + v3;
                return a + v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v3 + v3;
            }
            """,
        ),
        # Variable not used — no change (other passes clean up)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return 42;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return 42;
            }
            """,
        ),
    ],
)
def test_inline_multi_use_pure(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = InlineMultiUsePureExpressionTransformer().transform(game_ast)
    assert expected_ast == transformed_ast
