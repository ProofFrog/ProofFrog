"""Regression tests: don't inline a non-deterministic value into a loop body.

A single SYNTACTIC use inside a loop is DYNAMICALLY evaluated once per
iteration. Inlining a non-deterministic expression into such a use multiplies
its draw (one sample becomes q i.i.d. samples). Findings F-148
(InlineSingleUseVariable), F-162 (IfSplitBranchAssignment), F-156
(InlineLocalTupleLiteral). With an empty proof namespace every FuncCall is
treated non-deterministic.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import (
    InlineSingleUseVariable,
    IfSplitBranchAssignment,
    InlineLocalTupleLiteral,
)
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(pass_obj, src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(pass_obj.apply(game, _ctx()))


def test_f148_single_use_var_not_inlined_into_loop() -> None:
    out = _apply(
        InlineSingleUseVariable(),
        """
        Game G(Enc E, Int n) {
            Bool Probe(BitString<n> m) {
                Map<Int, BitString<n>> L;
                BitString<n> c = E.Enc(m);
                for (Int i = 0 to 2) { L[i] = c; }
                return L[0] == L[1];
            }
        }
        """,
    )
    assert "BitString<n> c = E.Enc(m)" in out  # not inlined into the loop


def test_f148_single_use_var_still_inlined_without_loop() -> None:
    out = _apply(
        InlineSingleUseVariable(),
        """
        Game G(Enc E, Int n) {
            BitString<n> Probe(BitString<n> m) {
                BitString<n> c = E.Enc(m);
                return c;
            }
        }
        """,
    )
    assert "c = E.Enc(m)" not in out  # inlined (single use, no loop)
    assert "return E.Enc(m)" in out


def test_f162_branch_value_not_split_into_loop() -> None:
    out = _apply(
        IfSplitBranchAssignment(),
        """
        Game G(P p, Int n) {
            Bool Oracle(Bool c) {
                BitString<n> x;
                Map<Int, BitString<n>> M;
                if (c) { x = p.f(0); } else { x = p.f(1); }
                for (Int i = 0 to 2) { M[i] = x; }
                return M[0] == M[1];
            }
        }
        """,
    )
    # The branch assignments survive (not moved into the loop as fresh calls).
    assert "x = p.f(0)" in out and "x = p.f(1)" in out


def test_f156_tuple_element_not_inlined_into_loop() -> None:
    out = _apply(
        InlineLocalTupleLiteral(),
        """
        Game G(Gen P, Int n) {
            Bool O() {
                [BitString<n>, Int] v = [P.Sample(), 0];
                BitString<n> acc = 0^n;
                for (Int i = 0 to 2) { acc = acc + v[0]; }
                return acc == 0^n;
            }
        }
        """,
    )
    assert "[P.Sample(), 0]" in out  # tuple not inlined into the loop
