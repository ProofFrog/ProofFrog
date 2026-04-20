"""Tests for the MapKeyReindex transform pass (design §3)."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_reindex import MapKeyReindex
from proof_frog.visitors import NameTypeMap


_TRAPDOOR_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic injective Image Eval(Input x);
}
"""


_NON_INJECTIVE_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic Image Eval(Input x);
}
"""


_NON_DETERMINISTIC_PRIMITIVE = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    injective Image Eval(Input x);
}
"""


def _ctx_with_primitive(primitive_src: str = _TRAPDOOR_PRIMITIVE) -> PipelineContext:
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )
    if primitive_src:
        prim = frog_parser.parse_string(primitive_src, frog_ast.FileType.PRIMITIVE)
        ctx.proof_namespace[prim.name] = prim
        ctx.proof_namespace["TT"] = prim
    return ctx


def _apply(game_src: str, ctx: PipelineContext) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return MapKeyReindex().apply(game, ctx)


def _apply_and_expect(
    game_src: str,
    expected_src: str,
    ctx: PipelineContext | None = None,
) -> None:
    ctx = ctx or _ctx_with_primitive()
    got = _apply(game_src, ctx)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(
    game_src: str, ctx: PipelineContext | None = None
) -> None:
    ctx = ctx or _ctx_with_primitive()
    original = frog_parser.parse_game(game_src)
    got = MapKeyReindex().apply(original, ctx)
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"


def test_basic_reindex() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Lookup(TT.Input a2) {
                if (TT.Eval(a2) in M) {
                    return M[TT.Eval(a2)];
                }
                return None;
            }
        }
        """,
    )


def test_reindex_with_scan_loop() -> None:
    _apply_and_expect(
        """
        Game G(T TT) {
            Map<TT.Input, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[a] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Input, BitString<16>] e in M.entries) {
                    if (TT.Eval(e[0]) == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
        """
        Game G(T TT) {
            Map<TT.Image, BitString<16>> M;
            Void Store(TT.Input a, BitString<16> s) {
                M[TT.Eval(a)] = s;
            }
            BitString<16>? Scan(TT.Image y) {
                for ([TT.Image, BitString<16>] e in M.entries) {
                    if (e[0] == y) {
                        return e[1];
                    }
                }
                return None;
            }
        }
        """,
    )
