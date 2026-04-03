"""Tests for the alpha-equivalent branch merging in SimplifyIfTransformer."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import SimplifyIfTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Branches identical up to local variable names: merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (true) {
                    BitString<n> a <- BitString<n>;
                    return a;
                }
            }
            """,
        ),
        # Two if-else-if branches identical up to local names: merged with OR
        # (the second branch body is kept after merging)
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else if (x == 2) {
                    BitString<n> b <- BitString<n>;
                    return b;
                } else {
                    return x;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1 || x == 2) {
                    BitString<n> b <- BitString<n>;
                    return b;
                } else {
                    return x;
                }
            }
            """,
        ),
        # Multiple local declarations, same structure: merged
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    BitString<n> c = a + m;
                    return c;
                } else {
                    BitString<n> d <- BitString<n>;
                    BitString<n> e = d + m;
                    return e;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (true) {
                    BitString<n> a <- BitString<n>;
                    BitString<n> c = a + m;
                    return c;
                }
            }
            """,
        ),
        # Different structure (not just variable names): NOT merged
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    return m;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    return m;
                }
            }
            """,
        ),
        # Local names differ but reference different outer variables: NOT merged
        (
            """
            BitString<n> f(Int x, BitString<n> m, BitString<n> p) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b + p;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m, BitString<n> p) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a + m;
                } else {
                    BitString<n> b <- BitString<n>;
                    return b + p;
                }
            }
            """,
        ),
        # No local declarations, identical bodies: merged (existing behavior)
        (
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (x == 1) {
                    return m;
                } else {
                    return m;
                }
            }
            """,
            """
            BitString<n> f(Int x, BitString<n> m) {
                if (true) {
                    return m;
                }
            }
            """,
        ),
        # Different number of local declarations: NOT merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    return x;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    return x;
                }
            }
            """,
        ),
        # Different sample types: NOT merged
        (
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<m> b <- BitString<m>;
                    return b;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> a <- BitString<n>;
                    return a;
                } else {
                    BitString<m> b <- BitString<m>;
                    return b;
                }
            }
            """,
        ),
    ],
)
def test_alpha_simplify_if(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = SimplifyIfTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
