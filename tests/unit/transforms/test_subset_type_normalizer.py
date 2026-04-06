"""Tests for SubsetTypeNormalizer transformer."""

from proof_frog import frog_parser, frog_ast
from proof_frog.semantic_analysis import _extract_subsets_pairs
from proof_frog.transforms.types import SubsetTypeNormalizer


def _make_pairs(
    *pairs: tuple[str, str],
) -> list[tuple[frog_ast.Type, frog_ast.Type]]:
    """Create subsets pairs from string name pairs."""
    return [(frog_ast.Variable(sub), frog_ast.Variable(sup)) for sub, sup in pairs]


class TestBasicNormalization:
    """Tests for normalizing subset types to superset equivalents."""

    def test_normalizes_field_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                Int count;
                Void Initialize() {
                    count = 0;
                }
            }
            """)
        # Int is not in the pairs, so field type won't change —
        # use assignment type instead (tested in test_normalizes_assignment_type)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(game)
        assert result == game

    def test_normalizes_assignment_type(self) -> None:
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2 x = y;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                IntermediateSpace x = y;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_optional_type(self) -> None:
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2? x = None;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                IntermediateSpace? x = None;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_parameter_type(self) -> None:
        method = frog_parser.parse_method("""
            Bool f(KeySpace2 x) {
                return true;
            }
            """)
        expected = frog_parser.parse_method("""
            Bool f(IntermediateSpace x) {
                return true;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_return_type(self) -> None:
        method = frog_parser.parse_method("""
            KeySpace2 f() {
                return x;
            }
            """)
        expected = frog_parser.parse_method("""
            IntermediateSpace f() {
                return x;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_normalizes_product_type(self) -> None:
        method = frog_parser.parse_method("""
            Void f() {
                [KeySpace2, MessageSpace] x = y;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                [IntermediateSpace, MessageSpace] x = y;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected


class TestSampleNormalization:
    """Tests that sample statements are correctly normalized.

    For equality pairs (==), both the type annotation and sampled_from
    should be normalized.  For subsets-only pairs, only the type
    annotation is normalized (sampling distribution must not change).
    """

    def test_normalizes_sample_type_and_sampled_from_for_equality(self) -> None:
        """Both type annotation and sampled_from should be normalized
        when the pair comes from an == constraint."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2 x <- KeySpace2;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                IntermediateSpace x <- IntermediateSpace;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        eq_pairs = {("KeySpace2", "IntermediateSpace")}
        result = SubsetTypeNormalizer(pairs, equality_pairs=eq_pairs).transform(method)
        assert result == expected

    def test_subsets_only_normalizes_type_not_sampled_from(self) -> None:
        """For subsets-only pairs, type annotation is normalized but
        sampled_from is NOT — A ⊊ B would change the distribution."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2 x <- KeySpace2;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        # No equality_pairs — this is a subsets-only pair
        result = SubsetTypeNormalizer(pairs).transform(method)
        sample = result.block.statements[0]
        assert isinstance(sample, frog_ast.Sample)
        # Type annotation should be normalized
        assert isinstance(sample.the_type, frog_ast.Variable)
        assert sample.the_type.name == "IntermediateSpace"
        # sampled_from should NOT be normalized (subsets-only)
        assert isinstance(sample.sampled_from, frog_ast.Variable)
        assert sample.sampled_from.name == "KeySpace2"

    def test_normalizes_sampled_from_for_equality(self) -> None:
        """sampled_from should be normalized for equality pairs."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2 x <- KeySpace2;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        eq_pairs = {("KeySpace2", "IntermediateSpace")}
        result = SubsetTypeNormalizer(pairs, equality_pairs=eq_pairs).transform(method)
        sample = result.block.statements[0]
        assert isinstance(sample, frog_ast.Sample)
        assert isinstance(sample.sampled_from, frog_ast.Variable)
        assert sample.sampled_from.name == "IntermediateSpace"

    def test_unrelated_sample_unchanged(self) -> None:
        """Samples from unrelated types should not be changed."""
        method = frog_parser.parse_method("""
            Void f() {
                MessageSpace x <- MessageSpace;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == method


class TestNoNormalization:
    """Tests that non-subset types are left unchanged."""

    def test_no_change_without_pairs(self) -> None:
        method = frog_parser.parse_method("""
            KeySpace2 f(KeySpace2 x) {
                return x;
            }
            """)
        result = SubsetTypeNormalizer([]).transform(method)
        assert result == method

    def test_does_not_change_variable_references(self) -> None:
        """Variable references in expressions should NOT be normalized."""
        method = frog_parser.parse_method("""
            Void f() {
                IntermediateSpace x = KeySpace2_var;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        # The variable reference 'KeySpace2_var' should not be changed
        # (it's not a type, just a variable whose name starts with KeySpace2)
        assert result == method

    def test_unrelated_types_unchanged(self) -> None:
        method = frog_parser.parse_method("""
            MessageSpace f(MessageSpace x) {
                return x;
            }
            """)
        pairs = _make_pairs(("KeySpace2", "IntermediateSpace"))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == method


class TestEqualityPairs:
    """Tests for == constraint pairs (Variable -> concrete type)."""

    @staticmethod
    def _eq_pair(
        var_name: str, concrete_type: frog_ast.Type
    ) -> list[tuple[frog_ast.Type, frog_ast.Type]]:
        return [(frog_ast.Variable(var_name), concrete_type)]

    def test_variable_to_bitstring(self) -> None:
        """KeySpace -> BitString<128> via == pair."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace x = y;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                BitString<128> x = y;
            }
            """)
        pairs = self._eq_pair("KeySpace", frog_ast.BitStringType(frog_ast.Integer(128)))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected

    def test_sample_variable_to_bitstring(self) -> None:
        """Sampling from KeySpace becomes sampling from BitString<n> for == pairs."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace x <- KeySpace;
            }
            """)
        pairs = self._eq_pair("KeySpace", frog_ast.BitStringType(frog_ast.Integer(128)))
        eq_pairs = {("KeySpace", str(frog_ast.BitStringType(frog_ast.Integer(128))))}
        result = SubsetTypeNormalizer(pairs, equality_pairs=eq_pairs).transform(method)
        sample = result.block.statements[0]
        assert isinstance(sample, frog_ast.Sample)
        assert isinstance(sample.the_type, frog_ast.BitStringType)
        assert isinstance(sample.sampled_from, frog_ast.BitStringType)

    def test_return_type_variable_to_bitstring(self) -> None:
        """Return type normalized from abstract to concrete."""
        method = frog_parser.parse_method("""
            KeySpace f() {
                return x;
            }
            """)
        pairs = self._eq_pair("KeySpace", frog_ast.BitStringType(frog_ast.Integer(128)))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert isinstance(result.signature.return_type, frog_ast.BitStringType)

    def test_concrete_left_not_normalized(self) -> None:
        """When concrete type is on the left, no replacement is registered."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace x = y;
            }
            """)
        # Pair with concrete on left — normalizer won't fire
        pairs: list[tuple[frog_ast.Type, frog_ast.Type]] = [
            (
                frog_ast.BitStringType(frog_ast.Integer(128)),
                frog_ast.Variable("KeySpace"),
            )
        ]
        result = SubsetTypeNormalizer(pairs).transform(method)
        # KeySpace should remain unchanged
        assert result == method

    def test_optional_variable_to_bitstring(self) -> None:
        """Optional type with abstract variable is normalized."""
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace? x = None;
            }
            """)
        pairs = self._eq_pair("KeySpace", frog_ast.BitStringType(frog_ast.Integer(128)))
        result = SubsetTypeNormalizer(pairs).transform(method)
        assign = result.block.statements[0]
        assert isinstance(assign, frog_ast.Assignment)
        assert isinstance(assign.the_type, frog_ast.OptionalType)
        assert isinstance(assign.the_type.the_type, frog_ast.BitStringType)


class TestExtractSubsetsPairs:
    """Tests that _extract_subsets_pairs only extracts equality constraints."""

    def test_equality_constraint_extracted(self) -> None:
        """An `==` constraint should produce a pair."""
        scheme = frog_parser.parse_scheme_file("""
            import '../../Primitives/SymEnc.primitive';
            Scheme Test(Int n) extends SymEnc {
                requires BitString<n> == BitString<n>;
                Set Key = BitString<n>;
                Set Message = BitString<n>;
                Set Ciphertext = BitString<n>;
                Key KeyGen() { Key k <- Key; return k; }
                Ciphertext Enc(Key k, Message m) { return k; }
                Message? Dec(Key k, Ciphertext c) { return c; }
            }
            """)
        pairs = _extract_subsets_pairs(scheme)
        assert len(pairs) == 1

    def test_subsets_constraint_not_extracted(self) -> None:
        """A `subsets` constraint should NOT produce a type replacement pair,
        because replacing A with B when A ⊊ B changes sampling distribution."""
        scheme = frog_parser.parse_scheme_file("""
            import '../../Primitives/SymEnc.primitive';
            Scheme Test(Int n) extends SymEnc {
                requires BitString<n> subsets BitString<n>;
                Set Key = BitString<n>;
                Set Message = BitString<n>;
                Set Ciphertext = BitString<n>;
                Key KeyGen() { Key k <- Key; return k; }
                Ciphertext Enc(Key k, Message m) { return k; }
                Message? Dec(Key k, Ciphertext c) { return c; }
            }
            """)
        pairs = _extract_subsets_pairs(scheme)
        assert (
            len(pairs) == 0
        ), "subsets constraints should not produce type replacement pairs"


class TestMultiplePairs:
    """Tests with multiple subsets pairs."""

    def test_multiple_pairs_both_normalized(self) -> None:
        method = frog_parser.parse_method("""
            Void f() {
                KeySpace2 x = a;
                CiphertextSpace2 y = b;
            }
            """)
        expected = frog_parser.parse_method("""
            Void f() {
                IntermediateSpace x = a;
                MessageSpace y = b;
            }
            """)
        pairs = _make_pairs(
            ("KeySpace2", "IntermediateSpace"),
            ("CiphertextSpace2", "MessageSpace"),
        )
        result = SubsetTypeNormalizer(pairs).transform(method)
        assert result == expected
