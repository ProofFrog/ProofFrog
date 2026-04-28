"""Backend protocol for LaTeX pseudocode packages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .. import ir


@dataclass(frozen=True)
class PackageSpec:
    name: str
    options: tuple[str, ...] = ()


class Backend(Protocol):
    name: str

    def required_packages(self) -> list[PackageSpec]: ...

    def preamble_extras(self) -> str: ...

    def render_procedure(self, p: ir.ProcedureBlock) -> str: ...

    def render_vstack(self, v: ir.VStack) -> str: ...

    def render_figure(self, f: ir.Figure) -> str: ...
