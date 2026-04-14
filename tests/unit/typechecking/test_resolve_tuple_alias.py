"""Tests for _resolve_type_alias handling of Tuple-of-types.

Regression test for the bug where a Tuple containing FieldAccess elements
(e.g., K.SharedSecret) was not resolved by _resolve_type_alias, causing
type mismatches against the equivalent ProductType whose elements were
resolved (e.g., Variable("SharedSecretSpace")).
"""

from proof_frog import frog_ast, semantic_analysis, visitors


def _make_visitor_with_kem() -> semantic_analysis.CheckTypeVisitor:
    """Create a CheckTypeVisitor that knows about a KEM-like primitive K."""
    kem_members: dict[str, frog_ast.ASTNode] = {
        "SharedSecret": frog_ast.Variable("SharedSecretSpace"),
        "Ciphertext": frog_ast.Variable("CiphertextSpace"),
    }
    kem_type = visitors.InstantiableType("K", kem_members, "KEM")
    visitor = semantic_analysis.CheckTypeVisitor({}, "test", {})
    visitor.variable_type_map_stack[-1]["K"] = kem_type
    return visitor


class TestResolveTupleAlias:
    """_resolve_type_alias should resolve Tuple-of-types like ProductType."""

    def test_tuple_field_access_resolved(self) -> None:
        """Tuple([Int, K.SharedSecret]) resolves to ProductType([Int, SharedSecretSpace])."""
        visitor = _make_visitor_with_kem()
        t = frog_ast.Tuple([
            frog_ast.IntType(),
            frog_ast.FieldAccess(frog_ast.Variable("K"), "SharedSecret"),
        ])
        resolved = visitor._resolve_type_alias(t)
        assert isinstance(resolved, frog_ast.ProductType)
        assert len(resolved.types) == 2
        assert resolved.types[0] == frog_ast.IntType()
        assert resolved.types[1] == frog_ast.Variable("SharedSecretSpace")

    def test_tuple_without_field_access_normalizes(self) -> None:
        """Tuple([Int, Bool]) normalizes to ProductType([Int, Bool])."""
        visitor = _make_visitor_with_kem()
        t = frog_ast.Tuple([frog_ast.IntType(), frog_ast.BoolType()])
        resolved = visitor._resolve_type_alias(t)
        assert isinstance(resolved, frog_ast.ProductType)
        assert resolved.types == [frog_ast.IntType(), frog_ast.BoolType()]

    def test_product_type_field_access_resolved(self) -> None:
        """ProductType with FieldAccess also resolves (existing behavior)."""
        visitor = _make_visitor_with_kem()
        t = frog_ast.ProductType([
            frog_ast.IntType(),
            frog_ast.FieldAccess(frog_ast.Variable("K"), "SharedSecret"),
        ])
        resolved = visitor._resolve_type_alias(t)
        assert isinstance(resolved, frog_ast.ProductType)
        assert resolved.types[1] == frog_ast.Variable("SharedSecretSpace")

    def test_check_types_tuple_vs_product_with_alias(self) -> None:
        """check_types matches Tuple([..., K.SharedSecret]) against ProductType([..., SharedSecretSpace])."""
        visitor = _make_visitor_with_kem()
        product = frog_ast.ProductType([
            frog_ast.IntType(),
            frog_ast.Variable("SharedSecretSpace"),
        ])
        tuple_t = frog_ast.Tuple([
            frog_ast.IntType(),
            frog_ast.FieldAccess(frog_ast.Variable("K"), "SharedSecret"),
        ])
        assert visitor.check_types(product, tuple_t)
        assert visitor.check_types(tuple_t, product)
