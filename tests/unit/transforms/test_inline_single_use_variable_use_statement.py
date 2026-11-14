"""F-149: Inline Single-Use Variables must not move an expression past a
write that runs inside the statement holding the use.

The pass scans the statements between `T v = expr;` and the statement that
holds the one use of `v` for writes to a free variable of `expr`. When that
statement is a branch or a loop, a write inside it can also run before the
use: earlier in the same branch, or anywhere in the loop (a later iteration
reads after an earlier one wrote). Inlining there would read the new value.
"""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    InlineSingleUseVariableTransformer,
    written_before_use_within,
)


@pytest.mark.parametrize(
    "method",
    [
        # The branch writes the free variable before the use (attack shape).
        """
        Int f(Int ctr, Bool b) {
            Int v = ctr + 1;
            if (b) {
                ctr = 100;
                return v;
            }
            return 0;
        }
        """,
        # The same in an else branch.
        """
        Int f(Int ctr, Bool b) {
            Int v = ctr + 1;
            if (b) {
                return 0;
            } else {
                ctr = 100;
                return v;
            }
        }
        """,
        # The write sits in an enclosing branch, the use in a nested one.
        """
        Int f(Int ctr, Bool b, Bool c) {
            Int v = ctr + 1;
            if (b) {
                ctr = 100;
                if (c) {
                    return v;
                }
            }
            return 0;
        }
        """,
        # The loop body writes the free variable after the use: the second
        # iteration would read the new value.
        """
        Int f(Int ctr) {
            Int total = 0;
            Int v = ctr + 1;
            for (Int j = 0 to 2) {
                total = total + v;
                ctr = 100;
            }
            return total;
        }
        """,
        # A loop inside the branch, writing in its body.
        """
        Int f(Int ctr, Bool b) {
            Int total = 0;
            Int v = ctr + 1;
            if (b) {
                for (Int j = 0 to 2) {
                    total = total + v;
                    ctr = ctr + 1;
                }
            }
            return total;
        }
        """,
        # A use in a loop header with a write in the body.
        """
        Int f(Int ctr) {
            Int total = 0;
            Int v = ctr + 1;
            for (Int j = 0 to v) {
                ctr = 0;
                total = total + 1;
            }
            return total;
        }
        """,
        # An element write to a map the expression reads.
        """
        Int f(Map<Int, Int> M, Int k, Int j, Bool b) {
            Int v = M[k] + 1;
            if (b) {
                M[j] = 5;
                return v;
            }
            return 0;
        }
        """,
        # A <-uniq draw inserts into the set the expression reads.
        """
        Int f(Set<BitString<8>> S, Bool b) {
            Int v = |S| + 1;
            if (b) {
                BitString<8> x <-uniq[S] BitString<8>;
                return v;
            }
            return 0;
        }
        """,
        # A ModInt product read after both factors change in the branch.
        """
        ModInt<q> f(ModInt<q> s, ModInt<q> t, ModInt<q> x, Bool c) {
            ModInt<q> v = s * t;
            if (c) {
                t = t + x;
                s = s + t;
                return v;
            }
            return s;
        }
        """,
    ],
)
def test_f149_declines_write_before_use_inside_use_statement(method: str) -> None:
    method_ast = frog_parser.parse_method(method)
    transformed = InlineSingleUseVariableTransformer().transform(method_ast)
    assert transformed == frog_parser.parse_method(method)


@pytest.mark.parametrize(
    "method,expected",
    [
        # The branch writes another variable before the use.
        (
            """
            Int f(Int ctr, Int other, Bool b) {
                Int v = ctr + 1;
                if (b) {
                    other = 100;
                    return v;
                }
                return other;
            }
            """,
            """
            Int f(Int ctr, Int other, Bool b) {
                if (b) {
                    other = 100;
                    return ctr + 1;
                }
                return other;
            }
            """,
        ),
        # The write is in another branch, which does not run before the use.
        (
            """
            Int f(Int ctr, Bool b) {
                Int v = ctr + 1;
                if (b) {
                    ctr = 100;
                    return 0;
                } else {
                    return v;
                }
            }
            """,
            """
            Int f(Int ctr, Bool b) {
                if (b) {
                    ctr = 100;
                    return 0;
                } else {
                    return ctr + 1;
                }
            }
            """,
        ),
        # The use is in a later condition: an earlier branch's block runs
        # only when that condition is not evaluated.
        (
            """
            Int f(Int ctr, Bool b) {
                Int v = ctr + 1;
                if (b) {
                    ctr = 100;
                    return 0;
                } else if (v == 2) {
                    return 1;
                }
                return 2;
            }
            """,
            """
            Int f(Int ctr, Bool b) {
                if (b) {
                    ctr = 100;
                    return 0;
                } else if (ctr + 1 == 2) {
                    return 1;
                }
                return 2;
            }
            """,
        ),
        # The write comes after the use in the same branch (no loop).
        (
            """
            Int f(Int ctr, Bool b) {
                Int v = ctr + 1;
                if (b) {
                    Int r = v * 2;
                    ctr = 100;
                    return r;
                }
                return 0;
            }
            """,
            """
            Int f(Int ctr, Bool b) {
                if (b) {
                    Int r = (ctr + 1) * 2;
                    ctr = 100;
                    return r;
                }
                return 0;
            }
            """,
        ),
        # A loop that writes only other variables.
        (
            """
            Int f(Int ctr) {
                Int total = 0;
                Int v = ctr + 1;
                for (Int j = 0 to 2) {
                    total = total + v;
                }
                return total;
            }
            """,
            """
            Int f(Int ctr) {
                Int total = 0;
                for (Int j = 0 to 2) {
                    total = total + (ctr + 1);
                }
                return total;
            }
            """,
        ),
    ],
)
def test_f149_still_inlines_when_no_write_precedes_use(
    method: str, expected: str
) -> None:
    method_ast = frog_parser.parse_method(method)
    transformed = InlineSingleUseVariableTransformer().transform(method_ast)
    assert transformed == frog_parser.parse_method(expected)


def _use_statement(method: str) -> frog_ast.Statement:
    """The statement after the first one in *method*'s body."""
    return frog_parser.parse_method(method).block.statements[1]


def test_written_before_use_within_simple_statement_is_false() -> None:
    stmt = _use_statement("Int f(Int c) { Int v = c; return v + c; }")
    assert not written_before_use_within(stmt, "v", {"c"})


def test_written_before_use_within_branch_prefix() -> None:
    stmt = _use_statement(
        "Int f(Int c, Bool b) { Int v = c; if (b) { c = 1; return v; } return 0; }"
    )
    assert written_before_use_within(stmt, "v", {"c"})
    assert not written_before_use_within(stmt, "v", {"d"})


def test_written_before_use_within_generic_loop_body() -> None:
    stmt = _use_statement(
        "Int f(Int c, Set<Int> S) { Int t = 0;"
        " for (Int e in S) { t = t + c; c = e; } return t; }"
    )
    assert written_before_use_within(stmt, "t", {"c"})
