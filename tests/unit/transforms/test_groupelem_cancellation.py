"""Tests for GroupElemCancellation and GroupElemExponentCombination."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import (
    GroupElemCancellationTransformer,
    GroupElemExponentCombinationTransformer,
)


def _groupelem_type() -> frog_ast.GroupElemType:
    return frog_ast.GroupElemType(frog_ast.Variable("G"))


def _modint_type() -> frog_ast.ModIntType:
    return frog_ast.ModIntType(frog_ast.FieldAccess(frog_ast.Variable("G"), "order"))


def _type_map() -> dict[str, frog_ast.Type]:
    return {
        "G": frog_ast.GroupType(),
        "a": _groupelem_type(),
        "b": _groupelem_type(),
        "x": _groupelem_type(),
        "m": _groupelem_type(),
    }


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: x * m / x  -->  m
        (
            """
            GroupElem<G> f(GroupElem<G> x, GroupElem<G> m) {
                return x * m / x;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> x, GroupElem<G> m) {
                return m;
            }
            """,
        ),
        # Partial: a * b * m / a  -->  b * m
        (
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b, GroupElem<G> m) {
                return a * b * m / a;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b, GroupElem<G> m) {
                return b * m;
            }
            """,
        ),
        # No negatives: a * b stays unchanged
        (
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b) {
                return a * b;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b) {
                return a * b;
            }
            """,
        ),
        # No matching terms: a * m / b stays unchanged
        (
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b, GroupElem<G> m) {
                return a * m / b;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> a, GroupElem<G> b, GroupElem<G> m) {
                return a * m / b;
            }
            """,
        ),
        # Complex expression terms: (g^a) * m / (g^a) --> m
        (
            """
            GroupElem<G> f(GroupElem<G> m, ModInt<G.order> a) {
                return (G.generator ^ a) * m / (G.generator ^ a);
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> m, ModInt<G.order> a) {
                return m;
            }
            """,
        ),
    ],
    ids=[
        "basic-cancel",
        "partial-cancel",
        "no-negatives",
        "no-match",
        "complex-expr-cancel",
    ],
)
def test_groupelem_cancellation(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    tm = _type_map()
    transformed = GroupElemCancellationTransformer(tm).transform(method_ast)

    assert transformed == expected_ast


def test_all_positives_cancel_returns_identity() -> None:
    """When all positive terms cancel, return G.identity."""
    method = """
    GroupElem<G> f(GroupElem<G> x) {
        return x / x;
    }
    """
    expected = """
    GroupElem<G> f(GroupElem<G> x) {
        return G.identity;
    }
    """
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    tm = _type_map()
    transformed = GroupElemCancellationTransformer(tm).transform(method_ast)
    assert transformed == expected_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # g^a * g^b = g^(a + b)
        (
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return (G.generator ^ a) * (G.generator ^ b);
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return G.generator ^ (a + b);
            }
            """,
        ),
        # g^a / g^b = g^(a - b)
        (
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return (G.generator ^ a) / (G.generator ^ b);
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return G.generator ^ (a - b);
            }
            """,
        ),
        # No combination: different bases
        (
            """
            GroupElem<G> f(GroupElem<G> x, GroupElem<G> y, ModInt<G.order> a, ModInt<G.order> b) {
                return (x ^ a) * (y ^ b);
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> x, GroupElem<G> y, ModInt<G.order> a, ModInt<G.order> b) {
                return (x ^ a) * (y ^ b);
            }
            """,
        ),
        # No combination: mixed exponent types (ModInt ^ Int)
        (
            """
            GroupElem<G> f(ModInt<G.order> a, Int n) {
                return (G.generator ^ a) * (G.generator ^ n);
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, Int n) {
                return (G.generator ^ a) * (G.generator ^ n);
            }
            """,
        ),
    ],
    ids=[
        "same-base-multiply",
        "same-base-divide",
        "different-bases-no-combine",
        "no-combine-mixed-exponent-types",
    ],
)
def test_groupelem_exponent_combination(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    tm = _type_map()
    tm["y"] = _groupelem_type()
    # Override a/b to ModInt for exponent combination tests
    tm["a"] = _modint_type()
    tm["b"] = _modint_type()
    tm["n"] = frog_ast.IntType()
    transformed = GroupElemExponentCombinationTransformer(tm).transform(method_ast)

    assert transformed == expected_ast
