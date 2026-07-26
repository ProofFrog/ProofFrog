"""Regression tests: field-write relocation must respect control-flow exits.

Both passes relocate a field write earlier in a method. If an early `return`
sits between the new and old positions, the field would be written on a trace
where the original never wrote it -- observable by another oracle.

  - F-197 RedundantFieldCopy: `v <- ...; if (b) { return w; } f = v;` must not
    become `f <- ...; if (b) { return w; }` (writes f on the b-path).
  - F-165 HoistFieldPureAlias: `g = A[0]+1; if (b) { return 0; } f = A[0];`
    must not hoist `f = A[0]` above the early return.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import RedundantFieldCopy, HoistFieldPureAlias
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _fires(pass_obj, src: str) -> bool:
    game = frog_parser.parse_game(src)
    return str(pass_obj.apply(game, _ctx())) != str(game)


def test_f197_redundant_field_copy_declines_across_early_return() -> None:
    assert not _fires(
        RedundantFieldCopy(),
        """
        Game G(Int n) {
            BitString<n> f;
            Set<BitString<n>> S;
            BitString<n> Store(Bool b, BitString<n> w) {
                BitString<n> v <-uniq[S] BitString<n>;
                if (b) { S = S union w; return w; }
                f = v;
                return w;
            }
        }
        """,
    )


def test_f197_redundant_field_copy_still_fires_without_early_return() -> None:
    # No early return -> the redundant copy is eliminated.
    assert _fires(
        RedundantFieldCopy(),
        """
        Game G(Int n) {
            BitString<n> f;
            BitString<n> Store(BitString<n> w) {
                BitString<n> v = w;
                f = v;
                return w;
            }
        }
        """,
    )


def test_f165_hoist_field_pure_alias_declines_across_early_return() -> None:
    assert not _fires(
        HoistFieldPureAlias(),
        """
        Game G() {
            Map<Int, Int> A;
            Int f;
            Int g;
            Int O1(Bool b) {
                g = A[0] + 1;
                if (b) { return 0; }
                f = A[0];
                return g;
            }
            Int O2() { return f; }
        }
        """,
    )
