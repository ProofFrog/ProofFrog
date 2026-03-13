"""Assumption-based passes: apply step-specific assumptions.

Unlike core pipeline passes which are singletons, assumption passes are
instantiated per proof step with specific assumed predicates and a game side.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import z3

from .. import frog_ast
from ..visitors import (
    Transformer,
    Z3FormulaVisitor,
    GetTypeMapVisitor,
    NameTypeMap,
)
from ._base import TransformPass, PipelineContext

if TYPE_CHECKING:
    from ..proof_engine import ProcessedAssumption, WhichGame


# ---------------------------------------------------------------------------
# Transformer class (moved from visitors.py)
# ---------------------------------------------------------------------------


class SimplifyRangeTransformer(Transformer):
    def __init__(
        self,
        proof_let_types: NameTypeMap,
        game: frog_ast.Game,
        operation: frog_ast.BinaryOperation | frog_ast.UnaryOperation,
    ) -> None:
        self.game = game
        self.proof_let_types = proof_let_types
        type_map = GetTypeMapVisitor(game.methods[0]).visit(game) + proof_let_types
        self.assumed_op = operation
        self.assumed_formula = Z3FormulaVisitor(type_map).visit(operation)
        if self.assumed_formula is not None:
            self.solver = z3.Solver()
            self.solver.set("timeout", 30000)
            self.solver.add(self.assumed_formula)

    def transform_unary_operation(
        self, unary_operation: frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        return self._get_op(unary_operation)

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        return self._get_op(binary_operation)

    def _get_op(
        self, operation: frog_ast.BinaryOperation | frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        if operation == self.assumed_op:
            return frog_ast.Boolean(True)
        if (
            operation.operator
            not in (
                frog_ast.BinaryOperators.EQUALS,
                frog_ast.BinaryOperators.NOTEQUALS,
                frog_ast.BinaryOperators.LEQ,
                frog_ast.BinaryOperators.LT,
                frog_ast.BinaryOperators.GT,
                frog_ast.BinaryOperators.GEQ,
                frog_ast.BinaryOperators.AND,
                frog_ast.BinaryOperators.OR,
                frog_ast.UnaryOperators.NOT,
                frog_ast.UnaryOperators.MINUS,
            )
            or self.assumed_formula is None
        ):
            return operation
        type_map = GetTypeMapVisitor(operation).visit(self.game) + self.proof_let_types
        statement_formula = Z3FormulaVisitor(type_map).visit(operation)
        if statement_formula is None:
            return operation
        self.solver.push()
        self.solver.add(statement_formula)
        satisfied = self.solver.check() == z3.sat
        self.solver.pop()
        if not satisfied:
            return frog_ast.Boolean(False)
        solver = z3.Solver()
        solver.set("timeout", 30000)
        solver.add(z3.Not(z3.Implies(self.assumed_formula, statement_formula)))
        if solver.check() == z3.unsat:
            return frog_ast.Boolean(True)
        return operation


# ---------------------------------------------------------------------------
# TransformPass wrapper
# ---------------------------------------------------------------------------


class ApplyAssumptions(TransformPass):
    """Applies step-specific assumptions for a particular game side.

    Unlike the core pipeline passes (which are singletons in CORE_PIPELINE),
    this pass is instantiated per-invocation with the specific assumptions
    and game side.
    """

    name = "Apply Assumptions"

    def __init__(
        self,
        step_assumptions: list[ProcessedAssumption],
        which: WhichGame,
        proof_let_types: NameTypeMap,
    ) -> None:
        self.step_assumptions = step_assumptions
        self.which = which
        self.proof_let_types = proof_let_types

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        for assumption in self.step_assumptions:
            if assumption.which != self.which:
                continue
            game = SimplifyRangeTransformer(
                self.proof_let_types, game, assumption.assumption
            ).transform(game)
        return game
