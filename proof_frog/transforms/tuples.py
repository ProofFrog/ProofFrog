"""Tuple-related passes: expand and simplify tuples.

Product-typed values are expanded into individual components for
canonicalization, then collapsed back when possible.
"""

from __future__ import annotations

import copy

from .. import frog_ast
from ..visitors import (
    BlockTransformer,
    NameTypeMap,
    Transformer,
    Visitor,
    SearchVisitor,
    ReplaceTransformer,
    AllConstantFieldAccesses,
    GetTypeMapVisitor,
    lvalue_base_name,
)
from ._base import (
    TransformPass,
    PipelineContext,
    has_nondeterministic_call,
    NearMiss,
)

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class ExpandTupleTransformer(Transformer):
    """Expands product-typed variables into individual component variables.

    A field or local of type ``T1 * T2`` is split into ``T1 v@0`` and
    ``T2 v@1``.  Index accesses like ``v[0]`` are rewritten to the
    corresponding component variable.  Only applies when all accesses
    use constant indices (checked via ``AllConstantFieldAccesses``).
    """

    def __init__(self) -> None:
        self.to_transform: list[str] = []
        self.lengths: list[int] = []

    def _is_transformable_tuple(
        self, the_type: frog_ast.Type, name: str, search_space: frog_ast.ASTNode
    ) -> bool:
        return isinstance(the_type, frog_ast.ProductType) and AllConstantFieldAccesses(
            name
        ).visit(search_space)

    @staticmethod
    def _has_reference(name: str, block: frog_ast.Block) -> bool:
        """Return True iff *name* is referenced (as a Variable) in *block*."""

        def is_named_variable(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.Variable) and node.name == name

        return SearchVisitor(is_named_variable).visit(block) is not None

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_fields = []
        for field in game.fields:
            if self._is_transformable_tuple(field.type, field.name, game):
                assert isinstance(field.type, frog_ast.ProductType)
                unfolded_types = field.type.types
                for index, the_type in enumerate(unfolded_types):
                    expression = None
                    if field.value:
                        field_values = frog_ast.tuple_literal_values(field.value)
                        assert field_values is not None
                        expression = field_values[index]
                    new_fields.append(
                        frog_ast.Field(the_type, f"{field.name}@{index}", expression)
                    )
                self.to_transform.append(field.name)
                self.lengths.append(len(unfolded_types))
            else:
                new_fields.append(field)
        return frog_ast.Game(
            (
                game.name,
                game.parameters,
                new_fields,
                [self.transform(method) for method in game.methods],
            )
        )

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        expanded_tuple_count = 0
        for stmt_idx, statement in enumerate(block.statements):
            # Assigning to the tuple means assigning each individual value
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.to_transform
            ):
                stmt_values = frog_ast.tuple_literal_values(statement.value)
                assert stmt_values is not None
                for index, tuple_value in enumerate(stmt_values):
                    new_statements.append(
                        frog_ast.Assignment(
                            None,
                            frog_ast.Variable(f"{statement.var}@{index}"),
                            tuple_value,
                        )
                    )
            # Asssigning to a tuple element means assigning to that one element
            elif (
                isinstance(statement, (frog_ast.Assignment, frog_ast.Sample))
                and isinstance(statement.var, frog_ast.ArrayAccess)
                and isinstance(statement.var.the_array, frog_ast.Variable)
                and statement.var.the_array.name in self.to_transform
            ):
                assert isinstance(statement.var.index, frog_ast.Integer)
                new_statement = copy.deepcopy(statement)
                new_statement.var = frog_ast.Variable(
                    f"{statement.var.the_array.name}@{statement.var.index.num}",
                )
                new_statements.append(new_statement)
            elif (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and self._is_transformable_tuple(
                    statement.the_type, statement.var.name, block
                )
                # Refuse to fire on a local-decl whose variable is not
                # referenced in subsequent statements of THIS block: the
                # use site is in an enclosing scope (e.g. this block is
                # the body of an if-branch), and expanding here would
                # split the decl into v@k components without rewriting
                # the outer-scope ``v[k]`` access, leaving it dangling.
                # The decl's own LHS does not count as a reference.
                and self._has_reference(
                    statement.var.name,
                    frog_ast.Block(list(block.statements[stmt_idx + 1 :])),
                )
            ):
                assert isinstance(statement.the_type, frog_ast.ProductType)
                unfolded_types = statement.the_type.types
                stmt_values = frog_ast.tuple_literal_values(statement.value)
                assert stmt_values is not None
                for index, the_type in enumerate(unfolded_types):
                    new_statements.append(
                        frog_ast.Assignment(
                            the_type,
                            frog_ast.Variable(f"{statement.var.name}@{index}"),
                            stmt_values[index],
                        )
                    )
                self.to_transform.append(statement.var.name)
                self.lengths.append(len(unfolded_types))
                expanded_tuple_count += 1
            else:
                new_statements.append(statement)
        new_block = frog_ast.Block(
            [self.transform(statement) for statement in new_statements]
        )
        self.to_transform = (
            self.to_transform[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.to_transform
        )
        self.lengths = (
            self.lengths[:-expanded_tuple_count]
            if expanded_tuple_count > 0
            else self.lengths
        )
        return new_block

    def transform_array_access(
        self, array_access: frog_ast.ArrayAccess
    ) -> frog_ast.Expression:
        if (
            not isinstance(array_access.the_array, frog_ast.Variable)
            or array_access.the_array.name not in self.to_transform
        ):
            return frog_ast.ArrayAccess(
                self.transform(array_access.the_array),
                self.transform(array_access.index),
            )
        assert isinstance(array_access.index, frog_ast.Integer)
        return frog_ast.Variable(
            f"{array_access.the_array.name}@{array_access.index.num}"
        )

    def transform_variable(self, var: frog_ast.Variable) -> frog_ast.Expression:
        if var.name not in self.to_transform:
            return var
        length = self.lengths[self.to_transform.index(var.name)]
        return frog_ast.Tuple(
            [frog_ast.Variable(f"{var.name}@{index}") for index in range(length)]
        )


class FoldTupleIndexTransformer(Transformer):
    """Constant-folds indexing a tuple literal: ``[e0, e1, ...][i]`` → ``e_i``.

    Only applies when the index is a constant integer and every discarded
    element (``e_j`` for ``j != i``) contains no non-deterministic function
    calls, ensuring that no randomised computation is silently removed.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_array_access(
        self, array_access: frog_ast.ArrayAccess
    ) -> frog_ast.Expression:
        arr = self.transform(array_access.the_array)
        idx = self.transform(array_access.index)

        if not (isinstance(arr, frog_ast.Tuple) and isinstance(idx, frog_ast.Integer)):
            return frog_ast.ArrayAccess(arr, idx)

        i = idx.num
        if i < 0 or i >= len(arr.values):
            return frog_ast.ArrayAccess(arr, idx)

        # Check that every DISCARDED element is pure (no non-deterministic calls)
        for j, elem in enumerate(arr.values):
            if j == i:
                continue
            if has_nondeterministic_call(
                elem, self._proof_namespace, self._proof_let_types
            ):
                return frog_ast.ArrayAccess(arr, idx)

        return arr.values[i]


class SimplifyTupleTransformer(Transformer):
    """Collapses a tuple literal back into the original variable.

    When a tuple ``[v[0], v[1], ...]`` reconstructs every element of a
    product-typed variable ``v`` in order, it is simplified to just ``v``.
    """

    def __init__(self, ast: frog_ast.ASTNode) -> None:
        self.ast = ast

    def transform_tuple(self, the_tuple: frog_ast.Tuple) -> frog_ast.Expression:
        if not all(
            isinstance(value, frog_ast.ArrayAccess) for value in the_tuple.values
        ):
            return the_tuple
        if not all(
            isinstance(value.index, frog_ast.Integer) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        if not all(
            value.index.num == index for index, value in enumerate(the_tuple.values)  # type: ignore
        ):
            return the_tuple
        if not all(
            isinstance(value.the_array, frog_ast.Variable) for value in the_tuple.values  # type: ignore
        ):
            return the_tuple
        tuple_val_name = the_tuple.values[0].the_array.name  # type: ignore
        if not all(
            value.the_array.name == tuple_val_name for value in the_tuple.values  # type: ignore
        ):
            return the_tuple

        type_map = GetTypeMapVisitor(the_tuple).visit(self.ast)
        tuple_type = type_map.get(tuple_val_name)
        assert isinstance(tuple_type, frog_ast.ProductType)
        if len(tuple_type.types) == len(the_tuple.values):
            return frog_ast.Variable(tuple_val_name)
        return the_tuple


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class ExpandTuple(TransformPass):
    name = "Expand Tuples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExpandTupleTransformer().transform(game)


class FoldTupleIndex(TransformPass):
    name = "Fold Tuple Literal Indexing"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return FoldTupleIndexTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class SimplifyTuple(TransformPass):
    name = "Simplify tuples that are copies of their fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyTupleTransformer(game).transform(game)


class CollapseSingleIndexTupleTransformer(BlockTransformer):
    """Collapses a product-typed variable accessed at a single constant index.

    When a typed local ``[T0, T1] v = expr`` (where *expr* is not a tuple
    literal) is only ever used as ``v[i]`` for one fixed index *i*, it is
    rewritten to ``Ti v = expr[i]`` and every ``v[i]`` is replaced with ``v``.

    This normalises composed-game canonical forms where a function call
    returning a product is only partially used, matching the form produced
    when a scheme-inlined game drops unused components.
    """

    def __init__(self) -> None:
        self._multi_assigned: set[str] = set()

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        # A variable assigned in more than one place within the method
        # (e.g. a phi-like variable declared in both arms of an if after
        # If-Split Branch Assignment) must NOT be collapsed: rewriting one
        # declaration to ``Ti v = expr[i]`` while leaving a sibling
        # ``[T0,T1] v = expr2`` produces an inconsistently-typed variable,
        # and a later inlining then substitutes the whole tuple in place of
        # ``v`` (dropping the index). Precompute the set of names with two
        # or more assignments in this method and skip them. Counting is
        # per-method so a name reused as an independent local in another
        # method is not affected.
        counts: dict[str, int] = {}

        def _count(node: frog_ast.ASTNode) -> bool:
            if isinstance(
                node,
                (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
            ):
                base = lvalue_base_name(node.var)
                if base is not None:
                    counts[base] = counts.get(base, 0) + 1
            return False

        SearchVisitor(_count).visit(method.block)
        saved = self._multi_assigned
        self._multi_assigned = {n for n, c in counts.items() if c > 1}
        try:
            new_block = self.transform(method.block)
        finally:
            self._multi_assigned = saved
        if new_block is method.block:
            return method
        return frog_ast.Method(method.signature, new_block)

    @staticmethod
    def _analyse_uses(var_name: str, block: frog_ast.Block) -> tuple[bool, set[int]]:
        """Return (has_bare_use, indices_used) for *var_name* in *block*.

        A "bare use" is any ``Variable(var_name)`` that is NOT the
        ``the_array`` child of an ``ArrayAccess`` node.
        """

        class _UsageVisitor(Visitor[None]):
            """Count total Variable refs and ArrayAccess refs."""

            def __init__(self, name: str) -> None:
                self.name = name
                self.total_var_refs = 0
                self.array_access_refs = 0
                self.non_constant_access = False
                self.indices: set[int] = set()

            def result(self) -> None:
                pass

            def visit_variable(self, var: frog_ast.Variable) -> None:
                if var.name == self.name:
                    self.total_var_refs += 1

            def visit_array_access(self, aa: frog_ast.ArrayAccess) -> None:
                if (
                    isinstance(aa.the_array, frog_ast.Variable)
                    and aa.the_array.name == self.name
                ):
                    self.array_access_refs += 1
                    if isinstance(aa.index, frog_ast.Integer):
                        self.indices.add(aa.index.num)
                    else:
                        self.non_constant_access = True

        visitor = _UsageVisitor(var_name)
        visitor.visit(block)
        # Bare uses = total Variable refs minus those inside ArrayAccess
        has_bare = visitor.total_var_refs > visitor.array_access_refs
        # If any access uses a non-constant index, treat as bare use
        # to prevent collapsing (the variable index may access any element)
        if visitor.non_constant_access:
            has_bare = True
        return has_bare, visitor.indices

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for stmt_idx, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.the_type, frog_ast.ProductType)
                and isinstance(statement.var, frog_ast.Variable)
                and frog_ast.tuple_literal_values(statement.value) is None
            ):
                continue

            var_name = statement.var.name
            if var_name in self._multi_assigned:
                continue
            remaining = frog_ast.Block(list(block.statements[stmt_idx + 1 :]))

            has_bare, indices_used = self._analyse_uses(var_name, remaining)
            if has_bare or len(indices_used) != 1:
                continue

            idx = next(iter(indices_used))
            assert isinstance(statement.the_type, frog_ast.ProductType)
            element_type = statement.the_type.types[idx]

            # Rewrite the declaration to extract just one element
            new_decl = frog_ast.Assignment(
                element_type,
                frog_ast.Variable(var_name),
                frog_ast.ArrayAccess(
                    copy.deepcopy(statement.value),
                    frog_ast.Integer(idx),
                ),
            )

            new_stmts = (
                list(block.statements[:stmt_idx])
                + [new_decl]
                + list(block.statements[stmt_idx + 1 :])
            )
            new_block = frog_ast.Block(new_stmts)

            # Replace all ArrayAccess(v, idx) with Variable(v)
            target = frog_ast.ArrayAccess(
                frog_ast.Variable(var_name), frog_ast.Integer(idx)
            )
            while True:
                found = SearchVisitor(
                    lambda n, t=target: (  # type: ignore[misc]
                        isinstance(n, frog_ast.ArrayAccess) and n == t
                    )
                ).visit(new_block)
                if found is None:
                    break
                new_block = ReplaceTransformer(
                    found, frog_ast.Variable(var_name)
                ).transform(new_block)

            return self.transform(new_block)

        return block


class CollapseSingleIndexTuple(TransformPass):
    name = "Collapse Single-Index Tuple Access"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return CollapseSingleIndexTupleTransformer().transform(game)


class _ProductLiteralValueRewriter(Transformer):
    """Rewrites ``ProductType`` tuple literals into ``Tuple`` nodes inside a
    single VALUE expression.

    Instantiation and inlining substitute namespace values for variables, and
    convert a ``Tuple`` whose members all satisfy ``isinstance(_, Type)`` into
    a ``ProductType`` so that Set-alias substitutions land in type positions
    as genuine types. Because ``Variable`` (and ``FieldAccess``) are both
    ``Expression`` and ``Type``, this also mangles ordinary tuple literals of
    bare variables (e.g. an inlined oracle argument ``[ss, ct]``) into
    ``ProductType`` nodes in expression positions, which downstream passes
    (``FoldTupleIndex``, ``TupleEqualityDecompose``) and ``Z3FormulaVisitor``
    do not recognize as tuple literals.

    This rewriter is applied only to expression slots that cannot hold a
    type (if-conditions, assignment/return values, loop bounds/iterables,
    map indices), so any ``ProductType`` it meets is a literal. Two guarded
    positions are left untouched because a bare ``ProductType`` there
    legitimately denotes a *space* rather than a literal: the operand of the
    cardinality operator ``|...|``, and the right-hand side of
    ``in``/``subsets``.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def transform_product_type(self, node: frog_ast.ProductType) -> frog_ast.ASTNode:
        values = frog_ast.tuple_literal_values(node)
        if values is not None and all(
            isinstance(v, frog_ast.Expression) for v in values
        ):
            return frog_ast.Tuple([self.transform(v) for v in values])
        if self.ctx is not None:
            self.ctx.near_misses.append(
                NearMiss(
                    transform_name="Normalize Product-Literal Tuples",
                    reason=(
                        "ProductType found in an expression position but not "
                        "converted to a tuple literal: not all members are "
                        "expressions"
                    ),
                    location=None,
                    suggestion=None,
                    variable=str(node),
                    method=None,
                )
            )
        return self._transform_children(node)

    def transform_unary_operation(
        self, node: frog_ast.UnaryOperation
    ) -> frog_ast.ASTNode:
        # `|X|` may take a space (type) operand: cardinality of a product
        # space must stay a ProductType (a Tuple there would mean length).
        if node.operator == frog_ast.UnaryOperators.SIZE:
            return node
        return self._transform_children(node)

    def transform_binary_operation(
        self, node: frog_ast.BinaryOperation
    ) -> frog_ast.ASTNode:
        # The RHS of `in` / `subsets` may be a space (type); leave it alone.
        if node.operator in (
            frog_ast.BinaryOperators.IN,
            frog_ast.BinaryOperators.SUBSETS,
        ):
            new_left = self.transform(node.left_expression)
            if new_left is node.left_expression:
                return node
            return frog_ast.BinaryOperation(
                node.operator, new_left, node.right_expression
            )
        return self._transform_children(node)


class NormalizeProductLiteralTransformer(BlockTransformer):
    """Applies ``_ProductLiteralValueRewriter`` to every method-body
    expression slot that can only hold a value, never a type. Declared types
    (``the_type``, sample spaces, loop variable types) are never touched."""

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _value(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        result: frog_ast.Expression = _ProductLiteralValueRewriter(self.ctx).transform(
            expr
        )
        return result

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        changed = False
        for statement in block.statements:
            new_statement = self._rewrite_statement(statement)
            changed = changed or new_statement is not statement
            new_statements.append(new_statement)
        return frog_ast.Block(new_statements) if changed else block

    def _rewrite_statement(self, statement: frog_ast.Statement) -> frog_ast.Statement:
        if isinstance(statement, frog_ast.Assignment):
            # `Set S = ...;` binds a type alias; leave its RHS alone.
            if isinstance(statement.the_type, frog_ast.SetType):
                return statement
            new_var = self._value(statement.var)
            new_value = self._value(statement.value)
            if new_var is statement.var and new_value is statement.value:
                return statement
            return frog_ast.Assignment(statement.the_type, new_var, new_value)
        if isinstance(statement, frog_ast.Sample):
            new_var = self._value(statement.var)
            if new_var is statement.var:
                return statement
            return frog_ast.Sample(statement.the_type, new_var, statement.sampled_from)
        if isinstance(statement, frog_ast.UniqueSample):
            new_var = self._value(statement.var)
            new_unique_set = self._value(statement.unique_set)
            if new_var is statement.var and new_unique_set is statement.unique_set:
                return statement
            return frog_ast.UniqueSample(
                statement.the_type,
                new_var,
                new_unique_set,
                statement.sampled_from,
                statement.surface_form,
            )
        if isinstance(statement, frog_ast.ReturnStatement):
            new_expression = self._value(statement.expression)
            if new_expression is statement.expression:
                return statement
            return frog_ast.ReturnStatement(new_expression)
        if isinstance(statement, frog_ast.IfStatement):
            new_conditions = [self._value(cond) for cond in statement.conditions]
            if all(
                new is old for new, old in zip(new_conditions, statement.conditions)
            ):
                return statement
            return frog_ast.IfStatement(new_conditions, list(statement.blocks))
        if isinstance(statement, frog_ast.NumericFor):
            new_start = self._value(statement.start)
            new_end = self._value(statement.end)
            if new_start is statement.start and new_end is statement.end:
                return statement
            return frog_ast.NumericFor(
                statement.name, new_start, new_end, statement.block
            )
        if isinstance(statement, frog_ast.GenericFor):
            new_over = self._value(statement.over)
            if new_over is statement.over:
                return statement
            return frog_ast.GenericFor(
                statement.var_type,
                statement.var_name,
                new_over,
                statement.block,
            )
        return statement


class NormalizeProductLiteral(TransformPass):
    name = "Normalize Product-Literal Tuples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return NormalizeProductLiteralTransformer(ctx).transform(game)
