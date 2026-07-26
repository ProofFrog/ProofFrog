import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import CollapseAssignmentTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            """
            Int f() {
                Int a = 1;
                a = 2;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 2;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                a = 2;
                a = 3;
                a = 4;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 4;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = 2;
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = 2;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = g();
                a = 3;
                return a;
            }
            """,
            """
            Int f() {
                Int a = g();
                a = 3;
                return a;
            }
            """,
        ),
        (
            """
            Int f() {
                Int b = 0;
                Int a = 1;
                b = b + 1;
                a = 2;
                return a;
            }
            """,
            """
            Int f() {
                Int b = 0;
                b = b + 1;
                Int a = 2;
                return a;
            }
            """,
        ),
    ],
)
def test_collapse_assignment(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    print("EXPECTED", expected_ast)
    transformed_ast = CollapseAssignmentTransformer().transform(game_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_element_mutation_not_collapsed() -> None:
    """An element mutation like v[0] = expr should NOT be treated as a
    full reassignment that allows collapsing the original declaration."""
    method_ast = frog_parser.parse_method("""
        Void f() {
            Map<Int, Int> M = {};
            M[0] = 42;
            return M;
        }
        """)
    expected_ast = frog_parser.parse_method("""
        Void f() {
            Map<Int, Int> M = {};
            M[0] = 42;
            return M;
        }
        """)
    transformed_ast = CollapseAssignmentTransformer().transform(method_ast)
    assert (
        transformed_ast == expected_ast
    ), "Element mutation M[0]=42 should not collapse the declaration of M"


def test_f146_sample_initial_not_collapsed() -> None:
    """F-146: the first statement's value is what the collapse DELETES. A Sample
    (`x <- S`) is a side-effecting draw -- sampling a possibly-empty domain is an
    observable termination event -- so deleting it by folding a later
    reassignment onto it changes observable behaviour. The sample must survive."""
    method = frog_parser.parse_method(
        """
        Int f() {
            Int x <- S;
            x = 0;
            return x;
        }
        """
    )
    result = CollapseAssignmentTransformer().transform(method)
    # The `x <- S` draw must NOT be deleted (no collapse into `Int x = 0`).
    assert result == method, "a Sample-initial draw must not be collapsed away"


def test_f146_sample_call_initial_not_collapsed() -> None:
    """F-146: a Sample whose `sampled_from` carries a call is likewise a
    side-effecting draw and must not be collapsed away."""
    method = frog_parser.parse_method(
        """
        Int f() {
            Int x <- G.Sample();
            x = 0;
            return x;
        }
        """
    )
    result = CollapseAssignmentTransformer().transform(method)
    assert result == method, "a Sample-call initial must not be collapsed away"
