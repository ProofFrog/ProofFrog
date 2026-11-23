"""F-420: no pass puts a variable the game changes into a type.

A type names only values that stay fixed (the structural rule for source
files, F-367), because the passes compare types by their text and read a
store into a declared variable as reading nothing of its type. The inliner
binds a callee parameter read in a type to a fresh variable when its
argument reads a changing variable; a forwarding pass must not put the
changing variable back (Remove Redundant Copies turned ``Int k0 = c;
ModInt<k0> v;`` into ``ModInt<c> v;``, after which Topological Sorting moved
``c = c + 1;`` in front of the store into ``v`` and Merge Bare Declaration
merged the declaration with the store after the write). ``apply_pass``, used
by every pipeline runner, refuses such an output.
"""

from __future__ import annotations

from collections import Counter

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import (
    PipelineContext,
    TransformPass,
    apply_pass,
    changing_type_name_counts,
)
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


@pytest.mark.parametrize(
    "source, expected",
    [
        # A field the game writes, read in a type.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ ModInt<c> v = a; c = c + 1; return v == v; } }",
            {"c": 1},
        ),
        # A field nothing writes.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ ModInt<c> v = a; return v == v; } }",
            {},
        ),
        # A local bound once and never written.
        (
            "Game T() { Int c = 2; Bool f(Int a) "
            "{ Int k = c; ModInt<k> v = a; c = c + 1; return v == v; } }",
            {},
        ),
        # A local bound twice.
        (
            "Game T() { Bool f(Int a, Bool b) { if (b) { Int k = 2; "
            "ModInt<k> v = a; return v == v; } Int k = 3; ModInt<k> w = a; "
            "return w == w; } }",
            {"k": 2},
        ),
        # An element write changes the array.
        (
            "Game T() { Array<Int, 2> A; Bool f(Int a) "
            "{ BitString<A[0]> x <- BitString<A[0]>; A[0] = 5; return x == x; } }",
            {"A": 2},
        ),
    ],
)
def test_changing_type_name_counts(source: str, expected: dict[str, int]) -> None:
    game = frog_parser.parse_game(source)
    assert changing_type_name_counts(game) == Counter(expected)


_BOUND = (
    "Game T() { Int c = 2; Bool f(Int a) "
    "{ Int k = c; ModInt<k> v = a; c = c + 1; return v == v; } }"
)


class _Forward(TransformPass):
    """Stands for a forwarding pass: returns a fixed game."""

    name = "Test Forward"

    def __init__(self, result: str) -> None:
        self.result = frog_parser.parse_game(result)

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return self.result


def test_apply_pass_refuses_a_changing_name_put_into_a_type() -> None:
    game = frog_parser.parse_game(_BOUND)
    ctx = _ctx()
    forwarded = (
        "Game T() { Int c = 2; Bool f(Int a) "
        "{ ModInt<c> v = a; c = c + 1; return v == v; } }"
    )
    result = apply_pass(_Forward(forwarded), game, ctx)
    assert result is game
    assert any(
        miss.transform_name == "Test Forward" and miss.variable == "c"
        for miss in ctx.near_misses
    ), ctx.near_misses


def test_apply_pass_refuses_a_write_to_a_name_a_type_reads() -> None:
    """Writing a name that a type already reads makes it change too."""
    game = frog_parser.parse_game(
        "Game T() { Int c = 2; Bool f(Int a) { ModInt<c> v = a; return v == v; } }"
    )
    ctx = _ctx()
    written = (
        "Game T() { Int c = 2; Bool f(Int a) "
        "{ ModInt<c> v = a; c = c + 1; return v == v; } }"
    )
    assert apply_pass(_Forward(written), game, ctx) is game


def test_apply_pass_keeps_an_output_that_adds_no_changing_name() -> None:
    game = frog_parser.parse_game(_BOUND)
    ctx = _ctx()
    output = (
        "Game T() { Int c = 2; Bool f(Int a) "
        "{ Int k = c; c = c + 1; ModInt<k> v = a; return v == v; } }"
    )
    result = apply_pass(_Forward(output), game, ctx)
    assert result == frog_parser.parse_game(output)
    assert not ctx.near_misses
