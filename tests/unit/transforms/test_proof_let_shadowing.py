"""F-361: a proof ``let:`` entry must not retype a same-named game name.

A proof's ``let:`` entries are the outer scope of every game in the proof,
so inside a game its own field, parameter or local wins. The type maps the
passes and the residual Z3 check read used to merge the proof's ``let:``
types last, and ``NameTypeMap.__add__`` lets its right operand win, so a
``let:`` entry not passed to the game retyped a same-named game field. These
tests pin the precedence at the shared helper, at a pass and at the residual
check, in both directions: the game's type blocks an unsound rewrite the
``let:`` type would allow, and allows a sound one the ``let:`` type would
block.
"""

from proof_frog import frog_ast, frog_parser, proof_engine
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import GroupElemSimplification
from proof_frog.visitors import (
    NameTypeMap,
    build_game_type_map,
    build_method_type_map,
    with_proof_let_types,
)


def _lets(**types: frog_ast.Type) -> NameTypeMap:
    lets = NameTypeMap()
    for name, the_type in types.items():
        lets.set(name, the_type)
    return lets


def _group_elem(group: str) -> frog_ast.GroupElemType:
    return frog_ast.GroupElemType(frog_ast.Variable(group))


def _ctx(lets: NameTypeMap) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=lets,
        proof_namespace={},
        subsets_pairs=[],
    )


def _returned(game: frog_ast.Game, method: str) -> str:
    oracle = next(m for m in game.methods if m.signature.name == method)
    return str(oracle.block.statements[-1])


# ---------------------------------------------------------------------------
# The shared type maps
# ---------------------------------------------------------------------------


def test_f361_game_field_shadows_let_in_type_maps() -> None:
    game = frog_parser.parse_game("""
        Game G(Group A, Group B) {
            GroupElem<B> t;
            GroupElem<B> O() { return t; }
        }
        """)
    lets = _lets(t=_group_elem("A"), u=frog_ast.IntType())
    method = game.methods[0]
    for type_map in (
        build_game_type_map(game, lets),
        build_method_type_map(game, method, lets),
    ):
        # The game's field keeps its own group; a let name the game does not
        # declare still gets its let type.
        assert type_map.get("t") == _group_elem("B")
        assert type_map.get("u") == frog_ast.IntType()


def test_f361_method_local_shadows_field_and_let() -> None:
    game = frog_parser.parse_game("""
        Game G(Int q) {
            Int x;
            Bool O() {
                ModInt<q> x = 0;
                return x == 0;
            }
        }
        """)
    lets = _lets(x=frog_ast.BoolType())
    type_map = build_method_type_map(game, game.methods[0], lets)
    assert isinstance(type_map.get("x"), frog_ast.ModIntType)


def test_f361_with_proof_let_types_fills_in_only_undeclared_names() -> None:
    declared = _lets(t=frog_ast.BoolType())
    merged = with_proof_let_types(
        declared, _lets(t=frog_ast.IntType(), n=frog_ast.IntType())
    )
    assert merged.get("t") == frog_ast.BoolType()
    assert merged.get("n") == frog_ast.IntType()
    assert with_proof_let_types(declared, None) is declared


# ---------------------------------------------------------------------------
# A pass: GroupElem Simplification's power-of-power rule
# ---------------------------------------------------------------------------


def _power_of_power_game(field_group: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"""
        Game P(Group G, Group H) {{
            GroupElem<{field_group}> t;
            GroupElem<{field_group}> Q(ModInt<G.order> x, ModInt<G.order> y) {{
                return (t ^ x) ^ y;
            }}
        }}
        """)


def test_f361_power_of_power_reads_the_field_group_not_the_let() -> None:
    """``(t ^ x) ^ y`` -> ``t ^ (x * y)`` with the product in
    ``ModInt<G.order>`` holds only if ``t`` is in ``G``. The field is in
    ``H``; a ``let:`` ``t`` in ``G`` must not make the rule fire (with
    ``|G| = 3``, ``|H| = 2``, ``x = y = 2``: identity vs ``t``)."""
    game = _power_of_power_game("H")
    out = GroupElemSimplification().apply(game, _ctx(_lets(t=_group_elem("G"))))
    assert _returned(out, "Q") == "return (t ^ x) ^ y;"


def test_f361_power_of_power_still_fires_on_a_field_in_the_exponent_group() -> None:
    """Positive control: the field is in ``G``, so the fold is sound, and a
    ``let:`` ``t`` in ``H`` must not block it."""
    game = _power_of_power_game("G")
    out = GroupElemSimplification().apply(game, _ctx(_lets(t=_group_elem("H"))))
    assert _returned(out, "Q") == "return t ^ (x * y);"


# ---------------------------------------------------------------------------
# The residual Z3 check
# ---------------------------------------------------------------------------


def _residual_pair(field_type: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    left = frog_parser.parse_game(f"""
        Game Left(Int q) {{
            {field_type} x;
            Bool O() {{ return x + x + x == x; }}
        }}
        """)
    right = frog_parser.parse_game(f"""
        Game Right(Int q) {{
            {field_type} x;
            Bool O() {{ return x + x == x; }}
        }}
        """)
    return left, right


def _residual_check(
    left: frog_ast.Game, right: frog_ast.Game, lets: NameTypeMap
) -> proof_engine.EquivalenceResult | None:
    def returned(game: frog_ast.Game) -> frog_ast.Expression:
        ret = game.methods[0].block.statements[-1]
        assert isinstance(ret, frog_ast.ReturnStatement)
        return ret.expression

    # pylint: disable=protected-access
    return proof_engine._z3_check_expression_pair(
        left, right, returned(left), returned(right), lets, {}, "return"
    )
    # pylint: enable=protected-access


def test_f361_residual_check_reads_the_field_type_not_the_let() -> None:
    """Over ``Int`` both returns hold exactly when ``x == 0``; over
    ``ModInt<q>`` they differ at ``q = 2``, ``x = 1``. The field is a
    ``ModInt<q>``; a ``let:`` ``Int x`` must not make the check certify the
    pair."""
    left, right = _residual_pair("ModInt<q>")
    lets = _lets(q=frog_ast.IntType(), x=frog_ast.IntType())
    result = _residual_check(left, right, lets)
    assert result is not None and not result.valid


def test_f361_residual_check_control_int_field_under_modint_let() -> None:
    """Positive control: an ``Int`` field makes the pair equivalent, and a
    ``let:`` ``ModInt<q> x`` must not stop the check from seeing it."""
    left, right = _residual_pair("Int")
    lets = _lets(q=frog_ast.IntType(), x=frog_ast.ModIntType(frog_ast.Variable("q")))
    assert _residual_check(left, right, lets) is None
