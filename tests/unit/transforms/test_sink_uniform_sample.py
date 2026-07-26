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


def test_f042_declines_when_variable_escapes_block() -> None:
    """F-042 scope guard: a block-local sample whose name is referenced outside
    its block with no governing outer declaration (an out-of-scope AST the
    typechecker would reject) must NOT be sunk -- sinking would leave the
    outside use reading a variable defined on only one path."""
    method = frog_parser.parse_method("""
        Bool O(Bool a, Bool b) {
            if (a) {
                ModInt<2> x <- ModInt<2>;
                if (b) {
                    ModInt<2> y = x;
                }
            }
            return x == 0;
        }
        """)
    # Unchanged: the guard declines because `x` escapes the `if (a)` block.
    assert SinkUniformSampleTransformer().transform(method) == method


def test_f042_still_fires_with_legitimate_shadowing() -> None:
    """F-042 guard precision: a *separate* outer declaration of the same name
    (legitimate block-scoped shadowing) governs the outside references, so the
    inner sink must still fire -- the guard only blocks true escapes."""
    method = frog_parser.parse_method("""
        ModInt<2> O(Bool a, Bool c) {
            if (a) {
                ModInt<2> x <- ModInt<2>;
                if (c) {
                    ModInt<2> y = x;
                }
            }
            if (c) {
                ModInt<2> x <- ModInt<2>;
                return x;
            }
            return 0;
        }
        """)
    transformed = SinkUniformSampleTransformer().transform(method)
    # The first block's `x` is sunk into its `if (c)` sub-branch; the sibling
    # `x` (a distinct declaration) is untouched.
    assert transformed != method
