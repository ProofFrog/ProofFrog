# pylint: disable=duplicate-code
# Counting/search patterns shared with algebraic uniform sampling transformers.
"""Inlining and assignment passes: redundant copy, inline single-use, collapse.

These passes reduce the number of local variables by inlining definitions,
collapsing assignment chains, and eliminating redundant copies, bringing the
AST closer to its minimal canonical form.
"""

from __future__ import annotations

import copy
import functools

from .. import frog_ast
from ..visitors import (
    BlockTransformer,
    SearchVisitor,
    Visitor,
    ReplaceTransformer,
    VariableCollectionVisitor,
)
from ._base import TransformPass, PipelineContext, has_nondeterministic_call


class _VarCountVisitor(Visitor[int]):
    """Count occurrences of a variable name in an AST subtree."""

    def __init__(self, var_name: str) -> None:
        self._name = var_name
        self._count = 0

    def result(self) -> int:
        return self._count

    def leave_variable(self, var: frog_ast.Variable) -> None:
        if var.name == self._name:
            self._count += 1


# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class RedundantCopyTransformer(BlockTransformer):
    """Eliminates redundant variable copies by substituting the original.

    When a typed assignment ``Type v = w`` creates a simple copy and neither
    ``v`` nor ``w`` is reassigned afterward, all uses of ``v`` are replaced
    with ``w`` and the copy assignment is removed.

    Example::

        BitString<n> ct = c;
        return ct;
      becomes:
        return c;
    """

    def _transform_block_wrapper(
        self,
        block: frog_ast.Block,
    ) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            # Potentially, could be a redundant copy
            if (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.value, frog_ast.Variable)
            ):
                copy_name = statement.var.name
                original_name = statement.value.name
            elif (
                isinstance(statement, frog_ast.Sample)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.sampled_from, frog_ast.Variable)
                and any(
                    isinstance(
                        s, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
                    )
                    and isinstance(s.var, frog_ast.Variable)
                    and s.var.name == statement.sampled_from.name
                    for s in block.statements[:index]
                )
            ):
                copy_name = statement.var.name
                original_name = statement.sampled_from.name
            else:
                continue

            # Self-assignment (e.g., r = r after inlining): just remove it
            if copy_name == original_name:
                return self.transform_block(
                    frog_ast.Block(
                        list(block.statements[:index])
                        + list(block.statements[index + 1 :])
                    )
                )

            def written_to(copy_name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(
                        node,
                        (
                            frog_ast.Sample,
                            frog_ast.Assignment,
                            frog_ast.UniqueSample,
                        ),
                    )
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == copy_name
                )

            remaining_block = frog_ast.Block(
                copy.deepcopy(block.statements[index + 1 :])
            )
            was_written = SearchVisitor[frog_ast.Variable](
                functools.partial(written_to, copy_name)
            ).visit(remaining_block)
            original_reassigned = SearchVisitor[frog_ast.Variable](
                functools.partial(written_to, original_name)
            ).visit(remaining_block)
            # If the copy was reassigned, or the original was reassigned
            # (making the substitution unsafe), skip.
            if was_written or original_reassigned:
                continue

            def copy_used(copy_name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == copy_name

            while True:
                copy_found = SearchVisitor[frog_ast.Variable](
                    functools.partial(copy_used, copy_name)
                ).visit(remaining_block)
                if copy_found is None:
                    break
                remaining_block = ReplaceTransformer(
                    copy_found, frog_ast.Variable(original_name)
                ).transform(remaining_block)

            return self.transform_block(
                frog_ast.Block(copy.deepcopy(block.statements[:index]))
                + remaining_block
            )
        return block


class InlineSingleUseVariableTransformer(BlockTransformer):
    """Inlines a declaration `Type v = expr` when v is used exactly once in
    subsequent statements and no variable free in expr is modified between
    the declaration and that single use site.

    This is more general than RedundantCopyTransformer, which only handles
    simple variable copies (where expr is a plain Variable).

    Example:
        v3 = v1 + G.evaluate(v2);
        return v3 + mL;
    becomes:
        return v1 + G.evaluate(v2) + mL;
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and not isinstance(statement.value, frog_ast.Variable)
                # Tuple literals are handled by ExpandTupleTransformer; inlining
                # them prematurely breaks that pipeline (e.g. c=[a,b]; return c[0]).
                and not isinstance(statement.value, frog_ast.Tuple)
            ):
                continue

            var_name = statement.var.name
            expr = statement.value

            def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, (frog_ast.Sample, frog_ast.Assignment))
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == name

            remaining_block = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            # Skip if var is reassigned anywhere in remaining
            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    remaining_block
                )
                is not None
            ):
                continue

            # Find the first use of var in remaining_block
            first_use_idx = None
            for i, s in enumerate(remaining_block.statements):
                if (
                    SearchVisitor(functools.partial(uses_var, var_name)).visit(s)
                    is not None
                ):
                    first_use_idx = i
                    break

            if first_use_idx is None:
                continue  # var not used; other transformers will clean it up

            # Count total occurrences of var in remaining_block.
            total_uses = _VarCountVisitor(var_name).visit(remaining_block)

            if total_uses != 1:
                continue

            # Collect free variables in expr and check none are written to
            # between the declaration and the single use site
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(expr))
            intermediate = frog_ast.Block(
                list(remaining_block.statements[:first_use_idx])
            )
            if any(
                SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                    intermediate
                )
                is not None
                for fv in free_vars
            ):
                continue

            # Perform the inlining: replace every occurrence of var in
            # remaining_block with expr (there is exactly one, verified above)
            expr_copy = copy.deepcopy(expr)
            while True:
                var_node = SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    remaining_block
                )
                if var_node is None:
                    break
                remaining_block = ReplaceTransformer(
                    var_node, copy.deepcopy(expr_copy)
                ).transform(remaining_block)

            # Rebuild: remove the declaration, keep the updated remaining block
            new_block = frog_ast.Block(
                list(block.statements[:index]) + list(remaining_block.statements)
            )
            return self.transform_block(new_block)

        return block


class InlineMultiUsePureExpressionTransformer(BlockTransformer):
    """Inlines a declaration ``Type v = expr`` when expr is a deterministic
    (function-call-free, or deterministic-only) expression, even if v is
    used more than once.

    Unlike ``InlineSingleUseVariableTransformer`` (which only inlines
    single-use variables), this pass handles multi-use variables by
    duplicating the expression at each use site.  This is safe because
    the expression contains no non-deterministic function calls and no
    free variable of the expression is reassigned anywhere after the
    declaration.

    This pass normalises the canonical form so that a multi-use pure
    expression is always represented inline rather than via a named
    variable, regardless of whether the source code named it.

    Expressions containing ``ArrayAccess`` or ``Slice`` nodes are excluded
    because inlining them spreads references to the indexed variable,
    which blocks other transforms (XOR simplification, dead code
    elimination, single-use inlining of the base variable).

    Example::

        BitString<N> v = a || b;
        return F(v, v);
      becomes:
        return F(a || b, a || b);
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
                and not isinstance(statement.value, frog_ast.Variable)
                and not isinstance(statement.value, frog_ast.Tuple)
            ):
                continue

            var_name = statement.var.name
            expr = statement.value

            # Skip ALL function calls (even deterministic ones): multi-use
            # inlining duplicates the call at every use site, changing
            # the canonical form.
            if (
                SearchVisitor(lambda n: isinstance(n, frog_ast.FuncCall)).visit(expr)
                is not None
            ):
                continue

            # Skip expressions containing array access or slicing.
            # Inlining these spreads references to the base variable,
            # preventing dead-code elimination and single-use inlining
            # of function-call results, and breaking algebraic patterns.
            if (
                SearchVisitor(
                    lambda n: isinstance(n, (frog_ast.ArrayAccess, frog_ast.Slice))
                ).visit(expr)
                is not None
            ):
                continue

            def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(
                        node,
                        (
                            frog_ast.Sample,
                            frog_ast.Assignment,
                            frog_ast.UniqueSample,
                        ),
                    )
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == name

            remaining_block = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            # Skip if var is reassigned
            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    remaining_block
                )
                is not None
            ):
                continue

            # Skip if var is not used at all
            if (
                SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    remaining_block
                )
                is None
            ):
                continue

            # Skip if any free variable in expr is reassigned
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(expr))
            if any(
                SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                    remaining_block
                )
                is not None
                for fv in free_vars
            ):
                continue

            # Replace all occurrences of var with expr
            expr_copy = copy.deepcopy(expr)
            while True:
                var_node = SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    remaining_block
                )
                if var_node is None:
                    break
                remaining_block = ReplaceTransformer(
                    var_node, copy.deepcopy(expr_copy)
                ).transform(remaining_block)

            new_block = frog_ast.Block(
                list(block.statements[:index]) + list(remaining_block.statements)
            )
            return self.transform_block(new_block)

        return block


class CollapseAssignmentTransformer(BlockTransformer):
    """Collapses a declaration followed by a reassignment into a single statement.

    When a variable is declared and later reassigned without its initial value
    being read, the later value is moved into the original declaration.
    Skips statements whose right-hand side contains non-deterministic function
    calls, which may have side effects.

    Example::

        Type v = expr1;
        v = expr2;
      becomes:
        Type v = expr2;
    """

    def __init__(self, proof_namespace: frog_ast.Namespace | None = None) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, (frog_ast.Assignment, frog_ast.Sample)):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue

            # Skip if the statement's value has non-deterministic calls
            if isinstance(statement, frog_ast.Assignment) and has_nondeterministic_call(
                statement.value, self._proof_namespace
            ):
                continue

            def uses_var(var: frog_ast.Variable, node: frog_ast.ASTNode) -> bool:
                return node == var

            uses_var_partial = functools.partial(uses_var, statement.var)
            for later_index, later_statement in enumerate(
                block.statements[index + 1 :]
            ):
                contains_var = SearchVisitor(uses_var_partial).visit(later_statement)
                if contains_var is None:
                    continue
                if not isinstance(
                    later_statement, (frog_ast.Assignment, frog_ast.Sample)
                ):
                    break
                later_rhs = (
                    later_statement.sampled_from
                    if isinstance(later_statement, frog_ast.Sample)
                    else later_statement.value
                )
                if (
                    contains_var
                    and SearchVisitor(uses_var_partial).visit(later_rhs) is not None
                ):
                    break
                if isinstance(later_statement, frog_ast.Sample):
                    replaced_statement: frog_ast.Statement = frog_ast.Sample(
                        statement.the_type,
                        copy.deepcopy(statement.var),
                        copy.deepcopy(later_rhs),
                    )
                else:
                    replaced_statement = frog_ast.Assignment(
                        statement.the_type,
                        copy.deepcopy(statement.var),
                        copy.deepcopy(later_rhs),
                    )
                return self.transform_block(
                    frog_ast.Block(
                        block.statements[:index]
                        + block.statements[index + 1 : index + later_index + 1]
                        + [replaced_statement]
                        + block.statements[index + later_index + 2 :]
                    )
                )

        return block


class RedundantFieldCopyTransformer(BlockTransformer):
    """Eliminates an intermediate local variable used only to assign to a field.

    When a local is declared, used solely to copy its value into a game field,
    and not referenced elsewhere, the local declaration is replaced by
    assigning directly to the field.

    Example::

        Type v <- Type;
        fieldName = v;
      becomes:
        fieldName <- Type;
    """

    def __init__(self) -> None:
        self.fields: list[str] = []

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if (
                isinstance(statement, frog_ast.Assignment)
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.fields
            ):
                if not isinstance(statement.value, frog_ast.Variable):
                    continue

                def search_for_other_use(
                    var: frog_ast.Variable, node: frog_ast.ASTNode
                ) -> bool:
                    return node == var

                no_other_uses = True
                decl_index = -1
                decl_statement: frog_ast.Assignment | frog_ast.Sample
                for other_index, other_statement in enumerate(block.statements):
                    if statement == other_statement:
                        continue
                    if (
                        isinstance(
                            other_statement, (frog_ast.Sample, frog_ast.Assignment)
                        )
                        and other_statement.the_type is not None
                        and other_statement.var == statement.value
                    ):
                        decl_index = other_index
                        decl_statement = other_statement
                        continue
                    # Check that the local variable being copied has no
                    # other uses besides the field assignment and its
                    # own declaration.  We must check uses of the local
                    # variable (statement.value), not the field
                    # (statement.var), to avoid leaving dangling
                    # references when the local is also used elsewhere.
                    assert isinstance(statement.value, frog_ast.Variable)
                    if (
                        SearchVisitor(
                            functools.partial(search_for_other_use, statement.value)
                        ).visit(other_statement)
                        is not None
                    ):
                        no_other_uses = False
                # decl_index == -1 implies we weren't able to find
                # the declaration of the variable on the RHS of the assignment. This means
                # it is a field, and isn't a redundant copy
                if not no_other_uses or decl_index == -1:
                    continue
                modified_statement = copy.deepcopy(decl_statement)
                modified_statement.var = statement.var
                modified_statement.the_type = None
                return self.transform(
                    frog_ast.Block(
                        list(block.statements[:decl_index])
                        + [modified_statement]
                        + list(block.statements[decl_index + 1 : index])
                        + list(block.statements[index + 1 :])
                    )
                )
        return block


class ForwardExpressionAliasTransformer(BlockTransformer):
    """Replaces repeated pure expressions with their named variable.

    When an assignment ``v = expr`` (typed local or field assignment) defines
    a named alias for a deterministic expression (no non-deterministic function
    calls) that is not a plain variable or tuple literal, subsequent
    structurally-identical occurrences of ``expr`` are replaced with ``v``.

    This is safe because the expression is deterministic and neither ``v``
    nor any free variable in ``expr`` is reassigned between the definition
    and use site.

    Example::

        PK1Space v3 = v1[0];
        ...
        return F(v3, v1[0]);
      becomes:
        PK1Space v3 = v1[0];
        ...
        return F(v3, v3);
    """

    def __init__(self, proof_namespace: frog_ast.Namespace | None = None) -> None:
        self.fields: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            is_typed_decl = (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.var, frog_ast.Variable)
            )
            is_field_assign = (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is None
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.fields
            )
            if not (is_typed_decl or is_field_assign):
                continue
            assert isinstance(statement, frog_ast.Assignment)
            assert isinstance(statement.var, frog_ast.Variable)
            # For field assignments from a variable (field = v or
            # field1 = field2), propagate the source name → field name
            # in subsequent code.
            if is_field_assign and isinstance(statement.value, frog_ast.Variable):
                local_name = statement.value.name
                field_name = statement.var.name
                remaining_block = frog_ast.Block(
                    copy.deepcopy(block.statements[index + 1 :])
                )

                def is_written_to_fv(name: str, node: frog_ast.ASTNode) -> bool:
                    return (
                        isinstance(
                            node,
                            (
                                frog_ast.Sample,
                                frog_ast.Assignment,
                                frog_ast.UniqueSample,
                            ),
                        )
                        and isinstance(node.var, frog_ast.Variable)
                        and node.var.name == name
                    )

                # Only propagate if the local is not reassigned after
                if (
                    SearchVisitor(
                        functools.partial(is_written_to_fv, local_name)
                    ).visit(remaining_block)
                    is not None
                ):
                    continue
                # And the field is not reassigned after
                if (
                    SearchVisitor(
                        functools.partial(is_written_to_fv, field_name)
                    ).visit(remaining_block)
                    is not None
                ):
                    continue

                # Find and replace one occurrence of the local variable
                def matches_local(name: str, node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == name

                match = SearchVisitor(
                    functools.partial(matches_local, local_name)
                ).visit(remaining_block)
                if match is not None:
                    remaining_block = ReplaceTransformer(
                        match, frog_ast.Variable(field_name)
                    ).transform(remaining_block)
                    return self._transform_block_wrapper(
                        frog_ast.Block(
                            copy.deepcopy(block.statements[: index + 1])
                            + list(remaining_block.statements)
                        )
                    )
                continue
            if isinstance(statement.value, (frog_ast.Variable, frog_ast.Tuple)):
                continue

            var_name = statement.var.name
            expr = statement.value

            # Only handle pure expressions (no non-deterministic function calls)
            if has_nondeterministic_call(expr, self._proof_namespace):
                continue

            remaining_block = frog_ast.Block(
                copy.deepcopy(block.statements[index + 1 :])
            )

            def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(
                        node,
                        (
                            frog_ast.Sample,
                            frog_ast.Assignment,
                            frog_ast.UniqueSample,
                        ),
                    )
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            # Skip if var is reassigned
            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    remaining_block
                )
                is not None
            ):
                continue

            # Skip if any free variable in expr is reassigned
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(expr))
            if any(
                SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                    remaining_block
                )
                is not None
                for fv in free_vars
            ):
                continue

            # Find a structurally-equal occurrence of expr in remaining block
            def matches_expr(
                target: frog_ast.Expression, node: frog_ast.ASTNode
            ) -> bool:
                return (
                    isinstance(node, frog_ast.Expression)
                    and type(node) is type(target)
                    and node == target
                )

            match = SearchVisitor(functools.partial(matches_expr, expr)).visit(
                remaining_block
            )
            if match is None:
                continue

            # Replace this one occurrence (by identity) with the variable
            remaining_block = ReplaceTransformer(
                match, frog_ast.Variable(var_name)
            ).transform(remaining_block)

            return self.transform_block(
                frog_ast.Block(
                    copy.deepcopy(block.statements[: index + 1])
                    + list(remaining_block.statements)
                )
            )

        return block


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class RedundantCopy(TransformPass):
    name = "Remove Redundant Copies"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RedundantCopyTransformer().transform(game)


class InlineSingleUseVariable(TransformPass):
    name = "Inline Single-Use Variables"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineSingleUseVariableTransformer().transform(game)


class CollapseAssignment(TransformPass):
    name = "Collapse Assignment"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return CollapseAssignmentTransformer(
            proof_namespace=ctx.proof_namespace
        ).transform(game)


class ForwardExpressionAlias(TransformPass):
    name = "Forward Expression Alias"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ForwardExpressionAliasTransformer(
            proof_namespace=ctx.proof_namespace
        ).transform(game)


class InlineMultiUsePureExpression(TransformPass):
    name = "Inline Multi-Use Pure Expressions"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineMultiUsePureExpressionTransformer().transform(game)


class RedundantFieldCopy(TransformPass):
    name = "Remove redundant variables for fields"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RedundantFieldCopyTransformer().transform(game)


class HoistFieldPureAliasTransformer(BlockTransformer):
    """Hoists field assignments of pure expressions before their first use.

    When a field assignment ``field = pure_expr`` (where pure_expr contains no
    non-deterministic function calls) appears AFTER a statement that uses the
    same ``pure_expr`` as a subexpression, this transform moves the field
    assignment to just before that earlier use and replaces the subexpression
    with the field variable.

    This ensures consistent canonical forms between compositions (where
    the field assignment may be ordered after a function call using the
    same subexpression) and intermediate games (where the field assignment
    naturally precedes the function call).

    Example::

        [SS, CT] v3 = KEM1.Encaps(v1[0]);
        field5 = v1[0];
      becomes:
        field5 = v1[0];
        [SS, CT] v3 = KEM1.Encaps(field5);
    """

    def __init__(self, proof_namespace: frog_ast.Namespace | None = None) -> None:
        self.fields: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.fields = [field.name for field in game.fields]
        new_game = copy.deepcopy(game)
        new_game.methods = [self.transform(method) for method in new_game.methods]
        return new_game

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for i, statement in enumerate(block.statements):
            # Only handle field assignments from pure expressions
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is None
                and isinstance(statement.var, frog_ast.Variable)
                and statement.var.name in self.fields
            ):
                continue
            expr = statement.value
            field_name = statement.var.name
            # Skip tuples, literals, and field-to-field copies
            if isinstance(
                expr,
                (
                    frog_ast.Tuple,
                    frog_ast.Integer,
                    frog_ast.Boolean,
                    frog_ast.NoneExpression,
                    frog_ast.BitStringLiteral,
                ),
            ):
                continue
            # Allow array accesses (original pattern) and local-variable copies
            # (scheme-inlining pattern where a local is copied to a field).
            # Field-to-field copies are skipped to avoid changing canonical forms
            # of games that are already matching.
            if isinstance(expr, frog_ast.Variable):
                if expr.name in self.fields:
                    continue  # field = other_field: skip
                # field = local_var: check it has a typed declaration in this block
                has_typed_decl = any(
                    isinstance(s, (frog_ast.Assignment, frog_ast.Sample))
                    and s.the_type is not None
                    and isinstance(s.var, frog_ast.Variable)
                    and s.var.name == expr.name
                    for s in block.statements[:i]
                )
                if not has_typed_decl:
                    continue  # not a local: skip
            elif not isinstance(expr, frog_ast.ArrayAccess):
                continue
            # Only handle pure expressions (no non-deterministic function calls)
            if has_nondeterministic_call(expr, self._proof_namespace):
                continue

            # Look for a structurally-equal subexpression in earlier statements
            def matches_expr(
                target: frog_ast.Expression, node: frog_ast.ASTNode
            ) -> bool:
                return (
                    isinstance(node, frog_ast.Expression)
                    and type(node) is type(target)
                    and node == target
                )

            for j in range(i):
                earlier = block.statements[j]
                match = SearchVisitor(functools.partial(matches_expr, expr)).visit(
                    earlier
                )
                if match is None:
                    continue

                # Verify the field is not referenced between j and i
                def refs_field(name: str, node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == name

                conflict = False
                for k in range(j, i):
                    if (
                        SearchVisitor(functools.partial(refs_field, field_name)).visit(
                            block.statements[k]
                        )
                        is not None
                    ):
                        conflict = True
                        break
                if conflict:
                    continue
                # Verify free variables of expr are all defined before j
                free_vars = VariableCollectionVisitor().visit(copy.deepcopy(expr))
                all_defined = True
                for fv in free_vars:
                    if fv.name in self.fields:
                        continue
                    # Check that fv is assigned in some statement before j

                    def assigns_var(name: str, node: frog_ast.ASTNode) -> bool:
                        return (
                            isinstance(
                                node,
                                (
                                    frog_ast.Sample,
                                    frog_ast.Assignment,
                                    frog_ast.UniqueSample,
                                ),
                            )
                            and isinstance(node.var, frog_ast.Variable)
                            and node.var.name == name
                        )

                    found_def = False
                    for k in range(j):
                        if (
                            SearchVisitor(
                                functools.partial(assigns_var, fv.name)
                            ).visit(block.statements[k])
                            is not None
                        ):
                            found_def = True
                            break
                    if not found_def:
                        all_defined = False
                        break
                if not all_defined:
                    continue
                # Hoist: move field assignment to before position j,
                # replace the subexpression in position j with the field.
                # Re-find the match in a deep copy (ReplaceTransformer uses
                # identity, so we need a node from the same copy).
                new_earlier = copy.deepcopy(earlier)
                match_in_copy = SearchVisitor(
                    functools.partial(matches_expr, expr)
                ).visit(new_earlier)
                if match_in_copy is None:
                    continue
                new_earlier = ReplaceTransformer(
                    match_in_copy, frog_ast.Variable(field_name)
                ).transform(new_earlier)
                new_stmts = (
                    list(block.statements[:j])
                    + [copy.deepcopy(statement)]
                    + [new_earlier]
                    + list(block.statements[j + 1 : i])
                    + list(block.statements[i + 1 :])
                )
                return self._transform_block_wrapper(frog_ast.Block(new_stmts))
        return block


class HoistFieldPureAlias(TransformPass):
    name = "Hoist Field Pure Alias"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return HoistFieldPureAliasTransformer(
            proof_namespace=ctx.proof_namespace
        ).transform(game)


class InlineSingleUseFieldTransformer(BlockTransformer):
    """Inlines a field assignment ``fieldA = expr`` when fieldA is used exactly
    once across all methods and no free variable in expr is modified between the
    definition and the single use site.

    After inlining, the field declaration is removed from the game.

    This complements ``InlineSingleUseVariableTransformer`` which only handles
    typed local declarations (``Type v = expr``).  This transform handles
    untyped field assignments where the field becomes a single-use alias after
    other transforms (e.g. ``IfConditionAliasSubstitution``) eliminate uses.

    Example::

        Game Test() {
            Int field4;
            Int ct_PQ;
            Void Initialize() {
                ct_PQ = 42;
                field4 = ct_PQ;
            }
        }

    becomes::

        Game Test() {
            Int field4;
            Void Initialize() {
                field4 = 42;
            }
        }
    """

    def __init__(self, proof_namespace: frog_ast.Namespace | None = None) -> None:
        self.field_names: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        return block  # All work done in transform_game

    def transform_game(self, game: frog_ast.Game) -> frog_ast.Game:
        self.field_names = [field.name for field in game.fields]
        changed = True
        result = game
        while changed:
            changed = False
            # Try inlining declared fields
            for field_name in list(self.field_names):
                new_game = self._try_inline_field(result, field_name)
                if new_game is not None:
                    result = new_game
                    self.field_names = [f.name for f in result.fields]
                    changed = True
                    break
            if changed:
                continue
            # Try inlining orphaned untyped variables: variables that have
            # untyped assignments but are NOT in the fields list (happens when
            # RemoveUnnecessaryFields removes a field declaration but leaves
            # the assignment statement).
            for orphan in self._find_orphaned_vars(result):
                new_game = self._try_inline_field(result, orphan)
                if new_game is not None:
                    result = new_game
                    self.field_names = [f.name for f in result.fields]
                    changed = True
                    break
        return result

    def _find_orphaned_vars(self, game: frog_ast.Game) -> list[str]:
        """Find variables with untyped assignments that are not in the fields list."""
        orphans: list[str] = []
        for method in game.methods:
            for stmt in method.block.statements:
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and stmt.the_type is None
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name not in self.field_names
                    and stmt.var.name not in orphans
                ):
                    orphans.append(stmt.var.name)
        return orphans

    def _try_inline_field(
        self, game: frog_ast.Game, field_name: str
    ) -> frog_ast.Game | None:
        """Try to inline a single field. Returns new game or None."""

        # 1. Find the single assignment to this field across all methods
        assign_count = 0
        assign_method_idx = -1
        assign_stmt_idx = -1
        assign_expr: frog_ast.Expression | None = None

        for mi, method in enumerate(game.methods):
            for si, stmt in enumerate(method.block.statements):
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and stmt.the_type is None
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name == field_name
                ):
                    assign_count += 1
                    assign_method_idx = mi
                    assign_stmt_idx = si
                    assign_expr = stmt.value

        if assign_count != 1 or assign_expr is None:
            return None

        # 2. Count total uses of field_name across the entire game
        def uses_field(node: frog_ast.ASTNode) -> bool:
            return isinstance(node, frog_ast.Variable) and node.name == field_name

        total_uses = 0
        count_game = copy.deepcopy(game)
        # Don't count the definition itself — replace the LHS variable name
        # so uses_field won't match it.
        count_def = count_game.methods[assign_method_idx].block.statements[
            assign_stmt_idx
        ]
        assert isinstance(count_def, frog_ast.Assignment)
        count_def.var = frog_ast.Variable("__placeholder__")

        while True:
            found = SearchVisitor(uses_field).visit(count_game)
            if found is None:
                break
            total_uses += 1
            count_game = ReplaceTransformer(
                found, frog_ast.Variable(field_name + "__counted__")
            ).transform(count_game)

        if total_uses == 0:
            return None

        # For multi-use fields, only inline if the expression is pure
        # (no non-deterministic function calls), so duplicating it is safe.
        is_pure = not has_nondeterministic_call(assign_expr, self._proof_namespace)
        if total_uses > 1 and not is_pure:
            return None

        # 3. All uses must be in the same method as the definition —
        # cross-method inlining is wrong because field values are stored once.
        all_same_method = True
        for mi, method in enumerate(game.methods):
            if mi == assign_method_idx:
                continue
            for si, stmt in enumerate(method.block.statements):
                if SearchVisitor(uses_field).visit(stmt) is not None:
                    all_same_method = False
                    break
            if not all_same_method:
                break

        if not all_same_method:
            return None

        # 4. Check that no free variable in expr is modified between def and last use
        last_use_idx = -1
        for si, stmt in enumerate(game.methods[assign_method_idx].block.statements):
            if si == assign_stmt_idx:
                continue
            if SearchVisitor(uses_field).visit(stmt) is not None:
                last_use_idx = si
        if last_use_idx >= 0:
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(assign_expr))
            intermediate_stmts = game.methods[assign_method_idx].block.statements[
                assign_stmt_idx + 1 : last_use_idx
            ]
            intermediate = frog_ast.Block(list(intermediate_stmts))

            def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, (frog_ast.Sample, frog_ast.Assignment))
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            if any(
                SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                    intermediate
                )
                is not None
                for fv in free_vars
            ):
                return None

        # 5. Perform the inlining — replace ALL occurrences in the method
        new_game = copy.deepcopy(game)

        method = new_game.methods[assign_method_idx]
        # Replace in each statement except the definition
        new_stmts = list(method.block.statements)
        for si, stmt in enumerate(new_stmts):
            if si == assign_stmt_idx:
                continue
            while True:
                field_node = SearchVisitor(uses_field).visit(stmt)
                if field_node is None:
                    break
                stmt = ReplaceTransformer(
                    field_node, copy.deepcopy(assign_expr)
                ).transform(stmt)
            new_stmts[si] = stmt
        method.block = frog_ast.Block(new_stmts)

        # Remove the definition statement
        method = new_game.methods[assign_method_idx]
        method.block = frog_ast.Block(
            list(method.block.statements[:assign_stmt_idx])
            + list(method.block.statements[assign_stmt_idx + 1 :])
        )

        # Remove the field declaration
        new_game.fields = [f for f in new_game.fields if f.name != field_name]

        return new_game


class InlineSingleUseField(TransformPass):
    name = "Inline Single-Use Field"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineSingleUseFieldTransformer(
            proof_namespace=ctx.proof_namespace
        ).transform(game)
