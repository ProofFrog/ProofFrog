"""Tests for product type comparison and _full_flatten_product."""

from proof_frog import frog_ast, semantic_analysis


def _make_product(
    *types: frog_ast.Type, left_assoc: bool = False
) -> frog_ast.BinaryOperation:
    """Build a product type from a list of component types.

    By default builds right-associative: A * (B * C).
    With left_assoc=True builds left-associative: (A * B) * C.
    """
    assert len(types) >= 2
    if left_assoc:
        result: frog_ast.Type = types[0]
        for t in types[1:]:
            result = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.MULTIPLY, result, t
            )
        assert isinstance(result, frog_ast.BinaryOperation)
        return result
    # right-associative
    result = types[-1]
    for t in reversed(types[:-1]):
        result = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY, t, result
        )
    assert isinstance(result, frog_ast.BinaryOperation)
    return result


class TestFullFlattenProduct:
    """Tests for _full_flatten_product."""

    def test_single_type(self) -> None:
        result = semantic_analysis._full_flatten_product(frog_ast.IntType())
        assert result == [frog_ast.IntType()]

    def test_simple_product(self) -> None:
        product = _make_product(frog_ast.Variable("A"), frog_ast.Variable("B"))
        result = semantic_analysis._full_flatten_product(product)
        assert result == [frog_ast.Variable("A"), frog_ast.Variable("B")]

    def test_right_associative_triple(self) -> None:
        """A * (B * C) -> [A, B, C]."""
        product = _make_product(
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        )
        result = semantic_analysis._full_flatten_product(product)
        assert result == [
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        ]

    def test_left_associative_triple(self) -> None:
        """(A * B) * C -> [A, B, C]."""
        product = _make_product(
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
            left_assoc=True,
        )
        result = semantic_analysis._full_flatten_product(product)
        assert result == [
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        ]

    def test_left_and_right_give_same_result(self) -> None:
        """Both associativities flatten to the same list."""
        types = [frog_ast.Variable("A"), frog_ast.Variable("B"), frog_ast.Variable("C")]
        left = semantic_analysis._full_flatten_product(
            _make_product(*types, left_assoc=True)
        )
        right = semantic_analysis._full_flatten_product(
            _make_product(*types, left_assoc=False)
        )
        assert left == right

    def test_four_element_left_associative(self) -> None:
        """((A * B) * C) * D -> [A, B, C, D]."""
        product = _make_product(
            frog_ast.IntType(),
            frog_ast.IntType(),
            frog_ast.IntType(),
            frog_ast.IntType(),
            left_assoc=True,
        )
        result = semantic_analysis._full_flatten_product(product)
        assert len(result) == 4
        assert all(isinstance(t, frog_ast.IntType) for t in result)

    def test_non_multiply_not_flattened(self) -> None:
        """A + B is not a product type and should not be flattened."""
        binop = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            frog_ast.IntType(),
            frog_ast.IntType(),
        )
        result = semantic_analysis._full_flatten_product(binop)
        assert len(result) == 1
        assert result[0] == binop


class TestCompareTypesProducts:
    """Tests for compare_types with product types."""

    def test_identical_products(self) -> None:
        product = _make_product(frog_ast.IntType(), frog_ast.IntType())
        assert semantic_analysis.compare_types(product, product)

    def test_left_assoc_vs_right_assoc(self) -> None:
        """(A * B) * C matches A * (B * C)."""
        types = [frog_ast.Variable("A"), frog_ast.Variable("B"), frog_ast.Variable("C")]
        left = _make_product(*types, left_assoc=True)
        right = _make_product(*types, left_assoc=False)
        assert semantic_analysis.compare_types(left, right)
        assert semantic_analysis.compare_types(right, left)

    def test_product_vs_tuple_type_list_two_elements(self) -> None:
        """A * B matches [A, B] (tuple literal type)."""
        product = _make_product(frog_ast.Variable("A"), frog_ast.Variable("B"))
        tuple_types = [frog_ast.Variable("A"), frog_ast.Variable("B")]
        assert semantic_analysis.compare_types(product, tuple_types)

    def test_right_assoc_product_vs_tuple_type_list_three_elements(self) -> None:
        """A * (B * C) matches [A, B, C] (tuple literal type)."""
        product = _make_product(
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        )
        tuple_types = [
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        ]
        assert semantic_analysis.compare_types(product, tuple_types)

    def test_left_assoc_product_vs_tuple_type_list_three_elements(self) -> None:
        """(A * B) * C matches [A, B, C] (tuple literal type).

        This is the key fix: Set field values are parsed as left-associative
        expressions, but tuple literals have flat type lists.
        """
        product = _make_product(
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
            left_assoc=True,
        )
        tuple_types = [
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        ]
        assert semantic_analysis.compare_types(product, tuple_types)

    def test_nested_product_components_vs_tuple_type_list(self) -> None:
        """(A * B) * (C * D * E) matches [(A * B), (C * D * E)].

        When product components are themselves products (e.g., EncapsKey * DecapsKey
        where EncapsKey = A * B), the comparison should match at the top level
        without flattening into components.
        """
        encaps_key = _make_product(frog_ast.Variable("A"), frog_ast.Variable("B"))
        decaps_key = _make_product(
            frog_ast.Variable("C"),
            frog_ast.Variable("D"),
            frog_ast.Variable("E"),
            left_assoc=True,
        )
        return_type = _make_product(encaps_key, decaps_key)
        tuple_types = [encaps_key, decaps_key]
        assert semantic_analysis.compare_types(return_type, tuple_types)

    def test_different_element_types_mismatch(self) -> None:
        """A * B does not match [A, C]."""
        product = _make_product(frog_ast.Variable("A"), frog_ast.Variable("B"))
        tuple_types = [frog_ast.Variable("A"), frog_ast.Variable("C")]
        assert not semantic_analysis.compare_types(product, tuple_types)

    def test_different_arity_mismatch(self) -> None:
        """A * B does not match [A, B, C]."""
        product = _make_product(frog_ast.Variable("A"), frog_ast.Variable("B"))
        tuple_types = [
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
            frog_ast.Variable("C"),
        ]
        assert not semantic_analysis.compare_types(product, tuple_types)
