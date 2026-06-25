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
    Visitor,
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


class UniqExclusionBranchEliminationTransformer(BlockTransformer):
    """Simplifies ``==`` / ``!=`` expressions whose result follows from
    ``<-uniq[S]`` constraints.

    For ``v <-uniq[S] T;`` in scope, every element of ``S`` is guaranteed
    distinct from ``v`` by FrogLang's exclusion-sampling semantics.  When a
    later expression contains ``v == s`` or ``s == v`` for some ``s`` that
    is structurally equal to an element of ``S`` (or, by transitivity,
    ``s <-uniq[S']`` with ``v`` lexically in ``S'``), the comparison is
    statically ``false``; ``v != s`` is statically ``true``.  This transform
    rewrites those subexpressions to the corresponding Boolean literal so
    that downstream passes (``BooleanIdentity``, ``BranchElimination``)
    fold the surrounding control flow.

    Constraint scope is **block-local**: tracking does not cross method
    boundaries or follow constraints into nested blocks (the transform
    recurses into nested blocks via the standard ``BlockTransformer``
    walk, but each block restarts its own constraint map).  A constraint
    is invalidated as soon as either side (the sampled variable, or any
    name appearing in its exclusion-set elements) is reassigned in the
    same block.

    Soundness: ``<-uniq[S]`` semantics guarantee ``v not in S`` at sample
    time; if neither ``v`` nor any free variable of an ``S`` element has
    been mutated since, the structural equality ``v == s`` is provably
    ``false``.  This is the same reasoning that justifies
    ``FreshInputRFToUniform`` (see TRANSFORMS.md).
    """

    @staticmethod
    def _free_variable_names(expr: frog_ast.Expression) -> set[str]:
        """Return the names of every ``Variable`` node free in *expr*.

        Used to detect when a name appearing in an exclusion-set element
        has been reassigned, which invalidates the constraint.
        """
        names: set[str] = set()

        def _collect(node: frog_ast.ASTNode) -> bool:
            if isinstance(node, frog_ast.Variable):
                names.add(node.name)
            return False

        SearchVisitor(_collect).visit(expr)
        return names

    @classmethod
    def _exclusion_elements(
        cls, unique_set: frog_ast.Expression
    ) -> tuple[list[frog_ast.Expression], set[str]] | None:
        """Extract the list of exclusion elements from a ``<-uniq[S]`` set.

        Currently handles literal sets ``{a, b, ...}``.  Returns the list
        of elements together with the union of their free-variable names
        (used for invalidation tracking).  Returns ``None`` if the set is
        not a literal.
        """
        if not isinstance(unique_set, frog_ast.Set):
            return None
        all_free: set[str] = set()
        for el in unique_set.elements:
            all_free |= cls._free_variable_names(el)
        return list(unique_set.elements), all_free

    @staticmethod
    def _written_var_names(stmt: frog_ast.Statement) -> set[str]:
        """Return the set of variable names written anywhere inside *stmt*.

        Used to invalidate constraints when a tracked variable (or a
        free variable of its exclusion-set elements) is reassigned.

        Walks the full statement, so writes nested in if/for branches
        count, and resolves element writes (``M[k] = v``) and slice
        writes through ``ArrayAccess``/``Slice`` layers to the backing
        variable. Invalidation happens before the statement's conditions
        are rewritten, so an if-statement writing a tracked variable in
        its own branch conservatively forgoes the fold of its own
        condition.
        """
        names: set[str] = set()

        def _collect(node: frog_ast.ASTNode) -> bool:
            if isinstance(
                node, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ):
                target: frog_ast.ASTNode = node.var
                while isinstance(target, (frog_ast.ArrayAccess, frog_ast.Slice)):
                    target = target.the_array
                if isinstance(target, frog_ast.Variable):
                    names.add(target.name)
            return False

        SearchVisitor(_collect).visit(stmt)
        return names

    def _try_simplify_eq(
        self,
        operator: frog_ast.BinaryOperators,
        left: frog_ast.Expression,
        right: frog_ast.Expression,
        constraints: dict[str, list[frog_ast.Expression]],
    ) -> frog_ast.Expression | None:
        """Return a Boolean literal if (left op right) follows from a
        ``<-uniq`` constraint; ``None`` otherwise.
        """
        if operator not in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            return None

        # Try left as the sampled var, right as a candidate exclusion element
        # (and symmetric).
        for sampled, candidate in ((left, right), (right, left)):
            if not isinstance(sampled, frog_ast.Variable):
                continue
            elems = constraints.get(sampled.name)
            if elems is None:
                continue
            for el in elems:
                if el == candidate:
                    if operator == frog_ast.BinaryOperators.EQUALS:
                        return frog_ast.Boolean(False)
                    return frog_ast.Boolean(True)
        return None

    def _rewrite_expr(
        self,
        expr: frog_ast.Expression,
        constraints: dict[str, list[frog_ast.Expression]],
    ) -> frog_ast.Expression:
        """Recursively rewrite ``==``/``!=`` subexpressions whose result is
        determined by a ``<-uniq`` constraint, leaving everything else
        unchanged.  Constraints do NOT propagate into nested blocks here
        (those are handled by the BlockTransformer recursion).
        """
        if isinstance(expr, frog_ast.BinaryOperation):
            new_left = self._rewrite_expr(expr.left_expression, constraints)
            new_right = self._rewrite_expr(expr.right_expression, constraints)
            simplified = self._try_simplify_eq(
                expr.operator, new_left, new_right, constraints
            )
            if simplified is not None:
                return simplified
            if (
                new_left is not expr.left_expression
                or new_right is not expr.right_expression
            ):
                return frog_ast.BinaryOperation(expr.operator, new_left, new_right)
            return expr
        if isinstance(expr, frog_ast.UnaryOperation):
            new_inner = self._rewrite_expr(expr.expression, constraints)
            if new_inner is not expr.expression:
                return frog_ast.UnaryOperation(expr.operator, new_inner)
            return expr
        if isinstance(expr, frog_ast.Tuple):
            new_values = [self._rewrite_expr(v, constraints) for v in expr.values]
            if any(nv is not ov for nv, ov in zip(new_values, expr.values)):
                return frog_ast.Tuple(new_values)
            return expr
        if isinstance(expr, frog_ast.FuncCall):
            new_args = [self._rewrite_expr(a, constraints) for a in expr.args]
            if any(na is not oa for na, oa in zip(new_args, expr.args)):
                return frog_ast.FuncCall(expr.func, new_args)
            return expr
        if isinstance(expr, frog_ast.ArrayAccess):
            new_arr = self._rewrite_expr(expr.the_array, constraints)
            new_idx = self._rewrite_expr(expr.index, constraints)
            if new_arr is not expr.the_array or new_idx is not expr.index:
                return frog_ast.ArrayAccess(new_arr, new_idx)
            return expr
        if isinstance(expr, frog_ast.Slice):
            new_arr = self._rewrite_expr(expr.the_array, constraints)
            new_start = self._rewrite_expr(expr.start, constraints)
            new_end = self._rewrite_expr(expr.end, constraints)
            if (
                new_arr is not expr.the_array
                or new_start is not expr.start
                or new_end is not expr.end
            ):
                return frog_ast.Slice(new_arr, new_start, new_end)
            return expr
        return expr

    def _transform_block_wrapper(
        self,
        block: frog_ast.Block,
    ) -> frog_ast.Block:
        # var_name -> exclusion elements (list of Expressions)
        constraints: dict[str, list[frog_ast.Expression]] = {}
        # var_name -> set of free-variable names whose mutation invalidates
        # the constraint
        invalidators: dict[str, set[str]] = {}
        new_stmts: list[frog_ast.Statement] = []
        changed = False
        for stmt in block.statements:
            written = self._written_var_names(stmt)
            # Invalidate any constraint whose sampled var or free-variable
            # of an exclusion element was reassigned BEFORE this statement
            # rewrites its expressions (so a self-shadowing reassignment
            # invalidates first, then we may add a new constraint).
            if written:
                to_drop = []
                for var_name, free_set in invalidators.items():
                    if var_name in written or (free_set & written):
                        to_drop.append(var_name)
                for v in to_drop:
                    constraints.pop(v, None)
                    invalidators.pop(v, None)

            if isinstance(stmt, frog_ast.IfStatement):
                new_conditions = [
                    self._rewrite_expr(c, constraints) for c in stmt.conditions
                ]
                if new_conditions != stmt.conditions:
                    changed = True
                    new_stmts.append(frog_ast.IfStatement(new_conditions, stmt.blocks))
                else:
                    new_stmts.append(stmt)
            elif isinstance(stmt, frog_ast.UniqueSample) and isinstance(
                stmt.var, frog_ast.Variable
            ):
                extracted = self._exclusion_elements(stmt.unique_set)
                if extracted is not None:
                    elems, free_vars = extracted
                    if elems:
                        constraints[stmt.var.name] = elems
                        invalidators[stmt.var.name] = free_vars
                new_stmts.append(stmt)
            else:
                # Apply the rewrite to other statement-level expressions, e.g.,
                # Assignment RHS, Return, Sample sampled_from, FuncCall args.
                # Done conservatively to avoid touching non-condition contexts
                # in this pass; ``BranchElimination`` only consumes conditions.
                # For simplicity (and to keep the soundness story narrow) we
                # leave non-condition expressions untouched here.
                new_stmts.append(stmt)

        if not changed:
            return block
        return frog_ast.Block(new_stmts)


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


class GuardConditionSimplificationTransformer(Transformer):
    """Replaces an if-condition by its known truth value inside its branches.

    Within ``if (C) { then } else { els }``, ``C`` holds throughout ``then``
    and is false throughout ``els`` (when ``C`` is deterministic and none of
    its variables are reassigned in the branch). So occurrences of ``C`` are
    replaced by ``true`` in ``then`` and by ``false`` in ``els``, after which
    boolean-identity / branch-elimination passes finish the simplification.

    Example::

        if (c in S) { v = c in S; } else { v = c in S && w; }
      becomes:
        if (c in S) { v = true; } else { v = false && w; }   (-> v = false)

    This collapses redundant re-tests of a membership/boolean guard -- e.g.
    when a reduction gates an oracle call on a set membership that the
    oracle itself also checks.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _is_deterministic(self, expr: frog_ast.Expression) -> bool:
        namespace = self.ctx.proof_namespace if self.ctx else {}
        let_types = self.ctx.proof_let_types if self.ctx else None
        return not has_nondeterministic_call(expr, namespace, let_types)

    @staticmethod
    def _reassigns_any(names: set[str], block: frog_ast.Block) -> bool:
        def writes(node: frog_ast.ASTNode) -> bool:
            return (
                isinstance(
                    node,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and isinstance(node.var, frog_ast.Variable)
                and node.var.name in names
            )

        return SearchVisitor(writes).visit(block) is not None

    def _substitute(
        self, block: frog_ast.Block, cond: frog_ast.Expression, value: bool
    ) -> frog_ast.Block:
        replace_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
        replace_map.set(copy.deepcopy(cond), frog_ast.Boolean(value))
        return SubstitutionTransformer(replace_map).transform(block)

    def transform_if_statement(
        self, if_statement: frog_ast.IfStatement
    ) -> frog_ast.IfStatement:
        new_blocks = list(if_statement.blocks)
        if len(if_statement.conditions) == 1:
            cond = if_statement.conditions[0]
            if self._is_deterministic(cond) and not isinstance(cond, frog_ast.Boolean):
                cond_vars = {v.name for v in VariableCollectionVisitor().visit(cond)}
                if not self._reassigns_any(cond_vars, new_blocks[0]):
                    new_blocks[0] = self._substitute(new_blocks[0], cond, True)
                if if_statement.has_else_block() and not self._reassigns_any(
                    cond_vars, new_blocks[1]
                ):
                    new_blocks[1] = self._substitute(new_blocks[1], cond, False)
        # Recurse into the (possibly substituted) children.
        return frog_ast.IfStatement(
            [self.transform(c) for c in if_statement.conditions],
            [self.transform(b) for b in new_blocks],
        )


class IfToBooleanAssignmentTransformer(BlockTransformer):
    """Collapses an if/else that assigns a boolean literal to one variable.

    ::

        if (C) { x = true; } else { x = false; }   ->   x = C;
        if (C) { x = false; } else { x = true; }   ->   x = !C;

    This turns a control-flow encoding of a boolean back into a plain
    assignment, so downstream passes (e.g. IfSplitBranchAssignment) can treat
    the branch as ending in a direct assignment.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                continue
            if len(statement.conditions) != 1 or len(statement.blocks) != 2:
                continue
            if not statement.has_else_block():
                continue
            then_block, else_block = statement.blocks
            if len(then_block.statements) != 1 or len(else_block.statements) != 1:
                continue
            then_stmt = then_block.statements[0]
            else_stmt = else_block.statements[0]
            if not (
                isinstance(then_stmt, frog_ast.Assignment)
                and isinstance(else_stmt, frog_ast.Assignment)
                and isinstance(then_stmt.var, frog_ast.Variable)
                and isinstance(else_stmt.var, frog_ast.Variable)
                and then_stmt.var.name == else_stmt.var.name
                and isinstance(then_stmt.value, frog_ast.Boolean)
                and isinstance(else_stmt.value, frog_ast.Boolean)
                and then_stmt.value.bool != else_stmt.value.bool
            ):
                continue
            cond = statement.conditions[0]
            value: frog_ast.Expression = (
                copy.deepcopy(cond) if then_stmt.value.bool else _negate_condition(cond)
            )
            new_assign = frog_ast.Assignment(
                then_stmt.the_type or else_stmt.the_type,
                frog_ast.Variable(then_stmt.var.name),
                value,
            )
            return self.transform_block(
                frog_ast.Block(
                    list(block.statements[:index])
                    + [new_assign]
                    + list(block.statements[index + 1 :])
                )
            )
        return block


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
        # Any statement following an unconditional top-level return is
        # unreachable. Truncating here keeps blocks well-formed when an
        # earlier pass flattens an if/else whose branches return into a
        # straight-line sequence with a trailing dead return (e.g. the
        # topological sort emitting `return a; return b;`).
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.ReturnStatement) and index + 1 < len(
                block.statements
            ):
                return frog_ast.Block(block.statements[: index + 1])

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
                    try:
                        dead_solver = z3.Solver()
                        dead_solver.set("timeout", 30000)
                        dead_constraints = list(path_constraints)
                        if formula_so_far is not None:
                            dead_constraints.append(z3.Not(formula_so_far))
                        dead_constraints.append(cond_formula)
                        dead_solver.add(z3.And(*dead_constraints))
                        check_result = dead_solver.check()
                    except (z3.Z3Exception, TypeError):
                        # Defense-in-depth: if the formula visitor yields an
                        # ill-sorted term for some condition (so z3.And raises
                        # a sort mismatch / boolean-conversion error), treat it
                        # as "cannot prove dead" and keep the branch -- the
                        # conservative, sound choice. Mirrors the guards at the
                        # two sibling z3 call sites in this file.
                        all_conditions_dead = False
                        break
                    if check_result != z3.unsat:
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

            # alias_pairs: each (field_variable, replacement_expression) means
            # the field equals the replacement within this branch, so the
            # field may be rewritten to the replacement there. Covers both
            # `local == field` (single field) and `param == [f0, ..., fn]`
            # (a tuple of fields equal to a param, yielding f_i -> param[i]).
            alias_pairs = self._alias_substitutions(condition)
            if not alias_pairs:
                continue

            new_branch = copy.deepcopy(statement.blocks[0])
            field_var_names = {f.name for f, _ in alias_pairs}

            # Phase 1: Inline single-assignment fields whose definitions
            # mention any comparison field.
            for dep_field, dep_expr in self.field_definitions.items():
                dep_vars = VariableCollectionVisitor().visit(dep_expr)
                if not any(v.name in field_var_names for v in dep_vars):
                    continue
                inline_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                inline_map.set(frog_ast.Variable(dep_field), copy.deepcopy(dep_expr))
                new_branch = SubstitutionTransformer(inline_map).transform(new_branch)

            # Phase 2: Substitute each comparison field with its replacement.
            # Stop at the first reassignment of any comparison field within the
            # branch, since after reassignment the field value may differ from
            # the replacement.
            alias_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
            for field_expr, replacement in alias_pairs:
                alias_map.set(field_expr, replacement)
            new_stmts: list[frog_ast.Statement] = []
            for stmt_idx, branch_stmt in enumerate(new_branch.statements):
                # Check if this statement reassigns one of the comparison fields
                if (
                    isinstance(
                        branch_stmt,
                        (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                    )
                    and isinstance(branch_stmt.var, frog_ast.Variable)
                    and branch_stmt.var.name in field_var_names
                ):
                    # Stop substituting: keep this and all remaining as-is
                    new_stmts.extend(new_branch.statements[stmt_idx:])
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

    def _alias_substitutions(
        self, condition: frog_ast.BinaryOperation
    ) -> list[tuple[frog_ast.Variable, frog_ast.Expression]]:
        """Return field -> replacement substitutions implied by an equality
        guard, valid within the (then) branch the guard asserts.

        Two shapes qualify:

        * ``local == field`` -> ``[(field, local)]`` (the original behaviour).
        * ``param == [f0, ..., fn]`` where ``param`` is a local/parameter
          variable and every ``f_i`` is a field -> ``[(f_i, param[i]), ...]``.
          This arises after a field whose value is a tuple (e.g. a public key
          ``pkS = [.., ..]``) is expanded to its literal, turning a
          ``pk == pkS`` guard into ``pk == [f0, f1]``; rewriting ``f_i`` to
          ``param[i]`` inside the branch brings it into the same form as the
          fall-through, letting the redundant branch collapse.
        """
        left = condition.left_expression
        right = condition.right_expression

        local_expr, field_expr = self._classify_alias_pair(left, right)
        if local_expr is not None and field_expr is not None:
            assert isinstance(field_expr, frog_ast.Variable)
            return [(field_expr, local_expr)]

        tuple_pairs = self._classify_tuple_alias(
            left, right
        ) or self._classify_tuple_alias(right, left)
        return tuple_pairs or []

    def _classify_tuple_alias(
        self,
        maybe_param: frog_ast.Expression,
        maybe_tuple: frog_ast.Expression,
    ) -> list[tuple[frog_ast.Variable, frog_ast.Expression]] | None:
        """Return ``[(f_i, param[i]), ...]`` when *maybe_param* is a plain
        local/parameter variable and *maybe_tuple* is a tuple literal whose
        every element is a field variable; otherwise None."""
        if not (
            isinstance(maybe_param, frog_ast.Variable)
            and maybe_param.name not in self.field_names
        ):
            return None
        if not isinstance(maybe_tuple, frog_ast.Tuple) or not maybe_tuple.values:
            return None
        if not all(self._is_field(v) for v in maybe_tuple.values):
            return None
        pairs: list[tuple[frog_ast.Variable, frog_ast.Expression]] = []
        for i, element in enumerate(maybe_tuple.values):
            assert isinstance(element, frog_ast.Variable)
            pairs.append(
                (
                    element,
                    frog_ast.ArrayAccess(
                        copy.deepcopy(maybe_param), frog_ast.Integer(i)
                    ),
                )
            )
        return pairs

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
    """Removes an if-without-else whose body duplicates the fall-through.

    Detects the pattern::

        if (cond) { B }     // B returns on every path
        B                   // the same statements B follow immediately

    and simplifies it to just ``B``, since the guard is redundant: when
    ``cond`` holds the body ``B`` runs and returns; when it does not, the
    identical fall-through ``B`` runs and returns. The simplest instance is
    ``if (cond) { return X; } return X;`` (a single-statement body), but the
    body may be any block that unconditionally returns -- e.g.::

        if (pk == pkS) { if (Verify(..)) return ss; return None; }
        if (Verify(..)) return ss;
        return None;

    collapses to ``if (Verify(..)) return ss; return None;``. (This arises
    after IfConditionAliasSubstitution rewrites a redundant case-split branch
    into the same form as its fall-through.)
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
            # The body must return on every path; otherwise control would
            # fall through to the statements after the if and run them in
            # addition to the body, so the guard would not be redundant.
            if not block_unconditionally_returns(if_body):
                continue
            # The statements immediately following the if must match the body
            # exactly. (Anything after that copy is dead, since the body
            # unconditionally returns, and is cleaned up by dead-code passes.)
            body_len = len(if_body.statements)
            following = block.statements[index + 1 : index + 1 + body_len]
            if list(if_body.statements) != list(following):
                continue
            # Drop the if; the identical fall-through copy remains.
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
            # ``ASTMap.set`` is last-write-wins, so we put init_field_rhs
            # first and sub_pairs last: where both cover the same field
            # (e.g. P asserts ``field_a == field_b`` while init also
            # rewrites ``field_b`` to a hoisted-call RHS), the equality
            # from P takes priority. This keeps P's connection between
            # field atoms intact in Z3 — overriding with the hoisted-call
            # RHS would replace one side of the equality with a structure
            # Z3 cannot relate to the other side's atom.
            all_sub_pairs: list[tuple[frog_ast.Expression, frog_ast.Expression]] = list(
                self._init_field_rhs
            ) + list(sub_pairs)
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


class FactorCommonGuardTransformer(BlockTransformer):
    """Transpose a P-first nested-if into V-first by factoring a shared inner
    guard out of an outer guard's arm and the fall-through.

    Recognizes (the outer ``if (P)`` has no else and returns on every path)::

        if (P) {
            if (V) { A }     // A returns on every path
            RET              // RET returns; the V-false case under P
        }
        if (V) { B }         // SAME condition V; B returns on every path
        RET                  // identical trailing RET; the V-false case under !P

    and rewrites it::

        if (V) {
            if (P) { A } else { B }
        }
        RET

    Every ``(P, V)`` combination yields the same result in both forms, so this
    is semantics-preserving. Its purpose is canonical normalization: a
    reduction Decaps that delegates verification to a challenger only for the
    challenge key produces a P-first nesting, whereas the corresponding game
    Decaps is V-first; collapsing both to the V-outer shape lets equivalent
    games match.

    Guard: ``P`` must contain no non-deterministic call. The transpose
    evaluates ``P`` only when ``V`` holds (instead of always), so a
    side-effecting / non-deterministic ``P`` could change behavior. ``V`` is
    evaluated exactly once in both forms, so it is unrestricted.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _is_deterministic(self, expr: frog_ast.Expression) -> bool:
        namespace = self.ctx.proof_namespace if self.ctx else {}
        let_types = self.ctx.proof_let_types if self.ctx else None
        return not has_nondeterministic_call(expr, namespace, let_types)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        stmts = block.statements
        for index in range(len(stmts) - 1):
            outer = stmts[index]
            if not isinstance(outer, frog_ast.IfStatement):
                continue
            if outer.has_else_block() or len(outer.conditions) != 1:
                continue
            outer_body = outer.blocks[0]
            if len(outer_body.statements) < 2:
                continue
            if not block_unconditionally_returns(outer_body):
                continue
            inner = outer_body.statements[0]
            if not isinstance(inner, frog_ast.IfStatement):
                continue
            if inner.has_else_block() or len(inner.conditions) != 1:
                continue
            if not block_unconditionally_returns(inner.blocks[0]):
                continue
            tail_p = list(outer_body.statements[1:])

            fall = stmts[index + 1]
            if not isinstance(fall, frog_ast.IfStatement):
                continue
            if fall.has_else_block() or len(fall.conditions) != 1:
                continue
            if fall.conditions[0] != inner.conditions[0]:
                continue
            if not block_unconditionally_returns(fall.blocks[0]):
                continue
            tail_fall = list(stmts[index + 2 :])
            # The V-false behavior must be identical whether or not P holds.
            if tail_p != tail_fall:
                continue

            p_cond = outer.conditions[0]
            v_cond = inner.conditions[0]
            if not self._is_deterministic(p_cond):
                continue

            new_inner = frog_ast.IfStatement(
                [copy.deepcopy(p_cond)],
                [
                    copy.deepcopy(inner.blocks[0]),
                    copy.deepcopy(fall.blocks[0]),
                ],
            )
            new_if = frog_ast.IfStatement(
                [copy.deepcopy(v_cond)], [frog_ast.Block([new_inner])]
            )
            return self.transform_block(
                frog_ast.Block(list(stmts[:index]) + [new_if] + tail_p)
            )
        return block


class MergeNestedGuardTransformer(BlockTransformer):
    """Merge a nested guard whose only effect is an inner early return.

    Recognizes (the outer ``if (P)`` has no else and returns on every path)::

        if (P) {
            if (Q) { BODY }   // BODY returns on every path
            TAIL              // the !Q case under P; returns on every path
        }
        TAIL                  // identical trailing TAIL; the !P case

    and rewrites it::

        if (P && Q) { BODY }
        TAIL

    Sound because every ``(P, Q)`` case yields the same result: ``P and Q``
    -> BODY; ``P and not Q`` -> TAIL; ``not P`` -> TAIL. This collapses the
    P-first nesting left behind once ``FactorCommonGuard`` has hoisted the
    shared verification guard, matching the conjunction guard written
    directly in the corresponding game (e.g. ``if (pk == pkS && c notin C)``).

    Guard: ``P`` and ``Q`` must contain no non-deterministic call, since the
    rewrite evaluates them as ``P && Q`` rather than as separate nested
    conditions.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _is_deterministic(self, expr: frog_ast.Expression) -> bool:
        namespace = self.ctx.proof_namespace if self.ctx else {}
        let_types = self.ctx.proof_let_types if self.ctx else None
        return not has_nondeterministic_call(expr, namespace, let_types)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        stmts = block.statements
        for index in range(len(stmts) - 1):
            outer = stmts[index]
            if not isinstance(outer, frog_ast.IfStatement):
                continue
            if outer.has_else_block() or len(outer.conditions) != 1:
                continue
            outer_body = outer.blocks[0]
            if len(outer_body.statements) < 2:
                continue
            if not block_unconditionally_returns(outer_body):
                continue
            inner = outer_body.statements[0]
            if not isinstance(inner, frog_ast.IfStatement):
                continue
            if inner.has_else_block() or len(inner.conditions) != 1:
                continue
            if not block_unconditionally_returns(inner.blocks[0]):
                continue
            tail_p = list(outer_body.statements[1:])
            tail_fall = list(stmts[index + 1 :])
            if not tail_p or tail_p != tail_fall:
                continue

            p_cond = outer.conditions[0]
            q_cond = inner.conditions[0]
            if not (self._is_deterministic(p_cond) and self._is_deterministic(q_cond)):
                continue

            merged_cond = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.AND,
                copy.deepcopy(p_cond),
                copy.deepcopy(q_cond),
            )
            new_if = frog_ast.IfStatement(
                [merged_cond], [copy.deepcopy(inner.blocks[0])]
            )
            return self.transform_block(
                frog_ast.Block(list(stmts[:index]) + [new_if] + tail_p)
            )
        return block


def _iter_block_nodes(block: frog_ast.Block) -> list[frog_ast.ASTNode]:
    """Return every AST node in *block* (the block and all descendants)."""
    nodes: list[frog_ast.ASTNode] = []

    class _Collector(Visitor[None]):
        def result(self) -> None:
            return None

        def leave_ast_node(self, node: frog_ast.ASTNode) -> None:
            nodes.append(node)

    _Collector().visit(block)
    return nodes


def _condition_literal(cond: frog_ast.Expression, holds: bool) -> tuple[str, bool]:
    """Normalize a known-true/known-false condition to a ``(base, polarity)``
    literal. ``!(X)`` flips the polarity, so ``X`` known-false and ``!(X)``
    known-true both yield ``(str(X), False)``. Used to compare path facts
    against the conjuncts of a guard."""
    base: frog_ast.Expression = cond
    polarity = holds
    while (
        isinstance(base, frog_ast.UnaryOperation)
        and base.operator == frog_ast.UnaryOperators.NOT
    ):
        base = base.expression
        polarity = not polarity
    return (str(base), polarity)


class DeadGuardedAssignmentEliminationTransformer(BlockTransformer):
    """Kills a boolean assignment whose value cannot be observed.

    When a block has the shape::

        ... assignments to v ...
        if (v) { if (G) { return R }; ... }
        return R                       // same R as the inner guarded return

    then on any path where ``G`` holds the result is ``R`` regardless of
    ``v``: if ``v`` is true the inner guard returns ``R``; if ``v`` is false
    the fall-through returns ``R``. So an assignment ``v = E`` reached only
    under path conditions that entail ``G`` is a dead store -- its value is
    replaced by ``false`` (enabling boolean simplification / IfToBoolean).

    This is the backward-dead-store counterpart to the forward guard
    reasoning the other passes do; it arises when a reduction's membership
    rejection (``if (pk == pkS && c notin C) ...``) dominates a real-
    verification call that the simulated game performs only on recorded
    ciphertexts.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            use = self._match_guarded_use(statement, block.statements[index + 1 :])
            if use is None:
                continue
            v_name, guard = use
            # Soundness: the assignment's value may only be killed if `v` is
            # read solely by the matched `if (v)` guard. Any other read of `v`
            # would observe the rewritten `false` value. Count reads (variable
            # occurrences that are not an assignment target); exactly one --
            # the guard condition -- is required.
            if self._read_count(block, v_name) != 1:
                continue
            guard_lits = [
                _condition_literal(g, True) for g in _flatten_top_level_and(guard)
            ]
            prefix = list(block.statements[:index])
            new_prefix = [self._kill(s, v_name, guard_lits, []) for s in prefix]
            if new_prefix != prefix:
                return self.transform_block(
                    frog_ast.Block(new_prefix + list(block.statements[index:]))
                )
        return block

    @staticmethod
    def _read_count(block: frog_ast.Block, name: str) -> int:
        """Number of read occurrences of *name* (Variable nodes that are not
        the assignment/sample target)."""
        total = 0
        writes = 0
        for node in _iter_block_nodes(block):
            if isinstance(node, frog_ast.Variable) and node.name == name:
                total += 1
            if (
                isinstance(
                    node,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                )
                and isinstance(node.var, frog_ast.Variable)
                and node.var.name == name
            ):
                writes += 1
        return total - writes

    @staticmethod
    def _match_guarded_use(
        statement: frog_ast.Statement,
        rest: Sequence[frog_ast.Statement],
    ) -> tuple[str, frog_ast.Expression] | None:
        if (
            not isinstance(statement, frog_ast.IfStatement)
            or statement.has_else_block()
            or len(statement.conditions) != 1
        ):
            return None
        guard_var = statement.conditions[0]
        if not isinstance(guard_var, frog_ast.Variable):
            return None
        body = statement.blocks[0]
        if not body.statements:
            return None
        inner = body.statements[0]
        if (
            not isinstance(inner, frog_ast.IfStatement)
            or inner.has_else_block()
            or len(inner.conditions) != 1
            or len(inner.blocks[0].statements) != 1
        ):
            return None
        inner_return = inner.blocks[0].statements[0]
        if not isinstance(inner_return, frog_ast.ReturnStatement):
            return None
        # The fall-through must be exactly `return R` with the same R.
        if len(rest) != 1 or not isinstance(rest[0], frog_ast.ReturnStatement):
            return None
        if rest[0].expression != inner_return.expression:
            return None
        return (guard_var.name, inner.conditions[0])

    def _kill(
        self,
        statement: frog_ast.Statement,
        var_name: str,
        guard_lits: list[tuple[str, bool]],
        path: list[tuple[str, bool]],
    ) -> frog_ast.Statement:
        if (
            isinstance(statement, frog_ast.Assignment)
            and isinstance(statement.var, frog_ast.Variable)
            and statement.var.name == var_name
            and not isinstance(statement.value, frog_ast.Boolean)
            and all(lit in path for lit in guard_lits)
        ):
            return frog_ast.Assignment(
                statement.the_type, statement.var, frog_ast.Boolean(False)
            )
        if isinstance(statement, frog_ast.IfStatement):
            new_blocks: list[frog_ast.Block] = []
            for block_index, branch in enumerate(statement.blocks):
                branch_path = list(path)
                if block_index < len(statement.conditions):
                    for prior in range(block_index):
                        branch_path.append(
                            _condition_literal(statement.conditions[prior], False)
                        )
                    branch_path.append(
                        _condition_literal(statement.conditions[block_index], True)
                    )
                else:
                    for cond in statement.conditions:
                        branch_path.append(_condition_literal(cond, False))
                new_blocks.append(
                    frog_ast.Block(
                        [
                            self._kill(s, var_name, guard_lits, branch_path)
                            for s in branch.statements
                        ]
                    )
                )
            return frog_ast.IfStatement(list(statement.conditions), new_blocks)
        return statement


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


class GuardConditionSimplification(TransformPass):
    name = "Guard Condition Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return GuardConditionSimplificationTransformer(ctx).transform(game)


class IfToBooleanAssignment(TransformPass):
    name = "If To Boolean Assignment"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return IfToBooleanAssignmentTransformer().transform(game)


class RedundantConditionalReturn(TransformPass):
    name = "Redundant Conditional Return"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RedundantConditionalReturnTransformer().transform(game)


class AbsorbRedundantEarlyReturn(TransformPass):
    name = "Absorb Redundant Early Return"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return AbsorbRedundantEarlyReturnTransformer().transform(game)


class FactorCommonGuard(TransformPass):
    name = "Factor Common Guard"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return FactorCommonGuardTransformer(ctx).transform(game)


class MergeNestedGuard(TransformPass):
    name = "Merge Nested Guard"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return MergeNestedGuardTransformer(ctx).transform(game)


class DeadGuardedAssignmentElimination(TransformPass):
    name = "Dead Guarded Assignment Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return DeadGuardedAssignmentEliminationTransformer().transform(game)


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


class UniqExclusionBranchElimination(TransformPass):
    name = "Uniq Exclusion Branch Elimination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return UniqExclusionBranchEliminationTransformer().transform(game)


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
