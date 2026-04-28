"""Backend-neutral pseudocode IR.

The IR is the seam between FrogLang-aware renderers and a specific LaTeX
pseudocode package. AST -> IR is shared; IR -> LaTeX is per-backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Sample:
    lhs: str
    rhs: str


@dataclass
class Assign:
    lhs: str
    rhs: str


@dataclass
class Return:
    expr: str


@dataclass
class If:
    cond: str


@dataclass
class Else:
    pass


@dataclass
class EndIf:
    pass


@dataclass
class For:
    header: str


@dataclass
class EndFor:
    pass


@dataclass
class Comment:
    text: str


@dataclass
class Raw:
    """Escape hatch: pre-rendered LaTeX line."""

    latex: str


Line = Union[Sample, Assign, Return, If, Else, EndIf, For, EndFor, Comment, Raw]


@dataclass
class ProcedureBlock:
    title: str
    lines: list[Line] = field(default_factory=list)


@dataclass
class VStack:
    blocks: list[ProcedureBlock]
    boxed: bool = True


@dataclass
class Figure:
    body: Union[VStack, ProcedureBlock]
    caption: str | None = None
    label: str | None = None
