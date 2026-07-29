"""Regression tests: don't relocate a call whose argument is an undefined read.

Reading an absent map key `M[k]` is an observable undefined-read abort. A pass
that hoists or deduplicates such a call to a position with broader reachability
changes the set of traces on which the abort occurs.

  - F-206 HoistDuplicateBranchCall: `F.eval(M[c])` in two branch returns must
    not hoist before the branches (would force the read on the fall-through).
  - F-200 DeduplicateDeterministicCalls: `F.eval(M[x])` in an else-if condition
    must not hoist to a pre-if local (would read M[x] on the `!(x in M)` path).
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import (
    HoistDuplicateBranchCallTransformer,
    DeduplicateDeterministicCallsTransformer,
)


def _det_ns():
    prim = frog_parser.parse_primitive_file(
        """
        Primitive P() {
            deterministic Int eval(Int x);
        }
        """
    )
    return {"F": prim}


def _hoist(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(HoistDuplicateBranchCallTransformer(_det_ns()).transform(game))


def _dedup(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(
        DeduplicateDeterministicCallsTransformer(proof_namespace=_det_ns()).transform(
            game
        )
    )


# ---- F-206 HoistDuplicateBranchCall ----


def test_f206_declines_hoist_of_map_read_call() -> None:
    out = _hoist(
        """
        Game G(P F) {
            Map<Int, Int> M;
            Int O(Bool b1, Bool b2, Int c) {
                if (b1) { return F.eval(M[c]); }
                if (b2) { return F.eval(M[c]); }
                return 0;
            }
        }
        """
    )
    assert "__hoist" not in out  # not hoisted


def test_f206_still_hoists_plain_arg_call() -> None:
    out = _hoist(
        """
        Game G(P F) {
            Int O(Bool b1, Bool b2, Int c) {
                if (b1) { return F.eval(c); }
                if (b2) { return F.eval(c); }
                return 0;
            }
        }
        """
    )
    assert "__hoist" in out  # plain arg: hoisted


# ---- F-200 DeduplicateDeterministicCalls ----


def test_f200_declines_dedup_of_elseif_map_read() -> None:
    out = _dedup(
        """
        Game G(P F) {
            Map<Int, Int> M;
            Int O(Int x, Int y, Int z) {
                if (!(x in M)) { return z; }
                else if (F.eval(M[x]) == y) { return y; }
                return F.eval(M[x]);
            }
        }
        """
    )
    assert "__determ" not in out  # not deduped
