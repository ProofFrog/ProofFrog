"""Backend-neutral pseudocode IR.

The IR is the seam between FrogLang-aware renderers and a specific LaTeX
pseudocode package. AST -> IR is shared; IR -> LaTeX is per-backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

# Each IR line carries a ``depth``: its control-flow nesting level. Markers
# (If/Else/EndIf/For/EndFor) take the depth of the *enclosing* block; the
# statements between a header and its end-marker take depth + 1. Backends
# prefix that many indents so nesting is visible (A3).
#
# Each line also carries a ``highlight`` flag, default False. The adjacent-game
# diff pass (D1, ``diff.py``) flips it to True on lines of a game that changed
# relative to its predecessor; backends wrap such lines in a change highlight.


@dataclass
class Sample:
    lhs: str
    rhs: str
    depth: int = 0
    highlight: bool = False


@dataclass
class Assign:
    lhs: str
    rhs: str
    depth: int = 0
    highlight: bool = False


@dataclass
class Return:
    expr: str
    depth: int = 0
    highlight: bool = False


@dataclass
class If:
    cond: str
    depth: int = 0
    highlight: bool = False


@dataclass
class Else:
    depth: int = 0
    highlight: bool = False


@dataclass
class EndIf:
    depth: int = 0
    highlight: bool = False


@dataclass
class For:
    header: str
    depth: int = 0
    highlight: bool = False


@dataclass
class EndFor:
    depth: int = 0
    highlight: bool = False


@dataclass
class Comment:
    text: str
    depth: int = 0
    highlight: bool = False


@dataclass
class Raw:
    """Escape hatch: pre-rendered LaTeX line."""

    latex: str
    depth: int = 0
    highlight: bool = False


Line = Union[Sample, Assign, Return, If, Else, EndIf, For, EndFor, Comment, Raw]


@dataclass
class ProcedureBlock:
    title: str
    lines: list[Line] = field(default_factory=list)


@dataclass
class VStack:
    blocks: list[ProcedureBlock]
    boxed: bool = True
    # Optional math-mode heading line rendered above the blocks (used to label
    # a column inside an HStack, e.g. the security-experiment title).
    heading: str | None = None


@dataclass
class HStack:
    """Lay several VStacks out side by side (e.g. the two sides of a notion)."""

    stacks: list[VStack]


@dataclass
class Figure:
    body: Union[VStack, ProcedureBlock, None] = None
    caption: str | None = None
    label: str | None = None
    heading: str | None = None  # rendered (math-mode) line above the body
