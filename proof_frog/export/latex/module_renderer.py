"""Render top-level FrogLang modules (Primitive, Scheme, Game) to LaTeX."""

from __future__ import annotations

from collections.abc import Sequence

from ... import frog_ast
from ...visitors import GetTypeMapVisitor, NameTypeMap
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
        # Optional proof-level let types, merged into every method's scope map
        # so operands referencing let-bound variables (e.g. a BitString let)
        # disambiguate `+`/`||`. Set by the proof renderer; None for standalone
        # module export.
        self.base_name_types: NameTypeMap | None = None

    @staticmethod
    def _scope_name_types(
        method: frog_ast.Method,
        fields: list[frog_ast.Field],
        base: NameTypeMap | None,
    ) -> NameTypeMap:
        """Build the name->Type map visible inside a method body.

        Layered so the innermost scope wins: proof lets (base), then module
        fields, then the method's own parameters and local declarations.
        """
        # A dummy stopping point that won't match any real node.
        method_map = GetTypeMapVisitor(frog_ast.Boolean(True)).visit(method)
        field_map = NameTypeMap()
        for field in fields:
            field_map.set(field.name, field.type)
        result = field_map + method_map
        if base is not None:
            result = base + result
        return result

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
        blocks = [
            self._method_block(method, head_macro, fields=s.fields)
            for method in s.methods
        ]
        vstack = ir.VStack(blocks=blocks, boxed=True)
        header = rf"\noindent\textbf{{Scheme {head_macro}}}\par\medskip"
        return header + "\n" + self.backend.render_vstack(vstack)

    def _method_block(
        self,
        method: frog_ast.Method,
        owner_macro: str,
        qualify: bool = True,
        fields: list[frog_ast.Field] | None = None,
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
        # Make this method's scope types visible to the expression renderer so
        # `+`/`||` disambiguate. Restored afterwards so nested/sibling renders
        # see their own scope.
        saved = self.expr.name_types
        self.expr.name_types = self._scope_name_types(
            method, fields or [], self.base_name_types
        )
        try:
            body = self.stmts.render_block(method.block)
        finally:
            self.expr.name_types = saved
        return ir.ProcedureBlock(title=title, lines=body)

    # ---- Game --------------------------------------------------------------

    def _method_blocks_vstack(self, g: frog_ast.Game) -> ir.VStack:
        """Return a boxed VStack of all method blocks for a game.

        Used both by ``render_game`` (which adds a heading) and by the proof
        renderer's figure builder (which needs the block stack without the
        heading).
        """
        side_macro = self.macros.register_algorithm(g.name)
        blocks = [
            self._method_block(m, side_macro, qualify=False, fields=g.fields)
            for m in g.methods
        ]
        return ir.VStack(blocks=blocks, boxed=True)

    def _game_title(self, g: frog_ast.Game, experiment_name: str | None) -> str:
        """The math-mode title (without ``$`` delimiters) for a game."""
        side_macro = self.macros.register_algorithm(g.name)
        params = ", ".join(self._render_param_name(p.name) for p in g.parameters)
        if experiment_name:
            exp_macro = self.macros.register_security_notion(experiment_name)
            return rf"\Experiment{{{exp_macro}}}{{{side_macro}}}{{{params}}}"
        return rf"{side_macro}({params})" if params else side_macro

    def render_game(self, g: frog_ast.Game, experiment_name: str | None = None) -> str:
        vstack = self._method_blocks_vstack(g)
        title = self._game_title(g, experiment_name)
        header = rf"\noindent\textbf{{Game}} ${title}$\par\medskip"
        return header + "\n" + self.backend.render_vstack(vstack)

    def render_game_file_games(
        self, games: Sequence[frog_ast.Game], experiment_name: str | None = None
    ) -> str:
        """Render a game file's games, side by side when there are exactly two.

        A two-game file is the Left/Right (or Real/Ideal) pair of a security
        definition; papers show these side by side. Other counts fall back to
        the vertically stacked per-game rendering.
        """
        if len(games) == 2:
            return self._render_games_side_by_side(games, experiment_name)
        return "\n\n".join(self.render_game(g, experiment_name) for g in games)

    def _render_games_side_by_side(
        self, games: Sequence[frog_ast.Game], experiment_name: str | None
    ) -> str:
        stacks = []
        for g in games:
            vstack = self._method_blocks_vstack(g)
            vstack.heading = f"${self._game_title(g, experiment_name)}$"
            stacks.append(vstack)
        header = r"\noindent\textbf{Game}\par\medskip"
        return header + "\n" + self.backend.render_hstack(ir.HStack(stacks=stacks))
