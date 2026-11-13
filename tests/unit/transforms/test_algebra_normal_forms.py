"""Tests for the exact ModInt / group-element normal forms in ``_algebra``.

The decision procedure must only ever answer "equal" for expressions that
are equal for every value of their free names; it may answer "not equal"
for equal ones (incompleteness), so every positive case below is an exact
identity and every negative case a genuine difference (or a case the
algebra must refuse to fold).
"""

from typing import Optional

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
        # A masked key update: d + H(pk^u) - H(U^sk) with pk = g^sk cancels.
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


# F-357: FrogLang has no ModInt<q> literal, so a ModInt<q> value that is a
# nonzero constant must not be rebuilt as an Int literal (2 is not 2 mod q).


@pytest.mark.parametrize(
    "text,value",
    [
        ("((k + 1) + 1) - k", 2),
        ("((k - k) + 1) + 1", 2),
        ("(k + 1) * (k - 1) - k * k", -1),
        ("(sk + 1) - sk", 1),
    ],
)
def test_f357_nonzero_modint_constant_is_kept_as_written(text: str, value: int) -> None:
    normalizer = Normalizer(_type_map())
    original = _expr(text)
    assert normalizer.canonical(original) == original
    assert [kept.value for kept in normalizer.kept_constants] == [value]


def test_f357_kept_constant_records_its_modulus() -> None:
    normalizer = Normalizer(_type_map())
    normalizer.canonical(_expr("((k + 1) + 1) - k"))
    (kept,) = normalizer.kept_constants
    assert kept.modulus == frog_ast.Variable("q")


def test_f357_constant_exponent_of_other_modulus_is_kept() -> None:
    # The exponent is a ModInt<q> value, q not the group order: an atom of
    # the group algebra whose own arithmetic must keep its modulus.
    normalizer = Normalizer(_type_map())
    original = _expr("G.generator ^ (((k + 1) + 1) - k)")
    assert normalizer.canonical(original) == original
    assert [kept.value for kept in normalizer.kept_constants] == [2]


def test_f357_constant_inside_atom_is_kept() -> None:
    normalizer = Normalizer(_type_map())
    rebuilt = normalizer.canonical(_expr("d + H(G.generator ^ (((k + 1) + 1) - k))"))
    assert rebuilt == _expr("d + H(G.generator ^ (((k + 1) + 1) - k))")
    assert len(normalizer.kept_constants) == 1


def test_f357_zero_modint_constant_is_still_rebuilt() -> None:
    # 0 mod q is 0 for every q.
    normalizer = Normalizer(_type_map())
    assert normalizer.canonical(_expr("(k + 1) - (1 + k)")) == frog_ast.Integer(0)
    assert not normalizer.kept_constants


def test_f357_modint_polynomial_with_constant_term_is_kept() -> None:
    # The value is k + 2, which has no rebuild without an Int literal next to
    # a ModInt operand (FrogLang refuses k + 2), so it is kept as written.
    normalizer = Normalizer(_type_map())
    original = _expr("((k + 1) + 1) - 0")
    assert normalizer.canonical(original) == original
    assert [kept.value for kept in normalizer.kept_constants] == [None]


def test_f357_int_constant_still_folds() -> None:
    normalizer = Normalizer(_type_map())
    assert normalizer.canonical(_expr("(n + 2) - n")) == frog_ast.Integer(2)
    assert not normalizer.kept_constants


def test_f357_group_order_exponent_constant_still_folds() -> None:
    # An exponent of the group's own order is read modulo that order, where
    # the Int literal has the same effect.
    normalizer = Normalizer(_type_map())
    rebuilt = normalizer.canonical(_expr("G.generator ^ ((sk + 2) - sk)"))
    assert rebuilt == _expr("G.generator ^ 2")
    assert not normalizer.kept_constants


def test_f357_rebuild_of_constant_modint_form() -> None:
    import sympy

    from proof_frog.transforms._algebra import ModIntForm

    normalizer = Normalizer(_type_map())
    q = frog_ast.Variable("q")
    assert normalizer.rebuild(ModIntForm(q, sympy.Integer(2))) is None
    assert normalizer.rebuild(ModIntForm(q, sympy.Integer(0))) == frog_ast.Integer(0)
    assert normalizer.rebuild(ModIntForm(None, sympy.Integer(2))) == frog_ast.Integer(2)


# F-378: a ModInt<q> value equal to 0 is rebuilt as the Int literal 0 only
# where an Int operand does not change the operation around it. As the base
# of a power (0 ^ 0 is the Int 1) or an operand of a division (0 / 0 is an
# Int division) it is kept as written.


@pytest.mark.parametrize(
    "text,positions",
    [
        ("(k - k) ^ n", ["the base of a power"]),
        ("(k - k) / (k - k)", ["an operand of a division"] * 2),
        # k + 1 is kept too, for its constant term (position None).
        ("(k + 1) / ((k + 1) - (1 + k))", [None, "an operand of a division"]),
        ("H(G.generator ^ ((k - k) / k))", ["an operand of a division"]),
    ],
)
def test_f378_zero_in_int_sensitive_position_is_kept(
    text: str, positions: list[Optional[str]]
) -> None:
    normalizer = Normalizer(_type_map())
    original = _expr(text)
    assert normalizer.canonical(original) == original
    assert [kept.position for kept in normalizer.kept_constants] == positions
    assert all(
        kept.value == (None if kept.position is None else 0)
        for kept in normalizer.kept_constants
    )


def test_f378_zero_power_base_inside_atom_is_kept() -> None:
    # A power with a non-literal exponent is an atom of the polynomial; its
    # base keeps the ModInt zero, so the sum is (k - k) ^ n twice, not the
    # Int expression 0 ^ n + 0 ^ n.
    normalizer = Normalizer(_type_map())
    rebuilt = normalizer.canonical(_expr("((k - k) ^ n + k) + ((k - k) ^ n - k)"))
    assert rebuilt == _expr("(k - k) ^ n + (k - k) ^ n")


def test_f378_zero_with_position_is_kept_whole() -> None:
    normalizer = Normalizer(_type_map())
    original = _expr("((k + 1) - k) - 1")
    assert normalizer.canonical(original, "the base of a power") == original
    (kept,) = normalizer.kept_constants
    assert (kept.value, kept.position) == (0, "the base of a power")


@pytest.mark.parametrize(
    "text,expected",
    [
        # Under ==, next to a ModInt operand, or as an exponent, the Int 0 is
        # read as 0 mod q.
        ("(k - k) == k", "0 == k"),
        ("G.generator ^ (k - k)", "G.generator ^ 0"),
        ("(k - k) * k + k", "k"),
        # An Int zero is exact in Int arithmetic.
        ("(n - n) / (n - n)", "0 / 0"),
    ],
)
def test_f378_zero_elsewhere_is_still_rebuilt(text: str, expected: str) -> None:
    normalizer = Normalizer(_type_map())
    assert normalizer.canonical(_expr(text)) == _expr(expected)
    assert not normalizer.kept_constants


def test_f378_power_of_zero_is_the_modint_constant_one() -> None:
    # (k - k) ^ 0 is 1 mod q: a nonzero constant, kept as written (F-357).
    normalizer = Normalizer(_type_map())
    original = _expr("(k - k) ^ 0")
    assert normalizer.canonical(original) == original
    assert [(k.value, k.position) for k in normalizer.kept_constants] == [(1, None)]
