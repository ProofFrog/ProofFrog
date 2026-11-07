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
