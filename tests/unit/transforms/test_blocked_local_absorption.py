"""Tests for BlockedLocalAbsorption."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import BlockedLocalAbsorption
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    group = frog_ast.Variable("G")
    lets.set("G", frog_ast.GroupType())
    lets.set(
        "H",
        frog_ast.FunctionType(
            frog_ast.GroupElemType(group),
            frog_ast.ModIntType(frog_ast.FieldAccess(group, "order")),
        ),
    )
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _apply(body: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game(
        f"""
        Game T(Group G) {{
            ModInt<G.order> sk;
            [GroupElem<G>, ModInt<G.order>] f(ModInt<G.order> d, ModInt<G.order> u) {{
                {body}
            }}
        }}
        """
    )
    return game, BlockedLocalAbsorption().apply(game, _ctx())


def _lines(game: frog_ast.Game) -> list[str]:
    return [str(s).strip() for s in game.methods[0].block.statements]


def test_absorbs_use_site_into_blocked_local() -> None:
    _, result = _apply(
        "GroupElem<G> x = G.generator ^ (sk * u);\n"
        "sk = sk + d;\n"
        "return [G.generator ^ sk, d + H(x)];"
    )
    assert _lines(result) == [
        "ModInt<G.order> x = d + H(G.generator ^ (sk * u));",
        "sk = sk + d;",
        "return [G.generator ^ sk, x];",
    ]


def test_stops_at_a_written_input() -> None:
    _, result = _apply(
        "GroupElem<G> x = G.generator ^ (sk * u);\n"
        "sk = sk + d;\n"
        "return [G.generator ^ sk, sk + H(x)];"
    )
    assert _lines(result) == [
        "ModInt<G.order> x = H(G.generator ^ (sk * u));",
        "sk = sk + d;",
        "return [G.generator ^ sk, sk + x];",
    ]


def test_no_fire_when_not_blocked() -> None:
    game, result = _apply(
        "GroupElem<G> x = G.generator ^ (sk * u);\n"
        "return [G.generator ^ sk, d + H(x)];"
    )
    assert result == game


def test_no_fire_through_a_nondeterministic_call() -> None:
    game, result = _apply(
        "GroupElem<G> x = G.generator ^ (sk * u);\n"
        "sk = sk + d;\n"
        "return [G.generator ^ sk, F.Sample(x)];"
    )
    assert result == game


def test_no_fire_when_used_twice() -> None:
    game, result = _apply(
        "GroupElem<G> x = G.generator ^ (sk * u);\n"
        "sk = sk + d;\n"
        "return [x, d + H(x)];"
    )
    assert result == game


def test_concatenation_is_not_typed_as_bool() -> None:
    # `||` on bit strings is concatenation; the absorbed local must not be
    # declared Bool (it is left alone, since the length is not inferred).
    game = frog_parser.parse_game(
        """
        Game T(Int n) {
            BitString<n> s;
            [BitString<2 * n>, Bool] f(BitString<n> y) {
                BitString<n> x = s;
                s = y;
                return [x || y, true];
            }
        }
        """
    )
    result = BlockedLocalAbsorption().apply(game, _ctx())
    assert "Bool x" not in str(result)


def _stale_type_ctx() -> PipelineContext:
    lets = NameTypeMap()
    q = frog_ast.Variable("q")
    lets.set("G", frog_ast.GroupType())
    lets.set("q", frog_ast.IntType())
    lets.set("H", frog_ast.FunctionType(frog_ast.ModIntType(q), frog_ast.IntType()))
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _stale_type_game(use: str) -> frog_ast.Game:
    return frog_parser.parse_game(
        f"""
        Game T(Group G, Int q) {{
            ModInt<q> s;
            GroupElem<G> h;
            Set<Int> S;
            GroupElem<G> Get(ModInt<q> r) {{
                ModInt<q> x = s;
                s = s + r;
                h = h * h;
                return h ^ ({use});
            }}
        }}
        """
    )


def test_f358_absorbed_local_is_retyped_before_the_next_round() -> None:
    # Round one absorbs H(x), an Int, and re-declares x as Int. Typing x
    # with the map built before that round (ModInt<q>) made x + |S| a
    # ModInt<q> and declared ModInt<q> x = H(s) + |S|;, reducing the Int sum
    # mod q. With x typed Int, x + |S| has no known type and the chain stops.
    result = BlockedLocalAbsorption().apply(
        _stale_type_game("H(x) + |S|"), _stale_type_ctx()
    )
    assert _lines(result) == [
        "Int x = H(s);",
        "s = s + r;",
        "h = h * h;",
        "return h ^ (x + |S|);",
    ]


def test_f358_absorbs_into_a_retyped_local() -> None:
    # Positive control: the one round that changes x's type still fires.
    result = BlockedLocalAbsorption().apply(
        _stale_type_game("H(x)"), _stale_type_ctx()
    )
    assert _lines(result) == [
        "Int x = H(s);",
        "s = s + r;",
        "h = h * h;",
        "return h ^ x;",
    ]


def test_absorbs_two_locals_in_one_block() -> None:
    game = frog_parser.parse_game(
        """
        Game T(Group G) {
            ModInt<G.order> sk;
            [GroupElem<G>, ModInt<G.order>, ModInt<G.order>] f(ModInt<G.order> d, ModInt<G.order> u) {
                GroupElem<G> x = G.generator ^ (sk * u);
                GroupElem<G> y = G.generator ^ (sk * d);
                sk = sk + d;
                return [G.generator ^ sk, d + H(x), u + H(y)];
            }
        }
        """
    )
    result = BlockedLocalAbsorption().apply(game, _ctx())
    assert _lines(result) == [
        "ModInt<G.order> x = d + H(G.generator ^ (sk * u));",
        "ModInt<G.order> y = u + H(G.generator ^ (sk * d));",
        "sk = sk + d;",
        "return [G.generator ^ sk, x, y];",
    ]


def test_absorbs_inside_an_if_block() -> None:
    game = frog_parser.parse_game(
        """
        Game T(Group G) {
            ModInt<G.order> sk;
            [GroupElem<G>, ModInt<G.order>] f(ModInt<G.order> d, ModInt<G.order> u) {
                if (d == u) {
                    GroupElem<G> x = G.generator ^ (sk * u);
                    sk = sk + d;
                    return [G.generator ^ sk, d + H(x)];
                }
                return [G.generator, d];
            }
        }
        """
    )
    result = BlockedLocalAbsorption().apply(game, _ctx())
    branch = result.methods[0].block.statements[0]
    assert isinstance(branch, frog_ast.IfStatement)
    assert [str(s).strip() for s in branch.blocks[0].statements] == [
        "ModInt<G.order> x = d + H(G.generator ^ (sk * u));",
        "sk = sk + d;",
        "return [G.generator ^ sk, x];",
    ]


def test_f370_no_fire_past_a_bare_redeclaration() -> None:
    # F-370(a), case B4: the bare re-declaration ModInt<G.order> x; is not a
    # read of x, so the use after it looked like the only one; moving the
    # definition would make the use read the earlier x's value.
    game, result = _apply(
        "ModInt<G.order> x = sk;\n"
        "sk = sk + d;\n"
        "ModInt<G.order> x;\n"
        "return [G.generator ^ sk, x + d];"
    )
    assert result == game
