"""Unit tests for UniqExclusionBranchElimination."""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import UniqExclusionBranchEliminationTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Direct equality with literal-set <-uniq exclusion: condition is false.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (false) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Symmetric: a == b vs b == a both simplify.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (b == a) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (false) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Inequality flips to true.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (a != b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (true) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Set with multiple elements: each is excluded.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                BitString<8> c <-uniq[{a, b}] BitString<8>;
                if (c == a) {
                    return 1;
                } else if (c == b) {
                    return 2;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                BitString<8> c <-uniq[{a, b}] BitString<8>;
                if (false) {
                    return 1;
                } else if (false) {
                    return 2;
                }
                return 0;
            }
            """,
        ),
        # No <-uniq constraint: condition unchanged.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Reassignment of the sampled variable invalidates the constraint.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                b <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Reassignment of an exclusion-set element also invalidates.
        (
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                a <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
            """
            Int f() {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                a <- BitString<8>;
                if (a == b) {
                    return 1;
                }
                return 0;
            }
            """,
        ),
        # Condition with `==` deeper inside an AND chain: still rewritten.
        (
            """
            Bool f(Bool other) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (other && a == b) {
                    return true;
                }
                return false;
            }
            """,
            """
            Bool f(Bool other) {
                BitString<8> a <- BitString<8>;
                BitString<8> b <-uniq[{a}] BitString<8>;
                if (other && false) {
                    return true;
                }
                return false;
            }
            """,
        ),
    ],
)
def test_uniq_exclusion_branch_elim(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed = UniqExclusionBranchEliminationTransformer().transform(method_ast)
    assert transformed == expected_ast
