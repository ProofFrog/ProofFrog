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
