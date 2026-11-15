import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import RedundantCopyTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Simple substitution
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Shouldn't be transformed (both variables used)
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = a + 1;
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                a = a + 1;
                return b;
            }
            """,
        ),
        # Douglas' test case
        (
            """
            BitString<lambda + stretch> Eval(BitString<lambda> k, BitString<lambda + stretch> m) { 
                BitString<lambda + stretch> v1 = G.evaluate(k);
                BitString<lambda + stretch> v2 = v1;
                BitString<lambda + stretch> v3 = v2 + m;
                return v1 + v3;
            }
            """,
            """
            BitString<lambda + stretch> Eval(BitString<lambda> k, BitString<lambda + stretch> m) { 
                BitString<lambda + stretch> v1 = G.evaluate(k);
                BitString<lambda + stretch> v3 = v1 + m;
                return v1 + v3;
            }
            """,
        ),
        # Many chained together
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                Int c = b;
                Int d = c;
                Int e = d;
                Int f = e;
                return f;
            }
            """,
            """
            Int f() {
                Int a = 1;
                return a;
            }
            """,
        ),
        # Works in if-statements too
        (
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    Int b = a;
                    x = b;
                } else {
                    Int a = 2;
                    Int b = a;
                    x = b;
                }
            }
            """,
            """
            Int f() {
                Int x = 0;
                if (True) {
                    Int a = 1;
                    x = a;
                } else {
                    Int a = 2;
                    x = a;
                }
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a = a + 1;
                }
                return b;
            }
            """,
            """
            Int f() {
                Int a = 1;
                Int b = a;
                if (True) {
                    a = a + 1;
                }
                return b;
            }
            """,
        ),
        (
            """
            Int f() {
                Int a = 1;
                if (True) {
                    Int b = a;
                    b = b + 1;
                }
                return a;
            }
            """,
            """
            Int f() {
                Int a = 1;
                if (True) {
                    Int b = a;
                    b = b + 1;
                }
                return a;
            }
            """,
        ),
        # F-179 positive: an array copy with no mutation still folds.
        (
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                return v[0];
            }
            """,
            """
            Int f(Array<Int, 2> w) {
                return w[0];
            }
            """,
        ),
        # F-179 decline: an element write to the original (`w[0] = 2`, an
        # ArrayAccess l-value) after the copy `v = w` must block the
        # substitution -- otherwise `return v[0]` would read post-mutation
        # state. The scan now peels the l-value via `lvalue_base_name`.
        (
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = 2;
                return v[0];
            }
            """,
            """
            Int f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = 2;
                return v[0];
            }
            """,
        ),
        # The original is overwritten, but the copy is read only in the value
        # that overwrites it (evaluated before the store): the copy goes.
        (
            """
            Int f(Int a, Int d) {
                Int b = a;
                a = b + d;
                return a;
            }
            """,
            """
            Int f(Int a, Int d) {
                a = a + d;
                return a;
            }
            """,
        ),
        # Reads of the copy before the overwrite only.
        (
            """
            Int f(Int a) {
                Int b = a;
                Int c = b + 1;
                a = 5;
                return c + a;
            }
            """,
            """
            Int f(Int a) {
                Int c = a + 1;
                a = 5;
                return c + a;
            }
            """,
        ),
        # The first write is nested in a branch, and the copy is not read from
        # there on: the reads before it are rewritten.
        (
            """
            Int f(Int a, Bool x) {
                Int b = a;
                Int c = b + 1;
                if (x) {
                    a = 1;
                }
                return c + a;
            }
            """,
            """
            Int f(Int a, Bool x) {
                Int c = a + 1;
                if (x) {
                    a = 1;
                }
                return c + a;
            }
            """,
        ),
        # Decline: the copy is read in the overwriting value AND afterwards.
        (
            """
            Int f(Int a, Int d) {
                Int b = a;
                a = b + d;
                return b;
            }
            """,
            """
            Int f(Int a, Int d) {
                Int b = a;
                a = b + d;
                return b;
            }
            """,
        ),
        # Decline: the copy is read after the original is resampled.
        (
            """
            BitString<8> f(BitString<8> a) {
                BitString<8> b = a;
                a <- BitString<8>;
                return a + b;
            }
            """,
            """
            BitString<8> f(BitString<8> a) {
                BitString<8> b = a;
                a <- BitString<8>;
                return a + b;
            }
            """,
        ),
        # Decline: the first write is nested in a branch that reads the copy
        # after the write.
        (
            """
            Int f(Int a, Bool x) {
                Int b = a;
                if (x) {
                    a = b + 1;
                    return b;
                }
                return a;
            }
            """,
            """
            Int f(Int a, Bool x) {
                Int b = a;
                if (x) {
                    a = b + 1;
                    return b;
                }
                return a;
            }
            """,
        ),
        # Decline: an element write is not a plain overwrite, even when the
        # copy is read only in its value.
        (
            """
            Array<Int, 2> f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = v[1];
                return w;
            }
            """,
            """
            Array<Int, 2> f(Array<Int, 2> w) {
                Array<Int, 2> v = w;
                w[0] = v[1];
                return w;
            }
            """,
        ),
    ],
)
def test_redundant_copies(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = RedundantCopyTransformer().transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_f181_sample_from_variable_not_a_copy() -> None:
    """F-181: `v <- w` samples a uniform element from the set `w` (a genuine
    draw, ruling 7.A.8), NOT a copy of `w`. RedundantCopy must not delete the
    draw and substitute the whole set."""
    method = frog_parser.parse_method(
        """
        Int f() {
            Set<Int> w = {0, 1};
            Int v <- w;
            return v;
        }
        """
    )
    out = str(RedundantCopyTransformer().transform(method))
    assert "Int v <- w" in out  # the draw is preserved, not deleted


def test_f181_plain_copy_still_eliminated() -> None:
    """Positive control: a plain typed alias `Int b = a;` is still eliminated."""
    method = frog_parser.parse_method(
        """
        Int f() {
            Int a = 1;
            Int b = a;
            return b;
        }
        """
    )
    out = str(RedundantCopyTransformer().transform(method))
    assert "Int b = a" not in out  # the copy is removed (b -> a)


def test_f183_declines_when_loop_binder_captures_copy_source() -> None:
    """F-183: a copy ``v = w`` must not be eliminated when a following ``for``
    binder rebinds the copy source ``w`` and the loop body uses ``v`` --
    substituting ``v -> w`` there would capture the binder's ``w``."""
    method = frog_parser.parse_method("""
        Int O(Int w) {
            Int acc = 0;
            Int v = w;
            for (Int w = 0 to 3) {
                acc = acc + v;
            }
            return acc;
        }
        """)
    # Unchanged: the loop-binder rebind of `w` blocks the substitution.
    assert RedundantCopyTransformer().transform(method) == method
