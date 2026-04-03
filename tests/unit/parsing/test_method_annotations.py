"""Tests for parsing ``deterministic`` and ``injective`` method annotations
on primitive declarations."""

from proof_frog import frog_ast, frog_parser


def test_deterministic_annotation() -> None:
    """A method marked ``deterministic`` should have the flag set."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive F(Int lambda, Int out) {
            deterministic BitString<out> evaluate(BitString<lambda> k);
        }
        """
    )
    assert len(primitive.methods) == 1
    assert primitive.methods[0].deterministic is True
    assert primitive.methods[0].injective is False


def test_injective_annotation() -> None:
    """A method marked ``injective`` should have the flag set."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            injective BitString<n> Encode(BitString<n> x);
        }
        """
    )
    assert len(primitive.methods) == 1
    assert primitive.methods[0].deterministic is False
    assert primitive.methods[0].injective is True


def test_both_annotations() -> None:
    """A method with both modifiers should have both flags set."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic injective BitString<n> Encode(BitString<n> x);
        }
        """
    )
    assert len(primitive.methods) == 1
    assert primitive.methods[0].deterministic is True
    assert primitive.methods[0].injective is True


def test_both_annotations_reversed_order() -> None:
    """Modifier order should not matter."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            injective deterministic BitString<n> Encode(BitString<n> x);
        }
        """
    )
    assert len(primitive.methods) == 1
    assert primitive.methods[0].deterministic is True
    assert primitive.methods[0].injective is True


def test_no_annotations() -> None:
    """A method without modifiers should have both flags False."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive F(Int lambda) {
            BitString<lambda> evaluate(BitString<lambda> k);
        }
        """
    )
    assert len(primitive.methods) == 1
    assert primitive.methods[0].deterministic is False
    assert primitive.methods[0].injective is False


def test_mixed_annotations_multiple_methods() -> None:
    """Different methods can have different annotations."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive K(Int n) {
            [BitString<n>, BitString<n>] KeyGen();
            deterministic BitString<n> Decaps(BitString<n> sk, BitString<n> ct);
            deterministic injective BitString<n> Encode(BitString<n> x);
        }
        """
    )
    assert len(primitive.methods) == 3

    keygen = primitive.methods[0]
    assert keygen.name == "KeyGen"
    assert keygen.deterministic is False
    assert keygen.injective is False

    decaps = primitive.methods[1]
    assert decaps.name == "Decaps"
    assert decaps.deterministic is True
    assert decaps.injective is False

    encode = primitive.methods[2]
    assert encode.name == "Encode"
    assert encode.deterministic is True
    assert encode.injective is True


def test_str_includes_modifiers() -> None:
    """The __str__ representation should include modifiers."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic injective BitString<n> Encode(BitString<n> x);
        }
        """
    )
    method_str = str(primitive.methods[0])
    assert "deterministic" in method_str
    assert "injective" in method_str
    assert "Encode" in method_str


def test_str_no_modifiers() -> None:
    """The __str__ representation should not include modifiers when absent."""
    primitive = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            BitString<n> Evaluate(BitString<n> x);
        }
        """
    )
    method_str = str(primitive.methods[0])
    assert "deterministic" not in method_str
    assert "injective" not in method_str
