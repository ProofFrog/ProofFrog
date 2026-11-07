"""Tests for SplitProductSample: a uniform product sample used only through
constant indices is a list of independent uniform component samples."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.sampling import SplitProductSample
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={}, proof_let_types=NameTypeMap(), proof_namespace={}, subsets_pairs=[]
    )


def _apply(body: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game(
        f"""
        Game T(Group G) {{
            ModInt<G.order> f() {{
                {body}
            }}
        }}
        """
    )
    return game, SplitProductSample().apply(game, _ctx())


def test_split_indexed_product_sample() -> None:
    _, result = _apply(
        "[ModInt<G.order>, BitString<8>] r <- [ModInt<G.order>, BitString<8>];\n"
        "ModInt<G.order> d = r[0];\n"
        "BitString<8> u = r[1];\n"
        "return d;"
    )
    statements = result.methods[0].block.statements
    first, second = statements[0], statements[1]
    assert isinstance(first, frog_ast.Sample) and isinstance(second, frog_ast.Sample)
    assert str(first.sampled_from) == "ModInt<G.order>"
    assert str(second.sampled_from) == "BitString<8>"
    assert "r[" not in str(result)


def test_no_split_when_used_whole() -> None:
    game, result = _apply(
        "[ModInt<G.order>, ModInt<G.order>] r <- [ModInt<G.order>, ModInt<G.order>];\n"
        "[ModInt<G.order>, ModInt<G.order>] s = r;\n"
        "return r[0];"
    )
    assert result == game


def test_no_split_when_reassigned() -> None:
    game, result = _apply(
        "[ModInt<G.order>, ModInt<G.order>] r <- [ModInt<G.order>, ModInt<G.order>];\n"
        "r <- [ModInt<G.order>, ModInt<G.order>];\n"
        "return r[0];"
    )
    assert result == game
