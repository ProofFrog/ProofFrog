import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import MergeProductSamplesTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Two uniform samples combined into a tuple in return
        (
            """
            A * B f() {
                A a <- A;
                B b <- B;
                return [a, b];
            }
            """,
            """
            A * B f() {
                A * B a <- A * B;
                return a;
            }
            """,
        ),
        # No merge: tuple in assignment (variable may be accessed via indices)
        (
            """
            Void f() {
                A a <- A;
                B b <- B;
                A * B z = [a, b];
                return z;
            }
            """,
            """
            Void f() {
                A a <- A;
                B b <- B;
                A * B z = [a, b];
                return z;
            }
            """,
        ),
        # No merge: non-sample variable
        (
            """
            A * B f() {
                A a <- A;
                B b = g();
                return [a, b];
            }
            """,
            """
            A * B f() {
                A a <- A;
                B b = g();
                return [a, b];
            }
            """,
        ),
        # No merge: variable used elsewhere
        (
            """
            A * B f() {
                A a <- A;
                B b <- B;
                A c = a;
                return [a, b];
            }
            """,
            """
            A * B f() {
                A a <- A;
                B b <- B;
                A c = a;
                return [a, b];
            }
            """,
        ),
        # No merge: non-uniform sample (type != sampled_from)
        (
            """
            A * B f() {
                A a <- B;
                B b <- B;
                return [a, b];
            }
            """,
            """
            A * B f() {
                A a <- B;
                B b <- B;
                return [a, b];
            }
            """,
        ),
        # No merge: duplicate variable in tuple
        (
            """
            A * A f() {
                A a <- A;
                return [a, a];
            }
            """,
            """
            A * A f() {
                A a <- A;
                return [a, a];
            }
            """,
        ),
    ],
)
def test_merge_product_samples(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = MergeProductSamplesTransformer().transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
