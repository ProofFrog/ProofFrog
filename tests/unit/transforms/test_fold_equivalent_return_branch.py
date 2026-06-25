"""Soundness regression tests for FoldEquivalentReturnBranch.

RC1 / F-119: ``_count_field_assigns_recursive`` counted only writes whose
l-value is a bare ``Variable``, so an element-mutated container field
(``F1[k] = v1``) was miscounted as single-write and the pass folded a branch
that returned it -- collapsing two genuinely-different container fields.  The
counter now peels element/slice/field accesses via ``lvalue_base_name``, so an
element-written field counts as written and the fold is declined.
"""

from proof_frog import frog_parser
from proof_frog.transforms.control_flow import FoldEquivalentReturnBranch
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> tuple[object, object]:
    game = frog_parser.parse_game(source)
    result = FoldEquivalentReturnBranch().apply(game, _ctx())
    return game, result


def test_element_mutated_container_fields_not_folded() -> None:
    """Two container fields that are element-written with *different* values
    must not be folded into a single return branch."""
    game, result = _apply(
        """
        Game Containers(Dict D) {
            Map<Int, D.V> F1;
            Map<Int, D.V> F2;

            Void Initialize() {
                F1 = D.empty();
                F2 = D.empty();
            }

            Map<Int, D.V> Oracle(Bool flag, Int k, D.V v1, D.V v2) {
                F1[k] = v1;
                F2[k] = v2;
                if (flag) {
                    return F1;
                }
                return F2;
            }
        }
        """
    )
    assert result == game, f"branch wrongly folded:\n{result}"


def test_positive_fold_still_fires() -> None:
    """Control: the intended sound use -- ``if (a == b) return a; return b;``
    -- must still fold."""
    game, result = _apply(
        """
        Game Positive() {
            Int Oracle(Int a, Int b) {
                if (a == b) {
                    return a;
                }
                return b;
            }
        }
        """
    )
    assert result != game, "intended fold did not fire"
