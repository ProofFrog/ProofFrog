"""Type rendering, including macroification of algorithm-like group names.

Part 3 secondary gap: a group variable inside a type argument (e.g.
``GroupElem<G>``, which prints as its group ``G``) must be macroified to
``\\G``, so a game reference reads ``\\RandomTargetGuessing(\\G)`` rather than
``\\RandomTargetGuessing(G)``.
"""

from pathlib import Path

from proof_frog import frog_ast
from proof_frog.export.latex.exporter import export_file
from proof_frog.export.latex.expr_renderer import ExprRenderer
from proof_frog.export.latex.macros import MacroRegistry
from proof_frog.export.latex.type_renderer import TypeRenderer

REPO = Path(__file__).resolve().parents[4]


def _types() -> TypeRenderer:
    return TypeRenderer(ExprRenderer(MacroRegistry()))


def test_group_elem_macroifies_algorithm_like_group() -> None:
    t = frog_ast.GroupElemType(frog_ast.Variable("G"))
    assert _types().render(t) == r"\G"


def test_group_elem_keeps_lowercase_group_plain() -> None:
    # A lowercase (non-algorithm-like) group name is not macroified; it renders
    # as a plain multi-letter identifier (one italic unit, not \mathsf).
    t = frog_ast.GroupElemType(frog_ast.Variable("grp"))
    assert _types().render(t) == r"\mathit{grp}"


def test_bare_type_variable_macroifies_algorithm_like_name() -> None:
    assert _types().render(frog_ast.Variable("G")) == r"\G"


def test_ddh_proof_macroifies_group_in_type_arg() -> None:
    out = export_file(str(REPO / "examples/Proofs/Group/DDH_implies_CDH.proof"))
    assert r"\RandomTargetGuessing(\G)" in out
    assert r"\RandomTargetGuessing(G)" not in out
