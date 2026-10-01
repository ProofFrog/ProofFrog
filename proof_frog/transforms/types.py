"""Type-related passes: subset normalization, dead null guard elimination.

These passes normalize type annotations and remove type-related dead code to
ensure canonical forms match across games with equivalent but differently
annotated types.
"""

from __future__ import annotations

import copy
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


class DeadNullGuardEliminator(MethodScopedTypeMapMixin, BlockTransformer):
    """Removes if (x == None) { ... } guards that can never execute.

    Two cases are handled:
    1. x has non-nullable declared type (can never be None).
    2. x was declared as `T? x = expr` where expr is provably non-nullable,
       based on the return type of a method call on a known instantiable
       (primitive or scheme) in the proof namespace.

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
        self._outer_bindings: list[tuple[str, frog_ast.Type]] = []
        self._conflicting: set[str] = set()

    def transform_game(self, game: frog_ast.Game) -> frog_ast.ASTNode:
        saved = self._outer_bindings
        self._outer_bindings = [(field.name, field.type) for field in game.fields]
        if self._scope_let_types is not None:
            self._outer_bindings += [
                (pair.name, pair.type) for pair in self._scope_let_types.type_map
            ]
        try:
            return self._transform_children(game)
        finally:
            self._outer_bindings = saved

    def transform_method(self, method: frog_ast.Method) -> frog_ast.ASTNode:
        saved = (self._method_name, self._conflicting)
        self._method_name = method.signature.name
        self._conflicting = _conflicting_names(method, self._outer_bindings)
        try:
            return super().transform_method(method)
        finally:
            self._method_name, self._conflicting = saved

    def _declared_type(self, name: str) -> Optional[frog_ast.Type]:
        """The type *name* is declared with, or None if it is unknown or the
        method binds *name* under more than one type."""
        if name in self._conflicting:
            return None
        return self.type_map.get(name)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # A nullable declaration `T? v = expr` with a provably non-nullable
        # expr makes v non-null for the guards after it, unless a later
        # statement, at any depth, may write v.
        non_null_locals: set[str] = set()
        # Locals initialised non-null that a later statement may write,
        # mapped to the declaration and that write: a guard on one is kept,
        # and reported.
        written_locals: dict[str, tuple[frog_ast.Assignment, frog_ast.ASTNode]] = {}
        new_statements: list[frog_ast.Statement] = []
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.IfStatement):
                if self._is_dead_null_guard(statement, non_null_locals):
                    continue
                self._report_kept_guard(statement, written_locals)
            new_statements.append(statement)
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
                if write is None:
                    non_null_locals.add(name)
                else:
                    written_locals[name] = (statement, write)
        return frog_ast.Block(new_statements)

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
                                sig.return_type, frog_ast.OptionalType
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
        instantiables = {
            k: v
            for k, v in ctx.proof_namespace.items()
            if isinstance(v, (frog_ast.Primitive, frog_ast.Scheme, frog_ast.Game))
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
