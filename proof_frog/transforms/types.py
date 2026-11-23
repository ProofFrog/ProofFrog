"""Type-related passes: subset normalization, dead null guard elimination.

These passes normalize type annotations and remove type-related dead code to
ensure canonical forms match across games with equivalent but differently
annotated types.
"""

from __future__ import annotations

import copy
import functools
from typing import Optional

from .. import frog_ast
from ..visitors import (
    SearchVisitor,
    Transformer,
    BlockTransformer,
    NameTypeMap,
    build_game_type_map,
    MethodScopedTypeMapMixin,
    lvalue_base_name,
)
from ._base import NearMiss, TransformPass, PipelineContext
from ._definedness import GameDefinedness

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


def _first_write(node: frog_ast.ASTNode, name: str) -> Optional[frog_ast.ASTNode]:
    """The first statement in *node*, at any depth, that may write *name*.

    Counts assignments, samples, element writes, ``for`` binders, bare
    redeclarations (``T? v;`` rebinds *name* to an unset, possibly-None
    variable) and tuple-destructuring bindings.  A write whose l-value has no
    variable base is counted too, since what it targets cannot be told.

    The last three are defense in depth: AlphaRename renames a redeclaration
    before this pass runs, the parser desugars destructuring into plain
    declarations, and the grammar's l-values always have a variable base.
    """

    def writes(inner: frog_ast.ASTNode) -> bool:
        if isinstance(
            inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            base = lvalue_base_name(inner.var)
            return base is None or base == name
        if isinstance(inner, frog_ast.VariableDeclaration):
            return inner.name == name
        if isinstance(inner, frog_ast.DestructuringBinding):
            return name in inner.names
        if isinstance(inner, frog_ast.NumericFor):
            return inner.name == name
        if isinstance(inner, frog_ast.GenericFor):
            return inner.var_name == name
        return False

    return SearchVisitor[frog_ast.ASTNode](writes).visit(node)


def _describe_write(write: frog_ast.ASTNode) -> str:
    """Name the kind of write *write* is, for a near-miss message."""
    if isinstance(write, (frog_ast.NumericFor, frog_ast.GenericFor)):
        return "a loop binder of the same name"
    if isinstance(write, (frog_ast.VariableDeclaration, frog_ast.DestructuringBinding)):
        return "a redeclaration"
    assert isinstance(
        write, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
    )
    if write.the_type is not None:
        return "a redeclaration"
    if not isinstance(write.var, frog_ast.Variable):
        return "an element write"
    if isinstance(write, frog_ast.Assignment):
        return "an assignment"
    return "a sample"


def _conflicting_names(
    method: frog_ast.Method, outer: list[tuple[str, frog_ast.Type]]
) -> set[str]:
    """Names bound in *method*'s scope under more than one type.

    *outer* lists the bindings visible from outside the method (fields,
    proof lets).  To these are added the method's parameters and every binder
    in its body, at any depth: typed declarations and ``for`` binders.  A
    name-to-type map of the method holds one type per name, so for a name
    returned here it is wrong at some use.
    """
    bindings: dict[str, list[frog_ast.Type]] = {}
    conflicting: set[str] = set()

    def bind(name: str, the_type: frog_ast.Type) -> None:
        bindings.setdefault(name, []).append(the_type)

    for name, the_type in outer:
        bind(name, the_type)
    for param in method.signature.parameters:
        bind(param.name, param.type)

    def collect(inner: frog_ast.ASTNode) -> bool:
        if isinstance(
            inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            if inner.the_type is not None and isinstance(inner.var, frog_ast.Variable):
                bind(inner.var.name, inner.the_type)
        elif isinstance(inner, frog_ast.VariableDeclaration):
            bind(inner.name, inner.type)
        elif isinstance(inner, frog_ast.NumericFor):
            bind(inner.name, frog_ast.IntType())
        elif isinstance(inner, frog_ast.GenericFor):
            bind(inner.var_name, inner.var_type)
        elif isinstance(inner, frog_ast.DestructuringBinding):
            conflicting.update(inner.names)
        return False

    SearchVisitor[frog_ast.ASTNode](collect).visit(method.block)
    conflicting.update(
        name
        for name, types in bindings.items()
        if any(other != types[0] for other in types[1:])
    )
    return conflicting


def _makes_call(node: frog_ast.ASTNode) -> bool:
    """Whether *node* contains a call anywhere."""
    return (
        SearchVisitor[frog_ast.ASTNode](
            lambda inner: isinstance(inner, frog_ast.FuncCall)
        ).visit(node)
        is not None
    )


class _NoneTestFolder(Transformer):
    """Folds the tests `e == None` / `e != None` of one statement whose
    operand can never be None, for :class:`DeadNullGuardEliminator`.

    Does not descend into the statement's nested blocks: the eliminator folds
    those when it reaches them, with the statements they hold, so that every
    fold is judged at its own statement.
    """

    def __init__(
        self,
        owner: DeadNullGuardEliminator,
        statement: frog_ast.Statement,
        report: bool,
    ) -> None:
        self.owner = owner
        self.statement = statement
        self.report = report

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        return block

    def transform_binary_operation(
        self, binary_op: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        new_op = self._transform_children(binary_op)
        if new_op.operator == frog_ast.BinaryOperators.AND:
            return self._drop_redundant_null_conjuncts(new_op)
        if new_op.operator not in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            return new_op
        if isinstance(new_op.right_expression, frog_ast.NoneExpression):
            tested = new_op.left_expression
        elif isinstance(new_op.left_expression, frog_ast.NoneExpression):
            tested = new_op.right_expression
        else:
            return new_op
        if self.owner.can_fold_none_test(self.statement, tested, self.report):
            return frog_ast.Boolean(
                new_op.operator == frog_ast.BinaryOperators.NOTEQUALS
            )
        return new_op

    def _drop_redundant_null_conjuncts(
        self, conjunction: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        """Drop each conjunct `y != None` that follows a conjunct `x == y` (or
        `y == x`) with `x` never None.

        A conjunct runs only when every earlier one was true, so when it runs
        `y` equals the value of `x`, which is not None: the test is true. `y`
        must make no call and read no map or array, so that both occurrences
        have the same value; the test must come after the equality, so the
        fold adds no evaluation.
        """
        conjuncts = _flatten_conjunction(conjunction)
        kept: list[frog_ast.Expression] = []
        for conjunct in conjuncts:
            subject = _not_none_subject(conjunct)
            if subject is not None and any(
                self._equates_never_none_with(earlier, subject) for earlier in kept
            ):
                if not _reads_only_variables(subject):
                    self.owner.note_unfolded_null_conjunct(subject)
                else:
                    continue
            kept.append(conjunct)
        if len(kept) == len(conjuncts):
            return conjunction
        return functools.reduce(
            lambda left, right: frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.AND, left, right
            ),
            kept,
        )

    def _equates_never_none_with(
        self, conjunct: frog_ast.Expression, subject: frog_ast.Expression
    ) -> bool:
        if not (
            isinstance(conjunct, frog_ast.BinaryOperation)
            and conjunct.operator == frog_ast.BinaryOperators.EQUALS
        ):
            return False
        for side, other in (
            (conjunct.left_expression, conjunct.right_expression),
            (conjunct.right_expression, conjunct.left_expression),
        ):
            if other == subject and self.owner.can_fold_none_test(
                self.statement, side, False
            ):
                return True
        return False


def _flatten_conjunction(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """The conjuncts of an `&&` chain, in evaluation order."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.AND
    ):
        return _flatten_conjunction(expr.left_expression) + _flatten_conjunction(
            expr.right_expression
        )
    return [expr]


def _not_none_subject(expr: frog_ast.Expression) -> Optional[frog_ast.Expression]:
    """The `y` of `y != None` or `None != y`, else None."""
    if not (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.NOTEQUALS
    ):
        return None
    if isinstance(expr.right_expression, frog_ast.NoneExpression):
        return expr.left_expression
    if isinstance(expr.left_expression, frog_ast.NoneExpression):
        return expr.right_expression
    return None


def _reads_only_variables(expr: frog_ast.Expression) -> bool:
    """No call, map or array read, or slice anywhere in *expr*."""
    return (
        SearchVisitor(
            lambda node: isinstance(
                node, (frog_ast.FuncCall, frog_ast.ArrayAccess, frog_ast.Slice)
            )
        ).visit(expr)
        is None
    )


class DeadNullGuardEliminator(MethodScopedTypeMapMixin, BlockTransformer):
    """Removes if (x == None) { ... } guards that can never execute, and
    folds the tests `x == None` / `x != None` that can never be true / false.

    Two cases are handled:
    1. x has non-nullable declared type (can never be None).
    2. x was declared as `T? x = expr` where expr is provably non-nullable,
       based on the return type of a method call on a known instantiable
       (primitive or scheme) in the proof namespace.

    A test that is not a removable guard (an if with an else, an else-if
    condition, a return, an operand of `&&`, ...) is folded to a Boolean
    literal when its operand qualifies by a rule that holds at every point of
    the method: a variable with a non-nullable declared type, a tuple literal
    that makes no call (folding drops the evaluation of the operand), or a
    call on a primitive or scheme whose return type is not optional (such a
    call has no effect, so dropping it is safe).  Case 2 depends on the
    position of the test and is used for guards only.  Inlining a method
    with a `T?` parameter at a call that passes a `T` produces such tests:
    `k == None` for a `k` drawn from the key space.

    After inlining, reduction bodies with null-narrowing guards produce
    patterns like `T? v = E.Enc(...); if (v == None) { return ...; } return v;`
    which can be simplified by this rule once E.Enc's non-nullable return
    type is known.

    The type map holds one type per name for a whole method.  A name bound
    twice under different types (a nullable field or parameter shadowed by a
    non-nullable local of an inner block, or two sibling-block locals) would
    get the wrong type at some guard, so the declared type of such a name is
    not trusted.  AlphaRename gives every local a distinct name before this
    pass runs; the check is there so the pass does not depend on it.

    Removing a guard removes the evaluation of the expression it tests, and
    lets the declaration of a local it tests be removed as unused.  A guard
    that can never fire is kept when the tested expression, or the
    initialiser of the tested local, reads a variable that may be unassigned
    at that point (a field only another oracle assigns, a local declared
    without a value).  Such a read yields the type's default and cannot fail
    (FROGLANG_REFERENCE.md section 6.9), so this is more cautious than
    soundness requires; it costs completeness only.
    """

    def __init__(
        self,
        type_map: NameTypeMap,
        proof_instantiables: Optional[dict[str, frog_ast.Instantiable]] = None,
        ctx: Optional[PipelineContext] = None,
    ) -> None:
        self.type_map = type_map
        self.proof_instantiables = proof_instantiables or {}
        self.ctx = ctx
        self._method_name: Optional[str] = None
        self._method: Optional[frog_ast.Method] = None
        self._facts = GameDefinedness(None, ctx)
        self._outer_bindings: list[tuple[str, frog_ast.Type]] = []
        self._conflicting: set[str] = set()

    def transform_game(self, game: frog_ast.Game) -> frog_ast.ASTNode:
        saved = (self._outer_bindings, self._facts)
        self._facts = GameDefinedness(game, self.ctx)
        self._outer_bindings = [(field.name, field.type) for field in game.fields]
        if self._scope_let_types is not None:
            self._outer_bindings += [
                (pair.name, pair.type) for pair in self._scope_let_types.type_map
            ]
        try:
            return self._transform_children(game)
        finally:
            self._outer_bindings, self._facts = saved

    def transform_method(self, method: frog_ast.Method) -> frog_ast.ASTNode:
        saved = (self._method_name, self._conflicting, self._method)
        self._method_name = method.signature.name
        self._method = method
        self._conflicting = _conflicting_names(method, self._outer_bindings)
        try:
            return super().transform_method(method)
        finally:
            self._method_name, self._conflicting, self._method = saved

    def _declared_type(self, name: str) -> Optional[frog_ast.Type]:
        """The type *name* is declared with, read through proof ``let:``
        type aliases, or None if it is unknown or the method binds *name*
        under more than one type."""
        if name in self._conflicting:
            return None
        return self._resolve_alias(self.type_map.get(name))

    def _resolve_alias(
        self, the_type: Optional[frog_ast.Type]
    ) -> Optional[frog_ast.Type]:
        """*the_type* read through the type names of the proof namespace,
        repeatedly: a name a ``let:`` entry defines as a type
        (``Set K = BitString<8>?;``) becomes that type, and a member alias
        of an instantiated scheme or primitive (``C.Elem``, with
        ``Set Elem = K;`` in it) becomes the member's type.

        A ``let:`` constant keeps its declared type as written (``K``,
        ``C.Elem``), which is not syntactically optional even when it stands
        for an optional type (F-416). A name with no definition (an abstract
        ``Set K;``, or a member ``Set Elem;`` with no value) is left as it
        is; a member alias that names no member of a namespace entry is
        unknown (None)."""
        namespace = self.ctx.proof_namespace if self.ctx is not None else {}
        seen: set[str] = set()
        while str(the_type) not in seen:
            seen.add(str(the_type))
            if isinstance(the_type, frog_ast.Variable):
                definition = namespace.get(the_type.name)
                if not isinstance(definition, frog_ast.Type):
                    return the_type
                the_type = definition
            elif isinstance(the_type, frog_ast.FieldAccess):
                member = self._member_type(the_type, namespace)
                if member is None:
                    return None
                if member is the_type:
                    return the_type
                the_type = member
            else:
                return the_type
        return the_type

    @staticmethod
    def _member_type(
        access: frog_ast.FieldAccess, namespace: frog_ast.Namespace
    ) -> Optional[frog_ast.Type]:
        """The type the member alias *access* (``C.Elem``) stands for: the
        value of the member in the instantiated scheme or primitive
        *namespace* binds ``C`` to; *access* itself for a member with no
        value; None when ``C`` is no such entry or has no such member."""
        if not isinstance(access.the_object, frog_ast.Variable):
            return None
        instantiable = namespace.get(access.the_object.name)
        if not isinstance(instantiable, (frog_ast.Primitive, frog_ast.Scheme)):
            return None
        for field in instantiable.fields:
            if field.name != access.name:
                continue
            if field.value is None:
                return access
            if isinstance(field.value, frog_ast.Type):
                return field.value
            return None
        return None

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # A nullable declaration `T? v = expr` with a provably non-nullable
        # expr makes v non-null for the guards after it, unless a later
        # statement, at any depth, may write v.
        non_null_locals: set[str] = set()
        # Locals initialised non-null that a later statement may write,
        # mapped to the declaration and that write: a guard on one is kept,
        # and reported.
        written_locals: dict[str, tuple[frog_ast.Assignment, frog_ast.ASTNode]] = {}
        # Locals initialised non-null from an expression that may read an
        # unassigned variable, mapped to that read.
        unassigned_inits: dict[str, tuple[str, str]] = {}
        new_statements: list[frog_ast.Statement] = []
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.IfStatement):
                if self._is_dead_null_guard(statement, non_null_locals):
                    tested = self._null_guard_subject(statement)
                    assert tested is not None
                    unassigned = self._unassigned_reads(statement, tested)
                    if not unassigned:
                        continue
                    self._report_unassigned_read(statement, unassigned[0])
                else:
                    self._report_unassigned_initialiser(statement, unassigned_inits)
                self._report_kept_guard(statement, written_locals)
            # An else-less guard was judged above, which reported why it stays.
            report = not (
                isinstance(statement, frog_ast.IfStatement)
                and self._null_guard_subject(statement) is not None
            )
            new_statements.append(
                _NoneTestFolder(self, statement, report).transform(statement)
            )
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.the_type, frog_ast.OptionalType)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.value is not None
                and self._is_nonnullable_expr(statement.value)
            ):
                name = statement.var.name
                write = next(
                    (
                        found
                        for later in block.statements[index + 1 :]
                        if (found := _first_write(later, name)) is not None
                    ),
                    None,
                )
                # The guard is what keeps this declaration, and so the
                # evaluation of its initialiser, alive. If the initialiser
                # may read an unassigned variable, the guard stays.
                init_reads = self._unassigned_reads(statement, statement.value)
                if init_reads:
                    unassigned_inits[name] = init_reads[0]
                elif write is None:
                    non_null_locals.add(name)
                else:
                    written_locals[name] = (statement, write)
        return frog_ast.Block(new_statements)

    def note_unfolded_null_conjunct(self, subject: frog_ast.Expression) -> None:
        """Record a near miss for a `y != None` conjunct kept after an equality
        with a value that is never None, because `y` makes a call or reads a
        map or array, so its two occurrences may differ."""
        if self.ctx is None:
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Dead Null Guard Elimination",
                reason=(
                    f"'{subject} != None' was kept after an equality with a value"
                    f" that is never None, because '{subject}' makes a call or"
                    " reads a map or array, so its two occurrences may differ"
                ),
                location=None,
                suggestion=(
                    "bind the value to a local and compare the local in both" " places"
                ),
                variable=None,
                method=None,
            )
        )

    def can_fold_none_test(
        self,
        statement: frog_ast.Statement,
        tested: frog_ast.Expression,
        report: bool = True,
    ) -> bool:
        """Whether a test of *tested* against None, in *statement*, may be
        folded: *tested* can never be None, by a rule that holds at every
        point of the method, and reads nothing that may be unassigned (the
        caution the guards get; more than soundness needs, see the class
        docstring).  With *report*, a test that almost folds is recorded as
        a near-miss."""
        if isinstance(tested, frog_ast.NoneExpression):
            return False
        if isinstance(tested, frog_ast.Tuple) and _makes_call(tested):
            return False
        if not self._is_nonnullable_expr(tested):
            if (
                report
                and isinstance(tested, frog_ast.Variable)
                and tested.name in self._conflicting
            ):
                self._report_untrusted_type(statement, tested.name)
            return False
        unassigned = self._unassigned_reads(statement, tested)
        if unassigned:
            if report:
                self._report_unassigned(
                    statement, "the expression it compares with None", unassigned[0]
                )
            return False
        return True

    def _report_untrusted_type(self, statement: frog_ast.Statement, name: str) -> None:
        """Record a near-miss for a None test not folded because the method
        binds the tested name under more than one type."""
        if self.ctx is None:
            return
        internal = name.startswith("__")
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Dead Null Guard Elimination",
                reason=(
                    f"Test of '{name}' against None not folded: the method "
                    f"binds '{name}' under more than one type, so its declared "
                    f"type is not trusted"
                ),
                location=statement.origin,
                suggestion="Give the bindings of the name different names",
                variable=None if internal else name,
                method=self._method_name,
            )
        )

    def _unassigned_reads(
        self, statement: frog_ast.Statement, expression: frog_ast.ASTNode
    ) -> list[tuple[str, str]]:
        """The variables *expression* reads that may be unassigned when
        *statement*, which evaluates it, runs, as ``(name, reason)``.

        Removing a guard removes the evaluation of the expression it tests,
        and lets the declaration of a local it tests be removed as unused.
        A guard that can never fire is removed only when everything those
        expressions read is definitely assigned: `if ([x, f] == None)`
        reads `f`. (More cautious than needed: such a read cannot fail.)
        """
        if self._method is None:
            return self._facts.for_method(None).unassigned_reads(expression)
        scope = self._facts.at_statement(self._method, statement)
        if scope is None:
            return [("?", "the statement could not be located in its method")]
        return scope.unassigned_reads(expression)

    def _report_unassigned(
        self, if_stmt: frog_ast.Statement, what: str, read: tuple[str, str]
    ) -> None:
        if self.ctx is None:
            return
        name, reason = read
        internal = name.startswith("__") or name == "?"
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Dead Null Guard Elimination",
                reason=(
                    f"Null guard not removed: it can never fire, but {what} "
                    f"reads '{name}', which may be unassigned ({reason})"
                ),
                location=if_stmt.origin,
                suggestion=(
                    f"Assign '{name}' before the guard on every path (a "
                    f"field: in a top-level statement of Initialize)"
                ),
                variable=None if internal else name,
                method=self._method_name,
            )
        )

    def _report_unassigned_read(
        self, if_stmt: frog_ast.IfStatement, read: tuple[str, str]
    ) -> None:
        self._report_unassigned(if_stmt, "the expression it tests", read)

    def _report_unassigned_initialiser(
        self,
        if_stmt: frog_ast.IfStatement,
        unassigned_inits: dict[str, tuple[str, str]],
    ) -> None:
        """Record a near-miss for a null guard kept because the initialiser
        of the local it tests may read an unassigned variable."""
        tested = self._null_guard_subject(if_stmt)
        if isinstance(tested, frog_ast.Variable) and tested.name in unassigned_inits:
            self._report_unassigned(
                if_stmt,
                "the initialiser of the local it tests",
                unassigned_inits[tested.name],
            )

    def _report_kept_guard(
        self,
        if_stmt: frog_ast.IfStatement,
        written_locals: dict[str, tuple[frog_ast.Assignment, frog_ast.ASTNode]],
    ) -> None:
        """Record a near-miss for a null guard kept only because the local it
        tests, though initialised non-null, may be written later."""
        if self.ctx is None:
            return
        tested = self._null_guard_subject(if_stmt)
        if not isinstance(tested, frog_ast.Variable):
            return
        found = written_locals.get(tested.name)
        if found is None:
            return
        declaration, write = found
        # AlphaRename has usually given the local an internal `__aN__` name
        # by now.  That name means nothing to the author and never appears in
        # the canonical diff, so describe the local by its declaration and
        # leave `variable` unset (the diagnostic matcher would otherwise look
        # for the name in the diff and drop the near-miss).
        internal = tested.name.startswith("__")
        subject = (
            f"a local of type '{declaration.the_type}' initialised to "
            f"'{declaration.value}'"
            if internal
            else f"'{tested.name}'"
        )
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Dead Null Guard Elimination",
                reason=(
                    f"Null guard not removed: {subject} starts out non-null, "
                    f"but {_describe_write(write)} later in the same block "
                    f"may change it"
                ),
                location=if_stmt.origin,
                suggestion=(
                    "Declare the local with a non-optional type, or write "
                    "the later value to a different variable"
                ),
                variable=None if internal else tested.name,
                method=self._method_name,
            )
        )

    def _is_nonnullable_expr(self, expr: frog_ast.ASTNode) -> bool:
        """Return True if expr is provably non-nullable.

        Handles:
        - Tuple literals.
        - Variables with non-nullable type in type_map.
        - Method calls obj.method(args) where obj is a known instantiable
          and method's declared return type is not Optional.
        """
        if isinstance(expr, frog_ast.NoneExpression):
            return False
        # A tuple literal is never None.
        if isinstance(expr, frog_ast.Tuple):
            return True
        if isinstance(expr, frog_ast.Variable):
            t = self._declared_type(expr.name)
            return t is not None and not isinstance(t, frog_ast.OptionalType)
        if isinstance(expr, frog_ast.FuncCall) and isinstance(
            expr.func, frog_ast.FieldAccess
        ):
            field_access = expr.func
            if isinstance(field_access.the_object, frog_ast.Variable):
                obj_name = field_access.the_object.name
                instantiable = self.proof_instantiables.get(obj_name)
                if instantiable is not None:
                    for method in instantiable.methods:
                        sig = (
                            method
                            if isinstance(method, frog_ast.MethodSignature)
                            else method.signature
                        )
                        if sig.name == field_access.name:
                            return not isinstance(
                                self._resolve_alias(sig.return_type),
                                frog_ast.OptionalType,
                            )
        return False

    @staticmethod
    def _null_guard_subject(
        if_stmt: frog_ast.IfStatement,
    ) -> Optional[frog_ast.Expression]:
        """The `x` of an else-less `if (x == None)` / `if (None == x)`."""
        if if_stmt.has_else_block() or len(if_stmt.conditions) != 1:
            return None
        condition = if_stmt.conditions[0]
        if not isinstance(condition, frog_ast.BinaryOperation):
            return None
        if condition.operator != frog_ast.BinaryOperators.EQUALS:
            return None
        if isinstance(condition.right_expression, frog_ast.NoneExpression):
            return condition.left_expression
        if isinstance(condition.left_expression, frog_ast.NoneExpression):
            return condition.right_expression
        return None

    def _is_dead_null_guard(
        self,
        if_stmt: frog_ast.IfStatement,
        non_null_locals: Optional[set[str]] = None,
    ) -> bool:
        """Check if this is a dead `if (x == None) { ... }` guard."""
        tested_expr = self._null_guard_subject(if_stmt)
        if tested_expr is None:
            return False

        # Case 1: tested expression is a variable with non-nullable type.
        if isinstance(tested_expr, frog_ast.Variable):
            var_type = self._declared_type(tested_expr.name)
            if var_type is not None and not isinstance(var_type, frog_ast.OptionalType):
                return True
            # Case 2: nullable var was assigned from a provably non-nullable expr.
            if non_null_locals and tested_expr.name in non_null_locals:
                return True

        # Case 3: tested expression is itself provably non-nullable
        # (e.g. a method call on a known primitive/scheme).
        if self._is_nonnullable_expr(tested_expr):
            return True

        return False


class SubsetTypeNormalizer(Transformer):
    """Normalizes subset types to their superset equivalents.

    Given subsets pairs like (KeySpace2, IntermediateSpace), replaces
    KeySpace2 with IntermediateSpace in type annotations. This ensures
    canonical forms match when the same value has different but
    subsets-equivalent type annotations in different games.

    For sampling distributions (``sampled_from`` in Sample statements),
    only equality pairs (``==``) are used, because ``subsets`` allows
    A ⊊ B where replacing ``x <- A`` with ``x <- B`` would change the
    distribution.
    """

    def __init__(
        self,
        subsets_pairs: list[tuple[frog_ast.Type, frog_ast.Type]],
        equality_pairs: set[tuple[str, str]] | None = None,
    ) -> None:
        self.type_replacements: dict[str, frog_ast.Type] = {}
        self._sampling_replacements: dict[str, frog_ast.Type] = {}
        eq_pairs = equality_pairs or set()
        for sub_type, super_type in subsets_pairs:
            if isinstance(sub_type, frog_ast.Variable):
                self.type_replacements[sub_type.name] = super_type
                # Only allow sampling normalization for equality pairs
                if (str(sub_type), str(super_type)) in eq_pairs:
                    self._sampling_replacements[sub_type.name] = super_type

    def transform_assignment(
        self, assignment: frog_ast.Assignment
    ) -> frog_ast.Assignment:
        new_type = self._normalize(assignment.the_type) if assignment.the_type else None
        return frog_ast.Assignment(
            new_type,
            self.transform(assignment.var),
            self.transform(assignment.value),
        )

    def transform_sample(self, sample: frog_ast.Sample) -> frog_ast.Sample:
        new_type = self._normalize(sample.the_type) if sample.the_type else None
        sampled = sample.sampled_from
        # sampled_from determines the sampling distribution — only normalize
        # with equality pairs (not subsets pairs, since A ⊊ B would change
        # the distribution).
        new_sampled: frog_ast.Expression = (
            self._normalize_sampling(sampled)  # type: ignore[assignment]
            if isinstance(sampled, frog_ast.Type)
            else self.transform(sampled)
        )
        return frog_ast.Sample(
            new_type,
            self.transform(sample.var),
            new_sampled,
        )

    def transform_field(self, field: frog_ast.Field) -> frog_ast.Field:
        return frog_ast.Field(
            self._normalize(field.type),
            field.name,
            self.transform(field.value) if field.value else None,
        )

    def transform_variable_declaration(
        self, decl: frog_ast.VariableDeclaration
    ) -> frog_ast.VariableDeclaration:
        return frog_ast.VariableDeclaration(self._normalize(decl.type), decl.name)

    def transform_parameter(self, param: frog_ast.Parameter) -> frog_ast.Parameter:
        return frog_ast.Parameter(self._normalize(param.type), param.name)

    def transform_method_signature(
        self, sig: frog_ast.MethodSignature
    ) -> frog_ast.MethodSignature:
        return frog_ast.MethodSignature(
            sig.name,
            self._normalize(sig.return_type),
            [self.transform(p) for p in sig.parameters],
        )

    def _normalize_sampling(self, the_type: frog_ast.Type) -> frog_ast.Type:
        """Normalize a type used in a sampling distribution.

        Only equality pairs are used, because subsets pairs could change
        the distribution.
        """
        if isinstance(the_type, frog_ast.OptionalType):
            return frog_ast.OptionalType(self._normalize_sampling(the_type.the_type))
        if (
            isinstance(the_type, frog_ast.Variable)
            and the_type.name in self._sampling_replacements
        ):
            return copy.deepcopy(self._sampling_replacements[the_type.name])
        if isinstance(the_type, frog_ast.ProductType):
            return frog_ast.ProductType(
                [self._normalize_sampling(t) for t in the_type.types]
            )
        return the_type

    def _normalize(self, the_type: frog_ast.Type) -> frog_ast.Type:
        if isinstance(the_type, frog_ast.OptionalType):
            return frog_ast.OptionalType(self._normalize(the_type.the_type))
        if (
            isinstance(the_type, frog_ast.Variable)
            and the_type.name in self.type_replacements
        ):
            return copy.deepcopy(self.type_replacements[the_type.name])
        if isinstance(the_type, frog_ast.ProductType):
            return frog_ast.ProductType([self._normalize(t) for t in the_type.types])
        # Recurse into collection element types so that, e.g.,
        # `Set<[KCiphertext, Sig]>` and `Set<[Message, Sig]>` normalize to the
        # same supertype annotation when `KCiphertext subsets Message`.
        if isinstance(the_type, frog_ast.SetType):
            if the_type.parameterization is None:
                return the_type
            return frog_ast.SetType(self._normalize(the_type.parameterization))
        if isinstance(the_type, frog_ast.MapType):
            return frog_ast.MapType(
                self._normalize(the_type.key_type),
                self._normalize(the_type.value_type),
            )
        if isinstance(the_type, frog_ast.ArrayType):
            return frog_ast.ArrayType(
                self._normalize(the_type.element_type), the_type.count
            )
        return the_type


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class DeadNullGuardElimination(TransformPass):
    name = "Dead Null Guard Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        # Primitives and schemes only.  Removing a guard on a call removes
        # the call, which is fine for a stateless primitive or scheme method
        # but would lose the state change of a game's oracle.  The engine
        # never binds a game in the proof namespace, so this costs nothing.
        instantiables: dict[str, frog_ast.Instantiable] = {
            k: v
            for k, v in ctx.proof_namespace.items()
            if isinstance(v, (frog_ast.Primitive, frog_ast.Scheme))
        }
        return (
            DeadNullGuardEliminator(type_map, instantiables, ctx)
            .scope_to_game(game, ctx.proof_let_types)
            .transform(game)
        )


class SubsetTypeNormalization(TransformPass):
    name = "Subset Type Normalization"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SubsetTypeNormalizer(
            ctx.subsets_pairs, equality_pairs=ctx.equality_pairs
        ).transform(game)
