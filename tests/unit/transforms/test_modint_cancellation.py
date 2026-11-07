"""Tests for ModIntCancellation: ModInt arithmetic whose terms cancel."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import ModIntCancellation
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


def _return_of(game: frog_ast.Game) -> frog_ast.Expression:
    statement = game.methods[0].block.statements[-1]
    assert isinstance(statement, frog_ast.ReturnStatement)
    return statement.expression


def _apply(body: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game(
        f"""
        Game T(Group G) {{
            ModInt<G.order> sk;
            ModInt<G.order> f(ModInt<G.order> d, ModInt<G.order> u, ModInt<G.order> a, ModInt<G.order> b) {{
                {body}
            }}
        }}
        """
    )
    return game, ModIntCancellation().apply(game, _ctx())


def test_hash_term_cancels() -> None:
    _, result = _apply(
        "return sk + ((d + H(G.generator ^ (sk * u))) - H(G.generator ^ (sk * u)));"
    )
    out = _return_of(result)
    assert "H(" not in str(out)
    assert str(out) in ("sk + d", "d + sk")


def test_cancellation_inside_larger_statement() -> None:
    _, result = _apply(
        "ModInt<G.order> x = a * (b + 1) - a;\nreturn x;"
    )
    first = result.methods[0].block.statements[0]
    assert isinstance(first, frog_ast.Assignment)
    assert str(first.value) in ("a * b", "b * a")


def test_no_fire_without_cancellation() -> None:
    game, result = _apply("return a * (b + d);")
    assert result == game


def test_no_fire_on_nondeterministic_call() -> None:
    # Two draws of a non-deterministic primitive method are different
    # values: (d + F.Sample()) - F.Sample() is not d.
    game, result = _apply("return (d + F.Sample()) - F.Sample();")
    assert result == game
