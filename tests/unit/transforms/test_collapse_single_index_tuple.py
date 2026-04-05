import pytest
from proof_frog import frog_parser, frog_ast
from proof_frog.transforms.tuples import CollapseSingleIndexTupleTransformer


@pytest.mark.parametrize(
    "method,expected_stmts",
    [
        # Core case: only v[1] is used, collapse to scalar
        # Expected: v becomes scalar typed, v[1] replaced with v
        (
            """
            Int f() {
                [Int, Int] v = challenger.g();
                return v[1];
            }
            """,
            2,  # assignment + return, v is now scalar
        ),
        # Only v[0] is used
        (
            """
            Int f() {
                [Int, Int] v = challenger.g();
                return v[0];
            }
            """,
            2,
        ),
        # Multiple uses of same index — still collapse
        (
            """
            Int f() {
                [Int, Int] v = challenger.g();
                Int a = v[1];
                return a + v[1];
            }
            """,
            3,  # collapsed v decl + a decl + return
        ),
    ],
)
def test_collapse_single_index_tuple_fires(
    method: str,
    expected_stmts: int,
) -> None:
    """Verify the transform fires and produces the right number of statements."""
    method_ast = frog_parser.parse_method(method)
    transformed = CollapseSingleIndexTupleTransformer().transform(method_ast)
    assert len(transformed.block.statements) == expected_stmts
    # After collapse, the declaration should have a non-product type
    first_stmt = transformed.block.statements[0]
    assert isinstance(first_stmt, frog_ast.Assignment)
    assert not isinstance(first_stmt.the_type, frog_ast.ProductType)


@pytest.mark.parametrize(
    "method",
    [
        # Should NOT transform: both indices used
        """
        Int f() {
            [Int, Int] v = challenger.g();
            return v[0] + v[1];
        }
        """,
        # Should NOT transform: bare variable use
        """
        [Int, Int] f() {
            [Int, Int] v = challenger.g();
            return v;
        }
        """,
        # Should NOT transform: value is a tuple literal (handled by ExpandTuple)
        """
        Int f() {
            [Int, Int] v = [1, 2];
            return v[1];
        }
        """,
        # Should NOT transform: no type annotation (parameter, not declaration)
        """
        Int f([Int, Int] v) {
            return v[1];
        }
        """,
        # Should NOT transform: variable index (v[x]) mixed with constant (v[0])
        """
        Int f(Int x) {
            [Int, Int] v = challenger.g();
            Int a = v[0];
            return v[x];
        }
        """,
        # Should NOT transform: variable-only index
        """
        Int f(Int x) {
            [Int, Int] v = challenger.g();
            return v[x];
        }
        """,
    ],
)
def test_collapse_single_index_tuple_no_change(method: str) -> None:
    """Verify the transform does NOT fire for these cases."""
    method_ast = frog_parser.parse_method(method)
    transformed = CollapseSingleIndexTupleTransformer().transform(method_ast)
    assert transformed == method_ast
