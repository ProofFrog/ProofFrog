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
            PackageSpec("amsthm"),
        ]

    def preamble_extras(self) -> str:
        return (
            r"\newtheorem{theorem}{Theorem}" + "\n"
            r"\providecommand{\todo}[1]{\textbf{TODO:} #1}" + "\n"
            r"\providecommand{\Experiment}[3]{\ensuremath{{#1}.{#2}(#3)}}" + "\n"
            r"\providecommand{\getsr}{\sample}"
        )

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
        if not p.lines:
            return "\\procedure[linenumbering]{$" + p.title + "$}{}"
        body = " \\\\\n    ".join(self._line(ln) for ln in p.lines)
        return "\\procedure[linenumbering]{$" + p.title + "$}{\n    " + body + "\n}"

    def render_vstack(self, v: ir.VStack) -> str:
        opt = "[boxed]" if v.boxed else ""
        body = "\n\\pclb\n".join(self.render_procedure(b) for b in v.blocks)
        inner = f"\\begin{{pcvstack}}{opt}\n{body}\n\\end{{pcvstack}}"
        if v.heading:
            # Title *above* the box: an outer (unboxed) pcvstack whose first
            # entry is the heading and second is the boxed inner stack. Entries
            # in a pcvstack are separated by a blank line (\par); \pclb would
            # keep them on one line (title beside the box instead of above it).
            return f"\\begin{{pcvstack}}\n{v.heading}\n\n{inner}\n\\end{{pcvstack}}"
        return inner

    def render_hstack(self, h: ir.HStack) -> str:
        body = "\n\\pchspace\n".join(self.render_vstack(v) for v in h.stacks)
        return f"\\begin{{pchstack}}\n{body}\n\\end{{pchstack}}"

    def render_figure(self, f: ir.Figure) -> str:
        parts = ["\\begin{figure}[ht]", "\\centering"]
        if f.heading:
            parts.append(f.heading)
            if f.body is not None:
                parts.append("\\par\\smallskip")
        if f.body is not None:
            inner = (
                self.render_vstack(f.body)
                if isinstance(f.body, ir.VStack)
                else self.render_procedure(f.body)
            )
            parts.append(inner)
        if f.caption:
            parts.append(rf"\caption{{{f.caption}}}")
        if f.label:
            parts.append(rf"\label{{{f.label}}}")
        parts.append("\\end{figure}")
        return "\n".join(parts)
