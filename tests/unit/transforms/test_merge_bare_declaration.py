"""Tests for MergeBareDeclaration."""

from proof_frog import frog_parser
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
