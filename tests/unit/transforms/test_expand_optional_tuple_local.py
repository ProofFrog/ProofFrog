"""Expand Tuple: an optional tuple local initialized with a tuple literal.

A local ``[A, B]? t = [a, b];`` holds a tuple, never ``None``: a tuple
literal is not ``None``. When nothing writes or re-declares ``t`` afterwards
and every later mention is an element read ``t[i]`` at a constant index, it
splits like a ``[A, B]`` local into ``A t@0 = a; B t@1 = b;``, each element
evaluated once, as the literal evaluates it. A ``None`` test or a use of the
whole ``t`` keeps it (attack-proof prerequisite G5: an adversary's optional
result tuple whose first element is read three times).
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.tuples import ExpandTuple, SplitBareTupleDeclarations
from proof_frog.visitors import NameTypeMap

_B = "BitString<8>"
_PAIR = f"[{_B}, {_B}]"


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _game(body: str, return_type: str = "Bool") -> frog_ast.Game:
    return frog_parser.parse_game(
        f"Game G() {{ {return_type} f({_B} a, {_B} b) {{ {body} }} }}"
    )


def _statements(game: frog_ast.Game) -> list[str]:
    return [" ".join(str(s).split()) for s in game.methods[0].block.statements]


def test_optional_tuple_local_splits() -> None:
    game = _game(f"{_PAIR}? t = [a, b]; return t[0] == t[1];")
    result = ExpandTuple().apply(game, _ctx())
    assert _statements(result) == [
        f"{_B} t@0 = a;",
        f"{_B} t@1 = b;",
        "return t@0 == t@1;",
    ]


def test_nested_optional_tuple_local_splits_both_levels() -> None:
    game = _game(
        f"[{_PAIR}, {_B}]? t = [[a, b], a]; " "return t[0][0] == t[1] && t[0][1] == b;"
    )
    ctx = _ctx()
    result = ExpandTuple().apply(ExpandTuple().apply(game, ctx), ctx)
    assert _statements(result) == [
        f"{_B} t@0@0 = a;",
        f"{_B} t@0@1 = b;",
        f"{_B} t@1 = a;",
        "return t@0@0 == t@1 && t@0@1 == b;",
    ]


@pytest.mark.parametrize(
    "body, return_type, reason",
    [
        # Written as a whole afterwards.
        (f"{_PAIR}? t = [a, b]; t = [b, a]; return t[0] == a;", "Bool", "written"),
        # An element written afterwards.
        (f"{_PAIR}? t = [a, b]; t[0] = b; return t[0] == a;", "Bool", "written"),
        # Re-declared in an inner block.
        (
            f"{_PAIR}? t = [a, b]; if (a == b) {{ {_PAIR}? t = [b, b]; "
            "return t[0] == a; } return t[1] == a;",
            "Bool",
            "written",
        ),
        # Compared with None.
        (
            f"{_PAIR}? t = [a, b]; if (t == None) {{ return false; }} "
            "return t[0] == a;",
            "Bool",
            "element reads",
        ),
        # Returned whole.
        (f"{_PAIR}? t = [a, b]; return t;", f"{_PAIR}?", "element reads"),
    ],
)
def test_optional_tuple_local_kept(body: str, return_type: str, reason: str) -> None:
    game = _game(body, return_type)
    ctx = _ctx()
    # The outer declaration stays whole (an inner one may split on its own).
    assert _statements(ExpandTuple().apply(game, ctx))[0] == f"{_PAIR}? t = [a, b];"
    misses = [nm for nm in ctx.near_misses if nm.variable == "t"]
    assert misses, ctx.near_misses
    assert misses[0].transform_name == "Expand Tuples"
    assert reason in misses[0].reason, misses[0].reason


def test_optional_tuple_local_with_opaque_value_kept() -> None:
    """The value may be None: only a tuple literal is known not to be."""
    game = frog_parser.parse_game(
        f"Game G(F E) {{ Bool f({_B} a) {{ {_PAIR}? t = E.Get(a); "
        "return t[0] == a; } }"
    )
    assert ExpandTuple().apply(game, _ctx()) == game


def test_bare_optional_tuple_declaration_kept() -> None:
    """``[A, B]? t;`` starts as None."""
    game = _game(f"{_PAIR}? t; t = [a, b]; return t[0] == a;")
    ctx = _ctx()
    assert SplitBareTupleDeclarations().apply(game, ctx) == game
    assert ExpandTuple().apply(game, ctx) == game


def test_near_miss_for_an_alpha_renamed_local_names_no_variable() -> None:
    """Alpha Rename runs first, so the pass sees ``__a0__``: the near miss
    describes the local by its declaration and leaves ``variable`` unset, or
    the diagnostics (which look for the name in the canonical diff) drop
    it."""
    game = frog_parser.parse_game(
        f"Game G() {{ {_PAIR}? f({_B} a, {_B} b) {{ "
        f"{_PAIR}? __a0__ = [a, b]; return __a0__; }} }}"
    )
    ctx = _ctx()
    assert ExpandTuple().apply(game, ctx) == game
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Expand Tuples"]
    assert misses, ctx.near_misses
    assert misses[0].variable is None
    assert "__a0__" not in misses[0].reason
    assert f"a local of type '{_PAIR}?' initialized to '[a, b]'" in misses[0].reason


def test_literal_shorter_than_its_type_is_kept() -> None:
    """An ill-typed AST (the type checker refuses it) neither splits nor
    crashes the pass."""
    game = _game(f"[{_B}, {_B}, {_B}]? t = [a, b]; return t[0] == a;")
    assert ExpandTuple().apply(game, _ctx()) == game
