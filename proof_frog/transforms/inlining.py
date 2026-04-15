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
from collections.abc import Callable, Sequence

from .. import frog_ast
from ..visitors import (
    BlockTransformer,
    NameTypeMap,
    SearchVisitor,
    SubstitutionTransformer,
    Visitor,
    ReplaceTransformer,
    VariableCollectionVisitor,
)
from ._base import (
    TransformPass,
    PipelineContext,
    has_nondeterministic_call,
    NearMiss,
    _lookup_primitive_method,
)


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

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

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
                if total_uses > 1 and self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Variable",
                            reason=(
                                f"Cannot inline '{var_name}': "
                                f"used {total_uses} times (need exactly 1)"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"If '{var_name}' should be inlined, restructure "
                                f"so it is used only once"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            # Collect free variables in expr and check none are written to
            # between the declaration and the single use site
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(expr))
            intermediate = frog_ast.Block(
                list(remaining_block.statements[:first_use_idx])
            )
            modified_free_vars = [
                fv.name
                for fv in free_vars
                if SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                    intermediate
                )
                is not None
            ]
            if modified_free_vars:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Variable",
                            reason=(
                                f"Cannot inline '{var_name}': free variable(s) "
                                f"{', '.join(repr(v) for v in modified_free_vars)} "
                                f"modified between declaration and use"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Reorder statements so that "
                                f"{', '.join(repr(v) for v in modified_free_vars)} "
                                f"{'is' if len(modified_free_vars) == 1 else 'are'} "
                                f"not modified between the declaration and use "
                                f"of '{var_name}'"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
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


class IfSplitBranchAssignmentTransformer(BlockTransformer):
    """Moves subsequent statements into if-else branches when all branches
    assign the same variable.

    When an if-else has every branch ending with an assignment to the same
    variable ``x``, and subsequent statements use ``x`` without reassigning
    it, those subsequent statements are moved into each branch with ``x``
    replaced by the branch's assigned value.

    Example::

        if (C) { x = A; } else { x = B; }
        return f(x);
      becomes:
        if (C) { return f(A); } else { return f(B); }
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.IfStatement):
                continue
            if not statement.has_else_block():
                continue

            # Check all branches end with an assignment to the same variable.
            var_name: str | None = None
            branch_values: list[frog_ast.Expression] = []
            all_match = True
            for blk in statement.blocks:
                if not blk.statements:
                    all_match = False
                    break
                last = blk.statements[-1]
                if not (
                    isinstance(last, frog_ast.Assignment)
                    and isinstance(last.var, frog_ast.Variable)
                ):
                    all_match = False
                    break
                if var_name is None:
                    var_name = last.var.name
                elif last.var.name != var_name:
                    all_match = False
                    break
                branch_values.append(last.value)

            if not all_match or var_name is None:
                continue

            # Must have subsequent statements
            subsequent = block.statements[index + 1 :]
            if not subsequent:
                continue

            # Variable must not be reassigned in subsequent statements
            def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(
                        node,
                        (
                            frog_ast.Assignment,
                            frog_ast.Sample,
                            frog_ast.UniqueSample,
                        ),
                    )
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    frog_ast.Block(list(subsequent))
                )
                is not None
            ):
                continue

            # If any branch value contains a non-deterministic call,
            # the variable must be used at most once in subsequent code.
            # Otherwise substitution would duplicate the call, changing
            # single-evaluation to multi-evaluation semantics.
            proof_ns: frog_ast.Namespace = self.ctx.proof_namespace if self.ctx else {}
            proof_let_types = self.ctx.proof_let_types if self.ctx else None
            has_nondet = any(
                has_nondeterministic_call(v, proof_ns, proof_let_types)
                for v in branch_values
            )
            if has_nondet:
                counter = _VarCountVisitor(var_name)
                counter.visit(frog_ast.Block(list(subsequent)))
                if counter.result() > 1:
                    continue

            # Build new blocks: for each branch, replace trailing assignment
            # with subsequent statements where var is substituted by value
            new_blocks: list[frog_ast.Block] = []
            for blk_idx, blk in enumerate(statement.blocks):
                prefix = list(blk.statements[:-1])
                value = branch_values[blk_idx]
                ast_map = frog_ast.ASTMap[frog_ast.ASTNode](identity=False)
                ast_map.set(frog_ast.Variable(var_name), copy.deepcopy(value))
                substituted = SubstitutionTransformer(ast_map).transform(
                    copy.deepcopy(frog_ast.Block(list(subsequent)))
                )
                new_blocks.append(frog_ast.Block(prefix + list(substituted.statements)))

            new_if = frog_ast.IfStatement(list(statement.conditions), new_blocks)
            # Also remove the declaration of var_name before the if, if any
            prior = list(block.statements[:index])
            cleaned_prior: list[frog_ast.Statement] = []
            for s in prior:
                if isinstance(s, frog_ast.VariableDeclaration) and s.name == var_name:
                    continue
                cleaned_prior.append(s)

            return self.transform_block(frog_ast.Block(cleaned_prior + [new_if]))

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
            # Inlining these spreads references to the indexed variable,
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

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not isinstance(statement, (frog_ast.Assignment, frog_ast.Sample)):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue

            # Skip if the statement's value has non-deterministic calls
            if isinstance(statement, frog_ast.Assignment) and has_nondeterministic_call(
                statement.value, self._proof_namespace, self._proof_let_types
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
                # Skip element mutations (v[i] = expr, M[k] = expr) — the
                # variable is being used, not fully overwritten.
                if not (
                    isinstance(later_statement.var, frog_ast.Variable)
                    and later_statement.var == statement.var
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
                decl_statement: (
                    frog_ast.Assignment | frog_ast.Sample | frog_ast.UniqueSample
                )
                for other_index, other_statement in enumerate(block.statements):
                    if other_index == index:
                        continue
                    if (
                        isinstance(
                            other_statement,
                            (
                                frog_ast.Sample,
                                frog_ast.Assignment,
                                frog_ast.UniqueSample,
                            ),
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
                # Check that the field is not accessed (read or written)
                # between the declaration and the field assignment.
                # Moving the assignment earlier would change observable
                # behaviour if the field is referenced in between.
                assert isinstance(statement.var, frog_ast.Variable)
                field_var_name = statement.var.name

                def is_field_ref(
                    node: frog_ast.ASTNode, fn: str = field_var_name
                ) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == fn

                field_accessed_between = False
                for between_idx in range(decl_index + 1, index):
                    between_stmt = block.statements[between_idx]
                    if SearchVisitor(is_field_ref).visit(between_stmt) is not None:
                        field_accessed_between = True
                        break
                if field_accessed_between:
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

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self.fields: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

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
            # Skip trivial literals.  Replacing a constant like ``0`` with a
            # named alias is lossy: subsequent passes (e.g. tuple expansion,
            # branch elimination) rely on seeing the constant directly to
            # decide whether to fire.  Aliasing literals also never reduces
            # complexity.
            if isinstance(
                statement.value,
                (
                    frog_ast.Integer,
                    frog_ast.Boolean,
                    frog_ast.BinaryNum,
                    frog_ast.NoneExpression,
                ),
            ):
                continue

            var_name = statement.var.name
            expr = statement.value

            # Only handle pure expressions (no non-deterministic function calls)
            if has_nondeterministic_call(
                expr, self._proof_namespace, self._proof_let_types
            ):
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


class IfSplitBranchAssignment(TransformPass):
    name = "If-Split Branch Assignment"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return IfSplitBranchAssignmentTransformer(ctx).transform(game)


class InlineSingleUseVariable(TransformPass):
    name = "Inline Single-Use Variables"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineSingleUseVariableTransformer(ctx).transform(game)


class CollapseAssignment(TransformPass):
    name = "Collapse Assignment"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return CollapseAssignmentTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class ForwardExpressionAlias(TransformPass):
    name = "Forward Expression Alias"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ForwardExpressionAliasTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class ExtractRepeatedTupleAccessTransformer(BlockTransformer):
    """Extract repeated ``var[constant]`` accesses into named variables.

    When ``v[i]`` (variable + integer index) appears 2+ times in a block
    and ``v`` is declared with a product (tuple) type, inserts a local
    declaration ``Ti __cse_v_i__ = v[i];`` right after ``v``'s assignment
    and replaces every occurrence with the new variable.

    This normalises games that destructure tuples explicitly
    (``pk = k[0]``) against games that use inline access
    (``Encaps(k[0])``).
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Build map: var_name -> declared type (from assignments in this block)
        var_types: dict[str, frog_ast.Type] = {}
        var_def_idx: dict[str, int] = {}
        for idx, stmt in enumerate(block.statements):
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.the_type is not None
            ):
                var_types[stmt.var.name] = stmt.the_type
                var_def_idx[stmt.var.name] = idx

        # Count occurrences of each (var_name, index) ArrayAccess pattern
        access_counts: dict[tuple[str, int], int] = {}
        for stmt in block.statements:

            def counter(node: frog_ast.ASTNode) -> bool:
                if (
                    isinstance(node, frog_ast.ArrayAccess)
                    and isinstance(node.the_array, frog_ast.Variable)
                    and isinstance(node.index, frog_ast.Integer)
                ):
                    key = (node.the_array.name, node.index.num)
                    access_counts[key] = access_counts.get(key, 0) + 1
                return False

            SearchVisitor(counter).visit(stmt)

        # Find first pattern with 2+ uses whose base var has a product type
        for (var_name, idx_val), count in access_counts.items():
            if count < 2:
                continue
            if var_name not in var_types:
                continue
            base_type = var_types[var_name]
            if not isinstance(base_type, frog_ast.ProductType):
                continue
            if idx_val < 0 or idx_val >= len(base_type.types):
                continue

            # Skip if the base variable is reassigned after its definition
            def _is_reassigned(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(
                        node,
                        (
                            frog_ast.Assignment,
                            frog_ast.Sample,
                            frog_ast.UniqueSample,
                        ),
                    )
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == name
                )

            remaining_after_def = frog_ast.Block(
                list(block.statements[var_def_idx[var_name] + 1 :])
            )
            if (
                SearchVisitor(functools.partial(_is_reassigned, var_name)).visit(
                    remaining_after_def
                )
                is not None
            ):
                continue

            elem_type = base_type.types[idx_val]
            cse_name = f"__cse_{var_name}_{idx_val}__"
            target_access = frog_ast.ArrayAccess(
                frog_ast.Variable(var_name), frog_ast.Integer(idx_val)
            )

            # Create the extraction: elem_type cse_name = var[idx];
            new_assignment = frog_ast.Assignment(
                elem_type,
                frog_ast.Variable(cse_name),
                copy.deepcopy(target_access),
            )

            # Insert after the base variable's definition
            insert_at = var_def_idx[var_name] + 1

            # Replace all occurrences of var[idx] with the CSE variable
            new_stmts = list(block.statements[:insert_at])
            new_stmts.append(new_assignment)

            remaining = frog_ast.Block(list(block.statements[insert_at:]))

            def _match_access(
                target: frog_ast.Expression, node: frog_ast.ASTNode
            ) -> bool:
                return node == target

            while True:
                match = SearchVisitor(
                    functools.partial(_match_access, target_access)
                ).visit(remaining)
                if match is None:
                    break
                remaining = ReplaceTransformer(
                    match, frog_ast.Variable(cse_name)
                ).transform(remaining)

            new_stmts.extend(remaining.statements)
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class ExtractRepeatedTupleAccess(TransformPass):
    """Extract repeated tuple element accesses into named variables."""

    name = "Extract Repeated Tuple Access"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExtractRepeatedTupleAccessTransformer().transform(game)


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

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self.fields: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types: NameTypeMap | None = proof_let_types

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
            if has_nondeterministic_call(
                expr, self._proof_namespace, self._proof_let_types
            ):
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

            def _search_use_positions(
                stmt: frog_ast.Statement,
                matcher: Callable[[frog_ast.ASTNode], bool],
            ) -> frog_ast.Expression | None:
                """Search only in use-position sub-expressions, skipping
                assignment targets (LHS) to avoid corrupting def sites."""
                if isinstance(stmt, frog_ast.Assignment):
                    return SearchVisitor(matcher).visit(stmt.value)
                if isinstance(stmt, (frog_ast.Sample, frog_ast.UniqueSample)):
                    return None
                return SearchVisitor(matcher).visit(stmt)

            def _modifies_var(name: str, node: frog_ast.ASTNode) -> bool:
                """Check if a statement modifies a variable, including
                element mutations like v[i] = expr."""
                if not isinstance(
                    node,
                    (
                        frog_ast.Sample,
                        frog_ast.Assignment,
                        frog_ast.UniqueSample,
                    ),
                ):
                    return False
                var = node.var
                if isinstance(var, frog_ast.Variable) and var.name == name:
                    return True
                if isinstance(var, frog_ast.ArrayAccess) and isinstance(
                    var.the_array, frog_ast.Variable
                ):
                    if var.the_array.name == name:
                        return True
                return False

            for j in range(i):
                earlier = block.statements[j]
                match = _search_use_positions(
                    earlier, functools.partial(matches_expr, expr)
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
                # Verify free variables are not modified between j and i.
                # This ensures the expression evaluates to the same value
                # at the hoist target (before j) as at the original
                # position i.  Field-type free variables must also be
                # checked — a field modified between j and i would cause
                # the hoisted expression to evaluate to a stale value.
                stable = True
                for fv in free_vars:
                    for k in range(j, i):
                        if (
                            SearchVisitor(
                                functools.partial(_modifies_var, fv.name)
                            ).visit(block.statements[k])
                            is not None
                        ):
                            stable = False
                            break
                    if not stable:
                        break
                if not stable:
                    continue
                # Hoist: move field assignment to before position j,
                # replace the subexpression in position j with the field.
                # Re-find the match in a deep copy (ReplaceTransformer uses
                # identity, so we need a node from the same copy).
                new_earlier = copy.deepcopy(earlier)
                match_in_copy = _search_use_positions(
                    new_earlier, functools.partial(matches_expr, expr)
                )
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
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


def _count_assigns_recursive(node: frog_ast.ASTNode, name: str) -> int:
    """Count all assignments/samples to *name* recursively in the AST."""
    count = 0

    def _counter(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        ):
            count += 1
        return False

    SearchVisitor(_counter).visit(node)
    return count


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

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        ctx: PipelineContext | None = None,
    ) -> None:
        self.field_names: list[str] = []
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self.ctx = ctx

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

        # 1. Find the single assignment to this field across all methods.
        #    Count recursively to catch assignments inside nested blocks
        #    (if-branches, etc.) that a shallow top-level scan would miss.
        assign_count = 0
        assign_method_idx = -1
        assign_stmt_idx = -1
        assign_expr: frog_ast.Expression | None = None

        for mi, method in enumerate(game.methods):
            # Count ALL assignments (including nested) for soundness
            method_assign_count = _count_assigns_recursive(method.block, field_name)
            assign_count += method_assign_count
            # Track the top-level assignment location for inlining
            for si, stmt in enumerate(method.block.statements):
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and stmt.the_type is None
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name == field_name
                ):
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
        is_pure = not has_nondeterministic_call(
            assign_expr,
            self._proof_namespace,
            self.ctx.proof_let_types if self.ctx else None,
        )
        if total_uses > 1 and not is_pure:
            if self.ctx is not None:
                self.ctx.near_misses.append(
                    NearMiss(
                        transform_name="Inline Single-Use Field",
                        reason=(
                            f"Cannot inline field '{field_name}': "
                            f"used {total_uses} times but expression "
                            f"contains non-deterministic calls"
                        ),
                        location=None,
                        suggestion=None,
                        variable=field_name,
                        method=None,
                    )
                )
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

        # Cross-method inlining is allowed when the expression is pure and
        # all its free variables are other fields (which persist across method
        # calls with the same value), so substitution is semantics-preserving.
        cross_method = False
        if not all_same_method:
            if not is_pure:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Field",
                            reason=(
                                f"Cannot inline field '{field_name}': "
                                f"used across multiple methods and expression "
                                f"contains non-deterministic calls"
                            ),
                            location=None,
                            suggestion=None,
                            variable=field_name,
                            method=None,
                        )
                    )
                return None
            # All free variables in the expression must be fields (accessible
            # from any method) — local variables would be out of scope.
            # Additionally, each free-variable field must:
            #   - be assigned at most once in the entire game (stable value)
            #   - be assigned in the same method and BEFORE the current
            #     field's assignment (so its value was already determined)
            free_vars = VariableCollectionVisitor().visit(copy.deepcopy(assign_expr))
            field_name_set = set(self.field_names)
            can_cross_method = True
            for fv in free_vars:
                if fv.name not in field_name_set:
                    can_cross_method = False
                    break
                # Check that this free-variable field is assigned/sampled
                # at most once across the whole game (stable value).
                fv_assign_count = sum(
                    _count_assigns_recursive(m.block, fv.name) for m in game.methods
                )
                if fv_assign_count > 1:
                    can_cross_method = False
                    break
                # The free var's assignment must be in the same method and
                # before the current field's assignment, so the value was
                # determined before capture.
                fv_assigned_before = False
                method_stmts = game.methods[assign_method_idx].block.statements
                for si in range(assign_stmt_idx):
                    stmt = method_stmts[si]
                    if (
                        isinstance(
                            stmt,
                            (
                                frog_ast.Assignment,
                                frog_ast.Sample,
                                frog_ast.UniqueSample,
                            ),
                        )
                        and isinstance(stmt.var, frog_ast.Variable)
                        and stmt.var.name == fv.name
                    ):
                        fv_assigned_before = True
                        break
                if not fv_assigned_before:
                    can_cross_method = False
                    break
            if not can_cross_method:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Field",
                            reason=(
                                f"Cannot inline field '{field_name}': "
                                f"used across multiple methods and expression "
                                f"references non-field or reassigned variables"
                            ),
                            location=None,
                            suggestion=None,
                            variable=field_name,
                            method=None,
                        )
                    )
                return None
            # Also check: no use of the field before its assignment in
            # the assignment method (same as step 4 for same-method path).
            for si in range(assign_stmt_idx):
                stmt = game.methods[assign_method_idx].block.statements[si]
                if SearchVisitor(uses_field).visit(stmt) is not None:
                    can_cross_method = False
                    break
            if not can_cross_method:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Field",
                            reason=(
                                f"Cannot inline field '{field_name}': "
                                f"used across multiple methods with "
                                f"use-before-def in assignment method"
                            ),
                            location=None,
                            suggestion=None,
                            variable=field_name,
                            method=None,
                        )
                    )
                return None
            cross_method = True

        if not cross_method:
            # 4. Check that no use occurs before the definition (use-before-def).
            #    If a field is used at position u < d in the same method, the use
            #    reads the field value from a *previous* invocation; inlining the
            #    current call's expression would be semantically wrong.
            first_use_idx = -1
            last_use_idx = -1
            for si, stmt in enumerate(game.methods[assign_method_idx].block.statements):
                if si == assign_stmt_idx:
                    continue
                if SearchVisitor(uses_field).visit(stmt) is not None:
                    if first_use_idx == -1:
                        first_use_idx = si
                    last_use_idx = si

            if 0 <= first_use_idx < assign_stmt_idx:
                return None

            # 5. Check that no free variable in expr is modified between
            #    def and last use
            if last_use_idx >= 0:
                free_vars = VariableCollectionVisitor().visit(
                    copy.deepcopy(assign_expr)
                )
                intermediate_stmts = game.methods[assign_method_idx].block.statements[
                    assign_stmt_idx + 1 : last_use_idx
                ]
                intermediate = frog_ast.Block(list(intermediate_stmts))

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

                if any(
                    SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                        intermediate
                    )
                    is not None
                    for fv in free_vars
                ):
                    return None

        # 6. Perform the inlining — replace occurrences across methods.
        #    In the assignment method, only replace uses AFTER the assignment
        #    (uses before the def read a prior value and must not be replaced).
        new_game = copy.deepcopy(game)

        for mi, method in enumerate(new_game.methods):
            new_stmts = list(method.block.statements)
            for si, stmt in enumerate(new_stmts):
                if mi == assign_method_idx and si <= assign_stmt_idx:
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
            proof_namespace=ctx.proof_namespace, ctx=ctx
        ).transform(game)


class _DeterministicCallCollector(Visitor[list[frog_ast.FuncCall]]):
    """Collect all FuncCall nodes that call deterministic primitive methods."""

    def __init__(self, proof_namespace: frog_ast.Namespace) -> None:
        self._proof_namespace = proof_namespace
        self._calls: list[frog_ast.FuncCall] = []

    def result(self) -> list[frog_ast.FuncCall]:
        return self._calls

    def visit_func_call(self, node: frog_ast.FuncCall) -> None:
        m = _lookup_primitive_method(node.func, self._proof_namespace)
        if m is not None and m.deterministic:
            self._calls.append(node)


class _AllPrimitiveFuncCallCollector(Visitor[list[frog_ast.FuncCall]]):
    """Collect all FuncCall nodes that call any primitive method."""

    def __init__(self, proof_namespace: frog_ast.Namespace) -> None:
        self._proof_namespace = proof_namespace
        self._calls: list[frog_ast.FuncCall] = []

    def result(self) -> list[frog_ast.FuncCall]:
        return self._calls

    def visit_func_call(self, node: frog_ast.FuncCall) -> None:
        if _lookup_primitive_method(node.func, self._proof_namespace) is not None:
            self._calls.append(node)


class DeduplicateDeterministicCallsTransformer(BlockTransformer):
    """Extract duplicate deterministic FuncCalls into a shared local variable.

    Within a single block, finds duplicate calls to ``deterministic`` primitive
    methods with structurally equal arguments, extracts the first occurrence
    into a fresh ``__determ_N__`` variable, and replaces all occurrences.

    Example::

        return [G.evaluate(k), G.evaluate(k)];
      becomes:
        BitString<n> __determ_0__ = G.evaluate(k);
        return [__determ_0__, __determ_0__];
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace,
        ctx: PipelineContext | None = None,
    ) -> None:
        self.proof_namespace = proof_namespace
        self._ctx = ctx
        self.counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Collect all deterministic calls from top-level statements only.
        # Skip parameterless calls (constants) — extracting them changes
        # variable numbering without benefit, since existing transforms
        # already handle pure constant expressions.
        all_calls: list[frog_ast.FuncCall] = []
        for statement in block.statements:
            # Skip inner blocks (if-statements); BlockTransformer handles them
            if isinstance(statement, frog_ast.IfStatement):
                continue
            collector = _DeterministicCallCollector(self.proof_namespace)
            collector.visit(statement)
            all_calls.extend(c for c in collector.result() if c.args)

        if not all_calls:
            # Check for near-miss: duplicate non-deterministic calls
            if self._ctx is not None:
                self._report_nondet_near_misses(block)
            return block

        # Group by structural equality; find first group with 2+ occurrences
        groups: list[list[frog_ast.FuncCall]] = []
        for call in all_calls:
            placed = False
            for group in groups:
                if call == group[0]:
                    group.append(call)
                    placed = True
                    break
            if not placed:
                groups.append([call])

        dup_group: list[frog_ast.FuncCall] | None = None
        for group in groups:
            if len(group) >= 2:
                # Verify no argument variable is reassigned between the
                # first and last statement containing a call from this group.
                if self._args_stable_across_calls(block, group):
                    dup_group = group
                    break

        if dup_group is None:
            return block

        # Look up the return type for the new assignment
        representative = dup_group[0]
        m = _lookup_primitive_method(representative.func, self.proof_namespace)
        assert m is not None
        return_type = copy.deepcopy(m.return_type)

        var_name = f"__determ_{self.counter}__"
        self.counter += 1

        # Create the new assignment statement
        new_assignment = frog_ast.Assignment(
            return_type,  # type: ignore[arg-type]
            frog_ast.Variable(var_name),
            copy.deepcopy(representative),
        )

        # Find the first statement containing a duplicate call and insert before it
        insert_index: int | None = None
        for index, statement in enumerate(block.statements):
            if isinstance(statement, frog_ast.IfStatement):
                continue
            collector = _DeterministicCallCollector(self.proof_namespace)
            collector.visit(statement)
            for found_call in collector.result():
                if found_call == representative:
                    insert_index = index
                    break
            if insert_index is not None:
                break

        assert insert_index is not None

        # Replace all occurrences in the block
        new_block = block
        for call in dup_group:
            new_block = ReplaceTransformer(call, frog_ast.Variable(var_name)).transform(
                new_block
            )

        # Insert the new assignment before the first occurrence
        new_stmts = (
            list(new_block.statements[:insert_index])
            + [new_assignment]
            + list(new_block.statements[insert_index:])
        )

        # Recurse to handle remaining duplicate groups
        return self.transform_block(frog_ast.Block(new_stmts))

    def _args_stable_across_calls(
        self,
        block: frog_ast.Block,
        call_group: list[frog_ast.FuncCall],
    ) -> bool:
        """Check that no argument variable of the call group is reassigned
        between the first and last statement containing a call."""
        # Collect all free variable names from call arguments
        representative = call_group[0]
        arg_vars: set[str] = set()
        for arg in representative.args:
            for fv in VariableCollectionVisitor().visit(copy.deepcopy(arg)):
                arg_vars.add(fv.name)
        if not arg_vars:
            return True

        # Find first and last statement indices containing a call from the group
        first_idx: int | None = None
        last_idx: int | None = None
        for idx, stmt in enumerate(block.statements):
            if isinstance(stmt, frog_ast.IfStatement):
                continue
            collector = _DeterministicCallCollector(self.proof_namespace)
            collector.visit(stmt)
            if any(c == representative for c in collector.result()):
                if first_idx is None:
                    first_idx = idx
                last_idx = idx
        if first_idx is None or last_idx is None or first_idx == last_idx:
            return True

        # Check that no argument variable is reassigned or element-mutated
        def is_written_to(name: str, node: frog_ast.ASTNode) -> bool:
            if not isinstance(
                node,
                (frog_ast.Sample, frog_ast.Assignment, frog_ast.UniqueSample),
            ):
                return False
            var = node.var
            if isinstance(var, frog_ast.Variable) and var.name == name:
                return True
            # Element mutation: v[i] = expr, M[k] = expr
            if isinstance(var, frog_ast.ArrayAccess) and isinstance(
                var.the_array, frog_ast.Variable
            ):
                if var.the_array.name == name:
                    return True
            return False

        intermediate = frog_ast.Block(list(block.statements[first_idx + 1 : last_idx]))
        for var_name in arg_vars:
            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    intermediate
                )
                is not None
            ):
                return False
        return True

    def _report_nondet_near_misses(self, block: frog_ast.Block) -> None:
        """Report near-misses for duplicate non-deterministic calls."""
        assert self._ctx is not None

        all_calls: list[frog_ast.FuncCall] = []
        for statement in block.statements:
            if isinstance(statement, frog_ast.IfStatement):
                continue
            collector = _AllPrimitiveFuncCallCollector(self.proof_namespace)
            collector.visit(statement)
            all_calls.extend(collector.result())

        # Group by structural equality
        groups: list[list[frog_ast.FuncCall]] = []
        for call in all_calls:
            placed = False
            for group in groups:
                if call == group[0]:
                    group.append(call)
                    placed = True
                    break
            if not placed:
                groups.append([call])

        for group in groups:
            if len(group) < 2:
                continue
            call = group[0]
            m = _lookup_primitive_method(call.func, self.proof_namespace)
            if m is None or not m.deterministic:
                self._ctx.near_misses.append(
                    NearMiss(
                        transform_name="Deduplicate Deterministic Calls",
                        reason=(
                            f"Duplicate call to {call.func} found but method "
                            f"is not annotated deterministic"
                        ),
                        location=None,
                        suggestion=(
                            "Add 'deterministic' annotation to the primitive "
                            "method declaration"
                        ),
                        variable=None,
                        method=None,
                    )
                )


class DeduplicateDeterministicCalls(TransformPass):
    name = "Deduplicate Deterministic Calls"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return DeduplicateDeterministicCallsTransformer(
            proof_namespace=ctx.proof_namespace, ctx=ctx
        ).transform(game)


# ---------------------------------------------------------------------------
# Cross-method deterministic field alias
# ---------------------------------------------------------------------------


def _is_stable_arg(
    expr: frog_ast.Expression,
    field_names: set[str],
    param_names: set[str],
) -> bool:
    """Return True if *expr* is stable across method invocations.

    An expression is stable if it depends only on game fields, game parameters,
    and constants — never on method-local variables.
    """
    if isinstance(
        expr, (frog_ast.Integer, frog_ast.Boolean, frog_ast.BitStringLiteral)
    ):
        return True
    if isinstance(expr, frog_ast.Variable):
        return expr.name in field_names or expr.name in param_names
    if isinstance(expr, frog_ast.FieldAccess):
        return _is_stable_arg(expr.the_object, field_names, param_names)
    if isinstance(expr, frog_ast.BinaryOperation):
        return _is_stable_arg(
            expr.left_expression, field_names, param_names
        ) and _is_stable_arg(expr.right_expression, field_names, param_names)
    if isinstance(expr, frog_ast.UnaryOperation):
        return _is_stable_arg(expr.expression, field_names, param_names)
    return False


def _collect_field_names_in_args(
    expr: frog_ast.Expression, field_names: set[str]
) -> set[str]:
    """Return the set of field names referenced in *expr*."""
    if isinstance(expr, frog_ast.Variable):
        if expr.name in field_names:
            return {expr.name}
        return set()
    if isinstance(expr, frog_ast.FieldAccess):
        return _collect_field_names_in_args(expr.the_object, field_names)
    if isinstance(expr, frog_ast.BinaryOperation):
        return _collect_field_names_in_args(
            expr.left_expression, field_names
        ) | _collect_field_names_in_args(expr.right_expression, field_names)
    if isinstance(expr, frog_ast.UnaryOperation):
        return _collect_field_names_in_args(expr.expression, field_names)
    return set()


def _fields_assigned_in_block(block: frog_ast.Block, field_names: set[str]) -> set[str]:
    """Return field names that are assigned anywhere in *block* (recursively)."""
    assigned: set[str] = set()
    for stmt in block.statements:
        if isinstance(
            stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            var = stmt.var
            # Direct variable assignment: k = expr, k <- Type
            if isinstance(var, frog_ast.Variable) and var.name in field_names:
                assigned.add(var.name)
            # Element mutation: arr[i] = expr, M[k] = expr
            if (
                isinstance(var, frog_ast.ArrayAccess)
                and isinstance(var.the_array, frog_ast.Variable)
                and var.the_array.name in field_names
            ):
                assigned.add(var.the_array.name)
        if isinstance(stmt, frog_ast.IfStatement):
            for blk in stmt.blocks:
                assigned |= _fields_assigned_in_block(blk, field_names)
        if isinstance(stmt, (frog_ast.NumericFor, frog_ast.GenericFor)):
            assigned |= _fields_assigned_in_block(stmt.block, field_names)
    return assigned


def _fields_assigned_after(
    statements: Sequence[frog_ast.Statement],
    after_idx: int,
    field_names: set[str],
) -> set[str]:
    """Return field names assigned in *statements* after index *after_idx*.

    Checks both top-level and nested (if/for) statements that appear after
    the statement at *after_idx*.
    """
    tail_block = frog_ast.Block(list(statements[after_idx + 1 :]))
    return _fields_assigned_in_block(tail_block, field_names)


class CrossMethodFieldAliasTransformer:
    """Replace deterministic calls in oracles with field references.

    When a field assignment ``field_x = det_call(stable_args)`` exists in one
    method (typically Initialize) and the same ``det_call(stable_args)`` appears
    in another method, this transformer replaces the call in the other method
    with ``field_x``.

    This does NOT introduce new fields — it reuses existing field assignments.
    This is safe because the field already exists in both games being compared,
    so the canonical form is not structurally altered.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace,
        ctx: PipelineContext | None = None,
    ) -> None:
        self.proof_namespace = proof_namespace
        self._ctx = ctx

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        field_names = {f.name for f in game.fields}
        param_names = {p.name for p in game.parameters}

        # Phase 1: Collect field assignments with deterministic RHS
        # (field_name, det_call, method_idx)
        field_aliases: list[tuple[str, frog_ast.FuncCall, int]] = []
        for midx, method in enumerate(game.methods):
            for sidx, stmt in enumerate(method.block.statements):
                if not (
                    isinstance(stmt, frog_ast.Assignment)
                    and stmt.the_type is None
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name in field_names
                    and isinstance(stmt.value, frog_ast.FuncCall)
                ):
                    continue
                call = stmt.value
                m = _lookup_primitive_method(call.func, self.proof_namespace)
                if m is None or not m.deterministic:
                    continue
                if not call.args:
                    continue
                if not all(
                    _is_stable_arg(a, field_names, param_names) for a in call.args
                ):
                    continue

                # Soundness check: the alias must be in Initialize.
                # If it's in an oracle, the adversary could call the
                # replacement-target oracle before the alias-source oracle,
                # reading an uninitialized field.
                if method.signature.name != "Initialize":
                    continue

                # Soundness check: the alias field and all argument fields
                # must not be reassigned after the alias statement in this
                # method, and must not be assigned in any other method.
                arg_fields = set()
                for a in call.args:
                    arg_fields |= _collect_field_names_in_args(a, field_names)
                guarded_fields = {stmt.var.name} | arg_fields

                # Check no reassignment after the alias in the source method
                modified_after = _fields_assigned_after(
                    method.block.statements, sidx, guarded_fields
                )
                if modified_after:
                    continue

                # Check no assignment in any other method
                modified_elsewhere = False
                for oidx, other_method in enumerate(game.methods):
                    if oidx == midx:
                        continue
                    if _fields_assigned_in_block(other_method.block, guarded_fields):
                        modified_elsewhere = True
                        break
                if modified_elsewhere:
                    continue

                field_aliases.append((stmt.var.name, call, midx))

        if not field_aliases:
            return game

        # Phase 2: For each field alias, check if the same call appears in
        # other methods and replace it
        for alias_field_name, alias_call, alias_midx in field_aliases:
            result = self._try_replace(game, alias_field_name, alias_call, alias_midx)
            if result is not None:
                return result

        return game

    def _try_replace(
        self,
        game: frog_ast.Game,
        alias_field_name: str,
        alias_call: frog_ast.FuncCall,
        alias_midx: int,
    ) -> frog_ast.Game | None:
        """Try to replace *alias_call* with *alias_field_name* in another method."""
        for midx, method in enumerate(game.methods):
            if midx == alias_midx:
                continue
            collector = _DeterministicCallCollector(self.proof_namespace)
            collector.visit(method.block)
            if not any(c == alias_call for c in collector.result()):
                continue
            # Found a match — replace and return
            new_game = copy.deepcopy(game)
            new_collector = _DeterministicCallCollector(self.proof_namespace)
            new_collector.visit(new_game.methods[midx].block)
            for new_call in new_collector.result():
                if new_call == alias_call:
                    new_game.methods[midx] = ReplaceTransformer(
                        new_call,
                        frog_ast.Variable(alias_field_name),
                    ).transform(new_game.methods[midx])
                    return new_game
        return None


class CrossMethodFieldAlias(TransformPass):
    name = "Cross-Method Field Alias"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return CrossMethodFieldAliasTransformer(
            proof_namespace=ctx.proof_namespace, ctx=ctx
        ).transform(game)
