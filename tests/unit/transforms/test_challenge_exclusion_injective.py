"""Tests for ChallengeExclusionRFToUniform with ``injective`` function wrappers.

These tests verify that the transform can see through calls to injective
primitive methods when comparing RF arguments between Initialize and oracle
methods.  This is the mechanism that makes the starfortress UG-KEM-CCA
proof's PRF randomness step verify automatically.
"""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.random_functions import (
    ChallengeExclusionRFToUniformTransformer,
)


def _make_namespace_with_injective() -> frog_ast.Namespace:
    """Build a proof namespace containing a primitive with an injective method.

    Primitive ``E`` has method ``Encode(BitString<8>) -> BitString<8>``
    marked ``deterministic injective``.
    """
    prim = frog_parser.parse_primitive_file("""
        Primitive E(Int n) {
            deterministic injective BitString<n> Encode(BitString<n> x);
        }
        """)
    return {"E": prim}


def _make_namespace_no_injective() -> frog_ast.Namespace:
    """Build a namespace where the method is NOT injective."""
    prim = frog_parser.parse_primitive_file("""
        Primitive E(Int n) {
            BitString<n> Encode(BitString<n> x);
        }
        """)
    return {"E": prim}


def _transform_with_namespace(
    source: str, namespace: frog_ast.Namespace
) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return ChallengeExclusionRFToUniformTransformer().transform(
        game, proof_namespace=namespace
    )


# ---- Positive tests: injective wrappers should be seen through ----


def test_injective_encode_wrapping_challenge_field() -> None:
    """RF args wrapped in injective Encode: Init has E.Encode(field), oracle
    has E.Encode(local) behind guard -> transform should fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result = RF(E.Encode(ct_star));
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(ct));
            return result;
        }
    }
    """
    expected = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result <- BitString<16>;
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(ct));
            return result;
        }
    }
    """
    ns = _make_namespace_with_injective()
    result = _transform_with_namespace(source, ns)
    expected_ast = frog_parser.parse_game(expected)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


def test_injective_in_concatenation() -> None:
    """Injective wrappers inside a concatenation: Init has
    E.Encode(field1) || E.Encode(field2), oracle has E.Encode(v1) || E.Encode(v2)
    behind tuple guard -> transform should fire."""
    source = """
    Game Test() {
        BitString<8> field1;
        BitString<8> field2;
        Function<BitString<16>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<16>, BitString<16>>;
            field1 = 1;
            field2 = 2;
            BitString<16> result = RF(E.Encode(field1) || E.Encode(field2));
            return result;
        }
        BitString<16> Query(BitString<8> v1, BitString<8> v2) {
            if ([v1, v2] == [field1, field2]) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(v1) || E.Encode(v2));
            return result;
        }
    }
    """
    expected = """
    Game Test() {
        BitString<8> field1;
        BitString<8> field2;
        Function<BitString<16>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<16>, BitString<16>>;
            field1 = 1;
            field2 = 2;
            BitString<16> result <- BitString<16>;
            return result;
        }
        BitString<16> Query(BitString<8> v1, BitString<8> v2) {
            if ([v1, v2] == [field1, field2]) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(v1) || E.Encode(v2));
            return result;
        }
    }
    """
    ns = _make_namespace_with_injective()
    result = _transform_with_namespace(source, ns)
    expected_ast = frog_parser.parse_game(expected)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


# ---- Negative tests: non-injective wrappers should NOT be seen through ----


def test_non_injective_encode_blocks_transform() -> None:
    """Same structure as the positive test, but the method is NOT marked
    injective -> transform should NOT fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result = RF(E.Encode(ct_star));
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(ct));
            return result;
        }
    }
    """
    ns = _make_namespace_no_injective()
    result = _transform_with_namespace(source, ns)
    # Should be unchanged — the Encode wrapping blocks the structural check
    original = frog_parser.parse_game(source)
    assert result == original


def test_no_namespace_blocks_transform() -> None:
    """Without a proof namespace, injective wrappers are not recognized
    -> transform should NOT fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result = RF(E.Encode(ct_star));
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                return 0;
            }
            BitString<16> result = RF(E.Encode(ct));
            return result;
        }
    }
    """
    result = _transform_with_namespace(source, {})
    original = frog_parser.parse_game(source)
    assert result == original


def test_different_functions_block_transform() -> None:
    """Init has E.Encode(field), oracle has F.Other(local) — different
    function names -> transform should NOT fire."""
    source = """
    Game Test() {
        BitString<8> ct_star;
        Function<BitString<8>, BitString<16>> RF;
        BitString<16> Initialize() {
            RF <- Function<BitString<8>, BitString<16>>;
            ct_star = 42;
            BitString<16> result = RF(E.Encode(ct_star));
            return result;
        }
        BitString<16> Query(BitString<8> ct) {
            if (ct == ct_star) {
                return 0;
            }
            BitString<16> result = RF(F.Other(ct));
            return result;
        }
    }
    """
    ns = _make_namespace_with_injective()
    result = _transform_with_namespace(source, ns)
    original = frog_parser.parse_game(source)
    assert result == original
