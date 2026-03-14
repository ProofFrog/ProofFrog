"""Tests for _extract_subsets_pairs in semantic_analysis."""

from proof_frog import frog_ast, semantic_analysis


def _make_scheme_with_requirements(
    requirements: list[frog_ast.Expression],
) -> frog_ast.Scheme:
    """Create a minimal scheme with the given requirements."""
    return frog_ast.Scheme(
        imports=[],
        name="TestScheme",
        parameters=[],
        primitive_name="TestPrimitive",
        fields=[],
        requirements=requirements,
        methods=[],
    )


class TestExtractSubsetsPairs:
    """Tests for extracting (sub, super) type pairs from requires clauses."""

    def test_single_subsets_pair(self) -> None:
        req = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.Variable("KeySpace2"),
            frog_ast.Variable("IntermediateSpace"),
        )
        scheme = _make_scheme_with_requirements([req])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 1
        assert pairs[0] == (
            frog_ast.Variable("KeySpace2"),
            frog_ast.Variable("IntermediateSpace"),
        )

    def test_multiple_subsets_pairs(self) -> None:
        req1 = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
        )
        req2 = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.Variable("C"),
            frog_ast.Variable("D"),
        )
        scheme = _make_scheme_with_requirements([req1, req2])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 2

    def test_equality_requirement_extracted(self) -> None:
        """Equality requirements should be extracted as type pairs."""
        req = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
        )
        scheme = _make_scheme_with_requirements([req])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 1

    def test_non_equality_non_subsets_requirement_ignored(self) -> None:
        """Non-EQUALS/SUBSETS requirements should be ignored."""
        req = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.LT,
            frog_ast.Variable("A"),
            frog_ast.Variable("B"),
        )
        scheme = _make_scheme_with_requirements([req])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 0

    def test_empty_requirements(self) -> None:
        scheme = _make_scheme_with_requirements([])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 0

    def test_primitive_returns_empty(self) -> None:
        """Primitives don't have subsets requirements."""
        primitive = frog_ast.Primitive(
            name="TestPrimitive",
            parameters=[],
            fields=[],
            methods=[],
        )
        pairs = semantic_analysis._extract_subsets_pairs(primitive)
        assert len(pairs) == 0

    def test_non_type_expressions_ignored(self) -> None:
        """Subsets with non-Type expressions should be skipped."""
        req = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBSETS,
            frog_ast.Integer(42),
            frog_ast.Variable("B"),
        )
        scheme = _make_scheme_with_requirements([req])
        pairs = semantic_analysis._extract_subsets_pairs(scheme)
        assert len(pairs) == 0
