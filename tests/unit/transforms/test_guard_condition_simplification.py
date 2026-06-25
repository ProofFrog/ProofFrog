"""Soundness regression tests for GuardConditionSimplification.

GuardConditionSimplification replaces an if-condition by its known truth value
inside its branches.  That is sound only when the condition's value is invariant
across the branch.  The audit (transform-soundness round 2, RC1) showed the
reassignment check was node-kind-incomplete: it saw only ``Assignment`` whose
``.var`` is a bare ``Variable`` named in the (FieldAccess-blind) condition
read-set.  Four attack shapes slipped past it (findings F-080, F-082, plus the
``<-uniq`` and loop-binder surfaces shared with RC2/RC4):

- GCS-1: element write ``M[k] = v`` (l-value is ``ArrayAccess``) mutates the
  guard set invisibly.
- GCS-2: ``x <-uniq[S] T`` implicitly inserts ``x`` into ``S`` (no AST write).
- GCS-3: ``cond_vars`` omitted variables under ``FieldAccess`` (``M`` in
  ``k in M.keys``), so even a whole-variable write ``M = N`` went undetected.
- GCS-4: a loop binder (``for (Int x = ...)``) shadowing a guard variable is
  not an ``Assignment`` and is not scope-aware-substituted.

Each attack must leave the inner re-test intact (pass declines).  The positive
controls must still fold (the read/write scanner is complete, not blunt).
"""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import GuardConditionSimplificationTransformer


def _run(src: str) -> str:
    method_ast = frog_parser.parse_method(src)
    return str(GuardConditionSimplificationTransformer().transform(method_ast))


# --- Attacks: the pass MUST decline (inner guard not frozen to a constant) ---

ATTACKS = {
    # GCS-1 (F-080): element write M[k] = 1 mutates the guard set `M`.
    "element_write": """
        Int O(Int k, Map<Int, Int> M) {
            if (k in M) {
                return 0;
            } else {
                M[k] = 1;
                if (k in M) {
                    return 100;
                } else {
                    return 200;
                }
            }
        }
    """,
    # GCS-2: <-uniq[S] inserts the draw into the guard set `S`.
    "uniq_insertion": """
        Int O(BitString<1> e, Set<BitString<1>> S) {
            if (e in S) {
                return 0;
            } else {
                BitString<1> y <-uniq[S] BitString<1>;
                if (e in S) {
                    return 1;
                } else {
                    return 2;
                }
            }
        }
    """,
    # GCS-3 (F-082): guard reads `M` through FieldAccess `M.keys`; the whole-
    # variable write `M = N` must be seen.
    "field_access_read": """
        Int O(Int k, Map<Int, Int> M) {
            if (k in M.keys) {
                return 0;
            } else {
                Map<Int, Int> N;
                N[k] = 1;
                M = N;
                if (k in M.keys) {
                    return 1;
                } else {
                    return 2;
                }
            }
        }
    """,
    # GCS-4: loop binder `x` shadows the guard variable `x`.
    "loop_binder_shadow": """
        Int O(Int x, Set<Int> S) {
            if (x in S) {
                Int acc = 0;
                for (Int x = 0 to 1) {
                    if (x in S) {
                        acc = acc + 1;
                    }
                }
                return acc;
            } else {
                return 99;
            }
        }
    """,
    # GCS-6 (already blocked): direct whole-variable reassignment of guard set.
    "whole_var_reassign": """
        Int O(Int e, Set<Int> S) {
            if (e in S) {
                return 0;
            } else {
                S = S union {e};
                if (e in S) {
                    return 1;
                } else {
                    return 2;
                }
            }
        }
    """,
}


@pytest.mark.parametrize("name", sorted(ATTACKS))
def test_attack_declines(name: str) -> None:
    src = ATTACKS[name]
    before = str(frog_parser.parse_method(src))
    after = _run(src)
    # The pass must not freeze the inner re-test to a constant.
    assert "if (true)" not in after and "if (false)" not in after, (
        f"{name}: guard wrongly substituted\n{after}"
    )
    assert before == after, f"{name}: pass mutated an unstable-guard branch\n{after}"


# --- Positive controls: the pass MUST still fire ---

CONTROLS = {
    # Plain redundant re-test, no writes at all.
    "redundant_retest": """
        Int f(Int x, Set<Int> S) {
            if (x in S) {
                if (x in S) {
                    return 1;
                }
                return 2;
            } else {
                if (x in S) {
                    return 3;
                }
                return 4;
            }
        }
    """,
    # FieldAccess guard with NO reassignment: the complete read-set must not
    # over-decline.  `k in M.keys` re-tested with M untouched should fold.
    "field_access_stable": """
        Int O(Int k, Map<Int, Int> M) {
            if (k in M.keys) {
                if (k in M.keys) {
                    return 1;
                }
                return 2;
            }
            return 0;
        }
    """,
    # Element write to an UNRELATED map must not block the fold.
    "unrelated_element_write": """
        Int O(Int k, Set<Int> S, Map<Int, Int> T) {
            if (k in S) {
                T[k] = 1;
                if (k in S) {
                    return 1;
                }
                return 2;
            }
            return 0;
        }
    """,
    # <-uniq into an UNRELATED set must not block the fold.
    "unrelated_uniq": """
        Int O(BitString<1> e, Set<BitString<1>> S, Set<BitString<1>> U) {
            if (e in S) {
                BitString<1> y <-uniq[U] BitString<1>;
                if (e in S) {
                    return 1;
                }
                return 2;
            }
            return 0;
        }
    """,
}


@pytest.mark.parametrize("name", sorted(CONTROLS))
def test_control_fires(name: str) -> None:
    src = CONTROLS[name]
    before = str(frog_parser.parse_method(src))
    after = _run(src)
    assert before != after, f"{name}: pass failed to fold a stable guard\n{after}"
    assert "if (true)" in after or "if (false)" in after, (
        f"{name}: inner guard not substituted\n{after}"
    )
