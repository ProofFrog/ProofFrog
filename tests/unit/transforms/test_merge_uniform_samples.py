import pytest
from sympy import Symbol
from proof_frog import frog_parser
from proof_frog.transforms.sampling import MergeUniformSamplesTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Two uniform samples concatenated in return
        (
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y <- BitString<lambda>;
                return x || y;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<2 * lambda> x <- BitString<2 * lambda>;
                return x;
            }
            """,
        ),
        # Three uniform samples concatenated
        (
            """
            BitString<3 * lambda> f() {
                BitString<lambda> a <- BitString<lambda>;
                BitString<lambda> b <- BitString<lambda>;
                BitString<lambda> c <- BitString<lambda>;
                return a || b || c;
            }
            """,
            """
            BitString<3 * lambda> f() {
                BitString<3 * lambda> a <- BitString<3 * lambda>;
                return a;
            }
            """,
        ),
        # Different lengths
        (
            """
            BitString<3 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<2 * lambda> y <- BitString<2 * lambda>;
                return x || y;
            }
            """,
            """
            BitString<3 * lambda> f() {
                BitString<3 * lambda> x <- BitString<3 * lambda>;
                return x;
            }
            """,
        ),
        # Non-sample variable in concatenation: no transformation
        (
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y = g();
                return x || y;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y = g();
                return x || y;
            }
            """,
        ),
        # Variable used elsewhere: no transformation
        (
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y <- BitString<lambda>;
                BitString<lambda> z = x;
                return x || y;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y <- BitString<lambda>;
                BitString<lambda> z = x;
                return x || y;
            }
            """,
        ),
        # Concatenation in assignment (not return)
        (
            """
            Void f() {
                BitString<lambda> x <- BitString<lambda>;
                BitString<lambda> y <- BitString<lambda>;
                BitString<2 * lambda> z = x || y;
                return z;
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> x <- BitString<2 * lambda>;
                BitString<2 * lambda> z = x;
                return z;
            }
            """,
        ),
        # No merge: non-uniform sample (type != sampled_from)
        (
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<2 * lambda>;
                BitString<lambda> y <- BitString<lambda>;
                return x || y;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<2 * lambda>;
                BitString<lambda> y <- BitString<lambda>;
                return x || y;
            }
            """,
        ),
        # No merge: only one sample in concatenation
        (
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                return x || x;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> x <- BitString<lambda>;
                return x || x;
            }
            """,
        ),
    ],
)
def test_merge_uniform_samples(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = MergeUniformSamplesTransformer(
        {"lambda": Symbol("lambda")}
    ).transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_merge_uniform_declines_on_domain_write_between_samples() -> None:
    """RC5: do not merge two ``BitString<n>`` samples when ``n`` is written
    between them -- the concatenation re-anchors both draws and the second
    draw's domain would differ from the first."""
    method = frog_parser.parse_method("""
        BitString<n + n> f() {
            BitString<n> x <- BitString<n>;
            n = 10;
            BitString<n> y <- BitString<n>;
            return x || y;
        }
        """)
    result = MergeUniformSamplesTransformer({"n": Symbol("n")}).transform(method)
    assert result == method


def test_merge_uniform_fires_when_no_domain_write() -> None:
    """RC5 conservatism: with no write to ``n`` between the samples, the merge
    still fires."""
    method = frog_parser.parse_method("""
        BitString<n + n> f() {
            BitString<n> x <- BitString<n>;
            BitString<n> y <- BitString<n>;
            return x || y;
        }
        """)
    result = MergeUniformSamplesTransformer({"n": Symbol("n")}).transform(method)
    # The two independent BitString<n> samples merge into a single
    # BitString<2 * n> sample (length arithmetic is engine-normalized).
    assert "2*n" in str(result).replace(" ", "")
    # Only one sample remains.
    assert str(result).count("<-") == 1
