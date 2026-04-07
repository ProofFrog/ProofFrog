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
        # Trivial literal aliases (Integer, Boolean, None) are NOT
        # propagated.  Replacing a constant like ``0`` with a named alias is
        # lossy: subsequent passes (e.g. tuple expansion, branch elimination)
        # rely on seeing the constant directly to decide whether to fire.
        # Regression test for the OTDDH=>OTHashedDDH proof that broke when
        # ``count = 0;`` caused later ``triple[0]`` to be rewritten as
        # ``triple[count]``.
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = 0;
                return v1[0];
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = 0;
                return v1[0];
            }
            """,
        ),
        (
            """
            Bool f(Bool x) {
                Bool v3 = false;
                return x || false;
            }
            """,
            """
            Bool f(Bool x) {
                Bool v3 = false;
                return x || false;
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
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "game,expected",
    [
        # Field assignment propagates expression alias to subsequent code
        (
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                [Int, Int] x = challenger.g();
                field1 = x[0];
                Int v = x[0];
            }
        }""",
            """
        Game Test() {
            Int field1;
            Void Initialize() {
                [Int, Int] x = challenger.g();
                field1 = x[0];
                Int v = field1;
            }
        }""",
        ),
        # Field-from-variable copy: field1 = v propagates v -> field1
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = challenger.g();
                field1 = v;
                return v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = challenger.g();
                field1 = v;
                return field1;
            }
        }""",
        ),
        # Should NOT propagate: local is reassigned after field copy
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = 1;
                field1 = v;
                v = 2;
                return v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = 1;
                field1 = v;
                v = 2;
                return v;
            }
        }""",
        ),
        # Should NOT propagate: field is reassigned after copy
        (
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = 1;
                field1 = v;
                field1 = 2;
                return v;
            }
        }""",
            """
        Game Test() {
            Int field1;
            Int Initialize() {
                Int v = 1;
                field1 = v;
                field1 = 2;
                return v;
            }
        }""",
        ),
    ],
)
def test_forward_expression_alias_field(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    transformed_ast = ForwardExpressionAliasTransformer().transform(game_ast)
    assert expected_ast == transformed_ast
