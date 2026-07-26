"""Tests for the shared write/rebind-detection helper ``reassigns_or_rebinds``.

It backs the RC1 interference checks in many structural-substitution passes, so
its node-kind coverage must match its "node-kind-complete" docstring."""

from proof_frog import frog_parser
from proof_frog.visitors import reassigns_or_rebinds


def _block(body: str):
    return frog_parser.parse_method(body).block


def test_f196_bare_declaration_counts_as_rebind() -> None:
    """F-196: a no-initializer local re-declaration ``T x;`` shadows the name and
    must be reported as a rebind -- otherwise a scope-blind structural
    substitution could capture the inner binding."""
    block = _block(
        """
        Int O(Int y) {
            Int x;
            return y;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is True


def test_f196_unrelated_declaration_is_not_a_rebind() -> None:
    """Control: a declaration of a different name does not count."""
    block = _block(
        """
        Int O(Int y) {
            Int w;
            return y;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is False


def test_typed_initializer_declaration_still_counts() -> None:
    """A typed ``T x = e;`` is an Assignment and was already caught via the
    l-value path; confirm the F-196 change does not disturb that."""
    block = _block(
        """
        Int O(Int y) {
            Int x = y + 1;
            return x;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is True
