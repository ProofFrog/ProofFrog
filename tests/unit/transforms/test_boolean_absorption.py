"""Tests for BooleanAbsorption.

Drops a conjunct ``B`` from an ``A && B`` chain when ``A``'s flattened
OR-disjuncts are a subset of ``B``'s.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import BooleanAbsorption
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx(namespace: frog_ast.Namespace | None = None) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


def _apply(
    source: str, namespace: frog_ast.Namespace | None = None
) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return BooleanAbsorption().apply(game, _ctx(namespace))


def test_and_with_or_superset_absorbs() -> None:
    source = """
    Game G() {
        Bool Check(Bool a, Bool b, Bool c) {
            return (a || b) && (a || b || c);
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Bool a, Bool b, Bool c) {
            return a || b;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_duplicate_conjuncts_are_collapsed() -> None:
    source = """
    Game G() {
        Bool Check(Bool a) {
            return a && a;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Bool a) {
            return a;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_no_subset_relationship_keeps_chain() -> None:
    source = """
    Game G() {
        Bool Check(Bool a, Bool b, Bool c, Bool d) {
            return (a || b) && (c || d);
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


# --------------------------------------------------------------------------
# Soundness gap regression test (Gap F: non-deterministic-call absorption)
# --------------------------------------------------------------------------


NS_NONDET_FLIP = """
Primitive T() {
    Bool flip();
}
"""


def test_gap_f_nondet_call_in_dropped_disjuncts_blocks_absorption() -> None:
    """Gap F distinguisher: ``F.flip() && (F.flip() || true)`` would be
    naively absorbed to ``F.flip()`` by disjunct-subset reasoning, but
    the dropped ``F.flip()`` is non-deterministic — observable counter
    advances differ. Post-fix: the absorption is blocked."""
    prim = frog_parser.parse_primitive_file(NS_NONDET_FLIP)
    namespace: frog_ast.Namespace = {"T": prim}
    source = """
    Game G() {
        Bool Check() {
            return T.flip() && (T.flip() || true);
        }
    }
    """
    # Post-fix: transform refuses to drop the second conjunct.
    assert _apply(source, namespace) == frog_parser.parse_game(source)


def test_three_conjunct_chain_with_redundant_middle() -> None:
    source = """
    Game G() {
        Bool Check(Bool a, Bool b, Bool c, Bool d) {
            return (a || b) && (a || b || c) && d;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Bool a, Bool b, Bool c, Bool d) {
            return (a || b) && d;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)
