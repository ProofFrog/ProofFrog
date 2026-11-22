"""Standardization passes: variable/field name standardization, field ordering.

These passes run once after the core fixed-point loop to assign canonical
names to variables and fields, ensuring two semantically equivalent games
produce identical ASTs.
"""

# pylint: disable=duplicate-code
# ``_ParameterStandardizer`` deliberately mirrors ``alpha_rename._AlphaRenamer``'s
# position-sensitive scope walk (``_active`` / ``_rewrite`` / ``_rename_block``);
# the two normalize different binder classes (parameters vs local binders) and the
# shared shape is the point, not accidental duplication.

from __future__ import annotations

import copy
import heapq
from typing import cast

from .. import frog_ast
from .. import dependencies
from ..visitors import (
    BlockTransformer,
    SearchVisitor,
    Transformer,
    lvalue_base_name,
    reassigns_or_rebinds,
    referenced_variable_names,
    referenced_variables_in_order,
    rename_value_references,
    type_position_names,
    walk_children,
)
from ._base import NearMiss, TransformPass, PipelineContext
from ._ordering import node_sort_key
from .alpha_rename import _RefRewriter, block_binder_names

# ---------------------------------------------------------------------------
# Transformer class (moved from visitors.py)
# ---------------------------------------------------------------------------


class VariableStandardizingTransformer(Transformer):
    """Give each method's local binders canonical ``vN`` names in binder order.

    Numbering follows the order of the binders themselves (typed assignments
    and samples, bare declarations, loop binders) in a pre-order walk of the
    method body, not the order in which the locals are first used.

    The scope walk renames references only while their binder is active. Bare
    declarations and loop binders count as locals. Untyped writes only follow
    an explicit binder already in scope.

    A minted name must not be one the method already uses for something else,
    so every name the walk does not resolve to a local binder is reserved:
    fields, game and method parameters, type names, every name the signature
    mentions, and every name that is free at some point of the body. The free
    names are found by the rename walk itself, run once in collecting mode
    (``_free_names``), so the two cannot disagree about what a binder covers.
    """

    def __init__(self) -> None:
        self._field_names: set[str] = set()
        self._game_type_names: set[str] = set()
        self._reserved: set[str] = set()
        self._counter = 0
        # Set while the walk runs in collecting mode: the names seen so far
        # that no active binder resolves. ``None`` while renaming.
        self._free: set[str] | None = None

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self._field_names = {field.name for field in game.fields} | {
            param.name for param in game.parameters
        }
        self._game_type_names = type_position_names([*game.parameters, *game.fields])
        methods = [self.transform_method(method) for method in game.methods]
        return frog_ast.Game((game.name, game.parameters, game.fields, methods))

    @staticmethod
    def _type_names(node: object, in_type: bool = False) -> set[str]:
        if isinstance(node, frog_ast.Variable):
            return {node.name} if in_type else set()
        if isinstance(node, list):
            names: set[str] = set()
            for item in node:
                names.update(
                    VariableStandardizingTransformer._type_names(item, in_type)
                )
            return names
        if isinstance(node, frog_ast.ASTNode):
            names = set()
            for _, child, child_in_type in walk_children(node, in_type, escape=True):
                names.update(
                    VariableStandardizingTransformer._type_names(child, child_in_type)
                )
            return names
        return set()

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        parameters = {param.name for param in method.signature.parameters}
        self._reserved = (
            self._field_names
            | parameters
            | self._game_type_names
            | self._type_names(method)
            | self._free_names(method, parameters)
        )
        self._counter = 0
        block = self._rename_block(method.block, [])
        return frog_ast.Method(method.signature, block)

    def _free_names(self, method: frog_ast.Method, parameters: set[str]) -> set[str]:
        """Every name in *method* that no local binder resolves where it occurs.

        This is the rename walk run in collecting mode: binders keep their
        names, and ``_rewrite`` records each name it meets that no active
        binder resolves instead of renaming the ones that one does. A
        binder covers references from its own statement onward, and a nested
        block binds nothing for its parent, so a name bound in one branch and
        read elsewhere is free there; a whole-method ``references - binders``
        set misses it.

        The signature is outside every local binder, so each name it mentions
        is free, including one that occurs only as a length argument
        (``BitString<n> O(BitString<n> m)``), which ``_type_names`` skips.
        """
        self._free = referenced_variable_names(method.signature)
        try:
            self._rename_block(
                method.block, [], {parameter: parameter for parameter in parameters}
            )
            return self._free
        finally:
            self._free = None

    def _fresh(self) -> str:
        self._counter += 1
        while f"v{self._counter}" in self._reserved:
            self._counter += 1
        return f"v{self._counter}"

    def _bind(self, name: str, local: dict[str, str]) -> str:
        """Open the binder *name* in *local* and return the name it gets: a
        fresh ``vN``, or itself while collecting free names."""
        new_name = name if self._free is not None else self._fresh()
        local[name] = new_name
        return new_name

    @staticmethod
    def _active(scopes: list[dict[str, str]]) -> dict[str, str]:
        active: dict[str, str] = {}
        for scope in scopes:
            active.update(scope)
        return active

    def _rewrite(
        self,
        node: frog_ast.ASTNode,
        scopes: list[dict[str, str]],
        in_type: bool = False,
    ) -> frog_ast.ASTNode:
        active = self._active(scopes)
        if self._free is not None:
            # Collecting: every name here that no active binder resolves is
            # free, whatever position it occurs in.
            self._free.update(referenced_variable_names(node) - active.keys())
            return node
        return cast(
            frog_ast.ASTNode,
            rename_value_references(node, active, in_type),
        )

    def _rename_block(
        self,
        block: frog_ast.Block,
        enclosing: list[dict[str, str]],
        initial: dict[str, str] | None = None,
    ) -> frog_ast.Block:
        local = dict(initial) if initial else {}
        scopes = enclosing + [local]
        return frog_ast.Block(
            [self._rename_statement(stmt, scopes, local) for stmt in block.statements]
        )

    def _rename_statement(
        self,
        stmt: frog_ast.Statement,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Statement:
        if isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return self._rename_assignment(stmt, scopes, local)
        if isinstance(stmt, frog_ast.VariableDeclaration):
            the_type = self._rewrite(stmt.type, scopes, True)
            name = self._bind(stmt.name, local)
            return frog_ast.VariableDeclaration(cast(frog_ast.Type, the_type), name)
        if isinstance(stmt, frog_ast.IfStatement):
            conditions = [
                cast(frog_ast.Expression, self._rewrite(c, scopes))
                for c in stmt.conditions
            ]
            blocks = [self._rename_block(b, scopes) for b in stmt.blocks]
            return frog_ast.IfStatement(conditions, blocks)
        if isinstance(stmt, frog_ast.NumericFor):
            start = cast(frog_ast.Expression, self._rewrite(stmt.start, scopes))
            end = cast(frog_ast.Expression, self._rewrite(stmt.end, scopes))
            loop_scope: dict[str, str] = {}
            name = self._bind(stmt.name, loop_scope)
            body = self._rename_block(stmt.block, scopes, loop_scope)
            return frog_ast.NumericFor(name, start, end, body)
        if isinstance(stmt, frog_ast.GenericFor):
            over = cast(frog_ast.Expression, self._rewrite(stmt.over, scopes))
            var_type = cast(frog_ast.Type, self._rewrite(stmt.var_type, scopes, True))
            loop_scope = {}
            name = self._bind(stmt.var_name, loop_scope)
            body = self._rename_block(stmt.block, scopes, loop_scope)
            return frog_ast.GenericFor(var_type, name, over, body)
        if isinstance(stmt, frog_ast.Block):
            return self._rename_block(stmt, scopes)
        return cast(frog_ast.Statement, self._rewrite(stmt, scopes))

    def _sampling_domain(
        self,
        stmt: frog_ast.Sample | frog_ast.UniqueSample,
        scopes: list[dict[str, str]],
    ) -> frog_ast.ASTNode:
        """The ``sampled_from`` of a draw, with every name an active local
        binder resolves renamed, bare names included.

        ``visitors.TYPE_SLOTS`` lists ``sampled_from`` as a type, and in a
        meaningful draw it is one: it names no local except in a length
        argument (``BitString<n>``), which is renamed in type context too. It
        is rewritten in expression context here because a bare name there can
        still resolve to a local. The typechecker only asks that the
        right-hand side of ``<-`` be a ``Type``, and ``Variable`` is one, so
        ``T x <- s;`` with ``s`` a local value reaches the engine. Under
        position-sensitive scoping that ``s`` is the local, and AlphaRename's
        name-keyed rewrite renames it with its binder. Left alone here, the
        binder would become ``vN`` while this reference kept its ``__aN__``
        name and referred to nothing. A name with no active local binder (a
        ``Set`` let, a type alias) is not in the scope map and is left as is.
        """
        return self._rewrite(stmt.sampled_from, scopes)

    def _rename_assignment(
        self,
        stmt: frog_ast.Assignment | frog_ast.Sample | frog_ast.UniqueSample,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Statement:
        new_stmt: frog_ast.Assignment | frog_ast.Sample | frog_ast.UniqueSample
        new_type = (
            cast(frog_ast.Type, self._rewrite(stmt.the_type, scopes, True))
            if stmt.the_type is not None
            else None
        )
        if isinstance(stmt, frog_ast.Assignment):
            new_stmt = frog_ast.Assignment(
                new_type,
                stmt.var,
                cast(frog_ast.Expression, self._rewrite(stmt.value, scopes)),
            )
        elif isinstance(stmt, frog_ast.Sample):
            new_stmt = frog_ast.Sample(
                new_type,
                stmt.var,
                cast(frog_ast.Expression, self._sampling_domain(stmt, scopes)),
            )
        else:
            new_stmt = frog_ast.UniqueSample(
                new_type,
                stmt.var,
                cast(frog_ast.Expression, self._rewrite(stmt.unique_set, scopes)),
                cast(frog_ast.Type, self._sampling_domain(stmt, scopes)),
                stmt.surface_form,
            )
        if stmt.the_type is not None and isinstance(stmt.var, frog_ast.Variable):
            new_stmt.var = frog_ast.Variable(self._bind(stmt.var.name, local))
        else:
            new_stmt.var = cast(frog_ast.Expression, self._rewrite(stmt.var, scopes))
        return new_stmt


class _ParameterStandardizer:
    """Rename each method's parameters to canonical ``arg1..argN``.

    Oracle/method parameter names are NOT adversary-observable: FrogLang calls
    are positional, so a parameter is a purely syntactic binder. ``AlphaRename``
    and ``VariableStandardizingTransformer`` normalize local binders and fields
    but deliberately leave parameters alone, so two games that are identical up
    to an oracle parameter name (``Decaps(c)`` vs ``Decaps(ct)``) canonicalize
    differently and a sound interchangeability hop between them is rejected.
    This pass closes that gap by giving every parameter a positional canonical
    name and rewriting its references in the body.

    Reference rewriting is position-sensitive, mirroring the scope model of
    ``AlphaRename``: a local declaration or loop binder that shadows a parameter
    name masks it from its binding point onward (its references then resolve to
    the shadowing binder, not the parameter, and are left untouched). Because
    normalization only removes a non-observable distinction, it can make two
    canonical forms match but never conflates genuinely different behaviour.

    With a pipeline context, a method whose rename is declined because a
    canonical name is taken records a near miss.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self._ctx = ctx

    def rename_game(self, game: frog_ast.Game) -> frog_ast.Game:
        field_names = {field.name for field in game.fields}
        new_methods = [self._rename_method(m, field_names) for m in game.methods]
        return frog_ast.Game((game.name, game.parameters, game.fields, new_methods))

    @staticmethod
    def _body_bound_names(block: frog_ast.Block) -> set[str]:
        """Names bound WITHIN a method body: ``for`` binders, typed local
        declarations and bare declarations (``T x;``, which mask a parameter
        just as a typed assignment does). Parameters are excluded -- they are
        what this pass renames.
        """
        names: set[str] = set()

        def _collect(node: frog_ast.ASTNode) -> bool:
            if isinstance(node, frog_ast.NumericFor):
                names.add(node.name)
            elif isinstance(node, frog_ast.GenericFor):
                names.add(node.var_name)
            elif isinstance(node, frog_ast.VariableDeclaration):
                names.add(node.name)
            elif (
                isinstance(
                    node,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and getattr(node, "the_type", None) is not None
                and isinstance(node.var, frog_ast.Variable)
            ):
                names.add(node.var.name)
            return False

        SearchVisitor(_collect).visit(block)
        return names

    def _rename_method(
        self, method: frog_ast.Method, field_names: set[str] | None = None
    ) -> frog_ast.Method:
        params = method.signature.parameters
        if not params:
            return method
        # F-306/F-307: the canonical target names arg1..argN must be FRESH w.r.t.
        # every name that could collide with a renamed parameter -- names bound
        # inside the body (loop binders, typed local declarations; AlphaRename
        # does not rename loop binders) AND the game's FIELDS. Renaming a
        # parameter to `arg1` when a body binder or a field is already named
        # `arg1` would capture/fuse the parameter with it (a body reference or a
        # field store silently rebinds). Standardization is only
        # canonicalization, so on a collision decline the rename for this method
        # -- never conflate.
        #
        # F-398: likewise every name the method reads that it does not bind,
        # such as a proof `let:` entry passed to the game: a parameter renamed
        # to it would capture the read. Every name the method mentions other
        # than its parameters is either a body binder, a field or such a name.
        targets = {f"arg{i + 1}" for i in range(len(params))}
        parameter_names = {param.name for param in params}
        bound_or_fields = self._body_bound_names(method.block) | (field_names or set())
        free = referenced_variable_names(method) - parameter_names - bound_or_fields
        if targets & (bound_or_fields | free):
            if self._ctx is not None:
                name = sorted(targets & (bound_or_fields | free))[0]
                what = (
                    "a field or a name the method binds"
                    if name in bound_or_fields
                    else "a name the method reads but does not bind (for "
                    "example a proof let: entry)"
                )
                self._ctx.near_misses.append(
                    NearMiss(
                        transform_name="Standardize Parameters",
                        reason=(
                            f"Parameter renaming declined in "
                            f"'{method.signature.name}': the canonical name "
                            f"'{name}' is {what}, so a parameter renamed to it "
                            "would capture or be captured by it"
                        ),
                        location=None,
                        suggestion=f"Rename '{name}' so it is not of the form arg<N>",
                        variable=name,
                        method=method.signature.name,
                    )
                )
            return method
        seed = {p.name: f"arg{i + 1}" for i, p in enumerate(params)}
        new_method = copy.deepcopy(method)
        new_method.block = self._rename_block(method.block, [seed])
        for i, param in enumerate(new_method.signature.parameters):
            param.name = f"arg{i + 1}"
        return new_method

    @staticmethod
    def _active(scopes: list[dict[str, str]]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for scope in scopes:
            merged.update(scope)
        return merged

    def _rewrite(
        self, node: frog_ast.Expression, scopes: list[dict[str, str]]
    ) -> frog_ast.Expression:
        return _RefRewriter(self._active(scopes)).transform(node)

    def _rename_block(
        self,
        block: frog_ast.Block,
        scopes: list[dict[str, str]],
        initial: dict[str, str] | None = None,
    ) -> frog_ast.Block:
        local: dict[str, str] = dict(initial) if initial else {}
        active = scopes + [local]
        new_statements = [
            self._rename_statement(s, active, local) for s in block.statements
        ]
        return frog_ast.Block(new_statements)

    def _rename_statement(
        self,
        statement: frog_ast.Statement,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Statement:
        if isinstance(
            statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return self._rename_binding(statement, scopes, local)
        if isinstance(statement, frog_ast.VariableDeclaration):
            # A bare typed declaration binds its name, masking a same-named param.
            local[statement.name] = statement.name
            return statement
        if isinstance(statement, frog_ast.ReturnStatement):
            return frog_ast.ReturnStatement(self._rewrite(statement.expression, scopes))
        if isinstance(statement, frog_ast.IfStatement):
            conditions = [self._rewrite(c, scopes) for c in statement.conditions]
            blocks = [self._rename_block(b, scopes) for b in statement.blocks]
            return frog_ast.IfStatement(conditions, blocks)
        if isinstance(statement, frog_ast.NumericFor):
            start = self._rewrite(statement.start, scopes)
            end = self._rewrite(statement.end, scopes)
            body = self._rename_block(
                statement.block, scopes, initial={statement.name: statement.name}
            )
            return frog_ast.NumericFor(statement.name, start, end, body)
        if isinstance(statement, frog_ast.GenericFor):
            over = self._rewrite(statement.over, scopes)
            body = self._rename_block(
                statement.block,
                scopes,
                initial={statement.var_name: statement.var_name},
            )
            return frog_ast.GenericFor(
                statement.var_type, statement.var_name, over, body
            )
        # Any other statement (e.g. a bare FuncCall) only references names.
        return _RefRewriter(self._active(scopes)).transform(statement)

    def _rename_binding(
        self,
        statement: frog_ast.Assignment | frog_ast.Sample | frog_ast.UniqueSample,
        scopes: list[dict[str, str]],
        local: dict[str, str],
    ) -> frog_ast.Statement:
        # Rewrite the right-hand side in the pre-binding scope (a self-reference
        # like `x = x` reads the outer/param `x`), then bind the target name.
        new_stmt = copy.copy(statement)
        if isinstance(new_stmt, frog_ast.Assignment):
            new_stmt.value = self._rewrite(new_stmt.value, scopes)
        elif isinstance(new_stmt, frog_ast.Sample):
            new_stmt.sampled_from = self._rewrite(new_stmt.sampled_from, scopes)
        else:  # UniqueSample
            new_stmt.unique_set = self._rewrite(new_stmt.unique_set, scopes)
        if new_stmt.the_type is not None and isinstance(
            new_stmt.var, frog_ast.Variable
        ):
            # Typed declaration: a new binder that masks a same-named param.
            local[new_stmt.var.name] = new_stmt.var.name
        else:
            # Untyped reassignment or non-Variable lvalue (`M[i]`, `obj.f`):
            # references in the target position resolve under the active scope.
            new_stmt.var = self._rewrite(new_stmt.var, scopes)
        return new_stmt


# ---------------------------------------------------------------------------
# Capture-aware field renaming (F-337 / issue #252)
# ---------------------------------------------------------------------------
#
# Field renaming used to run a name-keyed ``SubstitutionTransformer`` over the
# whole game.  Because ``frog_ast.Variable`` is declared
# ``class Variable(Expression, Type)`` (frog_ast.py L426), that substitution
# could not distinguish "the field named ``KA``" from "the TYPE named ``KA``"
# (a ``let:``-bound ``Set``), and rewrote both -- so a game whose field ``KA``
# was typed by a same-named set canonicalised to ``field1 field1``, losing the
# type, while a game whose field was named ``k`` kept it (``KA field1``).  That
# is a false REJECT on its own (issue #252), but it is also a false ACCEPT: it
# let a game sampling from set ``KA`` canonicalise to the same form as a game
# sampling from a *different* set the proof happened to name ``field1``.
#
# The rename now goes through ``visitors.rename_value_references``, which skips
# type positions, plus a decline guard on minting a name that is already an
# in-scope type name.
#
# Inside a method the rename also respects binders (F-326): a method parameter
# or a local binder named like a field hides the field, so a reference it
# resolves is not a field reference and keeps its name, and a renamed field
# reference that a binder of the target name would resolve declines the rename.


class _FieldRenameCapture(Exception):
    """A field reference cannot be renamed without changing what it reads.

    *method* is ``None`` when the clash is outside the methods (a game
    parameter, or a field's type or initializer). *free* marks a clash with a
    name the game reads but does not bind (F-398), as opposed to a binder of
    a method.
    """

    def __init__(
        self, method: str | None, name: str, reason: str, free: bool = False
    ) -> None:
        super().__init__(reason)
        self.method = method
        self.name = name
        self.reason = reason
        self.free = free


def _referenced_names(node: object) -> set[str]:
    """The names of every ``Variable`` in *node*, which may be an AST node,
    a list of them or a scalar."""
    if isinstance(node, list):
        names: set[str] = set()
        for item in node:
            names |= _referenced_names(item)
        return names
    if isinstance(node, frog_ast.ASTNode):
        return referenced_variable_names(node)
    return set()


def _free_target_capture(
    method: str | None, name: str, where: str
) -> _FieldRenameCapture:
    """The capture of a free name *name* by a field renamed to it (F-398)."""
    return _FieldRenameCapture(
        method,
        name,
        f"{where} reads '{name}', which is not one of the game's fields and "
        f"which nothing in the game binds there (for example a proof let: "
        f"entry); a field renamed to '{name}' would capture that read",
        free=True,
    )


class _RecordingRename(dict[str, str]):
    """A rename map that records the names it was asked to rename."""

    def __init__(self, mapping: dict[str, str]) -> None:
        super().__init__(mapping)
        self.used: set[str] = set()

    def __getitem__(self, key: str) -> str:
        self.used.add(key)
        return super().__getitem__(key)


class _ScopedFieldRenamer:
    """Rename field references in a method, respecting its binders.

    Under lexical scoping (ruling Q1) a method parameter covers the whole
    method, and a local binder (a typed assignment or draw, a bare
    declaration, a ``for`` binder) covers the rest of its block from its own
    statement on. A name such a binder covers is the binder, not the field,
    so it keeps its name. A field reference renamed to a name a binder covers
    at that point would be read as the binder: the renamer raises
    ``_FieldRenameCapture`` and the caller keeps the game as it is.

    A name in the signature that is both a parameter and a name of the
    rename (old or new) raises too, since a length in a parameter's type is
    not clearly inside or outside the parameters' scope.

    A target name read where no binder covers it and that is not a field
    (*field_names*) is free there, for example a proof ``let:`` entry the
    game reads. Once a field bears that name, the read would denote the
    field, so the renamer raises for it too (F-398), wherever the read is.
    """

    def __init__(self, rename: dict[str, str], field_names: set[str]) -> None:
        self.rename = rename
        self.targets = set(rename.values())
        self.field_names = field_names
        self._method = ""

    def method(self, method: frog_ast.Method) -> frog_ast.Method:
        self._method = method.signature.name
        parameters = {param.name for param in method.signature.parameters}
        ambiguous = (
            referenced_variable_names(method.signature)
            & parameters
            & (set(self.rename) | self.targets)
        )
        if ambiguous:
            name = sorted(ambiguous)[0]
            raise _FieldRenameCapture(
                self._method,
                name,
                f"the signature of '{self._method}' names '{name}', which is "
                "both one of its parameters and a field name the rename uses",
            )
        signature = cast(
            frog_ast.MethodSignature, self._rewrite(method.signature, parameters)
        )
        block = self._block(method.block, parameters)
        if signature is method.signature and block is method.block:
            return method
        new_method = copy.copy(method)
        new_method.signature = signature
        new_method.block = block
        return new_method

    def _rewrite(self, node: object, bound: set[str], in_type: bool = False) -> object:
        """Rename the field references in *node*, where the names in *bound*
        are binders in scope."""
        free_targets = (
            (_referenced_names(node) & self.targets) - bound - self.field_names
        )
        if free_targets:
            raise _free_target_capture(
                self._method, sorted(free_targets)[0], f"'{self._method}'"
            )
        rename = _RecordingRename(
            {old: new for old, new in self.rename.items() if old not in bound}
        )
        new_node = rename_value_references(node, rename, in_type)
        for old in sorted(rename.used):
            if rename[old] in bound:
                raise _FieldRenameCapture(
                    self._method,
                    rename[old],
                    f"renaming field '{old}' to '{rename[old]}' would make "
                    f"'{self._method}' read its own '{rename[old]}' (a parameter "
                    "or local of that name is in scope there) instead of the "
                    "field",
                )
        return new_node

    def _block(self, block: frog_ast.Block, enclosing: set[str]) -> frog_ast.Block:
        bound = set(enclosing)
        statements = [self._statement(stmt, bound) for stmt in block.statements]
        if all(new is old for new, old in zip(statements, block.statements)):
            return block
        new_block = copy.copy(block)
        new_block.statements = statements
        return new_block

    def _children(
        self,
        stmt: frog_ast.Statement,
        bound: set[str],
        keep: tuple[str, ...] = (),
    ) -> frog_ast.Statement:
        """*stmt* with every child but those in *keep* renamed under
        *bound*; a child that is a block opens a nested scope."""
        changed = False
        new_attrs: dict[str, object] = {}
        for attr, child, child_in_type in walk_children(stmt, False, escape=True):
            if attr in keep:
                continue
            if isinstance(child, frog_ast.Block):
                new_child: object = self._block(child, bound)
            elif isinstance(child, list) and any(
                isinstance(item, frog_ast.Block) for item in child
            ):
                new_items = [
                    (
                        self._block(item, bound)
                        if isinstance(item, frog_ast.Block)
                        else self._rewrite(item, bound, child_in_type)
                    )
                    for item in child
                ]
                new_child = (
                    child
                    if all(new is old for new, old in zip(new_items, child))
                    else new_items
                )
            else:
                new_child = self._rewrite(child, bound, child_in_type)
            new_attrs[attr] = new_child
            changed = changed or new_child is not child
        if not changed:
            return stmt
        new_stmt = copy.copy(stmt)
        for attr, new_child in new_attrs.items():
            setattr(new_stmt, attr, new_child)
        return new_stmt

    def _statement(
        self, stmt: frog_ast.Statement, bound: set[str]
    ) -> frog_ast.Statement:
        """Rename *stmt* under *bound*, then add the names it binds to
        *bound* (they cover the rest of the block)."""
        if isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            if stmt.the_type is not None and isinstance(stmt.var, frog_ast.Variable):
                new_stmt = self._children(stmt, bound, keep=("var",))
                bound.add(stmt.var.name)
                return new_stmt
            return self._children(stmt, bound)
        if isinstance(stmt, frog_ast.VariableDeclaration):
            new_stmt = self._children(stmt, bound)
            bound.add(stmt.name)
            return new_stmt
        if isinstance(stmt, frog_ast.DestructuringBinding):
            new_stmt = self._children(stmt, bound)
            bound.update(stmt.names)
            return new_stmt
        if isinstance(stmt, frog_ast.NumericFor):
            return self._loop(stmt, bound, stmt.name)
        if isinstance(stmt, frog_ast.GenericFor):
            return self._loop(stmt, bound, stmt.var_name)
        if isinstance(stmt, frog_ast.Block):
            return self._block(stmt, bound)
        return self._children(stmt, bound)

    def _loop(
        self,
        stmt: frog_ast.NumericFor | frog_ast.GenericFor,
        bound: set[str],
        binder: str,
    ) -> frog_ast.Statement:
        """A ``for`` loop: its header is outside its binder's scope, its
        body inside."""
        header = cast(
            frog_ast.NumericFor | frog_ast.GenericFor,
            self._children(stmt, bound, keep=("block",)),
        )
        block = self._block(stmt.block, bound | {binder})
        if header is stmt and block is stmt.block:
            return stmt
        new_stmt = copy.copy(header)
        new_stmt.block = block
        return new_stmt


def _check_targets_outside_methods(
    game: frog_ast.Game, rename: dict[str, str], field_names: set[str]
) -> None:
    """Raise ``_FieldRenameCapture`` when a target name of *rename* is taken
    outside the methods: a game parameter's name, the name of a field the
    rename keeps, or a name a game parameter's type or a field's type or
    initializer reads that is not a field (F-398)."""
    parameter_names = {parameter.name for parameter in game.parameters}
    declared = _referenced_names([*game.parameters, *game.fields])
    for name in sorted(set(rename.values())):
        if name in parameter_names:
            reason = (
                f"the game has a parameter '{name}'; a field renamed to "
                f"'{name}' would capture its reads"
            )
        elif name in field_names and name not in rename:
            reason = (
                f"the game keeps a field '{name}'; renaming another field to "
                f"'{name}' would fuse the two"
            )
        elif name in declared and name not in field_names:
            raise _free_target_capture(
                None, name, "a game parameter's or field's declaration"
            )
        else:
            continue
        raise _FieldRenameCapture(None, name, reason, free=True)


def _apply_field_rename(
    game: frog_ast.Game,
    rename: dict[str, str],
    ctx: PipelineContext | None = None,
    pass_name: str = "Standardize Field Names",
) -> frog_ast.Game:
    """Rename the game's fields by *rename* (old name to new name).

    The rename is simultaneous, so two fields may swap names
    (``field9 → field10`` and ``field10 → field9``).

    The rewrite is TYPE-POSITION AWARE (see ``visitors.TYPE_SLOTS``): only occurrences
    that can denote the field's *value* are renamed.  Additionally, if a target
    name would collide with a type/set name that is in scope in this game, the
    rename is DECLINED outright -- standardization is only canonicalization, so
    declining costs power but can never conflate two distinct games.

    In a method the rewrite is also SCOPE AWARE (``_ScopedFieldRenamer``): a
    reference that a method parameter or local binder of the same name
    covers is left alone, and if a renamed reference would be covered by a
    binder of its new name, the rename is declined with a near miss (F-326).

    A target name must also be FREE in the game (F-398): no game parameter,
    no field the rename keeps, and no name the game reads without binding it
    (a proof ``let:`` entry passed to the game, say), anywhere in the game.
    A field given such a name would capture it, so the rename is declined
    with a near miss.
    """
    if not rename:
        return game
    protected = type_position_names(game)
    if protected & set(rename.values()):
        # Minting `fieldN` here would fuse the field with a same-named type.
        return game
    field_names = {field.name for field in game.fields}
    renamer = _ScopedFieldRenamer(rename, field_names)
    try:
        _check_targets_outside_methods(game, rename, field_names)
        methods = [renamer.method(method) for method in game.methods]
    except _FieldRenameCapture as capture:
        if ctx is not None:
            if capture.free:
                suggestion = (
                    f"Rename '{capture.name}' (a proof let: entry, a game "
                    "parameter or a field the game keeps) so it is not of the "
                    "form field<N>"
                )
            else:
                suggestion = (
                    f"Rename the parameter or local '{capture.name}' in "
                    f"'{capture.method}' so it differs from the game's field "
                    "names and from field<N>"
                )
            ctx.near_misses.append(
                NearMiss(
                    transform_name=pass_name,
                    reason=f"Field renaming declined: {capture.reason}",
                    location=None,
                    suggestion=suggestion,
                    variable=capture.name,
                    method=capture.method,
                )
            )
        return game

    # Outside the methods nothing binds a name, so every other reference to
    # a field (in a field's type or initializer, a game parameter's type) is
    # renamed by name.
    new_game = copy.copy(game)
    for attr, child, child_in_type in walk_children(game, False, escape=True):
        if attr == "methods":
            new_game.methods = methods
        elif attr == "fields":
            new_fields = []
            for field in game.fields:
                new_field = copy.copy(rename_value_references(field, rename))
                new_field.name = rename.get(field.name, field.name)
                new_fields.append(new_field)
            new_game.fields = sorted(new_fields, key=lambda element: element.name)
        else:
            setattr(
                new_game, attr, rename_value_references(child, rename, child_in_type)
            )
    return new_game


def _field_order_rename_map(game: frog_ast.Game) -> dict[str, str]:
    """Canonical ``fieldN`` names in first-read order across oracle methods.

    Mirrors ``visitors.FieldOrderingVisitor`` but skips TYPE positions: a field
    named ``KA`` whose declared type is a same-named set must not be counted as
    "read" by its own type annotation (same ``Variable``-is-both-roles hazard as
    ``rename_value_references``, and it would otherwise perturb the numbering).
    """
    fields: list[str] = []
    rename_map: dict[str, str] = {}
    counter = 0
    in_initialize = False

    def walk(node: object, in_type: bool) -> None:
        nonlocal counter, in_initialize
        if isinstance(node, frog_ast.Variable):
            if (
                not in_type
                and node.name in fields
                and node.name not in rename_map
                and not in_initialize
            ):
                counter += 1
                rename_map[node.name] = f"field{counter}"
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item, in_type)
            return
        if not isinstance(node, frog_ast.ASTNode):
            return
        if isinstance(node, frog_ast.Field):
            fields.append(node.name)
        elif isinstance(node, frog_ast.MethodSignature):
            if node.name == "Initialize":
                in_initialize = True
        for _, child, child_in_type in walk_children(node, in_type, escape=True):
            walk(child, child_in_type)
        if isinstance(node, frog_ast.Method):
            in_initialize = False

    walk(game, False)
    # Fields used only in Initialize (or not at all) are numbered last, in
    # declaration order.
    for field_name in fields:
        if field_name not in rename_map:
            counter += 1
            rename_map[field_name] = f"field{counter}"
    return rename_map


def _phase3_lex_min_within_type(game: frog_ast.Game) -> frog_ast.Game:
    """Phase 3: within each contiguous same-type group of fields, swap
    field-number assignments so that the field with the lex-smaller
    ``Initialize``-body RHS gets the smaller field number.

    Stabilises canonical form across two semantically equivalent games
    that differ only in which interchangeable position holds which value
    (e.g. when KEM_PQ has two parallel keypairs whose ``[ek, dk]`` slots
    are bound in opposite orders by two reductions, leaving fields like
    ``field9 = v1[1]; field10 = v4[1]`` in one game and the swap in
    the other).
    """
    return _apply_field_rename(game, _phase3_rename_map(game))


def _phase3_rename_map(game: frog_ast.Game) -> dict[str, str]:
    """The field rename Phase 3 (:func:`_phase3_lex_min_within_type`) applies
    to *game*."""
    init_method: frog_ast.Method | None = None
    for m in game.methods:
        if m.signature.name == "Initialize":
            init_method = m
            break
    if init_method is None:
        return {}

    field_names = {f.name for f in game.fields}
    field_rhs_key: dict[str, tuple] = {}  # type: ignore[type-arg]
    for stmt in init_method.block.statements:
        if not isinstance(
            stmt,
            (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
        ):
            continue
        if not isinstance(stmt.var, frog_ast.Variable):
            continue
        if stmt.var.name not in field_names:
            continue
        if stmt.the_type is not None:
            # Typed local with the same name as a field — not a field assignment.
            continue
        if stmt.var.name in field_rhs_key:
            # Use the FIRST assignment to a field as its canonical RHS.
            continue
        if isinstance(stmt, frog_ast.Assignment):
            field_rhs_key[stmt.var.name] = ("a",) + node_sort_key(stmt.value)
        elif isinstance(stmt, frog_ast.Sample):
            field_rhs_key[stmt.var.name] = ("s",) + node_sort_key(stmt.sampled_from)
        else:  # UniqueSample
            field_rhs_key[stmt.var.name] = ("u",) + node_sort_key(stmt.sampled_from)

    # Group fields by type (the field list may be alphabetically sorted, so
    # same-type fields aren't necessarily contiguous in the list).  Within
    # each group we re-rank by Initialize-RHS sort key.
    def _field_num(name: str) -> int:
        try:
            return int(name[len("field") :])
        except (ValueError, TypeError):
            return -1

    groups: dict[str, list[str]] = {}
    for f in game.fields:
        groups.setdefault(str(f.type), []).append(f.name)

    rename: dict[str, str] = {}
    for names in groups.values():
        if len(names) <= 1:
            continue
        # Slots: sorted ascending by their numeric suffix.  These are the
        # available field-numbers for this type group.
        slots = sorted(names, key=_field_num)
        # Sort current names by their Initialize RHS, ties broken by
        # numeric suffix (so a stable result when RHS keys tie).
        sorted_names = sorted(
            names, key=lambda n: (field_rhs_key.get(n, ()), _field_num(n))
        )
        if sorted_names == slots:
            continue
        # The k-th sorted name should occupy slots[k].
        for k, sn in enumerate(sorted_names):
            if sn != slots[k]:
                rename[sn] = slots[k]

    return rename


def standardize_field_names(
    game: frog_ast.Game, ctx: PipelineContext | None = None
) -> frog_ast.Game:
    """Normalize field names to canonical ordering.

    Three-phase pass:

    1. Rename fields to ``fieldN`` based on first-read order in oracle
       methods (via :func:`_field_order_rename_map`).
    2. Regroup the resulting fields by type so that fields of the same
       type receive consecutive numbers regardless of how oracle
       predicates end up sorting them.  Preserves Phase-1 relative
       order within each type group.
    3. Within each contiguous same-type group, sort field-number
       assignments by the lex-min sort key of the field's ``Initialize``
       RHS, so two semantically equivalent games whose interchangeable
       positions are filled in opposite orders converge to the same
       field assignment.
    """
    field_rename_map = _field_order_rename_map(game)
    new_game = _apply_field_rename(game, field_rename_map, ctx)

    # Phase 2: group by type, preserving relative order within each group.
    # This re-numbers fields so that two semantically equivalent games whose
    # oracle predicates ordered conjuncts differently still end up assigning
    # the same field number to the same (type, within-type-rank) slot.
    def _field_num(name: str) -> int:
        try:
            return int(name[len("field") :])
        except (ValueError, TypeError):
            return -1

    # Sort keys: (type_key, original_field_number_within_phase_1)
    type_sorted = sorted(
        new_game.fields,
        key=lambda f: (str(f.type), _field_num(f.name)),
    )
    second_rename: dict[str, str] = {}
    for new_idx, field in enumerate(type_sorted):
        canonical = f"field{new_idx + 1}"
        if field.name != canonical:
            second_rename[field.name] = canonical
    new_game = _apply_field_rename(new_game, second_rename, ctx)

    # Phase 3 lex-min runs as a separate `FieldLexMinByRHS` pass after
    # the second `VariableStandardize`, where RHS sort keys see the
    # final local-variable names.

    return new_game


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class VariableStandardize(TransformPass):
    name = "Variable Standardization"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return VariableStandardizingTransformer().transform(game)


class StandardizeParameters(TransformPass):
    name = "Standardize Parameters"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _ParameterStandardizer(ctx).rename_game(game)


class StandardizeFieldNames(TransformPass):
    name = "Standardize Field Names"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return standardize_field_names(game, ctx)


class FieldLexMinByRHS(TransformPass):
    """Run only Phase-3 of field standardization (lex-min within type
    groups by Initialize RHS).  Used as a post-VariableStandardize pass
    so the RHS sort keys see the final local-variable names rather than
    the pre-rename ones.

    Iterates to a fixed point: a rename in one type group can change
    the sort key (via referenced field names) used by another group, so
    a single pass may not converge.
    """

    name = "Field Lex-Min By RHS"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for _ in range(8):  # bounded fixed-point; 8 iterations is ample
            new_game = _phase3_lex_min_within_type(game)
            if new_game is game:
                # A declined rename (F-326) also leaves the game as it is:
                # run it once more with ``ctx`` to record why.
                _apply_field_rename(game, _phase3_rename_map(game), ctx, self.name)
                return game
            # Compare via str() since AST objects may not implement __eq__.
            if str(new_game) == str(game):
                return new_game
            game = new_game
        return game


class BubbleSortFieldAssignments(TransformPass):
    name = "Bubble Sort Field Assignments"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return dependencies.BubbleSortFieldAssignment().transform(game)


def _abstract_names(
    key: tuple,  # type: ignore[type-arg]
    names: set[str],
    mapping: dict[str, str],
    fixed: dict[str, str],
) -> tuple:  # type: ignore[type-arg]
    """*key* (a :func:`node_sort_key` tuple) with each string in *names*
    replaced by ``@<k>``, numbering the names in order of appearance, and
    each string in *fixed* by its value."""
    abstracted: list[object] = []
    for item in key:
        if isinstance(item, tuple):
            abstracted.append(_abstract_names(item, names, mapping, fixed))
        elif isinstance(item, str) and item in names:
            if item not in mapping:
                mapping[item] = f"@{len(mapping)}"
            abstracted.append(mapping[item])
        elif isinstance(item, str) and item in fixed:
            abstracted.append(fixed[item])
        else:
            abstracted.append(item)
    return tuple(abstracted)


def _written_names(statement: frog_ast.Statement) -> set[str]:
    """The base names of every assignment and sample target in *statement*,
    at any depth (``M`` for ``M[k] = v``). A tuple target is left out: the
    result only orders statements, so a missing name costs canonicity, not
    soundness."""
    names: set[str] = set()

    def _collect(node: frog_ast.ASTNode) -> bool:
        if isinstance(
            node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            base = lvalue_base_name(node.var)
            if base is not None:
                names.add(base)
        return False

    SearchVisitor(_collect).visit(statement)
    return names


def _binder_counts(block: frog_ast.Block) -> dict[str, int]:
    """How many times each name is bound in *block*, at any depth: bare
    declarations, typed assignments and samples, and ``for`` binders."""
    counts: dict[str, int] = {}

    def _count(node: frog_ast.ASTNode) -> bool:
        name: str | None = None
        if isinstance(node, frog_ast.VariableDeclaration):
            name = node.name
        elif isinstance(node, frog_ast.NumericFor):
            name = node.name
        elif isinstance(node, frog_ast.GenericFor):
            name = node.var_name
        elif (
            isinstance(
                node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and node.the_type is not None
            and isinstance(node.var, frog_ast.Variable)
        ):
            name = node.var.name
        if name is not None:
            counts[name] = counts.get(name, 0) + 1
        return False

    SearchVisitor(_count).visit(block)
    return counts


class _StabilizeIndependentStatementsTransformer(BlockTransformer):
    """Sorts independent statements of a block into a canonical order.

    After variable standardization, two semantically equivalent games may still
    differ in the order of independent statements (e.g.,
    ``v1 = KEM2.KeyGen(); v2 = KEM1.KeyGen()`` vs.
    ``v1 = KEM1.KeyGen(); v2 = KEM2.KeyGen()``).  This transform sorts them
    with a topological sort of the block's dependency graph
    (:func:`dependencies.generate_dependency_graph`, the graph Topological
    Sorting uses), choosing among the statements free to go next by a key
    that does not depend on the order the code arrived in. A subsequent
    ``VariableStandardize`` pass re-normalises variable names after the
    reordering.

    The sorted statements are the typed declarations, assignments and
    samples (keyed by return position, then by value expression) and the
    ``if`` statements that contain no ``return`` (keyed by their structure,
    with the names they write or bind replaced by placeholders numbered in
    order of appearance, since those names come from the order itself).
    Every other statement (``for``, an ``if`` holding a ``return``, a bare
    declaration, a ``return``) keeps its position, and the sorted statements
    fill the positions they held, never crossing one of the fixed statements
    that depends on them or that they depend on.

    Then each bare declaration ``T v;`` moves down to just before the first
    statement that mentions ``v`` (several before one statement are ordered
    by first appearance in it), so that ``VariableStandardize`` names a
    result variable after the statement that computes it. A declaration is
    not moved past a statement that writes a name in its type, nor when ``v``
    is bound more than once in the block or its type mentions a name the
    block binds.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx
        self.fields: list[str] = []
        # Names bound to runtime values anywhere in the game, so the
        # dependency graph can tell a draw that may not complete (from a set
        # value, or `T \ E`) from a draw from a type.
        self.value_names: set[str] | None = None

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [f.name for f in game.fields]
        self.value_names = dependencies.game_value_names(game)
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(m) for m in new_game.methods]
        return new_game

    def _value_key(self, stmt: frog_ast.Statement) -> tuple:  # type: ignore[type-arg]
        """Structural sort key for the RHS expression, ignoring the assigned name.

        Returns a tuple built from ``node_sort_key`` so that ordering is
        based on AST shape rather than ``__str__`` output.  A numeric
        prefix distinguishes field declarations (0) from locals (1) so
        that fields sort deterministically before locals.
        """
        is_field = (
            isinstance(
                stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in self.fields
        )
        prefix = (0,) if is_field else (1,)
        if isinstance(stmt, frog_ast.Assignment):
            type_key = node_sort_key(stmt.the_type) if stmt.the_type else ()
            if stmt.value is not None:
                return prefix + (type_key, node_sort_key(stmt.value))
            return ()
        if isinstance(stmt, (frog_ast.Sample, frog_ast.UniqueSample)):
            type_key = (
                node_sort_key(stmt.the_type)
                if stmt.the_type
                else node_sort_key(stmt.sampled_from)
            )
            return prefix + (type_key, node_sort_key(stmt.sampled_from))
        return ()

    def _is_typed_decl(self, stmt: frog_ast.Statement) -> bool:
        if not isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return False
        if not isinstance(stmt.var, frog_ast.Variable):
            return False
        # Include field declarations even if the_type is None (field type
        # comes from the field definition, not the statement).
        if stmt.var.name in self.fields:
            return True
        if stmt.the_type is None:
            return False
        return True

    @staticmethod
    def _collect_vars_ltr(expr: frog_ast.Expression, result: list[str]) -> None:
        """Collect variable names from *expr* in left-to-right order."""
        if isinstance(expr, frog_ast.Variable):
            if expr.name not in result:
                result.append(expr.name)
        elif isinstance(expr, frog_ast.Tuple):
            for val in expr.values:
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    val, result
                )
        elif isinstance(expr, frog_ast.BinaryOperation):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.left_expression, result
            )
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.right_expression, result
            )
        elif isinstance(expr, frog_ast.FuncCall):
            if isinstance(expr.func, frog_ast.Expression):
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    expr.func, result
                )
            for arg in expr.args:
                _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                    arg, result
                )
        elif isinstance(expr, frog_ast.ArrayAccess):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.the_array, result
            )
        elif isinstance(expr, frog_ast.UnaryOperation):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.expression, result
            )
        elif isinstance(expr, frog_ast.Slice):
            _StabilizeIndependentStatementsTransformer._collect_vars_ltr(
                expr.the_array, result
            )

    def _compute_return_ranks(
        self,
        block: frog_ast.Block,
        stmts: list[frog_ast.Statement],
        sortable_indices: list[int],
        adj: dict[int, list[int]],
    ) -> dict[int, int]:
        """Compute a canonical rank for each sortable statement based on the
        return expression.

        Ranks are derived from the **top-level tuple position** in the
        return expression.  All variables within the same top-level tuple
        element share a rank, so value-key sorting still resolves ties.
        Ranks propagate backwards through the dependency graph so that a
        statement inherits the minimum rank of any statement that
        (transitively) depends on it.
        """
        # Find the return expression
        return_expr: frog_ast.Expression | None = None
        for s in block.statements:
            if isinstance(s, frog_ast.ReturnStatement):
                return_expr = s.expression
                break
        if return_expr is None:
            return {}

        # Split return into top-level groups; non-tuple returns are one group.
        groups: list[frog_ast.Expression]
        if isinstance(return_expr, frog_ast.Tuple):
            groups = list(return_expr.values)
        else:
            groups = [return_expr]

        if len(groups) < 2:
            # Single return value or non-tuple: every variable gets rank 0,
            # which is equivalent to no ranking (value-key decides).
            return {}

        # Collect variables from each group
        var_to_rank: dict[str, int] = {}
        for rank, group_expr in enumerate(groups):
            group_vars: list[str] = []
            self._collect_vars_ltr(group_expr, group_vars)
            for var_name in group_vars:
                if var_name not in var_to_rank:
                    var_to_rank[var_name] = rank
                else:
                    var_to_rank[var_name] = min(var_to_rank[var_name], rank)

        if not var_to_rank:
            return {}

        # Map variable names to sortable statement indices
        var_to_idx: dict[str, int] = {}
        for i in sortable_indices:
            s = stmts[i]
            if isinstance(
                s, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ) and isinstance(s.var, frog_ast.Variable):
                var_to_idx[s.var.name] = i

        # Assign direct return ranks
        ranks: dict[int, int] = {}
        for var_name, rank in var_to_rank.items():
            if var_name in var_to_idx:
                idx = var_to_idx[var_name]
                if idx not in ranks:
                    ranks[idx] = rank
                else:
                    ranks[idx] = min(ranks[idx], rank)

        # Build reverse adjacency: reverse_adj[j] = list of i that j
        # depends on (i.e. i must come before j).
        reverse_adj: dict[int, list[int]] = {i: [] for i in sortable_indices}
        for i in sortable_indices:
            for j in adj[i]:
                reverse_adj[j].append(i)

        # BFS backward propagation: if j has rank R, all statements i
        # that j depends on get min(current rank, R).
        from collections import deque  # pylint: disable=import-outside-toplevel

        queue: deque[int] = deque(idx for idx in ranks)
        while queue:
            j = queue.popleft()
            for i in reverse_adj[j]:
                new_rank = ranks[j]
                if i not in ranks or ranks[i] > new_rank:
                    ranks[i] = new_rank
                    queue.append(i)

        return ranks

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        stmts = list(block.statements)
        movable = self._movable_declarations(stmts)
        # The bare declarations go to the top while the other statements are
        # sorted, so that where an earlier run left one does not pin the
        # statements around it, and then down to their first use.
        new_stmts = self._sink_bare_declarations(
            self._sorted_statements(self._lift_bare_declarations(stmts, movable)),
            movable,
        )
        if new_stmts == stmts:
            return block
        return frog_ast.Block(new_stmts)

    def _sorted_statements(
        self, stmts: list[frog_ast.Statement]
    ) -> list[frog_ast.Statement]:
        block = frog_ast.Block(stmts)
        # Collect sortable statement indices.  If fewer than two are
        # sortable, no reordering is possible and we can skip the
        # (expensive) dependency-graph construction.
        sortable_indices = [
            i
            for i, s in enumerate(stmts)
            if self._is_typed_decl(s) or self._is_sortable_if(s)
        ]
        if len(sortable_indices) < 2:
            return stmts
        # The graph pins a draw whose domain may be empty relative to every
        # statement containing a return, so the reordering below never moves
        # it across an `if` that returns (F-327).
        graph = dependencies.generate_dependency_graph(
            block,
            [frog_ast.Field(frog_ast.Void(), f, None) for f in self.fields],
            {},
            self.value_names,
        )

        # Build dependency edges among sortable statements
        # adj[i] = list of sortable indices j that depend on i
        in_deg: dict[int, int] = {i: 0 for i in sortable_indices}
        adj: dict[int, list[int]] = {i: [] for i in sortable_indices}

        def _add_edge(src: int, dst: int) -> None:
            if dst not in adj[src]:
                adj[src].append(dst)
                in_deg[dst] += 1

        for i in sortable_indices:
            node_i = graph.get_node(stmts[i])
            for j in sortable_indices:
                if i != j:
                    node_j = graph.get_node(stmts[j])
                    if node_i in node_j.in_neighbours:
                        _add_edge(i, j)

        # Non-sortable statements (if, for, return, ...) stay in place,
        # but they can *depend* on a sortable stmt that precedes them or
        # *be depended on* by a sortable stmt that follows them.  If we
        # reorder the two sortable stmts across such a barrier, the
        # non-sortable stmt ends up referencing an undefined variable.
        # Encode the constraint by adding i -> j edges whenever a
        # non-sortable stmt k with i < k < j witnesses this.
        sortable_set = set(sortable_indices)
        for k, stmt_k in enumerate(stmts):
            if k in sortable_set:
                continue
            node_k = graph.get_node(stmt_k)
            # k depends on some earlier sortable i (node_i in node_k.in_neighbours):
            # any sortable j > k must sort after i, so add i -> j.
            for i in sortable_indices:
                if i >= k:
                    continue
                if graph.get_node(stmts[i]) not in node_k.in_neighbours:
                    continue
                for j in sortable_indices:
                    if j > k:
                        _add_edge(i, j)
            # k is depended on by some later sortable j (node_k in
            # node_j.in_neighbours): any sortable i < k must sort before j.
            for j in sortable_indices:
                if j <= k:
                    continue
                node_j = graph.get_node(stmts[j])
                if node_k not in node_j.in_neighbours:
                    continue
                for i in sortable_indices:
                    if i < k:
                        _add_edge(i, j)

        # Compute return-statement-based ranks.  Statements contributing
        # to earlier return values sort first, giving a canonical order
        # independent of source-code ordering.
        return_ranks = self._compute_return_ranks(block, stmts, sortable_indices, adj)

        # Canonical topological sort (Kahn's with min-heap).
        # Primary key: return rank (earlier return position first).
        # For fields: sort by canonical field name (assigned by
        #   FieldOrderingVisitor, independent of source order).
        # For locals: sort by value expression, then variable name.
        max_rank = len(stmts)

        def _heap_key(i: int) -> tuple:  # type: ignore[type-arg]
            rank = return_ranks.get(i, max_rank)
            s = stmts[i]
            name = ""
            if isinstance(
                s, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ) and isinstance(s.var, frog_ast.Variable):
                name = s.var.name
            if isinstance(s, frog_ast.IfStatement):
                # After the declarations free to go at the same point.
                return (rank, 2, self._if_key(s, placed_writers), "", i)
            is_field = name in self.fields
            if is_field:
                # Field name is canonical — use it as primary tiebreaker
                return (rank, 0, name, self._value_key(stmts[i]), i)
            # Local: value key is canonical (references primitives), name
            # is secondary (will be restandardised by the next pass).
            return (rank, 1, self._value_key(stmts[i]), name, i)

        # The position in the sorted order of the last placed statement that
        # writes each local: an if is keyed by these positions rather than
        # by the names it reads, which still reflect the input order.
        placed_writers: dict[str, int] = {}
        heap = [_heap_key(i) for i in sortable_indices if in_deg[i] == 0]
        heapq.heapify(heap)
        topo_order: list[int] = []
        while heap:
            popped = heapq.heappop(heap)
            idx = popped[-1]
            if popped[1] == 2 and heap and heap[0][:3] == popped[:3]:
                self._note_tied_ifs()
            topo_order.append(idx)
            for written in _written_names(stmts[idx]) - set(self.fields):
                placed_writers[written] = len(topo_order) - 1
            for j in adj[idx]:
                in_deg[j] -= 1
                if in_deg[j] == 0:
                    heapq.heappush(heap, _heap_key(j))

        # Place sorted statements back into the positions occupied by
        # sortable statements, preserving non-sortable statement positions.
        positions = sorted(sortable_indices)
        new_stmts = list(stmts)
        for pos, orig_idx in zip(positions, topo_order):
            new_stmts[pos] = stmts[orig_idx]
        return new_stmts

    @staticmethod
    def _is_sortable_if(stmt: frog_ast.Statement) -> bool:
        return (
            isinstance(stmt, frog_ast.IfStatement)
            and SearchVisitor(
                lambda node: isinstance(node, frog_ast.ReturnStatement)
            ).visit(stmt)
            is None
        )

    def _if_key(
        self, stmt: frog_ast.IfStatement, placed_writers: dict[str, int]
    ) -> tuple:  # type: ignore[type-arg]
        """Structural key of *stmt*: every local it writes or binds becomes a
        placeholder numbered in order of appearance, and every other local
        that a placed statement writes becomes that statement's position in
        the sorted order (*placed_writers*)."""
        own = set(_written_names(stmt))
        for branch in stmt.blocks:
            own.update(block_binder_names(branch))
        own -= set(self.fields)
        placed = {
            name: f"#{position}"
            for name, position in placed_writers.items()
            if name not in own
        }
        return _abstract_names(node_sort_key(stmt), own, {}, placed)

    def _note_tied_ifs(self) -> None:
        if self.ctx is None:
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Stabilize Independent Statements",
                reason=(
                    "Two independent if statements have the same structure "
                    "up to the names they write, so their order follows the "
                    "input"
                ),
                location=None,
                suggestion=(
                    "Make the two branches differ in what they read, or "
                    "write them in the same order on both sides of the hop"
                ),
                variable=None,
                method=None,
            )
        )

    @staticmethod
    def _movable_declarations(
        stmts: list[frog_ast.Statement],
    ) -> list[frog_ast.VariableDeclaration]:
        """The bare declarations of *stmts* whose name nothing else in the
        block binds and whose type mentions no name the block binds."""
        binder_counts = _binder_counts(frog_ast.Block(stmts))
        bound = set(binder_counts)
        return [
            statement
            for statement in stmts
            if isinstance(statement, frog_ast.VariableDeclaration)
            and binder_counts[statement.name] == 1
            and not referenced_variable_names(statement.type) & bound
        ]

    @staticmethod
    def _lift_bare_declarations(
        stmts: list[frog_ast.Statement],
        movable: list[frog_ast.VariableDeclaration],
    ) -> list[frog_ast.Statement]:
        """*stmts* with each movable bare declaration that no earlier
        statement mentions (by its name, or by writing a name in its type)
        moved to the top, in their original order."""
        lifted: list[frog_ast.Statement] = []
        for index, statement in enumerate(stmts):
            if not any(statement is declaration for declaration in movable):
                continue
            assert isinstance(statement, frog_ast.VariableDeclaration)
            type_names = referenced_variable_names(statement.type)
            if not any(
                statement.name in referenced_variable_names(earlier)
                or (type_names and reassigns_or_rebinds(type_names, earlier))
                for earlier in stmts[:index]
            ):
                lifted.append(statement)
        return lifted + [
            statement
            for statement in stmts
            if not any(statement is declaration for declaration in lifted)
        ]

    def _sink_bare_declarations(
        self,
        stmts: list[frog_ast.Statement],
        declarations: list[frog_ast.VariableDeclaration],
    ) -> list[frog_ast.Statement]:
        """*stmts* with each of *declarations* moved down to just before the
        first statement that mentions its name."""
        movable = [
            index
            for index, statement in enumerate(stmts)
            if any(statement is declaration for declaration in declarations)
        ]
        if not movable:
            return stmts
        rest = [s for index, s in enumerate(stmts) if index not in set(movable)]
        groups: dict[int, list[tuple[int, int, frog_ast.Statement]]] = {}
        for index in movable:
            declaration = stmts[index]
            assert isinstance(declaration, frog_ast.VariableDeclaration)
            type_names = referenced_variable_names(declaration.type)
            anchor = sum(1 for other in range(index) if other not in movable)
            target = anchor
            order = -1
            for position in range(anchor, len(rest)):
                candidate = rest[position]
                if declaration.name in referenced_variable_names(candidate):
                    target = position
                    order = [
                        variable.name
                        for variable in referenced_variables_in_order(candidate)
                    ].index(declaration.name)
                    break
                if type_names and reassigns_or_rebinds(type_names, candidate):
                    target = position
                    break
            groups.setdefault(target, []).append((order, index, declaration))
        result: list[frog_ast.Statement] = []
        for position in range(len(rest) + 1):
            for _, _, declaration in sorted(
                groups.get(position, []), key=lambda entry: entry[:2]
            ):
                result.append(declaration)
            if position < len(rest):
                result.append(rest[position])
        return result


class StabilizeIndependentStatements(TransformPass):
    name = "Stabilize Independent Statements"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _StabilizeIndependentStatementsTransformer(ctx).transform(game)
