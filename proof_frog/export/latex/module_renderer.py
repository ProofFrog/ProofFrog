"""Render top-level FrogLang modules (Primitive, Scheme, Game) to LaTeX."""

from __future__ import annotations

from ... import frog_ast
from . import ir
from .backends.base import Backend
from .expr_renderer import ExprRenderer, _looks_like_algorithm_name
from .macros import MacroRegistry
from .stmt_renderer import StmtRenderer
from .type_renderer import TypeRenderer


class ModuleRenderer:
    """Render Primitive, Scheme, and Game ASTs to LaTeX fragments.

    Output is a fragment (no document preamble); the caller wraps it.
    """

    def __init__(self, backend: Backend, macros: MacroRegistry | None = None) -> None:
        self.backend = backend
        self.macros = macros or MacroRegistry()
        self.expr = ExprRenderer(self.macros)
        self.types = TypeRenderer(self.expr)
        self.stmts = StmtRenderer(self.expr)

    # ---- Primitive ---------------------------------------------------------

    def render_primitive(self, p: frog_ast.Primitive) -> str:
        head_macro = self.macros.register_algorithm(p.name)
        params = ", ".join(self._param(par) for par in p.parameters)
        lines: list[str] = []
        lines.append(rf"\noindent\textbf{{Primitive {head_macro}}}")
        if params:
            lines.append(rf"\textit{{Parameters:}} ${params}$.")
        lines.append(r"\begin{itemize}")
        if p.fields:
            sets_str = ", ".join(rf"${head_macro}.{f.name}$" for f in p.fields)
            lines.append(rf"  \item Sets: {sets_str}.")
        for sig in p.methods:
            lines.append(rf"  \item {self._signature_inline(sig, head_macro)}")
        lines.append(r"\end{itemize}")
        return "\n".join(lines)

    def _render_param_name(self, name: str) -> str:
        if _looks_like_algorithm_name(name):
            return self.macros.register_algorithm(name)
        return self.expr.render(frog_ast.Variable(name))

    def _param(self, par: frog_ast.Parameter) -> str:
        return rf"{par.name} : {self.types.render(par.type)}"

    def _signature_inline(self, sig: frog_ast.MethodSignature, owner_macro: str) -> str:
        method_macro = self.macros.register_algorithm(sig.name)
        args = ", ".join(self._param(p) for p in sig.parameters)
        ret = self.types.render(sig.return_type)
        modifiers = []
        if sig.deterministic:
            modifiers.append("deterministic")
        if sig.injective:
            modifiers.append("injective")
        prefix = ""
        if modifiers:
            prefix = rf"\textit{{{', '.join(modifiers)}}}\ "
        return rf"{prefix}${method_macro}({args}) \to {ret}$ \quad (in ${owner_macro}$)"

    # ---- Scheme ------------------------------------------------------------

    def render_scheme(self, s: frog_ast.Scheme) -> str:
        head_macro = self.macros.register_algorithm(s.name)
        blocks = [self._method_block(method, head_macro) for method in s.methods]
        vstack = ir.VStack(blocks=blocks, boxed=True)
        header = rf"\noindent\textbf{{Scheme {head_macro}}}\par\medskip"
        return header + "\n" + self.backend.render_vstack(vstack)

    def _method_block(
        self,
        method: frog_ast.Method,
        owner_macro: str,
        qualify: bool = True,
    ) -> ir.ProcedureBlock:
        sig = method.signature
        method_macro = self.macros.register_algorithm(sig.name)
        args = ", ".join(
            self.expr.render(frog_ast.Variable(p.name)) for p in sig.parameters
        )
        title = (
            rf"{owner_macro}.{method_macro}({args})"
            if qualify
            else rf"{method_macro}({args})"
        )
        body = self.stmts.render_block(method.block)
        return ir.ProcedureBlock(title=title, lines=body)

    # ---- Game --------------------------------------------------------------

    def render_game(self, g: frog_ast.Game, experiment_name: str | None = None) -> str:
        side_macro = self.macros.register_algorithm(g.name)
        blocks: list[ir.ProcedureBlock] = []
        if g.methods:
            for m in g.methods:
                blocks.append(self._method_block(m, side_macro, qualify=False))
        vstack = ir.VStack(blocks=blocks, boxed=True)
        params = ", ".join(self._render_param_name(p.name) for p in g.parameters)
        if experiment_name:
            exp_macro = self.macros.register_security_notion(experiment_name)
            title = rf"\Experiment{{{exp_macro}}}{{{side_macro}}}{{{params}}}"
        else:
            title = rf"{side_macro}({params})" if params else side_macro
        header = rf"\noindent\textbf{{Game}} ${title}$\par\medskip"
        return header + "\n" + self.backend.render_vstack(vstack)
