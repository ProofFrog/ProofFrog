"""Tests for compare_types and _types_comparable in semantic_analysis."""

import pytest

from proof_frog import frog_ast, semantic_analysis


class TestCompareTypesBasic:
    """Basic compare_types behavior unchanged from before."""

    def test_same_type(self) -> None:
        assert semantic_analysis.compare_types(frog_ast.IntType(), frog_ast.IntType())

    def test_different_types(self) -> None:
        assert not semantic_analysis.compare_types(
            frog_ast.IntType(), frog_ast.BoolType()
        )

    def test_set_accepts_any_type(self) -> None:
        assert semantic_analysis.compare_types(
            frog_ast.SetType(), frog_ast.Variable("Foo")
        )

    def test_none_to_optional(self) -> None:
        assert semantic_analysis.compare_types(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.NoneExpression(),
        )


class TestCompareTypesOptional:
    """Tests for Optional type handling after implicit unwrap removal."""

    def test_optional_holds_base_type(self) -> None:
        """T? can hold T."""
        assert semantic_analysis.compare_types(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.Variable("Foo"),
        )

    def test_implicit_unwrap_removed(self) -> None:
        """T? should NOT be accepted where T is expected (no implicit unwrap)."""
        assert not semantic_analysis.compare_types(
            frog_ast.Variable("Foo"),
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
        )

    def test_optional_holds_optional_same_type(self) -> None:
        """T? can hold T?."""
        assert semantic_analysis.compare_types(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
        )

    def test_optional_rejects_different_base(self) -> None:
        """T? cannot hold S? when T != S."""
        assert not semantic_analysis.compare_types(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.OptionalType(frog_ast.Variable("Bar")),
        )


class TestCompareTypesSubsets:
    """Tests for compare_types with subsets pairs."""

    @staticmethod
    def _pairs() -> (
        list[tuple[semantic_analysis.PossibleType, semantic_analysis.PossibleType]]
    ):
        return [
            (frog_ast.Variable("KeySpace2"), frog_ast.Variable("IntermediateSpace"))
        ]

    def test_subset_to_superset(self) -> None:
        """KeySpace2 accepted where IntermediateSpace expected."""
        assert semantic_analysis.compare_types(
            frog_ast.Variable("IntermediateSpace"),
            frog_ast.Variable("KeySpace2"),
            self._pairs(),
        )

    def test_superset_to_subset(self) -> None:
        """IntermediateSpace accepted where KeySpace2 expected (bidirectional)."""
        assert semantic_analysis.compare_types(
            frog_ast.Variable("KeySpace2"),
            frog_ast.Variable("IntermediateSpace"),
            self._pairs(),
        )

    def test_unrelated_types_with_pairs(self) -> None:
        """Unrelated types still rejected even with subsets pairs present."""
        assert not semantic_analysis.compare_types(
            frog_ast.Variable("Foo"),
            frog_ast.Variable("Bar"),
            self._pairs(),
        )

    def test_optional_subsets_compatibility(self) -> None:
        """T? can hold S? when T and S are related by subsets."""
        assert semantic_analysis.compare_types(
            frog_ast.OptionalType(frog_ast.Variable("IntermediateSpace")),
            frog_ast.OptionalType(frog_ast.Variable("KeySpace2")),
            self._pairs(),
        )

    def test_no_subsets_without_pairs(self) -> None:
        """Without subsets pairs, related types are not compatible."""
        assert not semantic_analysis.compare_types(
            frog_ast.Variable("IntermediateSpace"),
            frog_ast.Variable("KeySpace2"),
        )


class TestTypesComparable:
    """Tests for _types_comparable used in equality comparisons."""

    def test_same_types(self) -> None:
        assert semantic_analysis._types_comparable(
            frog_ast.IntType(), frog_ast.IntType()
        )

    def test_different_types(self) -> None:
        assert not semantic_analysis._types_comparable(
            frog_ast.IntType(), frog_ast.BoolType()
        )

    def test_optional_equals_none(self) -> None:
        assert semantic_analysis._types_comparable(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.NoneExpression(),
        )

    def test_none_equals_optional(self) -> None:
        assert semantic_analysis._types_comparable(
            frog_ast.NoneExpression(),
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
        )

    def test_t_equals_t_optional(self) -> None:
        assert semantic_analysis._types_comparable(
            frog_ast.Variable("Foo"),
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
        )

    def test_t_optional_equals_t(self) -> None:
        assert semantic_analysis._types_comparable(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.Variable("Foo"),
        )

    def test_different_optional_types(self) -> None:
        assert not semantic_analysis._types_comparable(
            frog_ast.OptionalType(frog_ast.Variable("Foo")),
            frog_ast.OptionalType(frog_ast.Variable("Bar")),
        )

    def test_none_not_comparable_to_non_optional(self) -> None:
        assert not semantic_analysis._types_comparable(
            frog_ast.NoneExpression(),
            frog_ast.Variable("Foo"),
        )

    def test_variable_equals_bitstring(self) -> None:
        """Variable == BitStringType — needed for requires E.Key == BitString<n>."""
        assert semantic_analysis._types_comparable(
            frog_ast.Variable("KeySpace"),
            frog_ast.BitStringType(frog_ast.Integer(128)),
        )

    def test_bitstring_equals_variable(self) -> None:
        """BitStringType == Variable — symmetric with above."""
        assert semantic_analysis._types_comparable(
            frog_ast.BitStringType(frog_ast.Integer(128)),
            frog_ast.Variable("KeySpace"),
        )

    def test_variable_equals_modint(self) -> None:
        """Variable == ModIntType."""
        assert semantic_analysis._types_comparable(
            frog_ast.Variable("GroupElem"),
            frog_ast.ModIntType(frog_ast.Integer(7)),
        )

    def test_variable_equals_set(self) -> None:
        """Variable == SetType."""
        assert semantic_analysis._types_comparable(
            frog_ast.Variable("KeySpace"),
            frog_ast.SetType(),
        )

    def test_int_not_comparable_to_variable(self) -> None:
        """IntType is not a set-like type, so not comparable to Variable."""
        assert not semantic_analysis._types_comparable(
            frog_ast.IntType(),
            frog_ast.Variable("Foo"),
        )

    def test_bool_not_comparable_to_variable(self) -> None:
        """BoolType is not a set-like type, so not comparable to Variable."""
        assert not semantic_analysis._types_comparable(
            frog_ast.BoolType(),
            frog_ast.Variable("Foo"),
        )
