"""Tests for MergeBareDeclaration."""

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.inlining import MergeBareDeclaration
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={}, proof_let_types=NameTypeMap(), proof_namespace={}, subsets_pairs=[]
    )


def _lines(body: str) -> tuple[list[str], list[str]]:
    game = frog_parser.parse_game(f"Game T() {{\n Int f(Int a, Bool b) {{\n{body}\n}}\n}}")
    result = MergeBareDeclaration().apply(game, _ctx())
    before = [str(s).strip() for s in game.methods[0].block.statements]
    after = [str(s).strip() for s in result.methods[0].block.statements]
    return before, after


def test_merges_declaration_with_its_assignment() -> None:
    _, after = _lines("Int v;\nInt w = a + 1;\nv = a + w;\nreturn v;")
    assert after == ["Int w = a + 1;", "Int v = a + w;", "return v;"]


def test_no_merge_when_read_before_assignment() -> None:
    before, after = _lines("Int v;\nInt w = v + 1;\nv = a;\nreturn v + w;")
    assert after == before


def test_no_merge_when_assignment_reads_the_default() -> None:
    before, after = _lines("Int v;\nv = v + a;\nreturn v;")
    assert after == before


def test_no_merge_when_assigned_in_a_branch() -> None:
    before, after = _lines("Int v;\nif (b) {\nv = a;\n} else {\nv = 0;\n}\nreturn v;")
    assert after == before


# ---------------------------------------------------------------------------
# The assignment inside one branch of a later if
# ---------------------------------------------------------------------------


def test_merges_into_the_branch_holding_every_use() -> None:
    _, after = _lines("Int v;\nif (b) {\nv = a;\nreturn v;\n}\nreturn 0;")
    assert after == ["if (b) {\nInt v = a;\nreturn v;\n}", "return 0;"]


def test_merges_past_statements_in_the_block_and_the_branch() -> None:
    _, after = _lines(
        "Int v;\nInt w = a + 1;\nif (b) {\nInt x = w;\nv = x;\nreturn v;\n}\n"
        "return w;"
    )
    assert after == [
        "Int w = a + 1;",
        "if (b) {\nInt x = w;\nInt v = x;\nreturn v;\n}",
        "return w;",
    ]


def test_merges_into_an_else_if_branch() -> None:
    _, after = _lines(
        "Int v;\nif (b) {\nreturn 1;\n} else if (a == 2) {\nv = a;\nreturn v;\n}\n"
        "return 0;"
    )
    assert after == [
        "if (b) {\nreturn 1;\n} else if (a == 2) {\nInt v = a;\nreturn v;\n}",
        "return 0;",
    ]


def test_merges_into_an_else_branch() -> None:
    _, after = _lines("Int v;\nif (b) {\nreturn 1;\n} else {\nv = a;\nreturn v;\n}")
    assert after == ["if (b) {\nreturn 1;\n} else {\nInt v = a;\nreturn v;\n}"]


def _game(body: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"Game T() {{\n Int f(Int a, Bool b) {{\n{body}\n}}\n}}")


def test_merges_through_nested_ifs() -> None:
    game = _game("Int v;\nif (b) {\nif (a == 1) {\nv = a;\nreturn v;\n}\n}\nreturn 0;")
    expected = _game("if (b) {\nif (a == 1) {\nInt v = a;\nreturn v;\n}\n}\nreturn 0;")
    assert MergeBareDeclaration().apply(game, _ctx()) == expected


def test_merges_an_optional_declaration() -> None:
    # The shape inlining a decapsulation leaves: the result variable is
    # assigned and read only in the branch that returns it.
    _, after = _lines("Int? v;\nif (b) {\nv = a;\nreturn v != None;\n}\nreturn 0;")
    assert after == ["if (b) {\nInt? v = a;\nreturn v != None;\n}", "return 0;"]


def test_no_merge_when_read_after_the_if() -> None:
    # Moved into the branch, the declaration would no longer cover the read
    # after the if, which sees the default when b is false.
    before, after = _lines("Int v;\nif (b) {\nv = a;\n}\nreturn v;")
    assert after == before


def test_no_merge_when_a_condition_reads_the_variable() -> None:
    # The condition reads the default value before any assignment.
    before, after = _lines("Int v;\nif (v == a) {\nv = a;\nreturn v;\n}\nreturn 0;")
    assert after == before


def test_no_merge_when_a_later_condition_reads_the_variable() -> None:
    before, after = _lines(
        "Int v;\nif (b) {\nv = a;\nreturn v;\n} else if (v == 0) {\nreturn 1;\n}\n"
        "return 0;"
    )
    assert after == before


def test_no_merge_when_two_branches_use_the_variable() -> None:
    before, after = _lines(
        "Int v;\nif (b) {\nv = a;\nreturn v;\n} else {\nv = 1;\nreturn v;\n}"
    )
    assert after == before


def test_moves_when_the_branch_reads_the_default() -> None:
    # w holds the declaration's default value, so the declaration cannot
    # merge with the assignment; it moves, still bare, to the start of the
    # only branch that mentions v, where v starts at its default either way.
    game = _game("Int v;\nif (b) {\nInt w = v;\nv = a;\nreturn v + w;\n}\nreturn 0;")
    expected = _game(
        "if (b) {\nInt v;\nInt w = v;\nv = a;\nreturn v + w;\n}\nreturn 0;"
    )
    assert MergeBareDeclaration().apply(game, _ctx()) == expected


def test_no_merge_when_the_branch_rebinds_the_variable() -> None:
    # Merging would declare v twice in one block.
    before, after = _lines(
        "Int v;\nif (b) {\nv = a;\nInt v = 2;\nreturn v;\n}\nreturn 0;"
    )
    assert after == before


def test_no_merge_into_a_loop_body() -> None:
    # A loop body runs many times; only if-branches are entered.
    before, after = _lines("Int v;\nfor (Int i = 0 to a) {\nv = i;\n}\nreturn 0;")
    assert after == before


def test_moves_to_branch_start_above_a_loop() -> None:
    # The assignment is in a loop body, which is never entered, so the
    # declaration moves only to the start of the branch, above the loop.
    game = _game(
        "Int v;\nif (b) {\nfor (Int i = 0 to a) {\nv = i;\n}\nreturn v;\n}\n"
        "return 0;"
    )
    expected = _game(
        "if (b) {\nInt v;\nfor (Int i = 0 to a) {\nv = i;\n}\nreturn v;\n}\n"
        "return 0;"
    )
    assert MergeBareDeclaration().apply(game, _ctx()) == expected


def test_moves_bare_declaration_to_start_of_branch() -> None:
    # The branch holds every mention, but its first mention is a nested if
    # that assigns v on one path only, so no assignment can carry the
    # declaration; it moves to the start of the branch.
    game = _game(
        "Int v;\nif (b) {\nif (a == 1) {\nv = 1;\n}\nreturn v;\n}\nreturn 0;"
    )
    expected = _game(
        "if (b) {\nInt v;\nif (a == 1) {\nv = 1;\n}\nreturn v;\n}\nreturn 0;"
    )
    assert MergeBareDeclaration().apply(game, _ctx()) == expected


def test_moves_into_an_else_branch() -> None:
    game = _game(
        "Int v;\nif (b) {\nreturn 0;\n} else {\nif (a == 1) {\nv = 1;\n}\n"
        "return v;\n}"
    )
    expected = _game(
        "if (b) {\nreturn 0;\n} else {\nInt v;\nif (a == 1) {\nv = 1;\n}\n"
        "return v;\n}"
    )
    assert MergeBareDeclaration().apply(game, _ctx()) == expected


def test_no_move_when_an_else_if_condition_reads_the_variable() -> None:
    # The else-if condition reads the default on the path that skips the
    # first branch, so the declaration must stay above the if.
    before, after = _lines(
        "Int v;\nif (b) {\nif (a == 1) {\nv = 1;\n}\nreturn v;\n} "
        "else if (v == 0) {\nreturn 1;\n}\nreturn 0;"
    )
    assert after == before


def test_no_move_when_read_after_the_if() -> None:
    before, after = _lines(
        "Int v;\nif (b) {\nif (a == 1) {\nv = 1;\n}\n}\nreturn v;"
    )
    assert after == before


def test_no_move_when_the_branch_redeclares_the_variable() -> None:
    before, after = _lines(
        "Int v;\nif (b) {\nif (a == 1) {\nInt v = 1;\nreturn v;\n}\nreturn 0;\n}"
        "\nreturn 0;"
    )
    assert after == before


def test_move_records_no_near_miss() -> None:
    game = _game(
        "Int v;\nif (b) {\nif (a == 1) {\nv = 1;\n}\nreturn v;\n}\nreturn 0;"
    )
    ctx = _ctx()
    MergeBareDeclaration().apply(game, ctx)
    assert not [
        nm for nm in ctx.near_misses if nm.transform_name == "Merge Bare Declaration"
    ]


def test_engine_identifies_top_level_and_branch_declarations() -> None:
    """Two games that differ only in where `Int v;` sits, above the if or
    at the start of the only branch that mentions v, are the same program."""
    body = "if (a == 1) {{\nv = 1;\n}}\nreturn v + 1;"
    left = (
        "Game G() {\n Int f(Int a, Bool b) {\nInt v;\nif (b) {\n"
        + body.format()
        + "\n}\nreturn 0;\n}\n}"
    )
    right = (
        "Game G() {\n Int f(Int a, Bool b) {\nif (b) {\nInt v;\n"
        + body.format()
        + "\n}\nreturn 0;\n}\n}"
    )
    result = ProofEngine().check_equivalent(
        frog_parser.parse_game(left), frog_parser.parse_game(right)
    )
    assert result.valid


@pytest.mark.parametrize("optional", [False, True])
def test_engine_identifies_branch_result_with_its_guard(optional: bool) -> None:
    """The shape an inlined decapsulation leaves: the result is assigned
    and tested only in the branch that returns. Merged into the branch, the
    None test folds when `a` is not optional, and the game is `return b;`.
    With `a` optional, f(None, true) is false on the left and true on the
    right, so the engine must keep the games apart."""
    a_type = "Int?" if optional else "Int"
    left = f"""
        Game G() {{
            Bool f({a_type} a, Bool b) {{
                Int? v;
                if (b) {{
                    v = a;
                    return v != None;
                }}
                return false;
            }}
        }}
    """
    right = f"""
        Game G() {{
            Bool f({a_type} a, Bool b) {{
                return b;
            }}
        }}
    """
    result = ProofEngine().check_equivalent(
        frog_parser.parse_game(left), frog_parser.parse_game(right)
    )
    assert result.valid is not optional


# ---------------------------------------------------------------------------
# F-420: never past a write to a name the declared type reads
# ---------------------------------------------------------------------------


def test_no_merge_past_a_write_to_a_type_name() -> None:
    """Inlining can put a written variable in a type (a scheme method's
    `ModInt<k> v;` called with a field the game writes). Merged after
    `a = a + 1;`, the store would reduce modulo the new value."""
    before, after = _lines("ModInt<a> v;\na = a + 1;\nv = 2;\nreturn 0;")
    assert after == before


def test_no_move_past_a_write_to_a_type_name() -> None:
    before, after = _lines(
        "ModInt<a> v;\na = a + 1;\nif (b) {\nif (a == 1) {\nv = 1;\n}\nreturn 0;\n}"
        "\nreturn 0;"
    )
    assert after == before


def test_no_merge_past_a_rebinding_of_a_type_name() -> None:
    """A local of the type's name in between would capture the type."""
    before, after = _lines("BitString<a> v;\nInt a = 5;\nv = 0^a;\nreturn 0;")
    assert after == before
