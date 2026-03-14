"""Tests for compare_types with ProductType."""

from proof_frog import frog_ast, semantic_analysis


class TestCompareTypesProducts:
    """Tests for compare_types with product types."""

    def test_identical_products(self) -> None:
        product = frog_ast.ProductType([frog_ast.IntType(), frog_ast.IntType()])
        assert semantic_analysis.compare_types(product, product)

    def test_equal_products(self) -> None:
        """Two separately constructed but equal ProductTypes match."""
        a = frog_ast.ProductType([frog_ast.Variable("A"), frog_ast.Variable("B")])
        b = frog_ast.ProductType([frog_ast.Variable("A"), frog_ast.Variable("B")])
        assert semantic_analysis.compare_types(a, b)
        assert semantic_analysis.compare_types(b, a)

    def test_three_element_products(self) -> None:
        """[A, B, C] matches [A, B, C]."""
        a = frog_ast.ProductType(
            [frog_ast.Variable("A"), frog_ast.Variable("B"), frog_ast.Variable("C")]
        )
        b = frog_ast.ProductType(
            [frog_ast.Variable("A"), frog_ast.Variable("B"), frog_ast.Variable("C")]
        )
        assert semantic_analysis.compare_types(a, b)

    def test_nested_product_components(self) -> None:
        """[[A, B], [C, D, E]] matches [[A, B], [C, D, E]]."""
        inner1 = frog_ast.ProductType(
            [frog_ast.Variable("A"), frog_ast.Variable("B")]
        )
        inner2 = frog_ast.ProductType(
            [frog_ast.Variable("C"), frog_ast.Variable("D"), frog_ast.Variable("E")]
        )
        a = frog_ast.ProductType([inner1, inner2])
        b = frog_ast.ProductType([inner1, inner2])
        assert semantic_analysis.compare_types(a, b)

    def test_different_element_types_mismatch(self) -> None:
        """[A, B] does not match [A, C]."""
        a = frog_ast.ProductType([frog_ast.Variable("A"), frog_ast.Variable("B")])
        b = frog_ast.ProductType([frog_ast.Variable("A"), frog_ast.Variable("C")])
        assert not semantic_analysis.compare_types(a, b)

    def test_different_arity_mismatch(self) -> None:
        """[A, B] does not match [A, B, C]."""
        a = frog_ast.ProductType([frog_ast.Variable("A"), frog_ast.Variable("B")])
        b = frog_ast.ProductType(
            [frog_ast.Variable("A"), frog_ast.Variable("B"), frog_ast.Variable("C")]
        )
        assert not semantic_analysis.compare_types(a, b)

    def test_product_vs_non_product(self) -> None:
        """[Int, Int] does not match Int."""
        product = frog_ast.ProductType([frog_ast.IntType(), frog_ast.IntType()])
        assert not semantic_analysis.compare_types(product, frog_ast.IntType())
        assert not semantic_analysis.compare_types(frog_ast.IntType(), product)
