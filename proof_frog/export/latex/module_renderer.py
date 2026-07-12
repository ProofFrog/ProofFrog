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
        lines: list[str] = []
        lines.append(rf"\noindent\textbf{{Primitive {head_macro}}}")
        lines.append(r"\begin{itemize}")
        if p.parameters:
            params = ", ".join(self._param(par) for par in p.parameters)
            lines.append(rf"  \item Parameters: ${params}$.")
        # Only genuinely set-valued fields belong under "Sets:"; the integer
        # length fields (re-exposed parameters) already appear under Parameters.
        # Set names go through the algorithm macro so they read upright
        # (\mathsf), matching how they render in the method signatures below.
        set_fields = [f for f in p.fields if isinstance(f.type, frog_ast.SetType)]
        if set_fields:
            sets_str = ", ".join(
                rf"${head_macro}.{self.macros.register_algorithm(f.name)}$"
                for f in set_fields
            )
            lines.append(rf"  \item Sets: {sets_str}.")
        for sig in p.methods:
            lines.append(rf"  \item {self._signature_inline(sig)}")
        lines.append(r"\end{itemize}")
        return "\n".join(lines)

    def _render_typed_name(self, name: str, typ: frog_ast.Type) -> str:
        """Render a parameter name consistently with how it is used elsewhere.

        A numeric (length/index) parameter is a math variable, matching its use
        inside sizes (``Nss1`` -> ``Nss_{1}`` both here and in
        ``BitString<Nss1>``). A structural parameter (a set/group/scheme) keeps
        the upright algorithm macro its capitalized name gets in every other
        position.
        """
        numeric = isinstance(typ, (frog_ast.IntType, frog_ast.ModIntType))
        if not numeric and _looks_like_algorithm_name(name):
            return self.macros.register_algorithm(name)
        return self.expr.render(frog_ast.Variable(name))

    def _param(self, par: frog_ast.Parameter) -> str:
        name = self._render_typed_name(par.name, par.type)
        return rf"{name} \in {self.types.render(par.type)}"

    def _signature_inline(self, sig: frog_ast.MethodSignature) -> str:
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
        return rf"{prefix}${method_macro}({args}) \to {ret}$"

    # ---- Scheme ------------------------------------------------------------

    def render_scheme(self, s: frog_ast.Scheme) -> str:
        head_macro = self.macros.register_algorithm(s.name)
        blocks = [
            self._method_block(method, head_macro, fields=s.fields)
            for method in s.methods
        ]
        vstack = ir.VStack(blocks=blocks, boxed=True)
        header = rf"\noindent\textbf{{Scheme {head_macro}}}\par\medskip"
        return (
            header + "\n" + self.backend.fit_width(self.backend.render_vstack(vstack))
        )

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
        saved_ret = self.stmts.return_type
        self.expr.name_types = self._scope_name_types(
            method, fields or [], self.base_name_types
        )
        self.stmts.return_type = sig.return_type
        try:
            body = self.stmts.render_block(method.block)
        finally:
            self.expr.name_types = saved
            self.stmts.return_type = saved_ret
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

    def _notion_title(self, g: frog_ast.Game, experiment_name: str | None) -> str:
        """The math-mode block title ``Notion(params)`` (without ``$``).

        The security notion names the whole definition (e.g. ``\\mathsf{GapCDH}(G)``);
        the individual sides are labeled by the column captions below it. When no
        experiment name is given (a bare game), the game's own name is the title.
        """
        params = ", ".join(
            self._render_typed_name(p.name, p.type) for p in g.parameters
        )
        if experiment_name:
            head = self.macros.register_security_notion(experiment_name)
        else:
            head = self.macros.register_algorithm(g.name)
        return rf"{head}({params})" if params else head

    def _side_caption(self, g: frog_ast.Game) -> str:
        """The math-mode column caption for one side of a notion (its name)."""
        return self.macros.register_algorithm(g.name)

    def render_game(self, g: frog_ast.Game, experiment_name: str | None = None) -> str:
        vstack = self._method_blocks_vstack(g)
        if experiment_name:
            vstack.heading = f"${self._side_caption(g)}$"
        title = self._notion_title(g, experiment_name)
        header = rf"\noindent\textbf{{Game}} ${title}$\par\medskip"
        return (
            header + "\n" + self.backend.fit_width(self.backend.render_vstack(vstack))
        )

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
            vstack.heading = f"${self._side_caption(g)}$"
            stacks.append(vstack)
        # One block title naming the notion, with the two sides captioned below.
        title = self._notion_title(games[0], experiment_name)
        header = rf"\noindent\textbf{{Game}} ${title}$\par\medskip"
        hstack = self.backend.render_hstack(ir.HStack(stacks=stacks))
        return header + "\n" + self.backend.fit_width(hstack)
