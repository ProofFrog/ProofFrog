import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                } else {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                } else {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                } else if (x <= 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                } else if (x <= 0) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x == 0) {
                    return 2;
                }
                if (x < 0) {
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x == 0) {
                    return 2;
                }
                if (x < 0) {
                    return 3;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x < 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x < 0) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Bool b, Bool c) {
                if (b) {
                    return 1;
                }
                b = c;
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b, Bool c) {
                if (b) {
                    return 1;
                }
                b = c;
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Bool a, Bool b) {
                if (a) {
                    x = 1;
                } else if (b) {
                    return 1;
                }
                if (!a && !b) {
                    return 2;
                }
                if (a && !b) {
                    return 3;
                }
                if (a && b) {
                    return 4;
                }
                return 5;
            }
            """,
            """
            Int f(Int x, Bool a, Bool b) {
                if (a) {
                    x = 1;
                } else if (b) {
                    return 1;
                }
                if (!a && !b) {
                    return 2;
                }
                if (a && !b) {
                    return 3;
                }
                if (a && b) {
                    return 4;
                }
            }
            """,
        ),
        (
            """
            Int f(Bool a, Bool b) {
                if (b) {
                    return 1;
                }
                if (a) {
                    b = !b;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool a, Bool b) {
                if (b) {
                    return 1;
                }
                if (a) {
                    b = !b;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                if (!(x in S)) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s) {
                if (challenger.g() in S) {
                    return 1;
                }
                if (!(challenger.g() in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (challenger.g() in S) {
                    return 1;
                }
                if (!(challenger.g() in S)) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                x = 2;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                x = 2;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in S) {
                    return 1;
                }
                s = t;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in S) {
                    return 1;
                }
                s = t;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in s && x in t) {
                    return 1;
                }
                if (!(x in s) && x in t) {
                    return 2;
                }
                if (x in s && !(x in t)) {
                    return 3;
                }
                if (!(x in s) && !(x in t)) {
                    return 4;
                }
                return 5;
            }
            """,
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in s && x in t) {
                    return 1;
                }
                if (!(x in s) && x in t) {
                    return 2;
                }
                if (x in s && !(x in t)) {
                    return 3;
                }
                if (!(x in s) && !(x in t)) {
                    return 4;
                }
            }
            """,
        ),
    ],
)
def test_unreachable_transformer(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    print("EXPECTED: ", expected_ast)
    transformed_ast = visitors.RemoveUnreachableTransformer(method_ast).transform(
        method_ast
    )
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast
