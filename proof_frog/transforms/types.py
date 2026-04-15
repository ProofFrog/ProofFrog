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
    Transformer,
    BlockTransformer,
    NameTypeMap,
    build_game_type_map,
)
from ._base import TransformPass, PipelineContext

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class DeadNullGuardEliminator(BlockTransformer):
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
    """

    def __init__(
        self,
        type_map: NameTypeMap,
        proof_instantiables: Optional[dict[str, frog_ast.Instantiable]] = None,
    ) -> None:
        self.type_map = type_map
        self.proof_instantiables = proof_instantiables or {}

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Pre-pass: for nullable declarations `T? v = expr` where expr is
        # provably non-nullable, record v as effectively non-null.
        # But invalidate if the variable is later reassigned.
        non_null_locals: set[str] = set()
        for stmt in block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is not None
                and isinstance(stmt.the_type, frog_ast.OptionalType)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.value is not None
                and self._is_nonnullable_expr(stmt.value)
            ):
                non_null_locals.add(stmt.var.name)
            elif (
                isinstance(
                    stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
                )
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in non_null_locals
                and (not isinstance(stmt, frog_ast.Assignment) or stmt.the_type is None)
            ):
                # Variable is reassigned (untyped assignment, sample, or
                # unique sample) — it may now be nullable.
                non_null_locals.discard(stmt.var.name)

        new_statements: list[frog_ast.Statement] = []
        for statement in block.statements:
            if isinstance(statement, frog_ast.IfStatement) and self._is_dead_null_guard(
                statement, non_null_locals
            ):
                continue
            new_statements.append(statement)
        return frog_ast.Block(new_statements)

    def _is_nonnullable_expr(self, expr: frog_ast.ASTNode) -> bool:
        """Return True if expr is provably non-nullable.

        Handles:
        - Variables with non-nullable type in type_map.
        - Method calls obj.method(args) where obj is a known instantiable
          and method's declared return type is not Optional.
        """
        if isinstance(expr, frog_ast.NoneExpression):
            return False
        if isinstance(expr, frog_ast.Variable):
            t = self.type_map.get(expr.name)
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

    def _is_dead_null_guard(
        self,
        if_stmt: frog_ast.IfStatement,
        non_null_locals: Optional[set[str]] = None,
    ) -> bool:
        """Check if this is a dead `if (x == None) { ... }` guard."""
        if if_stmt.has_else_block() or len(if_stmt.conditions) != 1:
            return False
        condition = if_stmt.conditions[0]
        if not isinstance(condition, frog_ast.BinaryOperation):
            return False
        if condition.operator != frog_ast.BinaryOperators.EQUALS:
            return False

        # Identify which side is None and which is the tested expression.
        if isinstance(condition.right_expression, frog_ast.NoneExpression):
            tested_expr = condition.left_expression
        elif isinstance(condition.left_expression, frog_ast.NoneExpression):
            tested_expr = condition.right_expression
        else:
            return False

        # Case 1: tested expression is a variable with non-nullable type.
        if isinstance(tested_expr, frog_ast.Variable):
            var_type = self.type_map.get(tested_expr.name)
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
        return DeadNullGuardEliminator(type_map, instantiables).transform(game)


class SubsetTypeNormalization(TransformPass):
    name = "Subset Type Normalization"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SubsetTypeNormalizer(
            ctx.subsets_pairs, equality_pairs=ctx.equality_pairs
        ).transform(game)
