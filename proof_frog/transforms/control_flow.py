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
from typing import Sequence

import z3

from .. import frog_ast
from ..visitors import (
    Transformer,
    BlockTransformer,
    SearchVisitor,
    SubstitutionTransformer,
    VariableCollectionVisitor,
    Z3FormulaVisitor,
    GetTypeMapVisitor,
    NameTypeMap,
    assigns_variable,
    block_unconditionally_returns,
)
from ._base import TransformPass, PipelineContext, NearMiss, has_nondeterministic_call

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

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

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
                        new_if_statement.conditions = new_if_statement.conditions[
                            : i + 1
                        ]
                        new_if_statement.blocks = new_if_statement.blocks[: i + 1]
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

                # Near-miss: if-statement found but no condition is a literal
                if (
                    self.ctx is not None
                    and new_if_statement == if_statement
                    and all(
                        not isinstance(c, frog_ast.Boolean)
                        for c in if_statement.conditions
                    )
                ):
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Branch Elimination",
                            reason=(
                                "Branch not eliminated: no condition is "
                                "a compile-time constant"
                            ),
                            location=None,
                            suggestion=None,
                            variable=None,
                            method=None,
                        )
                    )
        return block


def _normalize_block_locals(block: frog_ast.Block) -> frog_ast.Block:
    """Rename locally-declared variables in *block* to v1, v2, ... by
    declaration order.  Used for alpha-equivalent comparison of branches."""
    rename_map: dict[str, str] = {}
    counter = 0

    # Collect local declarations (Sample and Assignment with the_type)
    for stmt in block.statements:
        if isinstance(stmt, (frog_ast.Sample, frog_ast.Assignment)):
            if (
                isinstance(stmt.var, frog_ast.Variable)
                and stmt.the_type is not None
                and stmt.var.name not in rename_map
            ):
                counter += 1
                rename_map[stmt.var.name] = f"__alpha_{counter}__"

    if not rename_map:
        return block

    normalized = copy.deepcopy(block)
    for old_name, new_name in rename_map.items():
        ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
        ast_map.set(frog_ast.Variable(old_name), frog_ast.Variable(new_name))
        normalized = SubstitutionTransformer(ast_map).transform(normalized)
    return normalized


def _blocks_alpha_equivalent(a: frog_ast.Block, b: frog_ast.Block) -> bool:
    """Check if two blocks are identical up to renaming of locally-declared
    variables."""
    return _normalize_block_locals(a) == _normalize_block_locals(b)


class SimplifyIfTransformer(Transformer):
    """Merges adjacent if/else-if branches that have identical bodies.

    When two consecutive branches execute the same block (up to alpha-
    renaming of locally-scoped variables), their conditions are combined
    with OR and one copy of the block is kept.  An else block that
    duplicates the preceding branch is also removed.

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
            if _blocks_alpha_equivalent(new_blocks[index], new_blocks[index + 1]):
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
            if _blocks_alpha_equivalent(new_blocks[-1], new_blocks[-2]):
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
            # Check that no intervening statement modifies a free variable
            # of the expression being inlined.  Without this check, moving
            # `expr` from its original evaluation point to the return point
            # could change its value.
            expr_free_vars = VariableCollectionVisitor().visit(
                copy.deepcopy(statement.value)
            )
            if expr_free_vars:
                for skipped_idx in range(index + 1, len(block.statements) - 1):
                    skipped = block.statements[skipped_idx]
                    if (
                        SearchVisitor(
                            functools.partial(assigns_variable, expr_free_vars)
                        ).visit(skipped)
                        is not None
                    ):
                        return block
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
        self._block_path: dict[int, list[z3.AstRef]] = {}
        self._block_versions: dict[int, dict[str, int]] = {}

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        def contains_unconditional_return(block: frog_ast.Block) -> bool:
            return any(
                isinstance(statement, frog_ast.ReturnStatement)
                for statement in block.statements
            )

        used_variables = VariableCollectionVisitor().visit(block)
        inherited_versions = self._block_versions.pop(id(block), None)
        variable_version_map = (
            dict(inherited_versions)
            if inherited_versions is not None
            else dict((var.name, 0) for var in used_variables)
        )

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

        # Inherit path constraints from enclosing block (if any)
        path_constraints: list[z3.AstRef] = self._block_path.pop(id(block), [])

        # Track if-conditions with unconditional returns that have
        # already been seen.  A subsequent if with the same condition
        # is dead code (the earlier check already returned).
        seen_return_conditions: list[frog_ast.Expression] = []
        dead_indices: list[int] = []
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                old_versions = dict(variable_version_map)
                # Track assignments as path constraints for nested reasoning
                if isinstance(statement, frog_ast.Assignment):
                    type_map = GetTypeMapVisitor(statement).visit(self.ast)
                    # The stopping point excludes the assignment itself,
                    # so manually add the declared type for the LHS.
                    if statement.the_type is not None and isinstance(
                        statement.var, frog_ast.Variable
                    ):
                        type_map.set(statement.var.name, statement.the_type)
                    formula_visitor.set_type_map(type_map)
                    # Compute RHS with current (pre-assignment) version map
                    formula_visitor.set_variable_version_map(variable_version_map)
                    rhs_formula = formula_visitor.visit(statement.value)
                    # Update version so LHS gets the new version
                    update_version(statement)
                    formula_visitor.set_variable_version_map(variable_version_map)
                    lhs_formula = formula_visitor.visit(statement.var)
                    if (
                        lhs_formula is not None
                        and rhs_formula is not None
                        and not isinstance(lhs_formula, str)
                        and not isinstance(rhs_formula, str)
                    ):
                        try:
                            path_constraints.append(lhs_formula == rhs_formula)
                        except (z3.Z3Exception, TypeError):
                            pass
                else:
                    update_version(statement)
                # If any variable was modified, invalidate syntactic
                # condition tracking (the same expression may now
                # evaluate differently).
                if variable_version_map != old_versions:
                    seen_return_conditions.clear()
                continue

            if statement.has_else_block() and all(
                contains_unconditional_return(if_block) for if_block in statement.blocks
            ):
                new_stmts = [
                    s
                    for i, s in enumerate(block.statements[: index + 1])
                    if i not in dead_indices
                ]
                return frog_ast.Block(new_stmts)

            # Syntactic check: if all conditions match a previously-seen
            # return condition AND the if has an unconditional return and
            # no else, the if-statement is dead.
            if (
                not statement.has_else_block()
                and all(contains_unconditional_return(b) for b in statement.blocks)
                and all(cond in seen_return_conditions for cond in statement.conditions)
            ):
                dead_indices.append(index)
                continue

            # Z3-based check for more complex subsumption
            if (
                formula_so_far is not None or path_constraints
            ) and not statement.has_else_block():
                type_map = GetTypeMapVisitor(statement).visit(self.ast)
                formula_visitor.set_type_map(type_map)
                formula_visitor.set_variable_version_map(variable_version_map)
                all_conditions_dead = True
                for condition in statement.conditions:
                    cond_formula = formula_visitor.visit(condition)
                    if cond_formula is None:
                        all_conditions_dead = False
                        break
                    dead_solver = z3.Solver()
                    dead_solver.set("timeout", 30000)
                    dead_constraints = list(path_constraints)
                    if formula_so_far is not None:
                        dead_constraints.append(z3.Not(formula_so_far))
                    dead_constraints.append(cond_formula)
                    dead_solver.add(z3.And(*dead_constraints))
                    if dead_solver.check() != z3.unsat:
                        all_conditions_dead = False
                        break
                if all_conditions_dead and all(
                    contains_unconditional_return(b) for b in statement.blocks
                ):
                    dead_indices.append(index)
                    continue

            solver = z3.Solver()
            solver.set("timeout", 30000)

            type_map = GetTypeMapVisitor(statement).visit(self.ast)
            formula_visitor.set_type_map(type_map)
            formula_visitor.set_variable_version_map(variable_version_map)
            # Save formula_so_far before this statement's return guards are added,
            # so inner block tagging uses only constraints from prior statements.
            formula_before_stmt = formula_so_far
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

            # Track conditions that lead to unconditional returns
            for condition_index, condition in enumerate(statement.conditions):
                if contains_unconditional_return(statement.blocks[condition_index]):
                    seen_return_conditions.append(condition)

            # Tag inner blocks with accumulated path constraints
            for cond_idx, cond in enumerate(statement.conditions):
                if cond_idx < len(statement.blocks):
                    inner_path = list(path_constraints)
                    if formula_before_stmt is not None:
                        inner_path.append(z3.Not(formula_before_stmt))
                    # Add preceding if-conditions as negated (we didn't take those branches)
                    for prev_idx in range(cond_idx):
                        prev_formula = formula_visitor.visit(
                            statement.conditions[prev_idx]
                        )
                        if prev_formula is not None and not isinstance(
                            prev_formula, str
                        ):
                            inner_path.append(z3.Not(prev_formula))
                    cond_formula = formula_visitor.visit(cond)
                    if cond_formula is not None and not isinstance(cond_formula, str):
                        inner_path.append(cond_formula)
                    self._block_path[id(statement.blocks[cond_idx])] = inner_path
                    self._block_versions[id(statement.blocks[cond_idx])] = dict(
                        variable_version_map
                    )

            update_version(statement)
            if formula_so_far is not None:
                solver.add(z3.Not(formula_so_far))
            satisfiable = solver.check()
            solver.reset()
            if satisfiable == z3.unsat:
                new_stmts = [
                    s
                    for i, s in enumerate(block.statements[: index + 1])
                    if i not in dead_indices
                ]
                return frog_ast.Block(new_stmts)

        if dead_indices:
            return frog_ast.Block(
                [s for i, s in enumerate(block.statements) if i not in dead_indices]
            )
        return block


def _count_field_assigns_recursive(node: frog_ast.ASTNode, field_name: str) -> int:
    """Count how many times *field_name* is assigned/sampled anywhere in the AST."""
    count = 0

    def _counter(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == field_name
        ):
            count += 1
        return False  # never stop early — visit all nodes

    SearchVisitor(_counter).visit(node)
    return count


class IfConditionAliasSubstitutionTransformer(BlockTransformer):
    """Substitutes field references with local/parameter aliases inside if-branches.

    When a condition is ``A == B`` where A is a local variable or method
    parameter and B is a field (or vice-versa), B is replaced by A within
    the if-branch body.  This brings the if-branch into the same form as
    the else-branch, enabling ``SimplifyIf`` to merge identical branches and
    ``BranchElimination`` to collapse the resulting trivially-true conditional.

    Additionally, when a single-assignment field's definition contains the
    comparison field, the field reference is first inlined (replaced with
    its defining expression) in the if-branch before the alias substitution.
    This handles cross-method patterns like::

        Initialize: field4 = KEM.Decaps(field7, field1);
        Decaps:     if (v5 == field1) { return F(field4, ...); }

    which becomes ``F(KEM.Decaps(field7, v5), ...)`` after inlining + alias,
    matching the else-branch ``F(KEM.Decaps(field7, v5), ...)``.

    Only the first (if) branch is rewritten; else-if and else blocks are
    left untouched because the equality guarantee only holds in the branch
    whose condition asserts it.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self.field_names: list[str] = []
        self.param_names: list[str] = []
        # Maps field name -> its assigned expression (only for single-assignment fields
        # whose definition is composed entirely of other fields)
        self.field_definitions: dict[str, frog_ast.Expression] = {}
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.field_names = [field.name for field in game.fields]
        self._collect_field_definitions(game)
        new_game = copy.deepcopy(game)
        new_game.methods = [self._transform_method(m) for m in new_game.methods]
        return new_game

    def _collect_field_definitions(self, game: frog_ast.Game) -> None:
        """Collect single-assignment field definitions across all methods.

        Uses recursive search to count assignments in nested blocks
        (if-branches, etc.), not just top-level statements.
        """
        assign_counts: dict[str, int] = {}
        definitions: dict[str, frog_ast.Expression] = {}

        for method in game.methods:
            # Collect top-level definitions (for the expression value)
            for stmt in method.block.statements:
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name in self.field_names
                ):
                    definitions[stmt.var.name] = stmt.value

            # Count ALL assignments recursively (including nested blocks)
            for field_name in self.field_names:
                count = _count_field_assigns_recursive(method.block, field_name)
                assign_counts[field_name] = assign_counts.get(field_name, 0) + count

        # Keep only single-assignment fields whose definitions reference
        # only other fields (not locals/params from the assigning method)
        # and contain no non-deterministic function calls (inlining would
        # create a fresh evaluation that may return a different value).
        self.field_definitions = {}
        for name, expr in definitions.items():
            if assign_counts.get(name, 0) != 1:
                continue
            used_vars = VariableCollectionVisitor().visit(expr)
            if not all(v.name in self.field_names for v in used_vars):
                continue
            # Referenced fields must also be single-assignment — if a
            # referenced field is reassigned after this definition, the
            # stored value diverges from the current field value.
            if not all(assign_counts.get(v.name, 0) == 1 for v in used_vars):
                continue
            if has_nondeterministic_call(
                expr, self._proof_namespace, self._proof_let_types
            ):
                continue
            self.field_definitions[name] = expr

    def _transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        self.param_names = [p.name for p in method.signature.parameters]
        return self.transform(method)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                continue
            if len(statement.conditions) < 1:
                continue
            condition = statement.conditions[0]
            if not isinstance(condition, frog_ast.BinaryOperation):
                continue
            if condition.operator != frog_ast.BinaryOperators.EQUALS:
                continue

            local_expr, field_expr = self._classify_alias_pair(
                condition.left_expression, condition.right_expression
            )
            if local_expr is None or field_expr is None:
                continue

            new_branch = copy.deepcopy(statement.blocks[0])

            # Phase 1: Inline single-assignment fields whose definitions
            # mention the comparison field.
            assert isinstance(field_expr, frog_ast.Variable)
            field_var_name = field_expr.name
            for dep_field, dep_expr in self.field_definitions.items():
                dep_vars = VariableCollectionVisitor().visit(dep_expr)
                if not any(v.name == field_var_name for v in dep_vars):
                    continue
                inline_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                inline_map.set(frog_ast.Variable(dep_field), copy.deepcopy(dep_expr))
                new_branch = SubstitutionTransformer(inline_map).transform(new_branch)

            # Phase 2: Substitute the comparison field with the local/param.
            # Stop at the first reassignment of the field within the branch,
            # since after reassignment the field value may differ from the local.
            alias_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
            alias_map.set(field_expr, local_expr)
            new_stmts: list[frog_ast.Statement] = []
            for branch_stmt in new_branch.statements:
                # Check if this statement reassigns the field
                if (
                    isinstance(
                        branch_stmt,
                        (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                    )
                    and isinstance(branch_stmt.var, frog_ast.Variable)
                    and branch_stmt.var.name == field_var_name
                ):
                    # Stop substituting: keep this and all remaining as-is
                    remaining_idx = new_branch.statements.index(branch_stmt)
                    new_stmts.extend(new_branch.statements[remaining_idx:])
                    break
                new_stmts.append(
                    SubstitutionTransformer(alias_map).transform(branch_stmt)
                )
            new_branch = frog_ast.Block(new_stmts)

            if new_branch == statement.blocks[0]:
                continue

            new_if = copy.deepcopy(statement)
            new_if.blocks[0] = new_branch
            return self.transform_block(
                frog_ast.Block(block.statements[:index])
                + frog_ast.Block([new_if])
                + frog_ast.Block(block.statements[index + 1 :])
            )
        return block

    def _classify_alias_pair(
        self,
        left: frog_ast.Expression,
        right: frog_ast.Expression,
    ) -> tuple[frog_ast.Expression | None, frog_ast.Expression | None]:
        """Return (local_or_param, field) if the pair qualifies, else (None, None)."""
        left_is_local = self._is_local_or_param(left)
        right_is_field = self._is_field(right)
        if left_is_local and right_is_field:
            return left, right

        right_is_local = self._is_local_or_param(right)
        left_is_field = self._is_field(left)
        if right_is_local and left_is_field:
            return right, left

        return None, None

    def _is_local_or_param(self, expr: frog_ast.Expression) -> bool:
        if isinstance(expr, frog_ast.Variable):
            return expr.name not in self.field_names
        # Also accept parameter[constant] (tuple-element access on a param)
        if (
            isinstance(expr, frog_ast.ArrayAccess)
            and isinstance(expr.the_array, frog_ast.Variable)
            and isinstance(expr.index, frog_ast.Integer)
            and expr.the_array.name in self.param_names
        ):
            return True
        return False

    def _is_field(self, expr: frog_ast.Expression) -> bool:
        return isinstance(expr, frog_ast.Variable) and expr.name in self.field_names


class RedundantConditionalReturnTransformer(BlockTransformer):
    """Removes if-without-else blocks whose return duplicates the fall-through.

    Detects the pattern::

        if (cond) { return X; }
        return X;

    and simplifies it to just ``return X;``, since the if-branch is
    redundant.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                continue
            if statement.has_else_block():
                continue
            if len(statement.conditions) != 1:
                continue
            if_body = statement.blocks[0]
            if not if_body.statements:
                continue
            last_if_stmt = if_body.statements[-1]
            if not isinstance(last_if_stmt, frog_ast.ReturnStatement):
                continue
            # Check if the statement after the if is a matching return
            if index + 1 >= len(block.statements):
                continue
            next_stmt = block.statements[index + 1]
            if not isinstance(next_stmt, frog_ast.ReturnStatement):
                continue
            if if_body != frog_ast.Block([next_stmt]):
                continue
            # The if-branch body is just `return X;` and the fall-through
            # is the same `return X;` — remove the if entirely.
            return self.transform_block(
                frog_ast.Block(block.statements[:index])
                + frog_ast.Block(block.statements[index + 1 :])
            )
        return block


class AbsorbRedundantEarlyReturnTransformer(BlockTransformer):
    """Absorbs an early ``if (P) { return X; }`` into following if-statements
    when the trailing top-level return value is structurally identical to ``X``.

    Pattern (left → right within a single block)::

        if (P) { return X; }
        if (Q1) { ... }    // intervening if-statements (no else block)
        ...
        if (Qk) { ... }
        return X;          // structurally identical X

    is rewritten to::

        if (!P && Q1) { ... }
        ...
        if (!P && Qk) { ... }
        return X;

    Soundness: when ``P`` holds, the original returns ``X`` immediately at the
    early return. In the rewrite, every intervening condition becomes
    ``!P && Qi``, which is false because ``!P`` is false; control falls
    through to the trailing ``return X``. ``X`` evaluates to the same value
    in both cases because no top-level statement between the early return
    and the trailing return modifies its free variables -- only
    if-statements appear there, and their bodies do not run when ``P``
    holds (their guards include ``!P``). When ``!P`` holds, the rewritten
    guards reduce to ``Qi``, matching the original.

    Scope: this transform fires only on the outermost block of each method
    body, never on nested if-bodies. When the same pattern arises inside
    a nested if-body, the enclosing condition typically already constrains
    ``P`` to be unreachable, and ``RemoveUnreachable`` will eliminate the
    early-return branch entirely (preserving canonical equivalence with
    proofs whose intermediate games omit the redundant ``!P`` conjunct).
    Absorbing the conjunct in nested contexts would introduce a stale
    ``!P`` that no other transform can drop.
    """

    def __init__(self) -> None:
        self._nesting_depth = 0

    def transform_if_statement(
        self, if_statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        # Recurse into branches with depth incremented so the nested blocks
        # don't trigger absorption.
        self._nesting_depth += 1
        try:
            new_blocks = [self.transform_block(b) for b in if_statement.blocks]
            new_conditions = [self.transform(c) for c in if_statement.conditions]
        finally:
            self._nesting_depth -= 1
        return frog_ast.IfStatement(new_conditions, new_blocks)

    def transform_numeric_for(
        self, for_stmt: frog_ast.NumericFor
    ) -> frog_ast.NumericFor:
        self._nesting_depth += 1
        try:
            new_block = self.transform_block(for_stmt.block)
            new_start = self.transform(for_stmt.start)
            new_end = self.transform(for_stmt.end)
        finally:
            self._nesting_depth -= 1
        return frog_ast.NumericFor(for_stmt.name, new_start, new_end, new_block)

    def transform_generic_for(
        self, for_stmt: frog_ast.GenericFor
    ) -> frog_ast.GenericFor:
        self._nesting_depth += 1
        try:
            new_block = self.transform_block(for_stmt.block)
            new_over = self.transform(for_stmt.over)
        finally:
            self._nesting_depth -= 1
        return frog_ast.GenericFor(
            for_stmt.var_type, for_stmt.var_name, new_over, new_block
        )

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        if self._nesting_depth > 0:
            return block
        for index, statement in enumerate(block.statements):
            if not _is_simple_early_return_if(statement):
                continue
            assert isinstance(statement, frog_ast.IfStatement)
            early_p = statement.conditions[0]
            return_stmt = statement.blocks[0].statements[0]
            assert isinstance(return_stmt, frog_ast.ReturnStatement)
            early_x = return_stmt.expression

            # Find the first top-level trailing return whose expression
            # structurally equals X. Allow only IfStatements (no else
            # block) between the early return and that trailing return.
            trailing_idx = _find_matching_trailing_return(
                block.statements, index + 1, early_x
            )
            if trailing_idx is None:
                continue

            # Build !P with light surface simplification (== ↔ !=); deeper
            # simplification happens via SimplifyNot / NormalizeCommutativeChains.
            neg_p = _negate_condition(early_p)

            new_intermediate: list[frog_ast.Statement] = []
            for k in range(index + 1, trailing_idx):
                inner_if = block.statements[k]
                assert isinstance(inner_if, frog_ast.IfStatement)
                new_conditions: list[frog_ast.Expression] = [
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.AND,
                        copy.deepcopy(neg_p),
                        cond,
                    )
                    for cond in inner_if.conditions
                ]
                new_intermediate.append(
                    frog_ast.IfStatement(new_conditions, list(inner_if.blocks))
                )

            new_stmts: list[frog_ast.Statement] = (
                list(block.statements[:index])
                + new_intermediate
                + list(block.statements[trailing_idx:])
            )
            return self.transform_block(frog_ast.Block(new_stmts))
        return block


def _is_simple_early_return_if(stmt: frog_ast.Statement) -> bool:
    """True iff ``stmt`` is ``if (P) { return X; }`` with no else, no else-if,
    body of length 1, and the body's sole statement is a value-bearing
    ReturnStatement.
    """
    if not isinstance(stmt, frog_ast.IfStatement):
        return False
    if len(stmt.conditions) != 1:
        return False
    if stmt.has_else_block():
        return False
    body = stmt.blocks[0]
    if len(body.statements) != 1:
        return False
    only = body.statements[0]
    return isinstance(only, frog_ast.ReturnStatement) and only.expression is not None


def _find_matching_trailing_return(
    statements: Sequence[frog_ast.Statement],
    start: int,
    expected: frog_ast.Expression,
) -> int | None:
    """Find the index of the first top-level ``return X'`` statement at or
    after ``start`` whose expression structurally equals ``expected``,
    provided every statement strictly before it (from ``start``) is an
    ``IfStatement`` without a final else block. Returns ``None`` if any
    other statement type, an else-bearing if, or a non-matching return is
    encountered first.
    """
    for k in range(start, len(statements)):
        s = statements[k]
        if isinstance(s, frog_ast.ReturnStatement):
            if s.expression is not None and s.expression == expected:
                return k
            return None
        if not isinstance(s, frog_ast.IfStatement):
            return None
        if s.has_else_block():
            return None
    return None


def _negate_condition(cond: frog_ast.Expression) -> frog_ast.Expression:
    """Build a logical negation of ``cond``, preferring the surface form the
    canonicalization pipeline already favors: ``a == b`` ↔ ``a != b``, and
    eliminating a leading ``!`` if present. Otherwise wrap in ``!(cond)`` and
    let ``SimplifyNot`` rewrite further.
    """
    if isinstance(cond, frog_ast.BinaryOperation):
        if cond.operator == frog_ast.BinaryOperators.EQUALS:
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.NOTEQUALS,
                copy.deepcopy(cond.left_expression),
                copy.deepcopy(cond.right_expression),
            )
        if cond.operator == frog_ast.BinaryOperators.NOTEQUALS:
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EQUALS,
                copy.deepcopy(cond.left_expression),
                copy.deepcopy(cond.right_expression),
            )
    if (
        isinstance(cond, frog_ast.UnaryOperation)
        and cond.operator == frog_ast.UnaryOperators.NOT
    ):
        return copy.deepcopy(cond.expression)
    return frog_ast.UnaryOperation(frog_ast.UnaryOperators.NOT, copy.deepcopy(cond))


class IfFalseReturnToConjunctionTransformer(BlockTransformer):
    """Absorbs an early ``if (P) { return false; }`` into a trailing
    ``return BoolExpr;`` at the top level of the same block.

    Pattern (left → right within a single block)::

        if (P) { return false; }
        return BoolExpr;

    is rewritten to::

        return !P && BoolExpr;

    Soundness: when ``P`` holds, the original returns ``false``
    immediately; in the rewrite the locals execute unconditionally and
    the return becomes ``false && BoolExpr = false``. When ``!P`` holds,
    both forms run the same locals and return ``BoolExpr``. Equivalence
    therefore holds iff the intervening statements are side-effect-free,
    which we approximate by accepting only typed-local declarations
    (``Type v = expr;``) — these introduce a fresh local from a pure
    expression and have no observable effect outside the method.
    Sample statements, field writes, and reassignments are rejected.

    Companion to ``AbsorbRedundantEarlyReturn``: that pass handles the
    case where the trailing return value is structurally identical to
    the early return value; this pass handles the specific case where
    the early return value is the literal ``false``.

    Gap G guard: each accepted typed-local declaration's RHS expression
    must be evaluation-pure (no non-deterministic / state-mutating
    FuncCall). Without this guard, a helper that mutates a game-visible
    field-typed Map (e.g. a manually-written guarded-lazy-RO) could be
    hoisted past the early return, populating state that the original
    skipped on the ``P`` branch.
    """

    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        n = len(block.statements)
        for index in range(n - 1):
            stmt = block.statements[index]
            if not isinstance(stmt, frog_ast.IfStatement):
                continue
            if len(stmt.conditions) != 1 or stmt.has_else_block():
                continue
            body = stmt.blocks[0]
            if len(body.statements) != 1:
                continue
            inner = body.statements[0]
            if not isinstance(inner, frog_ast.ReturnStatement):
                continue
            if not (
                isinstance(inner.expression, frog_ast.Boolean)
                and inner.expression.bool is False
            ):
                continue
            # Trailing return must be the last statement in the block,
            # with only side-effect-free typed-local declarations between
            # the if and it.
            trailing_idx = self._find_pure_trailing_return(block.statements, index + 1)
            if trailing_idx is None:
                continue
            trailing = block.statements[trailing_idx]
            assert isinstance(trailing, frog_ast.ReturnStatement)
            if trailing.expression is None:
                continue
            neg_p = _negate_condition(stmt.conditions[0])
            # Place the original return expression FIRST and the
            # negated guard last; this matches the natural order in
            # which the source-level "Q && ct != ctStar"-style
            # binding-game checks are written, so canonicalization of
            # the two sides of a hop converges without needing a
            # global AND-chain sort (which proved too disruptive to
            # other proofs).
            new_return_expr = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.AND,
                copy.deepcopy(trailing.expression),
                neg_p,
            )
            new_stmts: list[frog_ast.Statement] = (
                list(block.statements[:index])
                + list(block.statements[index + 1 : trailing_idx])
                + [frog_ast.ReturnStatement(new_return_expr)]
                + list(block.statements[trailing_idx + 1 :])
            )
            return self.transform_block(frog_ast.Block(new_stmts))
        return block

    def _find_pure_trailing_return(
        self,
        statements: Sequence[frog_ast.Statement],
        start: int,
    ) -> int | None:
        for idx in range(start, len(statements)):
            s = statements[idx]
            if isinstance(s, frog_ast.ReturnStatement):
                return idx
            if (
                isinstance(s, frog_ast.Assignment)
                and s.the_type is not None
                and isinstance(s.var, frog_ast.Variable)
            ):
                # Typed-local declaration; the RHS must additionally be
                # evaluation-pure. ``has_nondeterministic_call`` flags any
                # FuncCall whose callee is not an annotated-deterministic
                # primitive method or a ``Function<D, R>`` variable, which
                # is exactly the set of calls that may mutate game-visible
                # state (Sample, field assignment, map/array writes
                # through helper bodies).
                if has_nondeterministic_call(
                    s.value,
                    self.ctx.proof_namespace,
                    self.ctx.proof_let_types,
                ):
                    return None
                continue
            return None
        return None


class FoldEquivalentReturnBranchTransformer(BlockTransformer):
    """Folds ``if (P) { return X; } return Y;`` to ``return Y;`` when Z3
    proves ``P ⇒ (X ↔ Y)`` with FuncCalls modelled as opaque atoms.

    Pattern (left → right within a single block, only when the if has no
    else and the body is exactly a single ``return X;``)::

        if (P) { return X; }
        return Y;

    is rewritten to::

        return Y;

    Soundness: when P holds, the original returns X; the rewrite returns Y.
    The Z3 check establishes ``P ⇒ X == Y``, so X and Y agree under P.
    When !P holds, the original falls through to ``return Y;`` (the if-body
    is skipped); the rewrite also returns Y. Equivalence holds because no
    statement between the if and the trailing return modifies free
    variables — the pattern requires the if to be IMMEDIATELY followed by
    the trailing return.

    Gap-F guard: refuses to fold if any of P, X, Y contains a non-
    deterministic call (mirroring ``BooleanAbsorption`` and the
    equivalence-engine escape hatch). Without this guard, dropping an
    early return could elide a counter advance or other observable
    side-effect in the if-body's evaluation of X.

    Z3 modelling: this pass uses ``opaque_func_call_fallback=True`` so
    deterministic ``FuncCall`` and BitString-concat shapes that Z3 cannot
    mix become memoized opaque atoms keyed on ``str(node)``. To bridge
    the common pattern where P contains direct equalities ``a == b`` and
    Y references ``b`` while X references ``a`` (or vice versa), the pass
    first applies syntactic substitution from the top-level conjuncts of P
    to both X and Y. After substitution, ``H(b)`` and ``H(a)`` become
    structurally identical and intern to the same opaque atom — a sound
    consequence of treating each conjunct ``a == b`` from P as a Z3
    assertion ``a == b`` in the model under which X and Y are evaluated.

    Closes the canonical-form gap where the bare-game side of a binding
    proof is branchless but the reduction-composed side carries an
    explicit case-split if-statement whose body is semantically equal to
    the trailing return under the case-B condition.
    """

    def __init__(self, ctx: PipelineContext, ast: frog_ast.ASTNode) -> None:
        self.ctx = ctx
        self.ast = ast
        self._init_field_rhs: list[tuple[frog_ast.Variable, frog_ast.Expression]] = []
        if isinstance(ast, frog_ast.Game):
            self._init_field_rhs = self._collect_init_field_rhs(ast)

    @staticmethod
    def _collect_init_field_rhs(
        game: frog_ast.Game,
    ) -> list[tuple[frog_ast.Variable, frog_ast.Expression]]:
        """Collect ``F → rhs`` substitutions for fields F that are
        single-write in Initialize with a deterministic FuncCall RHS and
        no other writes in the game.
        """
        field_names = {f.name for f in game.fields}
        # Count assignments per field across all methods.
        counts: dict[str, int] = {}
        for method in game.methods:
            for name in field_names:
                counts[name] = counts.get(name, 0) + _count_field_assigns_recursive(
                    method.block, name
                )
        init = next((m for m in game.methods if m.signature.name == "Initialize"), None)
        if init is None:
            return []
        result: list[tuple[frog_ast.Variable, frog_ast.Expression]] = []
        for stmt in init.block.statements:
            if not (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is None
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in field_names
            ):
                continue
            if counts.get(stmt.var.name, 0) != 1:
                continue
            if not isinstance(stmt.value, frog_ast.FuncCall):
                continue
            result.append((stmt.var, stmt.value))
        return result

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index in range(len(block.statements) - 1):
            stmt = block.statements[index]
            if not isinstance(stmt, frog_ast.IfStatement):
                continue
            if stmt.has_else_block() or len(stmt.conditions) != 1:
                continue
            body = stmt.blocks[0]
            if len(body.statements) != 1:
                continue
            inner = body.statements[0]
            if not isinstance(inner, frog_ast.ReturnStatement):
                continue
            x_expr = inner.expression
            if x_expr is None:
                continue
            trailing = block.statements[index + 1]
            if not isinstance(trailing, frog_ast.ReturnStatement):
                continue
            y_expr = trailing.expression
            if y_expr is None:
                continue
            p_expr = stmt.conditions[0]
            # Gap-F: refuse on any non-deterministic call.
            if (
                has_nondeterministic_call(
                    p_expr,
                    self.ctx.proof_namespace,
                    self.ctx.proof_let_types,
                )
                or has_nondeterministic_call(
                    x_expr,
                    self.ctx.proof_namespace,
                    self.ctx.proof_let_types,
                )
                or has_nondeterministic_call(
                    y_expr,
                    self.ctx.proof_namespace,
                    self.ctx.proof_let_types,
                )
            ):
                continue
            # Apply syntactic equality substitution from top-level
            # conjuncts of P. For each conjunct of the form `a == b`
            # (where one side is a Variable), replace that Variable with
            # the other side in X and Y. This bridges the common case
            # where Y references one side of an equality stated in P and
            # X references the other.
            sub_pairs: list[tuple[frog_ast.Expression, frog_ast.Expression]] = []
            for conjunct in _flatten_top_level_and(p_expr):
                if (
                    isinstance(conjunct, frog_ast.BinaryOperation)
                    and conjunct.operator == frog_ast.BinaryOperators.EQUALS
                ):
                    a = conjunct.left_expression
                    b = conjunct.right_expression
                    if isinstance(b, frog_ast.Variable) and not isinstance(
                        a, frog_ast.Variable
                    ):
                        sub_pairs.append((b, a))
                    elif isinstance(a, frog_ast.Variable) and not isinstance(
                        b, frog_ast.Variable
                    ):
                        sub_pairs.append((a, b))
                    elif isinstance(a, frog_ast.Variable) and isinstance(
                        b, frog_ast.Variable
                    ):
                        if a.name < b.name:
                            sub_pairs.append((b, a))
                        else:
                            sub_pairs.append((a, b))
            # Augment with single-write Init-only field RHS expansions
            # so the comparison can see through hoisted-call fields.
            all_sub_pairs: list[tuple[frog_ast.Expression, frog_ast.Expression]] = list(
                sub_pairs
            ) + list(self._init_field_rhs)
            if all_sub_pairs:
                # Iterate substitution to a fixed point so chains like
                # `_hoisted_0 → EncodeEK(ek_T_0)` followed by P's
                # `ek_T_1 → ek_T_0` propagate fully.
                x_sub = copy.deepcopy(x_expr)
                y_sub = copy.deepcopy(y_expr)
                for _ in range(8):
                    sub_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(
                        identity=False
                    )
                    for k, v in all_sub_pairs:
                        sub_map.set(k, copy.deepcopy(v))
                    new_x = SubstitutionTransformer(sub_map).transform(
                        copy.deepcopy(x_sub)
                    )
                    new_y = SubstitutionTransformer(sub_map).transform(
                        copy.deepcopy(y_sub)
                    )
                    if new_x == x_sub and new_y == y_sub:
                        break
                    x_sub = new_x
                    y_sub = new_y
            else:
                x_sub = x_expr
                y_sub = y_expr
            # Build Z3 formulas with opaque-FuncCall fallback.
            type_map = GetTypeMapVisitor(stmt).visit(self.ast)
            visitor = Z3FormulaVisitor(
                type_map + (self.ctx.proof_let_types or NameTypeMap()),
                variable_version_map={},
                opaque_func_call_fallback=True,
            )
            p_formula = visitor.visit(p_expr)
            x_formula = visitor.visit(x_sub)
            y_formula = visitor.visit(y_sub)
            if (
                p_formula is None
                or x_formula is None
                or y_formula is None
                or isinstance(p_formula, str)
                or isinstance(x_formula, str)
                or isinstance(y_formula, str)
            ):
                continue
            try:
                solver = z3.Solver()
                solver.set("timeout", 30000)
                # Check Not(P => (X == Y)) is UNSAT, i.e., P AND X != Y is UNSAT.
                solver.add(z3.And(p_formula, x_formula != y_formula))
                if solver.check() != z3.unsat:
                    continue
            except (z3.Z3Exception, TypeError):
                continue
            # Fold: drop the if-statement entirely, keep the trailing return.
            new_stmts = list(block.statements[:index]) + list(
                block.statements[index + 1 :]
            )
            return self.transform_block(frog_ast.Block(new_stmts))
        return block


def _flatten_top_level_and(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """Flatten a left-associated ``A && B && C`` chain into [A, B, C]."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.AND
    ):
        return _flatten_top_level_and(expr.left_expression) + _flatten_top_level_and(
            expr.right_expression
        )
    return [expr]


class ElseUnwrapTransformer(BlockTransformer):
    """Unwraps else blocks when the if-branch unconditionally returns.

    Converts::

        if (C) { ...; return X; } else { S1; S2; }

    into::

        if (C) { ...; return X; }
        S1;
        S2;

    This recovers the ``if-return-then-rest`` pattern used in canonical forms.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                continue
            # Only single-condition if-else (no else-if chains)
            if len(statement.conditions) != 1:
                continue
            if not statement.has_else_block():
                continue
            # True branch must unconditionally return
            if not block_unconditionally_returns(statement.blocks[0]):
                continue

            # Remove the else block, splice its statements after the if
            else_block = statement.blocks[1]
            new_if = frog_ast.IfStatement(
                list(statement.conditions), [statement.blocks[0]]
            )
            return self.transform_block(
                frog_ast.Block(
                    list(block.statements[:index])
                    + [new_if]
                    + list(else_block.statements)
                    + list(block.statements[index + 1 :])
                )
            )
        return block


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class IfConditionAliasSubstitution(TransformPass):
    name = "If Condition Alias Substitution"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return IfConditionAliasSubstitutionTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class RedundantConditionalReturn(TransformPass):
    name = "Redundant Conditional Return"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RedundantConditionalReturnTransformer().transform(game)


class AbsorbRedundantEarlyReturn(TransformPass):
    name = "Absorb Redundant Early Return"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return AbsorbRedundantEarlyReturnTransformer().transform(game)


class IfFalseReturnToConjunction(TransformPass):
    name = "If False Return To Conjunction"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return IfFalseReturnToConjunctionTransformer(ctx).transform(game)


class FoldEquivalentReturnBranch(TransformPass):
    name = "Fold Equivalent Return Branch"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return FoldEquivalentReturnBranchTransformer(ctx, game).transform(game)


class BranchElimination(TransformPass):
    name = "Branch Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return BranchEliminiationTransformer(ctx).transform(game)


class ElseUnwrap(TransformPass):
    name = "Else Unwrap"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ElseUnwrapTransformer().transform(game)


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
