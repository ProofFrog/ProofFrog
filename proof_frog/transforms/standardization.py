"""Standardization passes: variable/field name standardization, field ordering."""

from __future__ import annotations

import copy
import functools

from .. import frog_ast
from .. import dependencies
from ..visitors import (
    BlockTransformer,
    SearchVisitor,
    ReplaceTransformer,
    SubstitutionTransformer,
    FieldOrderingVisitor,
)
from ._base import TransformPass, PipelineContext

# ---------------------------------------------------------------------------
# Transformer class (moved from visitors.py)
# ---------------------------------------------------------------------------


class VariableStandardizingTransformer(BlockTransformer):
    def __init__(self) -> None:
        self.variable_counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_block = copy.deepcopy(block)

        # Collect typed local variable names in statement order.
        ordered_names: list[str] = []
        for statement in new_block.statements:
            if not isinstance(statement, (frog_ast.Assignment, frog_ast.Sample)):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue
            if statement.the_type is None:
                continue
            ordered_names.append(statement.var.name)

        def replace_all(blk: frog_ast.Block, old: str, new: str) -> frog_ast.Block:
            # ReplaceTransformer uses identity (`is`) comparison, so we use
            # SearchVisitor to get the actual object reference first, then
            # replace one occurrence at a time until none remain.
            def var_used(var: frog_ast.Variable, node: frog_ast.ASTNode) -> bool:
                return node == var

            while True:
                found = SearchVisitor[frog_ast.Variable](
                    functools.partial(var_used, frog_ast.Variable(old))
                ).visit(blk)
                if found is None:
                    break
                blk = ReplaceTransformer(found, frog_ast.Variable(new)).transform(blk)
            return blk

        # Phase 1: rename each typed variable to a collision-free intermediate
        # name. These names cannot conflict with any user-written "v1", "v2", ...
        # names, so this step is always safe regardless of what names already exist.
        for i, old_name in enumerate(ordered_names):
            new_block = replace_all(new_block, old_name, f"__vstandard_{i}__")

        # Phase 2: rename intermediate names to v1, v2, v3, ... in order.
        # Phase 1 guarantees each source name is unique, so no collision is possible.
        for i in range(len(ordered_names)):
            self.variable_counter += 1
            new_block = replace_all(
                new_block, f"__vstandard_{i}__", f"v{self.variable_counter}"
            )

        return new_block


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


def standardize_field_names(game: frog_ast.Game) -> frog_ast.Game:
    """Normalize field names to canonical ordering."""
    field_rename_map = FieldOrderingVisitor().visit(game)
    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
    for field_name, normalized_name in field_rename_map.items():
        ast_map.set(frog_ast.Variable(field_name), frog_ast.Variable(normalized_name))

    new_game = SubstitutionTransformer(ast_map).transform(game)
    for field in new_game.fields:
        field.name = field_rename_map[field.name]
    new_game.fields.sort(key=lambda element: element.name)
    return new_game


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class VariableStandardize(TransformPass):
    name = "Variable Standardization"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return VariableStandardizingTransformer().transform(game)


class StandardizeFieldNames(TransformPass):
    name = "Standardize Field Names"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return standardize_field_names(game)


class BubbleSortFieldAssignments(TransformPass):
    name = "Bubble Sort Field Assignments"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return dependencies.BubbleSortFieldAssignment().transform(game)
