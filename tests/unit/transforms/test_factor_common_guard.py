import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import (
    FactorCommonGuardTransformer,
    MergeNestedGuardTransformer,
    GuardConditionSimplificationTransformer,
    IfToBooleanAssignmentTransformer,
    DeadGuardedAssignmentEliminationTransformer,
)


@pytest.mark.parametrize(
    "method,expected",
    [
        # P-first -> V-first: a shared inner `if (V)` is factored out of the
        # `if (P)` arm and the fall-through.
        (
            """
            Int f(Bool P, Bool V) {
                if (P) {
                    if (V) {
                        return 1;
                    }
                    return 2;
                }
                if (V) {
                    return 3;
                }
                return 2;
            }
            """,
            """
            Int f(Bool P, Bool V) {
                if (V) {
                    if (P) {
                        return 1;
                    } else {
                        return 3;
                    }
                }
                return 2;
            }
            """,
        ),
        # No change when the trailing returns differ (V-false behavior is not
        # the same under P and not-P).
        (
            """
            Int f(Bool P, Bool V) {
                if (P) {
                    if (V) {
                        return 1;
                    }
                    return 2;
                }
                if (V) {
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f(Bool P, Bool V) {
                if (P) {
                    if (V) {
                        return 1;
                    }
                    return 2;
                }
                if (V) {
                    return 3;
                }
                return 4;
            }
            """,
        ),
        # No change when the inner conditions differ (no shared guard).
        (
            """
            Int f(Bool P, Bool V, Bool W) {
                if (P) {
                    if (V) {
                        return 1;
                    }
                    return 2;
                }
                if (W) {
                    return 3;
                }
                return 2;
            }
            """,
            """
            Int f(Bool P, Bool V, Bool W) {
                if (P) {
                    if (V) {
                        return 1;
                    }
                    return 2;
                }
                if (W) {
                    return 3;
                }
                return 2;
            }
            """,
        ),
    ],
)
def test_factor_common_guard(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = FactorCommonGuardTransformer().transform(method_ast)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "method,expected",
    [
        # The nested guard whose only effect is an inner early return merges
        # into a conjunction.
        (
            """
            Int f(Bool P, Bool Q) {
                if (P) {
                    if (Q) {
                        return 1;
                    }
                    return 2;
                }
                return 2;
            }
            """,
            """
            Int f(Bool P, Bool Q) {
                if (P && Q) {
                    return 1;
                }
                return 2;
            }
            """,
        ),
        # No change when the trailing TAILs differ.
        (
            """
            Int f(Bool P, Bool Q) {
                if (P) {
                    if (Q) {
                        return 1;
                    }
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool P, Bool Q) {
                if (P) {
                    if (Q) {
                        return 1;
                    }
                    return 2;
                }
                return 3;
            }
            """,
        ),
    ],
)
def test_merge_nested_guard(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = MergeNestedGuardTransformer().transform(method_ast)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "method,expected",
    [
        # A guard condition is known true in its then-branch and false in its
        # else-branch, so re-tests of it simplify.
        (
            """
            Bool f(Int x, Set<Int> S) {
                Bool b = false;
                if (x in S) {
                    b = x in S;
                } else {
                    b = x in S;
                }
                return b;
            }
            """,
            """
            Bool f(Int x, Set<Int> S) {
                Bool b = false;
                if (x in S) {
                    b = true;
                } else {
                    b = false;
                }
                return b;
            }
            """,
        ),
    ],
)
def test_guard_condition_simplification(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = GuardConditionSimplificationTransformer().transform(method_ast)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "method,expected",
    [
        # if (C) { x = true } else { x = false }  ->  x = C
        (
            """
            Bool f(Int x, Set<Int> S) {
                Bool b = false;
                if (x in S) {
                    b = true;
                } else {
                    b = false;
                }
                return b;
            }
            """,
            """
            Bool f(Int x, Set<Int> S) {
                Bool b = false;
                b = x in S;
                return b;
            }
            """,
        ),
        # if (C) { x = false } else { x = true }  ->  x = !C
        (
            """
            Bool f(Bool c) {
                Bool b = false;
                if (c) {
                    b = false;
                } else {
                    b = true;
                }
                return b;
            }
            """,
            """
            Bool f(Bool c) {
                Bool b = false;
                b = !c;
                return b;
            }
            """,
        ),
    ],
)
def test_if_to_boolean_assignment(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = IfToBooleanAssignmentTransformer().transform(method_ast)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "method,expected",
    [
        # The `v = W` reached only under `P && !M` is dead: when `P && !M`,
        # `if (v) { if (P && !M) return 1 ... }` returns 1 whether or not v is
        # set, and the fall-through also returns 1. So it becomes `v = false`.
        # The `v = W` under `\!P` is NOT dead (the path does not entail G).
        (
            """
            Int f(Bool P, Bool M, Bool W) {
                Bool v = false;
                if (P) {
                    if (M) {
                        v = true;
                    } else {
                        v = W;
                    }
                } else {
                    v = W;
                }
                if (v) {
                    if (P && !M) {
                        return 1;
                    }
                    return 2;
                }
                return 1;
            }
            """,
            """
            Int f(Bool P, Bool M, Bool W) {
                Bool v = false;
                if (P) {
                    if (M) {
                        v = true;
                    } else {
                        v = false;
                    }
                } else {
                    v = W;
                }
                if (v) {
                    if (P && !M) {
                        return 1;
                    }
                    return 2;
                }
                return 1;
            }
            """,
        ),
        # Not applicable: the fall-through return (3) differs from the inner
        # guarded return (1), so v is observable.
        (
            """
            Int f(Bool P, Bool M, Bool W) {
                Bool v = false;
                if (P) {
                    if (M) { v = true; } else { v = W; }
                } else {
                    v = W;
                }
                if (v) {
                    if (P && !M) { return 1; }
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool P, Bool M, Bool W) {
                Bool v = false;
                if (P) {
                    if (M) { v = true; } else { v = W; }
                } else {
                    v = W;
                }
                if (v) {
                    if (P && !M) { return 1; }
                    return 2;
                }
                return 3;
            }
            """,
        ),
    ],
)
def test_dead_guarded_assignment_elimination(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    result = DeadGuardedAssignmentEliminationTransformer().transform(method_ast)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"
