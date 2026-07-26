"""Tests for GroupElemSimplification: power-of-power rule for GroupElem."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import GroupElemSimplificationTransformer


def _groupelem_type() -> frog_ast.GroupElemType:
    return frog_ast.GroupElemType(frog_ast.Variable("G"))


def _modint_type() -> frog_ast.ModIntType:
    return frog_ast.ModIntType(frog_ast.FieldAccess(frog_ast.Variable("G"), "order"))


def _type_map() -> dict[str, frog_ast.Type]:
    return {
        "G": frog_ast.GroupType(),
        "a": _modint_type(),
        "b": _modint_type(),
        "c": _modint_type(),
        "r": _modint_type(),
        "s": _modint_type(),
        "n": frog_ast.IntType(),
        "pk": _groupelem_type(),
        "m": _groupelem_type(),
        "x": _groupelem_type(),
    }


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic power-of-power: (g ^ a) ^ b  -->  g ^ (a * b)
        (
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return (G.generator ^ a) ^ b;
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b) {
                return G.generator ^ (a * b);
            }
            """,
        ),
        # Nested: ((g ^ a) ^ b) ^ c  -->  g ^ (a * b * c)
        (
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b, ModInt<G.order> c) {
                return ((G.generator ^ a) ^ b) ^ c;
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, ModInt<G.order> b, ModInt<G.order> c) {
                return G.generator ^ (a * b * c);
            }
            """,
        ),
        # Variable base that is GroupElem-typed: (pk ^ r) ^ s  -->  pk ^ (r * s)
        (
            """
            GroupElem<G> f(GroupElem<G> pk, ModInt<G.order> r, ModInt<G.order> s) {
                return (pk ^ r) ^ s;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> pk, ModInt<G.order> r, ModInt<G.order> s) {
                return pk ^ (r * s);
            }
            """,
        ),
        # No fire: single exponentiation (no nested power)
        (
            """
            GroupElem<G> f(ModInt<G.order> a) {
                return G.generator ^ a;
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a) {
                return G.generator ^ a;
            }
            """,
        ),
        # No fire: mixed exponent types (ModInt ^ Int) — MULTIPLY would be ill-typed
        (
            """
            GroupElem<G> f(ModInt<G.order> a, Int n) {
                return (G.generator ^ a) ^ n;
            }
            """,
            """
            GroupElem<G> f(ModInt<G.order> a, Int n) {
                return (G.generator ^ a) ^ n;
            }
            """,
        ),
    ],
    ids=[
        "basic-power-of-power",
        "nested-triple",
        "variable-base",
        "no-fire-single-exp",
        "no-fire-mixed-exponent-types",
    ],
)
def test_groupelem_simplification(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    tm = _type_map()
    # Apply repeatedly for nested cases
    transformed = method_ast
    while True:
        new = GroupElemSimplificationTransformer(tm).transform(transformed)
        if new == transformed:
            break
        transformed = new

    assert transformed == expected_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # g ^ 0 = G.identity
        (
            """
            GroupElem<G> f() {
                return G.generator ^ 0;
            }
            """,
            """
            GroupElem<G> f() {
                return G.identity;
            }
            """,
        ),
        # g ^ 1 = g
        (
            """
            GroupElem<G> f() {
                return G.generator ^ 1;
            }
            """,
            """
            GroupElem<G> f() {
                return G.generator;
            }
            """,
        ),
        # pk ^ 1 = pk
        (
            """
            GroupElem<G> f(GroupElem<G> pk) {
                return pk ^ 1;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> pk) {
                return pk;
            }
            """,
        ),
        # identity * g = g
        (
            """
            GroupElem<G> f(GroupElem<G> x) {
                return G.identity * x;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> x) {
                return x;
            }
            """,
        ),
        # g * identity = g
        (
            """
            GroupElem<G> f(GroupElem<G> x) {
                return x * G.identity;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> x) {
                return x;
            }
            """,
        ),
        # g / identity = g
        (
            """
            GroupElem<G> f(GroupElem<G> x) {
                return x / G.identity;
            }
            """,
            """
            GroupElem<G> f(GroupElem<G> x) {
                return x;
            }
            """,
        ),
    ],
    ids=[
        "exp-zero-identity",
        "exp-one-generator",
        "exp-one-variable",
        "identity-mul-left",
        "identity-mul-right",
        "div-by-identity",
    ],
)
def test_groupelem_identity_rules(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    tm = _type_map()
    transformed = GroupElemSimplificationTransformer(tm).transform(method_ast)

    assert transformed == expected_ast


def test_f285_non_group_identity_field_not_cancelled() -> None:
    """F-285/F-286: `x * E.identity` where `E` is NOT a Group (e.g. a scheme
    instance whose `identity` is a plain `Int` field) must not be cancelled --
    the multiplicative-identity rule required a type/group check, not a bare
    name-match on `.identity`."""
    method = frog_parser.parse_method(
        """
        Int f(Int x) {
            return x * E.identity;
        }
        """
    )
    # `E` is typed as a non-group (Int stands in for a scheme instance); `G`
    # remains a genuine Group so the positive path is unaffected.
    tm = {"E": frog_ast.IntType(), "x": frog_ast.IntType(), "G": frog_ast.GroupType()}
    out = GroupElemSimplificationTransformer(tm).transform(method)
    assert "x * E.identity" in str(out)  # not cancelled to x


def test_f285_genuine_group_identity_still_cancelled() -> None:
    """Positive control: `x * G.identity` with `G` typed Group still cancels."""
    method = frog_parser.parse_method(
        """
        GroupElem<G> f(GroupElem<G> x) {
            return x * G.identity;
        }
        """
    )
    tm = {"G": frog_ast.GroupType(), "x": frog_ast.GroupElemType(frog_ast.Variable("G"))}
    out = GroupElemSimplificationTransformer(tm).transform(method)
    assert "G.identity" not in str(out)  # cancelled -> return x
