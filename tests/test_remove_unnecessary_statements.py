import copy
import pytest
from proof_frog import dependencies, frog_parser


@pytest.mark.parametrize(
    "method,expected,fields",
    [
        (
            """
            Int f(Int x) {
                return x;
            }
            """,
            """
            Int f(Int x) {
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 1;
                return y;
            }
            """,
            """
            Int f(Int x) {
                Int y = 1;
                return y;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 1;
                return x;
            }
            """,
            """
            Int f(Int x) {
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y <- Int;
                return x + y;
            }
            """,
            """
            Int f(Int x) {
                Int y <- Int;
                return x + y;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int a = 5;
                Int b = a;
                Int c = a;
                Int d = 1;
                return c;
            }
            """,
            """
            Int f(Int x) {
                Int a = 5;
                Int c = a;
                return c;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                Int y = 5;
                if (True) {
                    y = 2;
                }
                return x;
            }
            """,
            """
            Int f(Int x) {
                if (True) {
                }
                return x;
            }
            """,
            [],
        ),
        (
            """
            Int f(Int x) {
                if (True) {
                    x = 2;
                }
                return x;
            }
            """,
            """
            Int f(Int x) {
                if (True) {
                    x = 2;
                }
                return x;
            }
            """,
            [],
        ),
    ],
)
def test_unnecessary_statements(method: str, expected: str, fields: list[str]) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    print("EXPECTED", expected_ast)
    transformed_block = dependencies.remove_unnecessary_statements(
        fields, method_ast.block
    )
    new_method = copy.deepcopy(method_ast)
    new_method.block = transformed_block
    print("TRANSFORMED", new_method)
    assert expected_ast == new_method
