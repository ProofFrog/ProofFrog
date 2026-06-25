import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import SinkUniformSampleTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: sample used in one branch, sunk into that branch
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> k <- BitString<n>;
                    return k;
                } else {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
            }
            """,
        ),
        # Sample used in else branch (second branch)
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    BitString<n> r <- BitString<n>;
                    return r;
                } else {
                    return k;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> r <- BitString<n>;
                    return r;
                } else {
                    BitString<n> k <- BitString<n>;
                    return k;
                }
            }
            """,
        ),
        # Other samples between the sunk sample and the if (no references);
        # both get sunk because the while-loop iterates
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                BitString<n> m <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    return m;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    BitString<n> k <- BitString<n>;
                    return k;
                } else {
                    BitString<n> m <- BitString<n>;
                    return m;
                }
            }
            """,
        ),
        # Variable used in the condition: no sinking
        (
            """
            BitString<n> f(BitString<n> x) {
                BitString<n> k <- BitString<n>;
                if (k == x) {
                    return k;
                } else {
                    return x;
                }
            }
            """,
            """
            BitString<n> f(BitString<n> x) {
                BitString<n> k <- BitString<n>;
                if (k == x) {
                    return k;
                } else {
                    return x;
                }
            }
            """,
        ),
        # Variable used in multiple branches: no sinking
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    return k;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    return k;
                }
            }
            """,
        ),
        # Variable used after the if: no sinking
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return k;
                }
                return k;
            }
            """,
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return k;
                }
                return k;
            }
            """,
        ),
        # Next statement is not an if: no sinking
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                return k;
            }
            """,
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                return k;
            }
            """,
        ),
        # Bare field sample (the_type is None): no sinking
        (
            """
            BitString<n> f(Int x) {
                k <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
            }
            """,
            """
            BitString<n> f(Int x) {
                k <- BitString<n>;
                if (x == 1) {
                    return k;
                } else {
                    BitString<n> r <- BitString<n>;
                    return r;
                }
            }
            """,
        ),
        # Sample used only after a following if-stmt that does not reference
        # the sample variable (neither condition nor any branch): sink the
        # sample past the if-stmt.
        (
            """
            BitString<n> f(Int x) {
                BitString<n> k <- BitString<n>;
                if (x == 1) {
                    return 0^n;
                }
                return k;
            }
            """,
            """
            BitString<n> f(Int x) {
                if (x == 1) {
                    return 0^n;
                }
                BitString<n> k <- BitString<n>;
                return k;
            }
            """,
        ),
    ],
)
def test_sink_uniform_sample(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = method_ast
    while True:
        new_ast = SinkUniformSampleTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_sink_declines_when_if_branch_writes_sampled_domain() -> None:
    """RC5: case 2 must not sink a ``ModInt<n>`` sample past an if whose branch
    writes the domain name ``n`` -- that would re-evaluate the sampling domain
    at the new position."""
    method = frog_parser.parse_method("""
        ModInt<n> O(Bool b) {
            ModInt<n> x <- ModInt<n>;
            if (b) {
                n = 2;
            }
            return x;
        }
        """)
    assert SinkUniformSampleTransformer().transform(method) == method


def test_sink_fires_when_if_branch_writes_unrelated_name() -> None:
    """RC5 conservatism: a write to an unrelated name does not block the sink."""
    method = frog_parser.parse_method("""
        ModInt<n> O(Bool b) {
            ModInt<n> x <- ModInt<n>;
            if (b) {
                junk = 2;
            }
            return x;
        }
        """)
    expected = frog_parser.parse_method("""
        ModInt<n> O(Bool b) {
            if (b) {
                junk = 2;
            }
            ModInt<n> x <- ModInt<n>;
            return x;
        }
        """)
    assert SinkUniformSampleTransformer().transform(method) == expected
