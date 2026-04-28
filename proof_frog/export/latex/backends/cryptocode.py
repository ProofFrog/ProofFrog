"""cryptocode-package backend."""

from __future__ import annotations

from .. import ir
from .base import PackageSpec

_CRYPTOCODE_OPTIONS = (
    "n",
    "advantage",
    "operators",
    "sets",
    "adversary",
    "landau",
    "probability",
    "notions",
    "logic",
    "ff",
    "mm",
    "primitives",
    "events",
    "complexity",
    "oracles",
    "asymptotics",
    "keys",
)


class CryptocodeBackend:
    """Render IR using the LaTeX ``cryptocode`` package."""

    name = "cryptocode"

    def required_packages(self) -> list[PackageSpec]:
        return [
            PackageSpec("cryptocode", _CRYPTOCODE_OPTIONS),
            PackageSpec("amsmath"),
            PackageSpec("amssymb"),
        ]

    def preamble_extras(self) -> str:
        return ""

    def _line(self, line: ir.Line) -> str:
        match line:
            case ir.Sample(lhs, rhs):
                return rf"{lhs} \getsr {rhs}"
            case ir.Assign(lhs, rhs):
                return rf"{lhs} \gets {rhs}"
            case ir.Return(expr):
                return rf"\pcreturn {expr}"
            case ir.If(cond):
                return rf"\pcif {cond} \pcthen"
            case ir.Else():
                return r"\pcelse"
            case ir.EndIf():
                return r"\pcfi"
            case ir.For(header):
                return rf"\pcfor {header} \pcdo"
            case ir.EndFor():
                return r"\pcendfor"
            case ir.Comment(text):
                return rf"\pccomment{{{text}}}"
            case ir.Raw(latex):
                return latex
        raise TypeError(f"unknown IR line: {line!r}")

    def render_procedure(self, p: ir.ProcedureBlock) -> str:
        body = " \\\\\n    ".join(self._line(ln) for ln in p.lines)
        return "\\procedure[linenumbering]{$" + p.title + "$}{\n    " + body + "\n}"

    def render_vstack(self, v: ir.VStack) -> str:
        opt = "[boxed]" if v.boxed else ""
        body = "\n\\pclb\n".join(self.render_procedure(b) for b in v.blocks)
        return f"\\begin{{pcvstack}}{opt}\n{body}\n\\end{{pcvstack}}"

    def render_figure(self, f: ir.Figure) -> str:
        inner = (
            self.render_vstack(f.body)
            if isinstance(f.body, ir.VStack)
            else self.render_procedure(f.body)
        )
        parts = ["\\begin{figure}[ht]", "\\centering", inner]
        if f.caption:
            parts.append(rf"\caption{{{f.caption}}}")
        if f.label:
            parts.append(rf"\label{{{f.label}}}")
        parts.append("\\end{figure}")
        return "\n".join(parts)
