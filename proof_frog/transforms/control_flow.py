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
