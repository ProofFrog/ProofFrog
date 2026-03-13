"""Structural passes: topological sort, remove duplicate/unnecessary fields.

These passes operate on the game structure as a whole rather than individual
expressions or blocks.
"""

from __future__ import annotations

import copy

from .. import frog_ast
from .. import visitors
from .. import dependencies
from .control_flow import RemoveStatementTransformer
from ._base import TransformPass, PipelineContext


def remove_duplicate_fields(game: frog_ast.Game) -> frog_ast.Game:
    """Remove fields that have the same type and always contain the same value."""
    for field in game.fields:
        for other_field in game.fields:
            if field.type == other_field.type and field.name < other_field.name:
                duplicated_statements = visitors.SameFieldVisitor(
                    (field.name, other_field.name)
                ).visit(game)
                if duplicated_statements is not None:
                    new_game = copy.deepcopy(game)
                    new_game.fields = [
                        the_field
                        for the_field in game.fields
                        if the_field.name != other_field.name
                    ]
                    ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                    ast_map.set(
                        frog_ast.Variable(other_field.name),
                        frog_ast.Variable(field.name),
                    )
                    return visitors.SubstitutionTransformer(ast_map).transform(
                        RemoveStatementTransformer(duplicated_statements).transform(
                            new_game
                        )
                    )
    return game


class TopologicalSort(TransformPass):
    name = "Topological Sorting"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if ctx.sort_game_fn is None:
            return game
        return ctx.sort_game_fn(game)


class RemoveDuplicateFields(TransformPass):
    name = "Remove Duplicate Fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return remove_duplicate_fields(game)


class RemoveUnnecessaryFields(TransformPass):
    name = "Remove unnecessary statements and fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return dependencies.remove_unnecessary_fields(game)
