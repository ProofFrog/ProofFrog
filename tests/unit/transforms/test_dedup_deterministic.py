"""Tests for DeduplicateDeterministicCalls transform.

Verifies that duplicate calls to deterministic primitive methods within a
single block are extracted into a fresh local variable, while non-deterministic
calls and single occurrences are left untouched.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    DeduplicateDeterministicCallsTransformer,
)


def _make_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is deterministic."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


def _make_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is NOT deterministic."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


class TestDeduplicateDeterministicCalls:
    """Tests for DeduplicateDeterministicCallsTransformer."""

    def test_duplicate_in_tuple(self) -> None:
        """Two identical deterministic calls in a tuple literal are extracted."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                return [__determ_0__, __determ_0__];
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_duplicate_across_statements(self) -> None:
        """Two assignments with the same deterministic call are deduplicated."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> b = G.evaluate(k);
                return [a, b];
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                BitString<n> b = __determ_0__;
                return [a, b];
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_triple_occurrence(self) -> None:
        """Three identical calls are all replaced with one variable."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                BitString<n> a = G.evaluate(k);
                BitString<n> b = G.evaluate(k);
                BitString<n> c = G.evaluate(k);
                return [a, b, c];
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                BitString<n> __determ_0__ = G.evaluate(k);
                BitString<n> a = __determ_0__;
                BitString<n> b = __determ_0__;
                BitString<n> c = __determ_0__;
                return [a, b, c];
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_nondeterministic_not_deduped(self) -> None:
        """Non-deterministic calls should NOT be deduplicated."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """
        )
        original = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                return [G.evaluate(k), G.evaluate(k)];
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_nondet_namespace()
        ).transform(method)
        assert result == original

    def test_single_occurrence_unchanged(self) -> None:
        """A single deterministic call should not be extracted."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                return G.evaluate(k);
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f(BitString<n> k) {
                return G.evaluate(k);
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_different_args_not_deduped(self) -> None:
        """Same function with different args should not be deduplicated."""
        method = frog_parser.parse_method(
            """
            Void f(BitString<n> k, BitString<n> j) {
                return [G.evaluate(k), G.evaluate(j)];
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Void f(BitString<n> k, BitString<n> j) {
                return [G.evaluate(k), G.evaluate(j)];
            }
            """
        )
        result = DeduplicateDeterministicCallsTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected
