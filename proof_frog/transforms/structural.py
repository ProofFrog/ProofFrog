"""Structural passes: topological sort, remove duplicate/unnecessary fields.

These passes operate on the game structure as a whole rather than individual
expressions or blocks.
"""

from __future__ import annotations

import copy
from typing import Optional

from .. import frog_ast
from .. import visitors
from .. import dependencies
from .control_flow import RemoveStatementTransformer
from ._base import TransformPass, PipelineContext


class _TrivialEncodingTransformer(visitors.Transformer):
    """Replace Prim.EncodeXxx(arg) with arg when Xxx == BitString<n> == return type.

    After instantiation, if a primitive's source Set for an encoding function is
    itself a BitString of the same size as the encoding target, the function is
    the identity and can be eliminated.  For example, if K.SharedSecret =
    BitString<prf_lambda> and K.EncodeSharedSecret returns BitString<prf_lambda>,
    then K.EncodeSharedSecret(x) simplifies to x.
    """

    def __init__(self, proof_namespace: frog_ast.Namespace) -> None:
        self.proof_namespace = proof_namespace

    def transform_func_call(self, func_call: frog_ast.FuncCall) -> frog_ast.ASTNode:
        # Transform children first.
        new_func = self.transform(func_call.func)
        new_args = [self.transform(arg) for arg in func_call.args]

        # Pattern: Prim.EncodeXxx(single_arg)
        if (
            isinstance(new_func, frog_ast.FieldAccess)
            and isinstance(new_func.the_object, frog_ast.Variable)
            and len(new_args) == 1
        ):
            prim_name = new_func.the_object.name
            method_name = new_func.name
            prim = self.proof_namespace.get(prim_name)
            if isinstance(prim, frog_ast.Primitive):
                method_sig: Optional[frog_ast.MethodSignature] = next(
                    (m for m in prim.methods if m.name == method_name), None
                )
                if (
                    method_sig is not None
                    and len(method_sig.parameters) == 1
                    and isinstance(
                        method_sig.parameters[0].type, frog_ast.BitStringType
                    )
                    and isinstance(method_sig.return_type, frog_ast.BitStringType)
                    and method_sig.parameters[0].type == method_sig.return_type
                ):
                    return new_args[0]

        result = copy.deepcopy(func_call)
        result.func = new_func
        result.args = new_args
        return result


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


class TrivialEncodingElimination(TransformPass):
    """Remove identity encoding calls: Prim.EncodeXxx(x) -> x when Xxx = BitString<n>."""

    name = "Trivial Encoding Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _TrivialEncodingTransformer(ctx.proof_namespace).transform(game)
