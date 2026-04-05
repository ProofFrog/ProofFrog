import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import BooleanIdentityTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # false || false -> false
        (
            """
            Bool f() {
                return false || false;
            }
            """,
            """
            Bool f() {
                return false;
            }
            """,
        ),
        # x || false -> x
        (
            """
            Bool f(Bool x) {
                return x || false;
            }
            """,
            """
            Bool f(Bool x) {
                return x;
            }
            """,
        ),
        # false || x -> x
        (
            """
            Bool f(Bool x) {
                return false || x;
            }
            """,
            """
            Bool f(Bool x) {
                return x;
            }
            """,
        ),
        # x || true -> true
        (
            """
            Bool f(Bool x) {
                return x || true;
            }
            """,
            """
            Bool f(Bool x) {
                return true;
            }
            """,
        ),
        # true || x -> true
        (
            """
            Bool f(Bool x) {
                return true || x;
            }
            """,
            """
            Bool f(Bool x) {
                return true;
            }
            """,
        ),
        # true && true -> true
        (
            """
            Bool f() {
                return true && true;
            }
            """,
            """
            Bool f() {
                return true;
            }
            """,
        ),
        # x && true -> x
        (
            """
            Bool f(Bool x) {
                return x && true;
            }
            """,
            """
            Bool f(Bool x) {
                return x;
            }
            """,
        ),
        # true && x -> x
        (
            """
            Bool f(Bool x) {
                return true && x;
            }
            """,
            """
            Bool f(Bool x) {
                return x;
            }
            """,
        ),
        # x && false -> false
        (
            """
            Bool f(Bool x) {
                return x && false;
            }
            """,
            """
            Bool f(Bool x) {
                return false;
            }
            """,
        ),
        # false && x -> false
        (
            """
            Bool f(Bool x) {
                return false && x;
            }
            """,
            """
            Bool f(Bool x) {
                return false;
            }
            """,
        ),
    ],
    ids=[
        "false_or_false",
        "x_or_false",
        "false_or_x",
        "x_or_true",
        "true_or_x",
        "true_and_true",
        "x_and_true",
        "true_and_x",
        "x_and_false",
        "false_and_x",
    ],
)
def test_boolean_identity(method: str, expected: str) -> None:
    parsed = frog_parser.parse_method(method)
    expected_parsed = frog_parser.parse_method(expected)
    result = BooleanIdentityTransformer().transform(parsed)
    assert result == expected_parsed


def test_bitstring_concat_not_simplified() -> None:
    """OR on BitString is concatenation — must not be simplified."""
    method = """
    BitString<2> f(BitString<1> a, BitString<1> b) {
        return a || b;
    }
    """
    parsed = frog_parser.parse_method(method)
    result = BooleanIdentityTransformer().transform(parsed)
    assert result == parsed
