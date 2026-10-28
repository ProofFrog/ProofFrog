"""Definite-assignment analysis for variable reads.

Decides, conservatively, whether every variable an expression reads is
definitely assigned where it is evaluated: a name it cannot prove assigned
is reported as possibly unassigned.

FrogLang has no undefined values (FROGLANG_REFERENCE.md section 6.9): a
variable read before it is assigned holds its type's default, so evaluating
an expression never fails and dropping or moving a read is sound without
this check. FoldLiteralConditions and DeadNullGuardElimination still
consult it before dropping an evaluation, and ExtractRepeatedTupleAccess
before hoisting a field read, a caution from before that rule was stated
that costs only completeness.

A name is definitely assigned at a read inside a method when it is

- a parameter of that method;
- a local in lexical scope bound by an initialized declaration
  (``T x = e;``, ``T x <- D;``, ``T x <-uniq[S] D;``) or a loop binder;
- a game field with a declared initializer, or one ``Initialize`` assigns in
  a top-level statement that no earlier ``return`` can skip (F-349) and that
  no call to a method of the game precedes, read from a method other than
  ``Initialize``;
- a game parameter or a proof ``let:`` name.

Everything else is declined, in particular a name whose binding is
ambiguous: one the method binds more than once, declares without a value
(``T x;``) anywhere, or shares with a game field or game parameter. So are a
field assigned only by another oracle, any field read inside ``Initialize``,
a name nothing binds, and any read outside a method.

Usage. Build one :class:`GameDefinedness` per game, then either

- walk a method yourself with :meth:`GameDefinedness.for_method`, calling
  ``enter_block`` / ``exit_block`` around each block, ``enter_loop`` /
  ``exit_loop`` around each loop body and ``declare`` after each statement,
  and query :meth:`MethodDefinedness.unassigned_reads` as you go; or
- ask for the scope at one statement with
  :meth:`GameDefinedness.at_statement`, which performs that walk and returns
  the scope as it stands just before the statement runs.
"""

from __future__ import annotations

from typing import Optional

from .. import frog_ast
from ..visitors import Visitor
from ._base import PipelineContext, may_return_before

_Loop = frog_ast.NumericFor | frog_ast.GenericFor


class _NodeCollector(Visitor[list[frog_ast.ASTNode]]):
    """Collects every node under the visited one, itself included, in
    source order."""

    def __init__(self) -> None:
        self.nodes: list[frog_ast.ASTNode] = []

    def result(self) -> list[frog_ast.ASTNode]:
        return self.nodes

    def visit_ast_node(self, node: frog_ast.ASTNode) -> None:
        self.nodes.append(node)


def _walk_nodes(node: frog_ast.ASTNode) -> list[frog_ast.ASTNode]:
    """Every AST node reachable from *node* (including itself)."""
    return _NodeCollector().visit(node)


def initialized_binder(node: frog_ast.ASTNode) -> Optional[str]:
    """The name a typed ``T x = e;`` / ``T x <- D;`` / ``T x <-uniq[S] D;``
    statement binds, or ``None`` for any other node."""
    if (
        isinstance(node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
        and node.the_type is not None
        and isinstance(node.var, frog_ast.Variable)
    ):
        return node.var.name
    return None


def loop_binder(loop: _Loop) -> str:
    """The name a ``for`` loop binds for its body."""
    if isinstance(loop, frog_ast.NumericFor):
        return loop.name
    return loop.var_name


def bare_declared_names(method: frog_ast.Method) -> list[str]:
    """Names *method* declares without a value (``T x;``), at any depth."""
    return [
        node.name
        for node in _walk_nodes(method.block)
        if isinstance(node, frog_ast.VariableDeclaration)
    ]


def method_binder_counts(method: frog_ast.Method) -> dict[str, int]:
    """How many times *method* binds each name: parameters, typed
    declarations (with or without a value) and loop binders."""
    names = bare_declared_names(method)
    names.extend(parameter.name for parameter in method.signature.parameters)
    for node in _walk_nodes(method.block):
        name = initialized_binder(node)
        if isinstance(node, (frog_ast.NumericFor, frog_ast.GenericFor)):
            name = loop_binder(node)
        if name is not None:
            names.append(name)
    return {name: names.count(name) for name in names}


def calls_game_method(game: frog_ast.Game, node: frog_ast.ASTNode) -> bool:
    """True if *node* calls a method of *game*, written ``M(...)`` or
    ``G.M(...)`` with ``G`` the game's own name."""
    methods = {method.signature.name for method in game.methods}
    for child in _walk_nodes(node):
        if not isinstance(child, frog_ast.FuncCall):
            continue
        func = child.func
        if isinstance(func, frog_ast.Variable) and func.name in methods:
            return True
        if (
            isinstance(func, frog_ast.FieldAccess)
            and isinstance(func.the_object, frog_ast.Variable)
            and func.the_object.name == game.name
            and func.name in methods
        ):
            return True
    return False


def initialize_unassigned_fields(game: frog_ast.Game) -> dict[str, str]:
    """The fields an oracle call may find unassigned, each with the reason.

    A field is assigned before any oracle runs when it has a declared
    initializer, or when ``Initialize`` assigns it in a top-level statement
    that no earlier ``return`` can skip (F-349) and that no call to a method
    of the game precedes or contains: such a call runs that method while the
    field may still be unassigned. A name that ``Initialize`` also binds as a
    local is not assigned that way either: an assignment to that name may
    target the local.

    Each reason completes the sentence "the field may be unassigned
    because ...".
    """
    candidates = [field.name for field in game.fields if field.value is None]
    initialize = next(
        (m for m in game.methods if m.signature.name == "Initialize"), None
    )
    assigned: set[str] = set()
    shadowed_names: set[str] = set()
    after_call: set[str] = set()
    if initialize is not None:
        shadowed = method_binder_counts(initialize)
        statements = initialize.block.statements
        called = False
        for index, statement in enumerate(statements):
            # A call in the assignment's own right-hand side runs before it.
            called = called or calls_game_method(game, statement)
            if not (
                isinstance(
                    statement,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and statement.the_type is None
                and isinstance(statement.var, frog_ast.Variable)
                and not may_return_before(statements, index)
            ):
                continue
            name = statement.var.name
            if name in shadowed:
                shadowed_names.add(name)
            elif called:
                after_call.add(name)
            else:
                assigned.add(name)
    reasons: dict[str, str] = {}
    for name in candidates:
        if name in assigned:
            continue
        if name in shadowed_names:
            reasons[name] = (
                f"Initialize also binds a local named '{name}', so its"
                " assignment to that name may target the local"
            )
        elif name in after_call:
            reasons[name] = (
                "Initialize calls a method of the game before assigning it,"
                " and that method may read it"
            )
        else:
            reasons[name] = (
                "Initialize does not assign it in a top-level statement before"
                " any return"
            )
    return reasons


def initialize_assigned_fields(game: frog_ast.Game) -> set[str]:
    """Fields every oracle call may read: those with a declared initializer
    and those ``Initialize`` assigns before any oracle can run (see
    :func:`initialize_unassigned_fields`)."""
    unassigned = initialize_unassigned_fields(game)
    return {field.name for field in game.fields if field.name not in unassigned}


class GameDefinedness:
    """The per-game facts of the analysis, computed once.

    *game* may be ``None`` (a method or expression analysed on its own):
    then no name resolves as a field or game parameter. *ctx* supplies the
    proof ``let:`` names; without it none resolve.
    """

    def __init__(
        self,
        game: Optional[frog_ast.Game],
        ctx: Optional[PipelineContext] = None,
    ) -> None:
        self.game = game
        self.ctx = ctx
        self.fields: set[str] = set()
        self.parameters: set[str] = set()
        self.initialize_assigned: set[str] = set()
        # The other fields, each with the reason an oracle may find it
        # unassigned.
        self.initialize_unassigned: dict[str, str] = {}
        if game is not None:
            self.fields = {field.name for field in game.fields}
            self.parameters = {parameter.name for parameter in game.parameters}
            self.initialize_unassigned = initialize_unassigned_fields(game)
            self.initialize_assigned = self.fields - set(self.initialize_unassigned)

    def is_let_name(self, name: str) -> bool:
        """True if *name* is a proof ``let:`` name."""
        return self.ctx is not None and (
            name in self.ctx.proof_namespace
            or self.ctx.proof_let_types.get(name) is not None
        )

    def for_method(self, method: Optional[frog_ast.Method]) -> MethodDefinedness:
        """A scope positioned at the start of *method*, with only its
        parameters bound. The caller drives it through the method body.
        With ``None`` every read is reported as outside a method."""
        return MethodDefinedness(self, method)

    def at_statement(
        self, method: frog_ast.Method, statement: frog_ast.Statement
    ) -> Optional[MethodDefinedness]:
        """The scope just before *statement* (matched by identity) runs in
        *method*, or ``None`` if *statement* is not in *method*.

        Query it for the expressions the statement itself evaluates, e.g.
        the right-hand side of a declaration: the name the statement binds
        is not in scope yet.
        """
        scope = MethodDefinedness(self, method)
        if scope.seek(method.block, statement):
            return scope
        return None


class MethodDefinedness:
    """Lexical scope within one method, and the queries against it.

    The scope starts with the method's parameters. A caller walking the
    method keeps it current with :meth:`enter_block` / :meth:`exit_block`,
    :meth:`enter_loop` / :meth:`exit_loop` and :meth:`declare`.
    """

    def __init__(self, game: GameDefinedness, method: Optional[frog_ast.Method]):
        self.game = game
        self.method = method
        self.binders: dict[str, int] = {}
        self.bare: set[str] = set()
        # Innermost scope last. Each holds the names bound by a parameter,
        # an initialized declaration or a loop binder.
        self._scopes: list[set[str]] = []
        if method is not None:
            self.binders = method_binder_counts(method)
            self.bare = set(bare_declared_names(method))
            self._scopes = [{p.name for p in method.signature.parameters}]

    @property
    def method_name(self) -> Optional[str]:
        return self.method.signature.name if self.method is not None else None

    # -- scope tracking --------------------------------------------------

    def enter_block(self) -> None:
        """Call before the first statement of a block."""
        self._scopes.append(set())

    def exit_block(self) -> None:
        """Call after the last statement of a block."""
        self._scopes.pop()

    def enter_loop(self, loop: _Loop) -> None:
        """Call after the loop header is evaluated and before its body: the
        binder is in scope for the body only."""
        self._scopes.append({loop_binder(loop)})

    def exit_loop(self) -> None:
        """Call after the loop body."""
        self._scopes.pop()

    def declare(self, statement: frog_ast.Statement) -> None:
        """Call after *statement* has been processed: an initialized
        declaration binds its name for the rest of the enclosing block.
        ``T x = e;`` does not have ``x`` in scope while ``e`` is evaluated.
        Any other statement binds nothing."""
        name = initialized_binder(statement)
        if name is not None and self._scopes:
            self._scopes[-1].add(name)

    def seek(self, block: frog_ast.Block, target: frog_ast.Statement) -> bool:
        """Advances the scope through *block* to just before *target*
        (matched by identity). Returns ``False``, with the scope restored,
        if *target* is not in *block*."""
        self.enter_block()
        for statement in block.statements:
            if statement is target or self._seek_nested(statement, target):
                return True
            self.declare(statement)
        self.exit_block()
        return False

    def _seek_nested(
        self, statement: frog_ast.Statement, target: frog_ast.Statement
    ) -> bool:
        if isinstance(statement, frog_ast.IfStatement):
            return any(self.seek(block, target) for block in statement.blocks)
        if isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            self.enter_loop(statement)
            if self.seek(statement.block, target):
                return True
            self.exit_loop()
        return False

    # -- queries ---------------------------------------------------------

    def unassigned_reason(self, name: str) -> Optional[str]:
        """Why a read of *name* at the current position may find it
        unassigned, or ``None`` when it is definitely assigned. The reason
        completes the sentence "'x' may be unassigned (...)"."""
        # pylint: disable=too-many-return-statements
        if self.method is None:
            return "it is read outside a method"
        fields = self.game.fields
        params = self.game.parameters
        if name in self.binders:
            if name in self.bare:
                return "it is declared without a value"
            if self.binders[name] != 1:
                return "the method binds that name more than once"
            if name in fields or name in params:
                return "it names both a local and a game field or parameter"
            if not any(name in scope for scope in self._scopes):
                return "its declaration is not in scope"
            return None
        if name in fields:
            if name in params:
                return "it names both a game field and a game parameter"
            if self.method.signature.name == "Initialize":
                return "it is a field read inside Initialize"
            gap = self.game.initialize_unassigned.get(name)
            if gap is not None:
                return f"it is a field and {gap}"
            return None
        if name in params:
            return None
        if self.game.is_let_name(name):
            return None
        return "it is not a parameter, local, field or let name"

    def unassigned_reads(self, node: frog_ast.ASTNode) -> list[tuple[str, str]]:
        """Every variable occurrence in *node* that may be unassigned at the
        current position, as ``(name, reason)``. Empty when every read is
        definitely assigned.

        Pass the expression that is evaluated (a condition, the right-hand
        side of a declaration), not a whole statement: every ``Variable``
        under *node* counts as a read, including an assignment target.
        """
        reads: list[tuple[str, str]] = []
        for child in _walk_nodes(node):
            if not isinstance(child, frog_ast.Variable):
                continue
            reason = self.unassigned_reason(child.name)
            if reason is not None:
                reads.append((child.name, reason))
        return reads
