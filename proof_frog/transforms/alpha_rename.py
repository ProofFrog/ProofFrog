"""Global pre-pipeline alpha-renaming of local binders.

FrogLang uses *position-sensitive* block scoping: a name used before its local
declaration binds to the enclosing (field / outer-local / parameter) scope, and
only from the declaration point onward does it bind to the local.  For example,
in ::

    Int out = x;   // reads the FIELD x (the local x is not declared yet)
    Int x = 0;     // declares the local x
    return out + x;// reads the LOCAL x

the first ``x`` is the field and the second is the local.  This mirrors the
typechecker's scope stack (``semantic_analysis.py`` ``visit_block`` /
``leave_assignment``), which adds a typed binder to the current scope *after*
visiting its right-hand side.

Several high-footfall passes rewrite code by splicing or normalising block-local
declarations (``BranchElimination``'s ``if(true){...}`` splice,
``SimplifyIf``'s branch normalisation).  When a body-local shadows an outer
local or a game field, a name-blind rewrite conflates the two bindings and can
certify a hop a distinguisher refutes (audit findings F-124, F-129).

This pass removes the collision at the root: it gives every *typed* local binder
a fresh, globally-unique name (``__aN__``), rewriting exactly the references that
resolve to it under position-sensitive scope.  No later splice or normalisation
then has a same-name collision to mishandle.  Because the renamed binders are
all typed, the post-pipeline ``VariableStandardize`` pass re-washes them to the
canonical ``vN`` names, so a sound proof's final canonical form is unchanged.

Scope discipline:

* Only *local* binders are renamed -- typed ``Assignment`` / ``Sample`` /
  ``UniqueSample`` and ``VariableDeclaration``.  Game fields, method parameters,
  game parameters, and proof-let / scheme / primitive names are left untouched
  (a reference that does not resolve to a renamed local is emitted verbatim).
* Names already beginning with ``__`` are skipped, so the pass is idempotent on
  its own output and does not disturb other passes' reserved-prefix temporaries
  (this is what lets it sit inside the fixed-point loop without diverging).
* Loop binders (``for (Int i ...)``) are not renamed; they are masked in the
  loop-body scope so a same-named outer local cannot leak in.
"""

from __future__ import annotations

import re

from .. import frog_ast
from ..visitors import Transformer
from ._base import TransformPass, PipelineContext

# Reserved prefix for engine-internal names.  We never rename a binder whose
# name already begins with ``__`` (idempotency + don't clobber other passes).
_RESERVED_PREFIX = "__"
_FRESH = "__a{0}__"
_FRESH_RE = re.compile(r"__a(\d+)__")


class _RefRewriter(Transformer):
    """Rename every ``Variable`` reference whose name is in *mapping*.

    Used on a single statement's reference positions (right-hand sides,
    conditions, loop bounds, lvalue index expressions) with the scope map that
    is active at that statement.  ``FieldAccess`` selectors are plain strings,
    not ``Variable`` nodes, so they are never touched.
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.Variable:
        new_name = self.mapping.get(variable.name)
        if new_name is None or new_name == variable.name:
            return variable
        return frog_ast.Variable(new_name)


class _AlphaRenamer:
    """Renames local binders to fresh ``__aN__`` names within one game."""

    def __init__(self) -> None:
        self._counter = 0

    def _fresh(self) -> str:
        name = _FRESH.format(self._counter)
        self._counter += 1
        return name

    def rename_game(self, game: frog_ast.Game) -> frog_ast.Game:
        # Start the counter above any ``__aN__`` already present, so a binder
        # introduced by an earlier fixed-point iteration (or by a downstream
        # pass that inlines user-named locals) never gets a fresh name that
        # collides with one already minted.  Without this, the loop never
        # converges: each iteration re-mints ``__a0__`` for a different binder.
        existing = [int(m) for m in _FRESH_RE.findall(str(game))]
        self._counter = (max(existing) + 1) if existing else 0
        new_methods = [
            frog_ast.Method(method.signature, self._rename_block(method.block, []))
            for method in game.methods
        ]
        new_game = frog_ast.Game((game.name, game.parameters, game.fields, new_methods))
        return new_game

    def _rename_block(
        self,
        block: frog_ast.Block,
        enclosing: list[dict[str, str]],
        initial: dict[str, str] | None = None,
    ) -> frog_ast.Block:
        """Rename one block.

        *enclosing* is the list of scope maps from enclosing blocks (innermost
        last).  *initial* seeds this block's own scope (used to mask a loop
        binder or method parameter inside the body).
        """
        local: dict[str, str] = dict(initial) if initial else {}
        scopes = enclosing + [local]
        new_statements: list[frog_ast.Statement] = []
        for statement in block.statements:
            new_statements.append(self._rename_statement(statement, scopes, local))
        return frog_ast.Block(new_statements)

    def _active(self, scopes: list[dict[str, str]]) -> dict[str, str]:
        """Flatten the scope stack (innermost wins)."""
        merged: dict[str, str] = {}
        for scope in scopes:
            merged.update(scope)
        return merged

    def _rewrite(
        self, node: frog_ast.Expression, scopes: list[dict[str, str]]
    ) -> frog_ast.Expression:
        return _RefRewriter(self._active(scopes)).transform(node)

    def _maybe_bind(self, name: str, local: dict[str, str]) -> str | None:
        """Allocate a fresh name for binder *name* and record it, or skip.

        Returns the fresh name, or ``None`` if *name* should not be renamed
        (already reserved-prefixed).
        """
        if name.startswith(_RESERVED_PREFIX):
            # Leave engine-internal names alone; still record an identity
            # binding so a later same-name reference resolves to it (not to an
            # outer local with the same reserved name, which cannot happen, but
            # keeps the scope model exact).
            local[name] = name
            return None
        fresh = self._fresh()
        local[name] = fresh
        return fresh

    def _rename_statement(  # pylint: disable=too-many-return-statements
        self,
        statement: frog_ast.Statement,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Statement:
        if isinstance(statement, frog_ast.Assignment):
            return self._rename_assignment(statement, scopes, local)
        if isinstance(statement, frog_ast.Sample):
            return self._rename_sample(statement, scopes, local)
        if isinstance(statement, frog_ast.UniqueSample):
            return self._rename_unique_sample(statement, scopes, local)
        if isinstance(statement, frog_ast.VariableDeclaration):
            fresh = self._maybe_bind(statement.name, local)
            if fresh is None:
                return statement
            return frog_ast.VariableDeclaration(statement.type, fresh)
        if isinstance(statement, frog_ast.ReturnStatement):
            return frog_ast.ReturnStatement(self._rewrite(statement.expression, scopes))
        if isinstance(statement, frog_ast.IfStatement):
            return self._rename_if(statement, scopes)
        if isinstance(statement, frog_ast.NumericFor):
            return self._rename_numeric_for(statement, scopes)
        if isinstance(statement, frog_ast.GenericFor):
            return self._rename_generic_for(statement, scopes)
        # Any other statement (e.g. a bare FuncCall) only references names; it
        # never binds.  Rewrite its references with the active scope.
        return _RefRewriter(self._active(scopes)).transform(statement)

    def _rename_assignment(
        self,
        statement: frog_ast.Assignment,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Assignment:
        new_value = self._rewrite(statement.value, scopes)
        if statement.the_type is not None and isinstance(
            statement.var, frog_ast.Variable
        ):
            fresh = self._maybe_bind(statement.var.name, local)
            new_var: frog_ast.Expression = (
                frog_ast.Variable(fresh) if fresh is not None else statement.var
            )
        else:
            # Untyped reassignment or non-Variable lvalue (e.g. M[i], obj.f):
            # not a binder.  Rewrite the lvalue's references with the scope as
            # it stands (the target name, if a renamed local, must follow).
            new_var = self._rewrite(statement.var, scopes)
        return frog_ast.Assignment(statement.the_type, new_var, new_value)

    def _rename_sample(
        self,
        statement: frog_ast.Sample,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Sample:
        new_from = self._rewrite(statement.sampled_from, scopes)
        if statement.the_type is not None and isinstance(
            statement.var, frog_ast.Variable
        ):
            fresh = self._maybe_bind(statement.var.name, local)
            new_var: frog_ast.Expression = (
                frog_ast.Variable(fresh) if fresh is not None else statement.var
            )
        else:
            new_var = self._rewrite(statement.var, scopes)
        return frog_ast.Sample(statement.the_type, new_var, new_from)

    def _rename_unique_sample(
        self,
        statement: frog_ast.UniqueSample,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.UniqueSample:
        new_set = self._rewrite(statement.unique_set, scopes)
        if statement.the_type is not None and isinstance(
            statement.var, frog_ast.Variable
        ):
            fresh = self._maybe_bind(statement.var.name, local)
            new_var: frog_ast.Expression = (
                frog_ast.Variable(fresh) if fresh is not None else statement.var
            )
        else:
            new_var = self._rewrite(statement.var, scopes)
        return frog_ast.UniqueSample(
            statement.the_type,
            new_var,
            new_set,
            statement.sampled_from,
            statement.surface_form,
        )

    def _rename_if(
        self, statement: frog_ast.IfStatement, scopes: list[dict[str, str]]
    ) -> frog_ast.IfStatement:
        new_conditions = [self._rewrite(c, scopes) for c in statement.conditions]
        new_blocks = [self._rename_block(b, scopes) for b in statement.blocks]
        return frog_ast.IfStatement(new_conditions, new_blocks)

    def _rename_numeric_for(
        self, statement: frog_ast.NumericFor, scopes: list[dict[str, str]]
    ) -> frog_ast.NumericFor:
        new_start = self._rewrite(statement.start, scopes)
        new_end = self._rewrite(statement.end, scopes)
        # The loop binder is not renamed, but it must mask a same-named outer
        # local inside the body.
        body = self._rename_block(
            statement.block, scopes, initial={statement.name: statement.name}
        )
        return frog_ast.NumericFor(statement.name, new_start, new_end, body)

    def _rename_generic_for(
        self, statement: frog_ast.GenericFor, scopes: list[dict[str, str]]
    ) -> frog_ast.GenericFor:
        new_over = self._rewrite(statement.over, scopes)
        body = self._rename_block(
            statement.block, scopes, initial={statement.var_name: statement.var_name}
        )
        return frog_ast.GenericFor(
            statement.var_type, statement.var_name, new_over, body
        )


class AlphaRename(TransformPass):
    name = "Alpha Rename"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _AlphaRenamer().rename_game(game)
