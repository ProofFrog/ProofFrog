"""Tests for SubsetTypeNormalizer transformer."""

from proof_frog import frog_parser, frog_ast
from proof_frog.transforms.types import SubsetTypeNormalizer


def _make_pairs(
    *pairs: tuple[str, str],
) -> list[tuple[frog_ast.Type, frog_ast.Type]]:
    """Create subsets pairs from string name pairs."""
    return [
        (frog_ast.Variable(sub), frog_ast.Variable(sup)) for sub, sup in pairs
    ]


class TestBasicNormalization:
    """Tests for normalizing subset types to superset equivalents."""

    def test_normalizes_field_type(self) -> None:
        game = frog_parser.parse_game(
            """
            Game G() {
                Int count;
                Void Initialize() {
                    count = 0;
                }
            }
            """
        )
        # Int is not in the pairs, so field type won't change —
        # use assignment type instead (tested in test_normalizes_assignment_type)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(game)
        assert result == game

    def test_normalizes_assignment_type(self) -> None:
        method = frog_parser.parse_method(
            """
            Void f() {
                KeySpace2 x = y;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f() {
                IntermediateSpace x = y;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_optional_type(self) -> None:
        method = frog_parser.parse_method(
            """
            Void f() {
                KeySpace2? x = None;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f() {
                IntermediateSpace? x = None;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_parameter_type(self) -> None:
        method = frog_parser.parse_method(
            """
            Bool f(KeySpace2 x) {
                return true;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Bool f(IntermediateSpace x) {
                return true;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_return_type(self) -> None:
        method = frog_parser.parse_method(
            """
            KeySpace2 f() {
                return x;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            IntermediateSpace f() {
                return x;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_product_type(self) -> None:
        method = frog_parser.parse_method(
            """
            Void f() {
                KeySpace2 * MessageSpace x = y;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f() {
                IntermediateSpace * MessageSpace x = y;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected


class TestNoNormalization:
    """Tests that non-subset types are left unchanged."""

    def test_no_change_without_pairs(self) -> None:
        method = frog_parser.parse_method(
            """
            KeySpace2 f(KeySpace2 x) {
                return x;
            }
            """
        )
        result = SubsetTypeNormalizer([]).transform(method)
        assert result == method

    def test_does_not_change_variable_references(self) -> None:
        """Variable references in expressions should NOT be normalized."""
        method = frog_parser.parse_method(
            """
            Void f() {
                IntermediateSpace x = KeySpace2_var;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        # The variable reference 'KeySpace2_var' should not be changed
        # (it's not a type, just a variable whose name starts with KeySpace2)
        assert result == method

    def test_unrelated_types_unchanged(self) -> None:
        method = frog_parser.parse_method(
            """
            MessageSpace f(MessageSpace x) {
                return x;
            }
            """
        )
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == method


class TestMultiplePairs:
    """Tests with multiple subsets pairs."""

    def test_multiple_pairs_both_normalized(self) -> None:
        method = frog_parser.parse_method(
            """
            Void f() {
                KeySpace2 x = a;
                CiphertextSpace2 y = b;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f() {
                IntermediateSpace x = a;
                MessageSpace y = b;
            }
            """
        )
        pairs = _make_pairs(
            ("KeySpace2", "IntermediateSpace"),
            ("CiphertextSpace2", "MessageSpace"),
        )
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected
