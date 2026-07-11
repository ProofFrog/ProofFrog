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


def test_collapse_skips_variable_assigned_in_multiple_places() -> None:
    """Must NOT collapse a name that is declared in more than one place in
    the method (e.g. the same variable written in both arms of an if, as
    produced by If-Split Branch Assignment). Collapsing one declaration to
    ``Ti v = expr[i]`` while leaving a sibling ``[T0,T1] v = expr2`` yields
    an inconsistently-typed variable; a later inlining then substitutes the
    whole tuple where ``v`` is used, dropping the index. (Regression for the
    seeded-form ROM binding proofs, whose SeededKEMWrapper.Decaps re-derives
    the keypair from the seed, producing exactly this shape.)

    Without the fix both ``v`` declarations collapse to a scalar; with it
    they remain product-typed.
    """
    method_ast = frog_parser.parse_method("""
        Int O(Bool b) {
            if (b) {
                [Int, Int] v = challenger.g();
                Int a = v[0];
            } else {
                [Int, Int] v = challenger.h();
                Int a = v[0];
            }
            return 0;
        }
        """)
    transformed = CollapseSingleIndexTupleTransformer().transform(method_ast)
    product_decls = 0
    stack: list[object] = [transformed]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if (
            isinstance(node, frog_ast.Assignment)
            and isinstance(node.var, frog_ast.Variable)
            and node.var.name == "v"
            and isinstance(node.the_type, frog_ast.ProductType)
        ):
            product_decls += 1
        if isinstance(node, frog_ast.ASTNode):
            for attr in vars(node).values():
                if isinstance(attr, frog_ast.ASTNode):
                    stack.append(attr)
                elif isinstance(attr, (list, tuple)):
                    stack.extend(a for a in attr if isinstance(a, frog_ast.ASTNode))
    assert product_decls == 2, (
        "a variable declared in both arms of an if must not be collapsed "
        f"(both declarations should stay product-typed):\n{transformed}"
    )
