"""Tests for the exact ModInt / group-element normal forms in ``_algebra``.

The decision procedure must only ever answer "equal" for expressions that
are equal for every value of their free names; it may answer "not equal"
for equal ones (incompleteness), so every positive case below is an exact
identity and every negative case a genuine difference (or a case the
algebra must refuse to fold).
"""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._algebra import Normalizer, node_count
from proof_frog.visitors import NameTypeMap


def _group() -> frog_ast.Variable:
    return frog_ast.Variable("G")


def _zq() -> frog_ast.ModIntType:
    return frog_ast.ModIntType(frog_ast.FieldAccess(_group(), "order"))


def _ge() -> frog_ast.GroupElemType:
    return frog_ast.GroupElemType(_group())


def _type_map() -> NameTypeMap:
    tm = NameTypeMap()
    tm.set("G", frog_ast.GroupType())
    for name in ("sk", "d", "u", "r", "a", "b", "s", "D"):
        tm.set(name, _zq())
    for name in ("pk", "m", "x", "P"):
        tm.set(name, _ge())
    tm.set("n", frog_ast.IntType())
    tm.set("k", frog_ast.ModIntType(frog_ast.Variable("q")))
    tm.set("H", frog_ast.FunctionType(_ge(), _zq()))
    return tm


def _expr(text: str) -> frog_ast.Expression:
    return frog_parser.parse_expression(text)


@pytest.mark.parametrize(
    "left,right",
    [
        # The UPKE update: d + H(pk^u) - H(U^sk) with pk = g^sk cancels.
        (
            "sk + ((d + H((G.generator ^ sk) ^ u)) - H((G.generator ^ u) ^ sk))",
            "sk + d",
        ),
        ("G.generator ^ sk * G.generator ^ d", "G.generator ^ (sk + d)"),
        ("(pk * G.generator ^ d) ^ r", "pk ^ r * G.generator ^ (d * r)"),
        ("pk / pk", "G.identity"),
        ("(G.generator ^ (s - D)) ^ r * (G.generator ^ r) ^ D", "G.generator ^ (s * r)"),
        ("a * (b + 1) - a", "a * b"),
        ("-(-a)", "a"),
        ("(a + b) ^ 2", "a * a + 2 * a * b + b * b"),
        ("[a + b, pk * G.identity]", "[b + a, pk]"),
        # Int exponents fold as well.
        ("G.generator ^ n * G.generator ^ n", "G.generator ^ (2 * n)"),
    ],
)
def test_equal_identities(left: str, right: str) -> None:
    normalizer = Normalizer(_type_map())
    assert normalizer.equal(_expr(left), _expr(right))


@pytest.mark.parametrize(
    "left,right",
    [
        ("sk + d", "sk - d"),
        ("G.generator ^ sk", "G.generator ^ d"),
        ("H(G.generator ^ (sk * u))", "H(G.generator ^ (sk * d))"),
        ("a * b", "a + b"),
        # A ModInt exponent whose modulus is not the group's order is not
        # folded: g^k * g^k is not g^(2k) reduced mod q.
        ("G.generator ^ k * G.generator ^ k", "G.generator ^ (2 * k)"),
        ("pk ^ r", "G.generator ^ r"),
    ],
)
def test_not_equal(left: str, right: str) -> None:
    normalizer = Normalizer(_type_map())
    assert not normalizer.equal(_expr(left), _expr(right))


def test_canonical_is_order_independent() -> None:
    normalizer = Normalizer(_type_map())
    first = normalizer.canonical(_expr("H(G.generator ^ (u * sk)) + d"))
    second = Normalizer(_type_map()).canonical(_expr("d + H((G.generator ^ sk) ^ u)"))
    assert first == second


def test_canonical_rebuild_is_smaller_after_cancellation() -> None:
    normalizer = Normalizer(_type_map())
    original = _expr("sk + ((d + H(G.generator ^ (sk * u))) - H(G.generator ^ (u * sk)))")
    rebuilt = normalizer.canonical(original)
    assert normalizer.equal(rebuilt, _expr("sk + d"))
    assert node_count(rebuilt) < node_count(original)
