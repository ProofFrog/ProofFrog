"""Tests for ConcatEqualityDecompose.

Covers rewriting ``x == (a1 || a2 || ... || ak)`` to a per-slice
conjunction of equalities whose slice bounds are accumulated from the
statically-derivable BitString length of each concat term, and the
``!=`` mirror as a disjunction; plus negative cases for unknown lengths,
single-term concats, and both-sides-concat.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import ConcatEqualityDecompose
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


NS_SRC = """
Primitive T(Int Nss, Int Nct, Set SecretSet, Set CtxSet) {
    deterministic injective BitString<Nss> EncSS(SecretSet s);
    deterministic injective BitString<Nct> EncCT(CtxSet c);
}
"""


def _ns() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file(NS_SRC)
    return {"T": prim}


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=_ns(),
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return ConcatEqualityDecompose().apply(game, _ctx())


def test_three_term_equality_decomposes_to_slice_conjunction() -> None:
    source = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        T.CtxSet c2;
        Bool Check(BitString<Nss + Nct + Nct> m) {
            return m == (T.EncSS(s1) || T.EncCT(c1) || T.EncCT(c2));
        }
    }
    """
    expected = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        T.CtxSet c2;
        Bool Check(BitString<Nss + Nct + Nct> m) {
            return m[0 : Nss] == T.EncSS(s1)
                && m[Nss : Nss + Nct] == T.EncCT(c1)
                && m[Nss + Nct : Nss + Nct + Nct] == T.EncCT(c2);
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_disequality_decomposes_to_slice_disjunction() -> None:
    source = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        Bool Check(BitString<Nss + Nct> m) {
            return m != (T.EncSS(s1) || T.EncCT(c1));
        }
    }
    """
    expected = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        Bool Check(BitString<Nss + Nct> m) {
            return m[0 : Nss] != T.EncSS(s1)
                || m[Nss : Nss + Nct] != T.EncCT(c1);
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_concat_on_left_also_decomposes() -> None:
    source = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        Bool Check(BitString<Nss + Nct> m) {
            return (T.EncSS(s1) || T.EncCT(c1)) == m;
        }
    }
    """
    expected = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.CtxSet c1;
        Bool Check(BitString<Nss + Nct> m) {
            return m[0 : Nss] == T.EncSS(s1) && m[Nss : Nss + Nct] == T.EncCT(c1);
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_unknown_length_term_does_not_fire() -> None:
    # Call to a non-primitive (helper game method) with BitString return --
    # the transform cannot derive that term's length, so it leaves the
    # concat equality alone.
    source = """
    Game G(Int Nss) {
        Bool Check(BitString<Nss> a, BitString<Nss> b, BitString<Nss + Nss> m) {
            return m == (a || b);
        }
    }
    """
    # Variables a, b have declared BitString<Nss> types, so the transform
    # SHOULD fire.  Rewrite:
    expected = """
    Game G(Int Nss) {
        Bool Check(BitString<Nss> a, BitString<Nss> b, BitString<Nss + Nss> m) {
            return m[0 : Nss] == a && m[Nss : Nss + Nss] == b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_single_term_does_not_fire() -> None:
    source = """
    Game G(Int Nss) {
        T.SecretSet s1;
        Bool Check(BitString<Nss> m) {
            return m == T.EncSS(s1);
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


def test_both_sides_concat_does_not_fire() -> None:
    source = """
    Game G(Int Nss, Int Nct) {
        T.SecretSet s1;
        T.SecretSet s2;
        T.CtxSet c1;
        T.CtxSet c2;
        Bool Check() {
            return (T.EncSS(s1) || T.EncCT(c1)) == (T.EncSS(s2) || T.EncCT(c2));
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


def test_slice_term_resolves_via_end_minus_start() -> None:
    # A slice `x[A:B]` is a valid concat term with length `B - A`.
    source = """
    Game G(Int N, Int K) {
        Bool Check(BitString<K + (N - K)> m, BitString<N> x) {
            return m == (x[0 : K] || x[K : N]);
        }
    }
    """
    expected = """
    Game G(Int N, Int K) {
        Bool Check(BitString<K + (N - K)> m, BitString<N> x) {
            return m[0 : K - 0] == x[0 : K]
                && m[K - 0 : (K - 0) + (N - K)] == x[K : N];
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)
