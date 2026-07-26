"""Regression tests: group-exponent folding respects the modulus/order.

Folding group exponents (`g^a * g^b -> g^(a+b)`, `g^a / g^b -> g^(a-b)`,
`(g^e1)^e2 -> g^(e1*e2)`) reduces the combined exponent modulo the exponents'
ModInt modulus M. That matches the group law only when `g^M == identity`,
i.e. the group order divides M. The provable case is M == the base group's
order. These tests pin:

  - decline when M is a foreign/too-small modulus (F-272, F-273, F-283);
  - decline two different ModInt moduli (F-274, ill-typed ADD);
  - still fold when M is the group order, and when exponents are Int.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import build_game_type_map, NameTypeMap
from proof_frog.transforms.algebraic import (
    GroupElemExponentCombinationTransformer,
    GroupElemSimplificationTransformer,
)


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    for m in game.methods:
        if m.signature.name == name:
            return m
    raise KeyError(name)


def _combine(method_src: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game("Game G(Group G) {\n" + method_src + "\n}")
    out = (
        GroupElemExponentCombinationTransformer(build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    return game, out


def _fired(game: frog_ast.Game, out: frog_ast.Game) -> bool:
    return _method(out, "f") != _method(game, "f")


# ---- F-272: g^a * g^b, exponents ModInt<2>, group order != 2 -> decline ----


def test_f272_mul_declines_foreign_small_modulus() -> None:
    game, out = _combine(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<2> a, ModInt<2> b) {
            return h ^ a * h ^ b;
        }
        """
    )
    assert not _fired(game, out)


# ---- F-273: g^a / g^b, same foreign modulus -> decline ----


def test_f273_div_declines_foreign_small_modulus() -> None:
    game, out = _combine(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<2> a, ModInt<2> b) {
            return h ^ a / h ^ b;
        }
        """
    )
    assert not _fired(game, out)


# ---- F-274: g^a * g^b with two DIFFERENT ModInt moduli -> decline ----


def test_f274_mul_declines_mismatched_moduli() -> None:
    game, out = _combine(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<4> a, ModInt<6> b) {
            return h ^ a * h ^ b;
        }
        """
    )
    assert not _fired(game, out)


# ---- Positive: modulus IS the group order -> folds ----


def test_mul_fires_when_modulus_is_group_order() -> None:
    game, out = _combine(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<G.order> a, ModInt<G.order> b) {
            return h ^ a * h ^ b;
        }
        """
    )
    assert _fired(game, out)


# ---- Positive: Int exponents fold (exact integer arithmetic) ----


def test_mul_fires_on_int_exponents() -> None:
    game, out = _combine(
        """
        GroupElem<G> f(GroupElem<G> h, Int a, Int b) {
            return h ^ a * h ^ b;
        }
        """
    )
    assert _fired(game, out)


# ---- F-283: power-of-power (g^e1)^e2 with foreign modulus -> decline ----


def _powfold(method_src: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game("Game G(Group G) {\n" + method_src + "\n}")
    out = (
        GroupElemSimplificationTransformer(build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    return game, out


def test_f283_powerfold_declines_foreign_modulus() -> None:
    game, out = _powfold(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<3> a, ModInt<3> b) {
            return (h ^ a) ^ b;
        }
        """
    )
    assert not _fired(game, out)


def test_powerfold_fires_when_modulus_is_group_order() -> None:
    game, out = _powfold(
        """
        GroupElem<G> f(GroupElem<G> h, ModInt<G.order> a, ModInt<G.order> b) {
            return (h ^ a) ^ b;
        }
        """
    )
    assert _fired(game, out)
