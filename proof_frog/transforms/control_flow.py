# pylint: disable=duplicate-code
# SimplifyReturnTransformer shares transform_game pattern with inlining module.
"""Control flow passes: branch elimination, if/return simplification, unreachable.

These passes simplify the control flow graph by eliminating dead branches,
merging equivalent branches, inlining trivial returns, and removing
unreachable code after points where all paths have returned.
"""

from __future__ import annotations

import copy
import functools

import z3

from .. import frog_ast
from ..visitors import (
    Transformer,
    BlockTransformer,
    SearchVisitor,
    VariableCollectionVisitor,
    Z3FormulaVisitor,
    GetTypeMapVisitor,
    NameTypeMap,
)
from ._base import TransformPass, PipelineContext

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class BranchEliminiationTransformer(BlockTransformer):
    """Removes if/else-if branches whose conditions are statically known.

    When a condition is the literal ``true``, the branch body is inlined
    and all subsequent branches are dropped.  When a condition is the
    literal ``false``, the branch is removed entirely.  If every branch
    is eliminated the whole if-statement is removed.
    """

    def _transform_block_wrapper(
        self,
        block: frog_ast.Block,
    ) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.IfStatement):
                if_statement = statement
                new_if_statement = copy.deepcopy(if_statement)

                i = 0
                while True:
                    if i >= len(new_if_statement.conditions):
                        break
                    condition = new_if_statement.conditions[i]
                    if isinstance(condition, frog_ast.Boolean) and condition.bool:
                        new_if_statement.conditions = if_statement.conditions[: i + 1]
                        new_if_statement.blocks = if_statement.blocks[: i + 1]
                        if i == len(new_if_statement.conditions) - 1 and i > 0:
                            del new_if_statement.conditions[-1]
                        break
                    if isinstance(condition, frog_ast.Boolean) and not condition.bool:
                        del new_if_statement.conditions[i]
                        del new_if_statement.blocks[i]
                    else:
                        i += 1

                prior_block = frog_ast.Block(block.statements[:index])
                remaining_block = frog_ast.Block(block.statements[index + 1 :])

                if not new_if_statement.blocks:
                    return prior_block + remaining_block

                if (
                    len(new_if_statement.conditions) == 1
                    and isinstance(new_if_statement.conditions[0], frog_ast.Boolean)
                    and new_if_statement.conditions[0].bool
                ) or not new_if_statement.conditions:
                    return self.transform_block(
                        prior_block + new_if_statement.blocks[0] + remaining_block
                    )

                if new_if_statement != if_statement:
                    return self.transform_block(
                        prior_block
                        + frog_ast.Block([new_if_statement])
                        + remaining_block
                    )
        return block


class SimplifyIfTransformer(Transformer):
    """Merges adjacent if/else-if branches that have identical bodies.

    When two consecutive branches execute the same block, their conditions
    are combined with OR and one copy of the block is kept.  An else block
    that duplicates the preceding branch is also removed.

    Example::

        if (a) { return x; } else if (b) { return x; }
      becomes:
        if (a || b) { return x; }
    """

    def transform_if_statement(
        self, if_statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        new_blocks: list[frog_ast.Block] = copy.deepcopy(if_statement.blocks)
        new_conditions = copy.deepcopy(if_statement.conditions)
        index = 0
        while index < len(new_blocks) - (1 if not if_statement.has_else_block() else 2):
            if new_blocks[index] == new_blocks[index + 1]:
                del new_blocks[index]
                new_conditions[index] = frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.OR,
                    copy.deepcopy(new_conditions[index]),
                    copy.deepcopy(new_conditions[index + 1]),
                )
                del new_conditions[index + 1]
            else:
                index += 1

        if if_statement.has_else_block():
            if new_blocks[-1] == new_blocks[-2]:
                del new_blocks[-1]
                del new_conditions[-1]

            if not new_conditions:
                new_conditions = [frog_ast.Boolean(True)]
        return frog_ast.IfStatement(new_conditions, new_blocks)


class SimplifyReturnTransformer(BlockTransformer):
    """Inlines the value of an assignment into a trailing return statement.

    When a block ends with ``Type v = expr; return v;``, the assignment is
    removed and the return is rewritten as ``return expr;``.  Field variables
    are skipped because their assignment is a meaningful state mutation.

    Example::

        BitString<n> v3 = v1 + G.evaluate(v2);
        return v3;
      becomes:
        return v1 + G.evaluate(v2);
    """

    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        if not block.statements:
            return block
        last_statement = block.statements[-1]
        if not isinstance(last_statement, frog_ast.ReturnStatement):
            return block
        if not isinstance(last_statement.expression, frog_ast.Variable):
            return block
        if last_statement.expression.name in self.fields:
            return block
        index = len(block.statements) - 1

        def uses_var(variable: frog_ast.Expression, node: frog_ast.ASTNode) -> bool:
            return variable == node

        uses_var_partial = functools.partial(uses_var, last_statement.expression)
        while index >= 0:
            index -= 1
            statement = block.statements[index]
            if SearchVisitor(uses_var_partial).visit(statement) is None:
                continue
            if not isinstance(statement, (frog_ast.Variable, frog_ast.Assignment)):
                break
            if statement.var != last_statement.expression:
                break
            return self.transform_block(
                frog_ast.Block(block.statements[:index])
                + frog_ast.Block(block.statements[index + 1 : -1])
                + frog_ast.Block([frog_ast.ReturnStatement(statement.value)])
            )

        return block


class RemoveStatementTransformer(BlockTransformer):
    """Filters out specific statement instances (matched by identity) from all blocks."""

    def __init__(self, to_remove: list[frog_ast.Statement]):
        self.to_remove = to_remove

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        new_statements = []
        for statement in block.statements:
            if statement not in self.to_remove:
                new_statements.append(statement)
        return frog_ast.Block(new_statements)


# Consider case where else if condition might have a return but then the if condition doesn't
# Then in order to check whether it's definitely true we need (not A and B) where A is first condition and B is second.


class RemoveUnreachableTransformer(BlockTransformer):
    """Removes statements that follow a point where all execution paths return.

    Handles two cases:

    1. An if/else where every branch contains an unconditional return --
       all subsequent statements are trivially dead.
    2. A sequence of if-statements whose return-bearing branches, taken
       together, cover all possible executions.  Uses Z3 to check whether
       the negation of the accumulated return conditions is unsatisfiable,
       proving that no execution can reach subsequent statements.
    """

    def __init__(self, ast: frog_ast.ASTNode):
        self.ast = ast

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        def contains_unconditional_return(block: frog_ast.Block) -> bool:
            return any(
                isinstance(statement, frog_ast.ReturnStatement)
                for statement in block.statements
            )

        used_variables = VariableCollectionVisitor().visit(block)
        variable_version_map = dict((var.name, 0) for var in used_variables)

        def update_version(node: frog_ast.ASTNode) -> None:
            updated = []

            def assigns_variable_search(search_node: frog_ast.ASTNode) -> bool:
                if not isinstance(search_node, (frog_ast.Assignment, frog_ast.Sample)):
                    return False
                var = None
                if isinstance(search_node.var, frog_ast.Variable):
                    var = search_node.var
                if isinstance(search_node.var, frog_ast.ArrayAccess) and isinstance(
                    search_node.var.the_array, frog_ast.Variable
                ):
                    var = search_node.var.the_array

                if var in used_variables and var not in updated:
                    variable_version_map[var.name] += 1
                    updated.append(var)
                    return True
                return False

            while SearchVisitor(assigns_variable_search).visit(node) is not None:
                pass

        formula_so_far = None

        formula_visitor = Z3FormulaVisitor(NameTypeMap())

        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                update_version(statement)
                continue

            if statement.has_else_block() and all(
                contains_unconditional_return(if_block) for if_block in statement.blocks
            ):
                return frog_ast.Block(block.statements[: index + 1])
            solver = z3.Solver()
            solver.set("timeout", 30000)

            type_map = GetTypeMapVisitor(statement).visit(self.ast)
            formula_visitor.set_type_map(type_map)
            formula_visitor.set_variable_version_map(variable_version_map)
            condition_formulae: list[z3.AstRef] = []
            for condition_index, condition in enumerate(statement.conditions):
                individual_formula = formula_visitor.visit(condition)
                if individual_formula is None:
                    break
                if contains_unconditional_return(statement.blocks[condition_index]):
                    to_get_here = (
                        individual_formula
                        if not condition_formulae
                        else z3.And(
                            *(
                                z3.Not(condition_formula)
                                for condition_formula in condition_formulae
                            ),
                            individual_formula,
                        )
                    )
                    formula_so_far = (
                        z3.Or(to_get_here, formula_so_far)
                        if formula_so_far is not None
                        else to_get_here
                    )
                condition_formulae.append(individual_formula)

            update_version(statement)
            if formula_so_far is not None:
                solver.add(z3.Not(formula_so_far))
            satisfiable = solver.check()
            solver.reset()
            if satisfiable == z3.unsat:
                return frog_ast.Block(block.statements[: index + 1])

        return block


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class BranchElimination(TransformPass):
    name = "Branch Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return BranchEliminiationTransformer().transform(game)


class SimplifyReturn(TransformPass):
    name = "Simplify Returns"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyReturnTransformer().transform(game)


class SimplifyIf(TransformPass):
    name = "Simplify Ifs"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyIfTransformer().transform(game)


class RemoveUnreachable(TransformPass):
    name = "Remove unreachable blocks of code"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RemoveUnreachableTransformer(game).transform(game)
