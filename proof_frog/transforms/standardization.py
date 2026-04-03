"""Standardization passes: variable/field name standardization, field ordering.

These passes run once after the core fixed-point loop to assign canonical
names to variables and fields, ensuring two semantically equivalent games
produce identical ASTs.
"""

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
    """Renames all typed local variables to canonical names (v1, v2, v3, ...).

    Variables are numbered in declaration order across all methods.  A
    two-phase rename is used (first to collision-free intermediates, then
    to final names) to avoid conflicts when user-written names overlap
    with the v1/v2/... namespace.
    """

    def __init__(self) -> None:
        self.variable_counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_block = copy.deepcopy(block)

        # Collect typed local variable names in statement order.
        ordered_names: list[str] = []
        for statement in new_block.statements:
            if not isinstance(
                statement, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
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
    # Ensure independent copies before mutation — transform may share objects
    new_game = copy.copy(new_game)
    new_game.fields = [copy.copy(f) for f in new_game.fields]
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


class _StabilizeIndependentStatementsTransformer(BlockTransformer):
    """Sorts independent assignment/sample statements by their value expression.

    After variable standardization, two semantically equivalent games may still
    differ in the order of independent statements (e.g.,
    ``v1 = KEM2.KeyGen(); v2 = KEM1.KeyGen()`` vs.
    ``v1 = KEM1.KeyGen(); v2 = KEM2.KeyGen()``).  This transform sorts such
    independent pairs by a key derived from the value expression (with the
    assigned variable name replaced by a placeholder), producing a canonical
    order.  A subsequent ``VariableStandardize`` pass re-normalises variable
    names after the reordering.

    Only adjacent typed declaration pairs whose values differ and that have no
    dependency between them are swapped.
    """

    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [f.name for f in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(m) for m in new_game.methods]
        return new_game

    @staticmethod
    def _value_key(stmt: frog_ast.Statement) -> str:
        """Sort key based on the RHS expression, ignoring the assigned name."""
        if isinstance(stmt, frog_ast.Assignment) and stmt.the_type is not None:
            return str(stmt.the_type) + " = " + str(stmt.value)
        if isinstance(stmt, (frog_ast.Sample, frog_ast.UniqueSample)):
            if stmt.the_type is not None:
                return str(stmt.the_type) + " <- " + str(stmt.sampled_from)
        return ""

    def _is_typed_decl(self, stmt: frog_ast.Statement) -> bool:
        if not isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            return False
        if not isinstance(stmt.var, frog_ast.Variable):
            return False
        if stmt.the_type is None:
            return False
        # Only sort non-field declarations
        return stmt.var.name not in self.fields

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        graph = dependencies.generate_dependency_graph(
            block, [frog_ast.Field(frog_ast.Void(), f, None) for f in self.fields], {}
        )
        new_stmts = list(block.statements)
        swapped = True
        while swapped:
            swapped = False
            for i in range(1, len(new_stmts)):
                first, second = new_stmts[i - 1], new_stmts[i]
                if not (self._is_typed_decl(first) and self._is_typed_decl(second)):
                    continue
                key_a = self._value_key(first)
                key_b = self._value_key(second)
                if not key_a or not key_b or key_a <= key_b:
                    continue
                # Check independence
                node_a = graph.get_node(first)
                node_b = graph.get_node(second)
                if node_a in node_b.in_neighbours or node_b in node_a.in_neighbours:
                    continue
                new_stmts[i - 1] = second
                new_stmts[i] = first
                swapped = True
        if new_stmts == list(block.statements):
            return block
        return frog_ast.Block(new_stmts)


class StabilizeIndependentStatements(TransformPass):
    name = "Stabilize Independent Statements"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _StabilizeIndependentStatementsTransformer().transform(game)
