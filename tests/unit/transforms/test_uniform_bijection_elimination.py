"""Tests for UniformBijectionElimination transform pass."""

import pytest
from proof_frog import frog_parser, frog_ast
from proof_frog.transforms.structural import UniformBijectionElimination
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


# ---------------------------------------------------------------------------
# Positive tests: transform fires
# ---------------------------------------------------------------------------


def test_basic_local_bijection_elimination() -> None:
    """Local uniform sample wrapped in det+inj BitString<n>->BitString<n>."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    expected = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return x;
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == expected


def test_field_cross_method_bijection_elimination() -> None:
    """Field sampled in one method, used as f(field) in two methods."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> k;
            BitString<256> Initialize() {
                k <- BitString<256>;
                return K.Encode(k);
            }
            BitString<256> Query() {
                return K.Encode(k);
            }
        }
    """)
    expected = frog_parser.parse_game("""
        Game Test() {
            BitString<256> k;
            BitString<256> Initialize() {
                k <- BitString<256>;
                return k;
            }
            BitString<256> Query() {
                return k;
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == expected


def test_multiple_uses_all_wrapped_same_function() -> None:
    """Multiple uses of uniform variable, all wrapped in the same function."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                BitString<256> a = K.Encode(x);
                return K.Encode(x);
            }
        }
    """)
    expected = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                BitString<256> a = x;
                return x;
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == expected


# ---------------------------------------------------------------------------
# Negative tests: transform does NOT fire
# ---------------------------------------------------------------------------


def test_not_deterministic() -> None:
    """Injective but NOT deterministic -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_not_injective() -> None:
    """Deterministic but NOT injective -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_mixed_uses_bare_and_wrapped() -> None:
    """Some uses are f(x), some are bare x -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                BitString<256> a = K.Encode(x);
                return x;
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_different_functions() -> None:
    """Uses wrapped in different functions -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                BitString<256> a = K.Encode(x);
                return H.Hash(x);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            ),
            "H": _prim(
                "Primitive H() {"
                "  deterministic injective BitString<256> Hash(BitString<256> x);"
                "}"
            ),
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_type_mismatch() -> None:
    """BitString<n> -> BitString<m> where n != m -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<512> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<512> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_two_argument_method() -> None:
    """Two-argument method -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f(BitString<256> x, BitString<256> y) {
                return K.Encode(x, y);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256>"
                "    Encode(BitString<256> a, BitString<256> b);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_unknown_primitive() -> None:
    """Unknown primitive name -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx({})  # no primitives in namespace
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_not_a_sample() -> None:
    """Assignment (not uniform sample) -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f(BitString<256> y) {
                BitString<256> x = y;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx(
        {
            "K": _prim(
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> x);"
                "}"
            )
        }
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game


def test_no_annotations() -> None:
    """Method with no annotations -> no change."""
    game = frog_parser.parse_game("""
        Game Test() {
            BitString<256> f() {
                BitString<256> x <- BitString<256>;
                return K.Encode(x);
            }
        }
    """)
    ctx = _make_ctx(
        {"K": _prim("Primitive K() {" "  BitString<256> Encode(BitString<256> x);" "}")}
    )
    result = UniformBijectionElimination().apply(game, ctx)
    assert result == game
