"""Regression tests for InlineSingleUseField's step-5 interference scan (F-214).

Inlining a single-use field across an intermediate window is unsound if that
window mutates the field. The private scan matched only a bare `name = ...`
lvalue, so a nested element write (`M[0]=1`) or a `<-uniq[S]` insertion that
grows `S` slipped through and the field was inlined past its own mutation
(reading a stale value). The scan now routes through the complete shared
`reassigns_or_rebinds` helper.
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineSingleUseFieldTransformer


def _after(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(InlineSingleUseFieldTransformer().transform(game))


def test_f214_declines_inline_past_element_write() -> None:
    # A = |M|; M[0] = 1; return A  -- inlining A past the element write would
    # read the post-write |M|. The field must survive (no inline).
    after = _after(
        """
        Game G() {
            Map<Int, Int> M;
            Int A;
            Int O() {
                A = |M|;
                M[0] = 1;
                return A;
            }
        }
        """
    )
    assert "Int A;" in after


def test_f214_declines_inline_past_uniq_growth() -> None:
    # A = |S|; x <-uniq[S] BitString<n>; return A -- the uniq draw grows S,
    # so inlining A past it reads the post-growth |S|. Field must survive.
    after = _after(
        """
        Game G(Int n) {
            Set<BitString<n>> S;
            Int A;
            Int O() {
                A = |S|;
                BitString<n> x <-uniq[S] BitString<n>;
                return A;
            }
        }
        """
    )
    assert "Int A;" in after


def test_f214_still_inlines_without_interference() -> None:
    # A = 5; return A -- no interference, the field is single-use and inlined
    # away (positive control: the guard is not over-declining).
    after = _after(
        """
        Game G() {
            Int A;
            Int O() {
                A = 5;
                return A;
            }
        }
        """
    )
    assert "Int A;" not in after
    assert "return 5;" in after


def test_f215_declines_write_inside_compound_last_use_statement() -> None:
    # A = ctr; if (c) { ctr = 100; return A; } -- the free var `ctr` is written
    # INSIDE the compound last-use statement, before the use of A within it. The
    # step-5 scan slice `[def+1 : last_use]` excluded that statement, so the
    # write escaped and inlining A -> ctr would read the post-write value (100).
    # The field must survive (no inline).
    after = _after(
        """
        Game G() {
            Int ctr;
            Int A;
            Int O(Bool c) {
                ctr = 0;
                A = ctr;
                if (c) {
                    ctr = 100;
                    return A;
                }
                return 0;
            }
        }
        """
    )
    assert "Int A;" in after, "field must not inline past a write in its last-use statement"
