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


_DIFF_COLOR = "blue"


class CryptocodeBackend:
    """Render IR using the LaTeX ``cryptocode`` package."""

    name = "cryptocode"

    def __init__(self, diff_style: str = "box") -> None:
        # How a diff-highlighted line (D1) renders: "box" wraps it in
        # cryptocode's gray ``\gamechange`` colorbox; "color" wraps it in a
        # color group. Selectable by the user via ``--diff-style``.
        self.diff_style = diff_style

    def required_packages(self) -> list[PackageSpec]:
        return [
            PackageSpec("cryptocode", _CRYPTOCODE_OPTIONS),
            PackageSpec("amsmath"),
            PackageSpec("amssymb"),
            PackageSpec("amsthm"),
            PackageSpec("adjustbox"),
            PackageSpec("varwidth"),
        ]

    def fit_width(self, content: str) -> str:
        """Shrink ``content`` to ``\\textwidth`` only if it is wider (A1).

        ``adjustbox``'s ``max width`` leaves content narrower than the text
        block untouched and scales down anything that would otherwise run past
        the right margin (and the box frame) without erroring.

        cryptocode's ``pcvstack`` / ``pchstack`` need vertical mode, so they
        cannot be placed directly in ``adjustbox``'s LR box ("Not allowed in
        LR mode"). Wrapping them in a ``varwidth`` first gives ``adjustbox`` a
        box whose width is the content's *natural* width: ``varwidth`` shrinks
        to fit its body up to the supplied bound. The bound is a generous
        ``4\\textwidth`` so genuinely over-wide figures still measure their
        true width (and thus scale down) rather than clamping at the bound and
        overflowing.
        """
        boxed = rf"\begin{{varwidth}}{{4\textwidth}}{content}\end{{varwidth}}"
        return rf"\adjustbox{{max width=\textwidth}}{{{boxed}}}"

    def preamble_extras(self) -> str:
        return (
            r"\newtheorem{theorem}{Theorem}" + "\n"
            r"\providecommand{\todo}[1]{\textbf{TODO:} #1}" + "\n"
            r"\providecommand{\Experiment}[3]{\ensuremath{\mathsf{Exp}^{#1.#2}_{#3}}}"
            + "\n"
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

    def highlight(self, content: str) -> str:
        """Wrap diff-changed math content in the configured highlight (D1).

        Used both for changed procedure lines and for the changed components of
        a symbolic game heading (e.g. ``DDH.Left`` -> ``DDH.Right``). Procedure
        cells and headings are both math mode, but ``\\gamechange`` typesets its
        argument inside a ``\\colorbox`` (an LR box), where math mode is *off* --
        so the math content must be re-entered explicitly with ``$...$`` or it
        errors ("Missing $ inserted"). The ``\\color`` group, by contrast, keeps
        the surrounding math mode, so it needs no delimiters. Any ``\\pcind``
        indent is applied by the caller *outside* this wrapper so only the
        content is marked.
        """
        if self.diff_style == "color":
            return rf"{{\color{{{_DIFF_COLOR}}} {content}}}"
        return rf"\gamechange{{${content}$}}"

    def _indented_line(self, line: ir.Line) -> str:
        """Render one IR line, prefixing one ``\\pcind`` per nesting depth.

        ``\\pcind`` is cryptocode's one-level procedure indent. The indent goes
        *after* the ``\\\\`` line break (added by the join) and *before* the
        line content, so guarded bodies sit one level deeper than their
        If/For markers (A3). A diff-highlighted line is wrapped *inside* the
        indent so the box/color hugs the content, not the leading space.
        """
        rendered = self._line(line)
        if line.highlight:
            rendered = self.highlight(rendered)
        if line.depth <= 0:
            return rendered
        return r"\pcind" * line.depth + " " + rendered

    def render_procedure(self, p: ir.ProcedureBlock) -> str:
        # Drop the closing ``\pcfi``: A3 indentation already shows the guarded
        # body's scope, and papers do not number a ``fi`` line. (``\pcelse`` /
        # ``\pcendfor`` are kept -- only the redundant ``if`` terminator goes.)
        lines = [ln for ln in p.lines if not isinstance(ln, ir.EndIf)]
        if not lines:
            return "\\procedure[linenumbering]{$" + p.title + "$}{}"
        body = " \\\\\n    ".join(self._indented_line(ln) for ln in lines)
        return "\\procedure[linenumbering]{$" + p.title + "$}{\n    " + body + "\n}"

    def render_vstack(self, v: ir.VStack) -> str:
        # A little vertical breathing room between stacked oracles, via
        # ``pcvstack``'s ``space=`` key (its inter-entry gap, default 0pt).
        # ``\pclb`` itself takes no argument -- a ``\pclb[..]`` leaks the
        # bracketed text into the next cell rather than adding space.
        keys = ["space=\\smallskipamount"]
        if v.boxed:
            keys.insert(0, "boxed")
        opt = "[" + ",".join(keys) + "]"
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
        # A2: side-by-side columns are top-aligned. cryptocode has no [top] key
        # on pchstack, but each pcvstack already raises its content to the strut
        # top (`\raisebox{\dimexpr\ht\strutbox-\height}{\begin{varwidth}[t]...}`
        # in cryptocode.sty), so unequal-height columns share a top edge by
        # default -- the alignment game pairs read best with. Verified visually
        # on an asymmetric pair; no key to add.
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
            parts.append(self.fit_width(inner))
        if f.caption:
            parts.append(rf"\caption{{{f.caption}}}")
        if f.label:
            parts.append(rf"\label{{{f.label}}}")
        parts.append("\\end{figure}")
        return "\n".join(parts)
