"""Unit tests for ``SliceOfInlineConcat``.

The transform simplifies ``(a || b)[start:end]`` to ``a`` (or ``b``)
when the slice bounds match exactly the boundary of one operand, with
operand lengths recovered from declared ``BitString<...>`` types
(fields, parameters, locals).
"""

import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import SliceOfInlineConcatTransformer


@pytest.mark.parametrize(
    "game,expected",
    [
        # Field-scoped operands: slice on the LHS boundary -> a.
        (
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<8> f() {
                    return (a || b)[0 : 8];
                }
            }
            """,
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<8> f() {
                    return a;
                }
            }
            """,
        ),
        # Field-scoped operands: slice on the RHS boundary -> b.
        (
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<16> f() {
                    return (a || b)[8 : 8 + 16];
                }
            }
            """,
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<16> f() {
                    return b;
                }
            }
            """,
        ),
        # Non-trivial length expression (e.g. KEM_PQ.Nseed flavour).
        (
            """
            Game G() {
                BitString<n> a;
                BitString<m> b;
                BitString<n> f() {
                    return (a || b)[0 : n];
                }
            }
            """,
            """
            Game G() {
                BitString<n> a;
                BitString<m> b;
                BitString<n> f() {
                    return a;
                }
            }
            """,
        ),
        # Negative case: bounds don't match an operand boundary -> unchanged.
        (
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<4> f() {
                    return (a || b)[0 : 4];
                }
            }
            """,
            """
            Game G() {
                BitString<8> a;
                BitString<16> b;
                BitString<4> f() {
                    return (a || b)[0 : 4];
                }
            }
            """,
        ),
        # Negative case: operand length not derivable -> unchanged.
        (
            """
            Game G() {
                BitString<8> f() {
                    return (g() || h())[0 : 8];
                }
            }
            """,
            """
            Game G() {
                BitString<8> f() {
                    return (g() || h())[0 : 8];
                }
            }
            """,
        ),
        # Method-parameter operands: slice on LHS boundary -> a.
        (
            """
            Game G() {
                BitString<8> f(BitString<8> a, BitString<16> b) {
                    return (a || b)[0 : 8];
                }
            }
            """,
            """
            Game G() {
                BitString<8> f(BitString<8> a, BitString<16> b) {
                    return a;
                }
            }
            """,
        ),
        # Method-local typed declarations: slice on RHS boundary -> b.
        (
            """
            Game G() {
                BitString<24> f() {
                    BitString<8> a = g();
                    BitString<16> b = h();
                    return (a || b)[8 : 8 + 16];
                }
            }
            """,
            """
            Game G() {
                BitString<24> f() {
                    BitString<8> a = g();
                    BitString<16> b = h();
                    return b;
                }
            }
            """,
        ),
    ],
)
def test_slice_of_inline_concat(game: str, expected: str) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)
    transformed = SliceOfInlineConcatTransformer().transform_game(game_ast)
    assert transformed == expected_ast


# ---------------------------------------------------------------------------
# F-029: the operand length used at the slice site must be the operand's TRUE
# length in its own scope, not a stale flat name-keyed table.  The pass must
# DECLINE (leave the slice unchanged) when a stale length would otherwise make
# a wrong boundary match.  Each game below is a soundness attack from the
# SliceOfInlineConcat prosecution.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "game",
    [
        # Attack 1 (Gap B): a decl-only local `BitString<n> x;` + untyped
        # resample shadows the 2n-bit parameter `x`.  The old flat scan kept
        # the parameter length (2n) for `x`, so `(x || b)[0 : 2n]` matched
        # Case 1 against the stale 2n and returned the n-bit local `x`,
        # dropping `b`.  Scope-aware tracking records `x = n`, so Case 1's
        # `end (2n) == |x| (n)` is false and the slice is left intact.
        """
        Game G(Int n) {
            BitString<2 * n> Oracle(BitString<2 * n> x, BitString<n> b) {
                BitString<n> x;
                x <- BitString<n>;
                return (x || b)[0 : 2 * n];
            }
        }
        """,
        # Attack 2 (Gap A): a nested-block redeclaration `BitString<2n> a`
        # shadows the outer `BitString<n> a`.  The flat top-level scan never
        # saw the inner declaration, so the slice on the inner (2n-bit) `a`
        # fired Case 1 against the outer length n.  Scope-aware tracking
        # records `a = 2n` inside the if-block, so the slice is left intact.
        """
        Game G(Int n) {
            BitString<n> Oracle(Bool cond, BitString<n> b) {
                BitString<n> a <- BitString<n>;
                if (cond) {
                    BitString<2 * n> a <- BitString<2 * n>;
                    return (a || b)[0 : n];
                }
                return a;
            }
        }
        """,
        # Attack 3 (Gap A, Case 2): same nested redeclaration, exercising the
        # Case 2 boundary `[|a| : |a| + |b|]`.  The slice reads a middle window
        # of the inner 2n-bit `a` and must not be rewritten to `b`.
        """
        Game G(Int n) {
            [BitString<n>, BitString<n>] Oracle(Bool cond, BitString<n> b) {
                BitString<n> a <- BitString<n>;
                if (cond) {
                    BitString<2 * n> a <- BitString<2 * n>;
                    return [(a || b)[n : n + n], b];
                }
                return [b, b];
            }
        }
        """,
    ],
)
def test_slice_of_inline_concat_declines_on_stale_length(game: str) -> None:
    game_ast = frog_parser.parse_game(game)
    transformed = SliceOfInlineConcatTransformer().transform_game(game_ast)
    assert transformed == game_ast, "pass must decline when the operand length is shadowed"
