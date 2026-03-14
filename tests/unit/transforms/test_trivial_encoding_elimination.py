"""Tests for TrivialEncodingElimination transform pass."""

import pytest
from proof_frog import frog_parser, frog_ast
from proof_frog.transforms.structural import TrivialEncodingElimination
from proof_frog.transforms._base import PipelineContext


def _make_ctx(primitives: dict[str, frog_ast.Primitive]) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types={},
        proof_namespace=dict(primitives),
        subsets_pairs=[],
    )


def _prim(prim_text: str) -> frog_ast.Primitive:
    return frog_parser.parse_primitive_file(prim_text)


@pytest.mark.parametrize(
    "game_text,expected_text,prims",
    [
        # Identity encoding: K.EncodeSharedSecret(x) -> x when input == output type
        (
            """
            Game Test() {
                BitString<256> f(BitString<256> x) {
                    return K.EncodeSharedSecret(x);
                }
            }
            """,
            """
            Game Test() {
                BitString<256> f(BitString<256> x) {
                    return x;
                }
            }
            """,
            {
                "K": "Primitive K() { BitString<256> EncodeSharedSecret(BitString<256> ss); }"
            },
        ),
        # Non-identity encoding: input and output types differ -> no simplification
        (
            """
            Game Test() {
                BitString<512> f(BitString<256> x) {
                    return H.hash(x);
                }
            }
            """,
            """
            Game Test() {
                BitString<512> f(BitString<256> x) {
                    return H.hash(x);
                }
            }
            """,
            {"H": "Primitive H() { BitString<512> hash(BitString<256> x); }"},
        ),
        # Two-argument method: should NOT simplify
        (
            """
            Game Test() {
                BitString<256> f(BitString<256> x, BitString<256> y) {
                    return K.Encode(x, y);
                }
            }
            """,
            """
            Game Test() {
                BitString<256> f(BitString<256> x, BitString<256> y) {
                    return K.Encode(x, y);
                }
            }
            """,
            {
                "K": "Primitive K() { BitString<256> Encode(BitString<256> a, BitString<256> b); }"
            },
        ),
        # Unknown primitive name: should NOT simplify (identity-safe no-op)
        (
            """
            Game Test() {
                BitString<256> f(BitString<256> x) {
                    return K.Encode(x);
                }
            }
            """,
            """
            Game Test() {
                BitString<256> f(BitString<256> x) {
                    return K.Encode(x);
                }
            }
            """,
            {},  # no primitives in namespace
        ),
    ],
)
def test_trivial_encoding_elimination(
    game_text: str,
    expected_text: str,
    prims: dict[str, str],
) -> None:
    game = frog_parser.parse_game(game_text)
    expected = frog_parser.parse_game(expected_text)
    ctx = _make_ctx({name: _prim(src) for name, src in prims.items()})

    result = TrivialEncodingElimination().apply(game, ctx)
    assert result == expected
