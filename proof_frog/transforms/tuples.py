"""Tuple-related passes: expand and simplify tuples.

Product-typed values are expanded into individual components for
canonicalization, then collapsed back when possible.
"""

from __future__ import annotations

import copy

from .. import frog_ast
from ..visitors import (
    Transformer,
    AllConstantFieldAccesses,
    GetTypeMapVisitor,
)
from ._base import TransformPass, PipelineContext

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
        return (
            isinstance(the_type, frog_ast.BinaryOperation)
            and the_type.operator == frog_ast.BinaryOperators.MULTIPLY
            and AllConstantFieldAccesses(name).visit(search_space)
        )

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        new_fields = []
        for field in game.fields:
            if self._is_transformable_tuple(field.type, field.name, game):
                assert isinstance(field.type, frog_ast.BinaryOperation)
                unfolded_types = frog_ast.expand_tuple_type(field.type)
                # If the value has fewer elements than the fully-flattened
                # type, and the right side of the product is itself a nested
                # product (which is what expand_tuple_type over-flattened),
                # fall back to a top-level-only split.
                if (
                    field.value
                    and isinstance(field.value, frog_ast.Tuple)
                    and len(field.value.values) < len(unfolded_types)
                    and isinstance(
                        field.type.right_expression, frog_ast.BinaryOperation
                    )
                    and field.type.right_expression.operator
                    == frog_ast.BinaryOperators.MULTIPLY
                ):
                    unfolded_types = frog_ast.split_tuple_type_top(field.type)
                for index, the_type in enumerate(unfolded_types):
                    expression = None
                    if field.value:
                        assert isinstance(field.value, frog_ast.Tuple)
                        expression = field.value.values[index]
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
                [self.transform(phase) for phase in game.phases],
            )
        )

    def transform_block(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements: list[frog_ast.Statement] = []
        expanded_tuple_count = 0
        for index, statement in enumerate(block.statements):
            # Assigning to the tuple means assigning each individual value
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.to_transform
            ):
                assert isinstance(statement.value, frog_ast.Tuple)
                for index, tuple_value in enumerate(statement.value.values):
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
            ):
                assert isinstance(statement.the_type, frog_ast.BinaryOperation)
                unfolded_types = frog_ast.expand_tuple_type(statement.the_type)
                assert isinstance(statement.value, frog_ast.Tuple)
                # If the value has fewer elements than the fully-flattened
                # type, and the right side of the product is itself a nested
                # product (which is what expand_tuple_type over-flattened),
                # fall back to a top-level-only split.
                if (
                    len(statement.value.values) < len(unfolded_types)
                    and isinstance(
                        statement.the_type.right_expression,
                        frog_ast.BinaryOperation,
                    )
                    and statement.the_type.right_expression.operator
                    == frog_ast.BinaryOperators.MULTIPLY
                ):
                    unfolded_types = frog_ast.split_tuple_type_top(statement.the_type)
                for index, the_type in enumerate(unfolded_types):
                    new_statements.append(
                        frog_ast.Assignment(
                            the_type,
                            frog_ast.Variable(f"{statement.var.name}@{index}"),
                            statement.value.values[index],
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
        assert isinstance(tuple_type, frog_ast.BinaryOperation)
        expanded_type_array = frog_ast.expand_tuple_type(tuple_type)
        if len(expanded_type_array) == len(the_tuple.values):
            return frog_ast.Variable(tuple_val_name)
        return the_tuple


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class ExpandTuple(TransformPass):
    name = "Expand Tuples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExpandTupleTransformer().transform(game)


class SimplifyTuple(TransformPass):
    name = "Simplify tuples that are copies of their fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyTupleTransformer(game).transform(game)
