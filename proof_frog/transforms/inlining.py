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
from typing import Optional

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

    def __init__(self, function_var_names: set[str] | None = None) -> None:
        super().__init__()
        self._function_var_names = function_var_names or set()

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

            # Skip function calls in general — multi-use inlining
            # duplicates the call at every use site, changing the
            # canonical form.  EXCEPTION: calls to a sampled
            # ``Function<D, R>`` proof-let are deterministic in
            # FrogLang (same input → same output) AND their canonical
            # form should match the inline-form of games that don't
            # extract the call to a local; allow inlining for those.
            if (
                SearchVisitor(lambda n: isinstance(n, frog_ast.FuncCall)).visit(expr)
                is not None
            ):
                if not (
                    self._function_var_names
                    and isinstance(expr, frog_ast.FuncCall)
                    and isinstance(expr.func, frog_ast.Variable)
                    and expr.func.name in self._function_var_names
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


class InlineLocalTupleLiteralTransformer(BlockTransformer):
    """Inline a local typed tuple-literal binding when the variable is used
    only at constant indices and not reassigned, substituting each ``v[k]``
    with the corresponding tuple element.

    Bridges a gap between ``ExpandTupleTransformer`` (which fires
    block-locally and can leave outer-scope ``v[i]`` accesses unrewritten
    when ``v`` was originally declared in an if-branch that
    ``BranchElimination`` later collapsed) and
    ``InlineSingleUseVariableTransformer`` (which skips Tuple RHS to avoid
    breaking the tuple-expansion pipeline).

    Preconditions for firing on ``[T0,...,Tn-1] v = [e0,...,en-1];``:

    1. No bare reference to ``v`` in the remaining block (every reference
       is the ``the_array`` child of an ``ArrayAccess`` node).
    2. Every ``v[k]`` access has ``k`` a constant integer in ``[0, n)``.
    3. ``v`` is not reassigned in the remaining block, and no free
       variable of any ``e_i`` is reassigned anywhere later.
    4. For each index ``i``: if ``v[i]`` is used 2+ times, ``e_i`` must
       be deterministic (no non-deterministic calls); if ``v[i]`` is
       never used, ``e_i`` must also be deterministic (so dropping it is
       safe). When ``v[i]`` is used exactly once, ``e_i`` may have any
       side effects (single substitution preserves the evaluation count).
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: NameTypeMap | None = None,
        ctx: PipelineContext | None = None,
    ) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types
        self.ctx = ctx

    @staticmethod
    def _classify_uses(
        var_name: str, block: frog_ast.Block
    ) -> tuple[bool, bool, dict[int, int]]:
        """Walk ``block`` and classify references to ``var_name``.

        Returns ``(has_bare_use, has_non_constant_index, index_counts)``
        where ``index_counts[k]`` is the number of ``var_name[k]`` accesses
        for constant integer ``k``.
        """

        class _Classifier(Visitor[None]):
            def __init__(self, name: str) -> None:
                self.name = name
                self.total_var_refs = 0
                self.array_access_refs = 0
                self.has_non_constant = False
                self.counts: dict[int, int] = {}

            def result(self) -> None:
                pass

            def visit_variable(self, var: frog_ast.Variable) -> None:
                if var.name == self.name:
                    self.total_var_refs += 1

            def visit_array_access(self, aa: frog_ast.ArrayAccess) -> None:
                if (
                    isinstance(aa.the_array, frog_ast.Variable)
                    and aa.the_array.name == self.name
                ):
                    self.array_access_refs += 1
                    if isinstance(aa.index, frog_ast.Integer):
                        self.counts[aa.index.num] = self.counts.get(aa.index.num, 0) + 1
                    else:
                        self.has_non_constant = True

        visitor = _Classifier(var_name)
        visitor.visit(block)
        has_bare = visitor.total_var_refs > visitor.array_access_refs
        return has_bare, visitor.has_non_constant, visitor.counts

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
                and isinstance(statement.the_type, frog_ast.ProductType)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.value, frog_ast.Tuple)
            ):
                continue

            tuple_values = statement.value.values
            unfolded_types = statement.the_type.types
            if len(tuple_values) != len(unfolded_types):
                continue

            var_name = statement.var.name
            remaining = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            has_bare, has_non_const, counts = self._classify_uses(var_name, remaining)
            # Refuse to fire when the variable has no uses in this block:
            # it may be referenced from an enclosing scope (e.g. when this
            # block is the body of an if-branch and the use is in the
            # surrounding method body). Removing the declaration here
            # would leave those outer-scope references dangling.
            if not counts and not has_bare and not has_non_const:
                continue
            if has_bare:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Local Tuple Literal",
                            reason=(
                                f"Cannot inline '{var_name}': has a bare use "
                                f"(not as v[k])"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Restructure so '{var_name}' is only "
                                f"referenced as '{var_name}[k]'"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue
            if has_non_const:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Local Tuple Literal",
                            reason=(
                                f"Cannot inline '{var_name}': accessed at a "
                                f"non-constant index"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Constant-fold the index expression for "
                                f"'{var_name}[...]' first"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue
            if counts and (
                max(counts.keys()) >= len(tuple_values) or min(counts.keys()) < 0
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

            # v itself must not be reassigned later.
            if (
                SearchVisitor(functools.partial(is_written_to, var_name)).visit(
                    remaining
                )
                is not None
            ):
                continue

            # No free variable of any e_i may be reassigned later.
            free_var_reassigned = False
            for e_i in tuple_values:
                free_vars = VariableCollectionVisitor().visit(copy.deepcopy(e_i))
                if any(
                    SearchVisitor(functools.partial(is_written_to, fv.name)).visit(
                        remaining
                    )
                    is not None
                    for fv in free_vars
                ):
                    free_var_reassigned = True
                    break
            if free_var_reassigned:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Local Tuple Literal",
                            reason=(
                                f"Cannot inline '{var_name}': a free variable "
                                f"of some tuple element is reassigned later"
                            ),
                            location=statement.origin,
                            suggestion=None,
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            # Per-element purity check: dropped or duplicated elements must
            # be free of non-deterministic calls.
            purity_blocked = False
            for i, e_i in enumerate(tuple_values):
                count_i = counts.get(i, 0)
                if count_i != 1 and has_nondeterministic_call(
                    e_i, self._proof_namespace, self._proof_let_types
                ):
                    purity_blocked = True
                    if self.ctx is not None:
                        self.ctx.near_misses.append(
                            NearMiss(
                                transform_name="Inline Local Tuple Literal",
                                reason=(
                                    f"Cannot inline '{var_name}': element "
                                    f"{i} has a non-deterministic call but "
                                    f"is used {count_i} time(s) "
                                    f"(needs exactly 1)"
                                ),
                                location=statement.origin,
                                suggestion=(
                                    "Hoist the non-deterministic call to "
                                    "its own deterministic local"
                                ),
                                variable=var_name,
                                method=None,
                            )
                        )
                    break
            if purity_blocked:
                continue

            # Substitute every v[k] occurrence with a deep copy of e_k.
            def matches_indexed_use(target_name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.ArrayAccess)
                    and isinstance(node.the_array, frog_ast.Variable)
                    and node.the_array.name == target_name
                    and isinstance(node.index, frog_ast.Integer)
                )

            while True:
                aa = SearchVisitor(
                    functools.partial(matches_indexed_use, var_name)
                ).visit(remaining)
                if aa is None:
                    break
                k = aa.index.num
                remaining = ReplaceTransformer(
                    aa, copy.deepcopy(tuple_values[k])
                ).transform(remaining)

            return self.transform_block(
                frog_ast.Block(
                    list(block.statements[:index]) + list(remaining.statements)
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


class InlineLocalTupleLiteral(TransformPass):
    name = "Inline Local Tuple Literal"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineLocalTupleLiteralTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
            ctx=ctx,
        ).transform(game)


class ExtractRepeatedTupleAccessTransformer(BlockTransformer):
    """Extract repeated ``var[constant]`` accesses and slice expressions.

    **Tuple phase.** When ``v[i]`` (variable + integer index) appears
    2+ times in a block and ``v`` is declared with a product (tuple)
    type, inserts ``Ti __cse_v_i__ = v[i];`` right after ``v``'s
    assignment and replaces every occurrence with the new variable.
    Also fires when ``v`` is a ``GenericFor`` loop binder, inserting the
    extraction at the top of the loop body. This symmetrises games whose
    loop body source writes ``m = e[0]`` explicitly against games whose
    loop body obtains the same accesses via inlining a helper method.

    (Method parameters are intentionally NOT eligible for tuple
    extraction: doing so breaks the ``[v[0], v[1], ...] -> v`` fold in
    ``SimplifyTuple`` when a reconstructed tuple literal elsewhere
    references the same indices.)

    **Slice phase.** When a ``v[A:B]`` slice expression (variable base,
    syntactically-equal bounds) appears 2+ times in a block, inserts
    ``BitString<B - A> __cse_slice_v_N__ = v[A:B];`` at the definition
    point (after ``v``'s block-local assignment, or at position 0 for
    method parameters / fields / enclosing-scope bases) and replaces
    every matching slice with the new variable. Unlike the tuple phase,
    method parameters ARE eligible, because no canonicalization pass
    folds a concatenation of slices back into the base variable.

    The slice phase symmetrises canonical forms between games that
    hoist a named slice at source level (``k2enc = m[A:B];`` then using
    ``k2enc`` in multiple branches) against games whose scan-loop body
    obtains the same slice via inlining a helper + concat-equality
    decomposition.
    """

    def __init__(self) -> None:
        super().__init__()
        # Loop-binder types visible from the enclosing ``GenericFor``.
        # Extraction for these is inserted at position 0 of the loop body.
        self._scope_types: dict[str, frog_ast.Type] = {}

    def transform_generic_for(self, gf: frog_ast.GenericFor) -> frog_ast.GenericFor:
        new_over = self.transform(gf.over)
        saved = dict(self._scope_types)
        try:
            self._scope_types[gf.var_name] = gf.var_type
            new_block = self.transform(gf.block)
        finally:
            self._scope_types = saved
        if new_block is gf.block and new_over is gf.over:
            return gf
        return frog_ast.GenericFor(gf.var_type, gf.var_name, new_over, new_block)

    @staticmethod
    def _has_full_reconstruction(
        var_name: str, base_type: frog_ast.ProductType, block: frog_ast.Block
    ) -> bool:
        """Return True iff ``block`` contains a tuple literal whose values
        are exactly ``[var_name[0], var_name[1], ..., var_name[n-1]]`` in
        order, where ``n = len(base_type.types)``.

        Such a literal would be folded back to ``var_name`` by
        ``SimplifyTuple``; CSE'ing any of its index accesses would block
        that fold.
        """
        n = len(base_type.types)

        def is_full_recon(node: frog_ast.ASTNode) -> bool:
            if not isinstance(node, frog_ast.Tuple):
                return False
            if len(node.values) != n:
                return False
            for i, val in enumerate(node.values):
                if not (
                    isinstance(val, frog_ast.ArrayAccess)
                    and isinstance(val.the_array, frog_ast.Variable)
                    and val.the_array.name == var_name
                    and isinstance(val.index, frog_ast.Integer)
                    and val.index.num == i
                ):
                    return False
            return True

        return SearchVisitor(is_full_recon).visit(block) is not None

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        """Expose ProductType method parameters for tuple-extraction.

        Symmetrises games whose source-level code already extracts
        ``v = ct0[1]`` against games whose source uses the param access
        ``ct0[1]`` inline.  Block-local declarations still shadow params
        on name collision.
        """
        saved = dict(self._scope_types)
        try:
            for param in method.signature.parameters:
                if isinstance(param.type, frog_ast.ProductType):
                    self._scope_types[param.name] = param.type
            new_block = self.transform(method.block)
        finally:
            self._scope_types = saved
        if new_block is method.block:
            return method
        return frog_ast.Method(method.signature, new_block)

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        var_types: dict[str, frog_ast.Type] = dict(self._scope_types)
        # Sentinel -1 = scope-external (insert at top of this block).
        var_def_idx: dict[str, int] = {name: -1 for name in var_types}
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

            # Don't CSE when the variable's full tuple-literal
            # reconstruction ``[v[0], v[1], ..., v[n-1]]`` appears
            # somewhere in the block: extracting one index would block
            # ``SimplifyTuple``'s ``[v[0], v[1], ...] -> v`` fold-back,
            # leaving the canonical form less reduced.
            if self._has_full_reconstruction(var_name, base_type, block):
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

        # Slice-extraction phase: extract repeated ``v[A:B]`` slices
        # (variable base, syntactically-equal bounds) into a local
        # ``BitString<B - A> cse = v[A:B];``. Mirrors the tuple path
        # but uses structural equality on the full Slice expression.
        # Unlike the tuple path, method parameters are eligible as
        # bases (SimplifyTuple only folds ArrayAccess, not Slice, so
        # hoisting a slice of a param doesn't interact).
        slice_occurrences: list[frog_ast.Slice] = []
        for stmt in block.statements:

            def slice_collector(node: frog_ast.ASTNode) -> bool:
                if isinstance(node, frog_ast.Slice) and isinstance(
                    node.the_array, frog_ast.Variable
                ):
                    slice_occurrences.append(node)
                return False

            SearchVisitor(slice_collector).visit(stmt)

        # Group by structural equality.
        slice_groups: list[tuple[frog_ast.Slice, int]] = []
        for sl in slice_occurrences:
            for idx, (rep, cnt) in enumerate(slice_groups):
                if sl == rep:
                    slice_groups[idx] = (rep, cnt + 1)
                    break
            else:
                slice_groups.append((sl, 1))

        for rep_slice, count in slice_groups:
            if count < 2:
                continue
            assert isinstance(rep_slice.the_array, frog_ast.Variable)
            var_name = rep_slice.the_array.name

            # Determine insertion point: after block-local def if any,
            # else at top (scope-external: param / field / enclosing).
            def_idx = -1
            for idx, stmt in enumerate(block.statements):
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
                    and stmt.var.name == var_name
                    and stmt.the_type is not None
                ):
                    def_idx = idx
                    break

            # Skip if base is reassigned anywhere after def (or anywhere
            # in block for scope-external case). Reassignment would
            # invalidate the hoist.
            def _is_reassigned_slice(name: str, node: frog_ast.ASTNode) -> bool:
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

            check_from = def_idx + 1 if def_idx >= 0 else 0
            remaining_block = frog_ast.Block(list(block.statements[check_from:]))
            if (
                SearchVisitor(functools.partial(_is_reassigned_slice, var_name)).visit(
                    remaining_block
                )
                is not None
            ):
                continue

            insert_at = def_idx + 1 if def_idx >= 0 else 0

            # Build a CSE name that does not collide with prior hoists
            # on the same base variable (different (start, end) pairs in
            # the same block would otherwise alias). Use a counter over
            # existing assignments whose name matches the prefix.
            prefix = f"__cse_slice_{var_name}_"
            existing = 0
            for stmt in block.statements:
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name.startswith(prefix)
                ):
                    existing += 1
            cse_name = f"{prefix}{existing}__"
            length_expr = frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.SUBTRACT,
                copy.deepcopy(rep_slice.end),
                copy.deepcopy(rep_slice.start),
            )
            elem_type = frog_ast.BitStringType(length_expr)

            new_assignment = frog_ast.Assignment(
                elem_type,
                frog_ast.Variable(cse_name),
                copy.deepcopy(rep_slice),
            )

            new_stmts = list(block.statements[:insert_at])
            new_stmts.append(new_assignment)
            remaining = frog_ast.Block(list(block.statements[insert_at:]))

            def _match_slice(target: frog_ast.Slice, node: frog_ast.ASTNode) -> bool:
                return node == target

            while True:
                match = SearchVisitor(functools.partial(_match_slice, rep_slice)).visit(
                    remaining
                )
                if match is None:
                    break
                remaining = ReplaceTransformer(
                    match, frog_ast.Variable(cse_name)
                ).transform(remaining)

            new_stmts.extend(remaining.statements)
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class ExtractRepeatedTupleAccess(TransformPass):
    """Extract repeated tuple element accesses and slice expressions."""

    name = "Extract Repeated Tuple Access"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ExtractRepeatedTupleAccessTransformer().transform(game)


class InlineMultiUsePureExpression(TransformPass):
    name = "Inline Multi-Use Pure Expressions"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        function_var_names: set[str] = set()
        if ctx.proof_let_types is not None:
            for pair in ctx.proof_let_types.type_map:
                if isinstance(pair.type, frog_ast.FunctionType):
                    function_var_names.add(pair.name)
        return InlineMultiUsePureExpressionTransformer(
            function_var_names=function_var_names
        ).transform(game)


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
        pinned = self.ctx.pinned_fields if self.ctx is not None else set()
        while changed:
            changed = False
            # Try inlining declared fields. Pinned fields (registered by a
            # producing pass via ``PipelineContext.pinned_fields``) are
            # considered only for same-method inlining; cross-method inlining
            # of a pinned field would re-expose the pattern the producer was
            # canonicalizing, preventing the fixed-point loop from converging.
            # ``_try_inline_field`` enforces the same-method-only restriction
            # when the field is pinned.
            for field_name in list(self.field_names):
                new_game = self._try_inline_field(
                    result, field_name, is_pinned=field_name in pinned
                )
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
                new_game = self._try_inline_field(result, orphan, is_pinned=False)
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
        self, game: frog_ast.Game, field_name: str, is_pinned: bool = False
    ) -> frog_ast.Game | None:
        """Try to inline a single field. Returns new game or None.

        When *is_pinned* is True, cross-method inlining is rejected: a
        producing pass (e.g. ``HoistDeterministicCallToInitialize``) has
        asked that this field survive because re-inlining it across
        methods would re-expose the pattern the producer was canonicalizing,
        causing the fixed-point loop to oscillate. Same-method inlining is
        still allowed because the producer targets non-Initialize calls,
        and same-method substitution doesn't introduce such calls.
        """

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
            if is_pinned:
                # Producer pinned this field; reject cross-method inline to
                # avoid oscillation with the producer's re-fire.
                return None
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
            # Use the game's actual fields (not ``self.field_names``,
            # which is only refreshed at the ``transform_game`` level).
            field_name_set = {f.name for f in game.fields}
            # Promotion branch: when some free vars are Initialize-locals
            # rather than fields, try to promote them to fields so the
            # cross-method inline can then fire.  See
            # ``InlineSingleUseFieldViaLocalPromotion.md``.
            #
            # Gate: only attempt promotion when the field's RHS is a
            # top-level bitstring concatenation (``||`` chain).  This is
            # the shape used for Hash-input layouts that
            # ``ConcatEqualityDecompose`` matches against a slice-wise
            # equality on the use side.  Other shapes (e.g. tuple
            # projections ``v[0]``) do not benefit from promotion and
            # can perturb the canonical form that already works via
            # other routes.
            is_concat_chain = (
                isinstance(assign_expr, frog_ast.BinaryOperation)
                and assign_expr.operator == frog_ast.BinaryOperators.OR
            )
            local_fv_names: list[str] = []
            seen: set[str] = set()
            for fv in free_vars:
                if fv.name not in field_name_set and fv.name not in seen:
                    local_fv_names.append(fv.name)
                    seen.add(fv.name)
            if local_fv_names and is_concat_chain:
                promoted = self._try_promote_locals(
                    game,
                    field_name,
                    local_fv_names,
                    assign_method_idx,
                    assign_stmt_idx,
                )
                if promoted is None:
                    return None
                return self._try_inline_field(promoted, field_name)
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

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def _try_promote_locals(
        self,
        game: frog_ast.Game,
        field_name: str,
        local_names: list[str],
        assign_method_idx: int,
        assign_stmt_idx: int,
    ) -> frog_ast.Game | None:
        """Promote each local in ``local_names`` to a game field so the
        cross-method inlining path can treat its RHS as referencing only
        fields.  Returns the promoted game, or ``None`` if any local is
        not a promotion candidate (emitting a ``NearMiss`` describing
        which precondition failed).

        A local ``L`` is a promotion candidate iff:

        1. Its sole defining statement is a top-level ``Sample``,
           ``UniqueSample``, or typed ``Assignment`` in the same method
           as the field being inlined, at an index strictly less than
           ``assign_stmt_idx``.
        2. ``_count_assigns_recursive`` over the whole game returns 1 for
           ``L`` (no reassignments anywhere).

        The soundness argument (see design doc
        ``2026-04-22-promote-locals-for-cross-method-inline-design.md``)
        relies on Initialize executing exactly once per game lifecycle,
        so a single top-level definition in Initialize has the same
        lifetime as a field assigned in Initialize.
        """
        method = game.methods[assign_method_idx]
        method_stmts = method.block.statements
        existing_field_names = {f.name for f in game.fields}
        reserved = set(existing_field_names)
        promotions: list[tuple[str, str, frog_ast.Type, int, frog_ast.Statement]] = []
        for local_name in local_names:
            # Total assignments across whole game must equal 1.
            total = sum(
                _count_assigns_recursive(m.block, local_name) for m in game.methods
            )
            if total != 1:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Field",
                            reason=(
                                f"Cannot promote local '{local_name}' for "
                                f"cross-method inlining of field "
                                f"'{field_name}': reassigned {total} times "
                                f"(need exactly 1)"
                            ),
                            location=None,
                            suggestion=None,
                            variable=local_name,
                            method=None,
                        )
                    )
                return None
            # Locate the defining statement: top-level typed
            # Sample/UniqueSample/Assignment in the same method, before
            # the field's assignment.
            def_idx = -1
            def_stmt: frog_ast.Statement | None = None
            for si in range(assign_stmt_idx):
                stmt = method_stmts[si]
                if (
                    isinstance(
                        stmt,
                        (
                            frog_ast.Sample,
                            frog_ast.UniqueSample,
                            frog_ast.Assignment,
                        ),
                    )
                    and stmt.the_type is not None
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name == local_name
                ):
                    def_idx = si
                    def_stmt = stmt
                    break
            if def_stmt is None:
                # Distinguish: defined later (in this method, after the
                # field) vs not at top level in this method at all.
                defined_later = False
                defined_nested = False
                for si in range(assign_stmt_idx, len(method_stmts)):
                    stmt = method_stmts[si]
                    if (
                        isinstance(
                            stmt,
                            (
                                frog_ast.Sample,
                                frog_ast.UniqueSample,
                                frog_ast.Assignment,
                            ),
                        )
                        and stmt.the_type is not None
                        and isinstance(stmt.var, frog_ast.Variable)
                        and stmt.var.name == local_name
                    ):
                        defined_later = True
                        break
                if not defined_later:
                    # Count == 1, but no top-level typed def in this
                    # method at all — it must be inside a nested block
                    # or be an untyped assignment.
                    defined_nested = True
                if self.ctx is not None:
                    if defined_later:
                        reason = (
                            f"Cannot promote local '{local_name}' for "
                            f"cross-method inlining of field "
                            f"'{field_name}': defined after field's "
                            f"assignment"
                        )
                    elif defined_nested:
                        reason = (
                            f"Cannot promote local '{local_name}' for "
                            f"cross-method inlining of field "
                            f"'{field_name}': defined in a nested block "
                            f"or via an untyped assignment, not at top "
                            f"level"
                        )
                    else:
                        reason = (
                            f"Cannot promote local '{local_name}' for "
                            f"cross-method inlining of field "
                            f"'{field_name}': defining statement is not "
                            f"a sample or typed assignment"
                        )
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Inline Single-Use Field",
                            reason=reason,
                            location=None,
                            suggestion=None,
                            variable=local_name,
                            method=None,
                        )
                    )
                return None
            assert isinstance(
                def_stmt,
                (frog_ast.Sample, frog_ast.UniqueSample, frog_ast.Assignment),
            )
            assert def_stmt.the_type is not None
            i = 0
            while f"_promoted_{local_name}_{i}" in reserved:
                i += 1
            new_name = f"_promoted_{local_name}_{i}"
            reserved.add(new_name)
            promotions.append(
                (local_name, new_name, def_stmt.the_type, def_idx, def_stmt)
            )

        # Build the promoted game.
        new_game = copy.deepcopy(game)
        for local_name, new_name, ftype, _, _ in promotions:
            new_game.fields.append(frog_ast.Field(copy.deepcopy(ftype), new_name, None))
        new_stmts = list(new_game.methods[assign_method_idx].block.statements)
        for local_name, new_name, _, def_idx, _ in promotions:
            old = new_stmts[def_idx]
            if isinstance(old, frog_ast.Sample):
                new_stmts[def_idx] = frog_ast.Sample(
                    None,
                    frog_ast.Variable(new_name),
                    copy.deepcopy(old.sampled_from),
                )
            elif isinstance(old, frog_ast.UniqueSample):
                new_stmts[def_idx] = frog_ast.UniqueSample(
                    None,
                    frog_ast.Variable(new_name),
                    copy.deepcopy(old.unique_set),
                    copy.deepcopy(old.sampled_from),
                )
            elif isinstance(old, frog_ast.Assignment):
                new_stmts[def_idx] = frog_ast.Assignment(
                    None,
                    frog_ast.Variable(new_name),
                    copy.deepcopy(old.value),
                )
        new_game.methods[assign_method_idx].block = frog_ast.Block(new_stmts)
        for local_name, new_name, _, _, _ in promotions:
            matcher = functools.partial(
                lambda name, node: (
                    isinstance(node, frog_ast.Variable) and node.name == name
                ),
                local_name,
            )
            while True:
                found = SearchVisitor(matcher).visit(new_game)
                if found is None:
                    break
                new_game = ReplaceTransformer(
                    found, frog_ast.Variable(new_name)
                ).transform(new_game)
        return new_game


class InlineSingleUseField(TransformPass):
    name = "Inline Single-Use Field"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InlineSingleUseFieldTransformer(
            proof_namespace=ctx.proof_namespace, ctx=ctx
        ).transform(game)


# ---------------------------------------------------------------------------
# HoistGroupExpToInitialize — cache field^X computations as new fields
# ---------------------------------------------------------------------------


def _is_groupelem_field(fld: frog_ast.Field) -> bool:
    return isinstance(fld.type, frog_ast.GroupElemType)


def _free_var_names(expr: frog_ast.Expression) -> set[str]:
    return {v.name for v in VariableCollectionVisitor().visit(copy.deepcopy(expr))}


def _stmt_writes_var(stmt: frog_ast.Statement, name: str) -> bool:
    """True if *stmt* (top-level only) assigns/samples to ``name``."""
    return (
        isinstance(stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
        and isinstance(stmt.var, frog_ast.Variable)
        and stmt.var.name == name
    )


class _GroupExpFinder(Visitor[Optional[frog_ast.BinaryOperation]]):
    """Find the first ``Variable(name) ^ <expr>`` BinaryOperation in a tree."""

    def __init__(self, base_field_name: str) -> None:
        self._base_field_name = base_field_name
        self._found: Optional[frog_ast.BinaryOperation] = None

    def result(self) -> Optional[frog_ast.BinaryOperation]:
        return self._found

    def leave_binary_operation(self, node: frog_ast.BinaryOperation) -> None:
        if self._found is not None:
            return
        if node.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return
        if (
            isinstance(node.left_expression, frog_ast.Variable)
            and node.left_expression.name == self._base_field_name
        ):
            self._found = node


class HoistGroupExpToInitializeTransformer:
    """Hoist ``<F> ^ <X>`` expressions into a fresh field assigned in Init,
    where ``F`` is a single-write ``GroupElem<G>`` field with a pure
    deterministic RHS and ``X`` is a stable expression.

    Soundness: the new field captures the value of ``F.rhs ^ X`` at
    Initialize-end.  This is semantics-preserving when:

    1. ``F`` is assigned exactly once, at top level of ``Initialize``.
    2. ``F``'s RHS contains no non-deterministic call.
    3. Every free variable of ``X`` is a game field or game parameter
       (cross-method-visible, stable across oracle calls).
    4. None of the free variables of ``F.rhs`` or ``X`` are reassigned
       after ``F``'s definition (in or outside ``Initialize``).

    The new field's RHS is the inlined form ``F.rhs ^ X`` so that the
    immediately-following ``GroupElem Simplification`` pass can fold any
    nested power-of-power.

    Motivation: closes the gap where ``field1 = G.generator ^ v1`` and a
    use site ``field1 ^ field2`` would otherwise hide the nested
    ``(g^v1)^field2`` pattern from the algebraic simplifier.
    """

    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        result = game
        changed = True
        while changed:
            changed = False
            new_game = self._try_one_hoist(result)
            if new_game is not None:
                result = new_game
                changed = True
        return result

    # pylint: disable-next=too-many-return-statements,too-many-locals,too-many-branches
    def _try_one_hoist(self, game: frog_ast.Game) -> frog_ast.Game | None:
        # Locate Initialize.
        init_idx: int | None = None
        for mi, method in enumerate(game.methods):
            if method.signature.name == "Initialize":
                init_idx = mi
                break
        if init_idx is None:
            return None

        # Defensive guard: if Initialize has an early return (nested in if/for,
        # or any non-terminal ReturnStatement), splicing a new assignment could
        # be skipped on the early-return path.  Well-typed FrogLang Void
        # Initialize methods cannot produce this shape through the parser, but
        # AST-level consumers could.  Mirrors HoistDeterministicCallToInitialize.
        init_stmts_for_guard = game.methods[init_idx].block.statements
        if _has_early_return_in_init(init_stmts_for_guard):
            return None

        field_names = {f.name for f in game.fields}
        param_names = {p.name for p in game.parameters}

        # Walk every GroupElem field eligible to be a base.
        for fld in game.fields:
            if not _is_groupelem_field(fld):
                continue
            base_info = self._eligible_base(game, fld.name, init_idx)
            if base_info is None:
                continue
            base_assign_idx, base_rhs = base_info

            # Look for `<base> ^ X` in any non-Init method.
            for mi, method in enumerate(game.methods):
                if mi == init_idx:
                    continue
                hit = _GroupExpFinder(fld.name).visit(method.block)
                if hit is None:
                    continue
                exp_x = hit.right_expression
                # X must be stable: free vars all in fields or params.
                if not all(
                    n in field_names or n in param_names for n in _free_var_names(exp_x)
                ):
                    continue
                # Free vars of base_rhs and X must not be mutated after the
                # base's definition.
                free_all = _free_var_names(base_rhs) | _free_var_names(exp_x)
                if not self._free_vars_stable_after_base(
                    game, init_idx, base_assign_idx, free_all
                ):
                    continue
                if any(n == fld.name for n in _free_var_names(exp_x)):
                    continue  # avoid degenerate self-reference
                fresh = self._fresh_name(field_names)
                # Mark as pinned so ``InlineSingleUseField`` leaves it
                # alone — see ``PipelineContext.pinned_fields``.
                self.ctx.pinned_fields.add(fresh)
                return self._build_hoisted_game(
                    game,
                    init_idx,
                    base_assign_idx,
                    base_rhs,
                    exp_x,
                    fresh,
                    target_method_idx=mi,
                    target_node=hit,
                )
        return None

    @staticmethod
    def _fresh_name(existing: set[str]) -> str:
        i = 0
        while True:
            name = f"_hge_{i}"
            if name not in existing:
                return name
            i += 1

    def _eligible_base(
        self, game: frog_ast.Game, field_name: str, init_idx: int
    ) -> tuple[int, frog_ast.Expression] | None:
        total = sum(_count_assigns_recursive(m.block, field_name) for m in game.methods)
        if total != 1:
            return None
        init_stmts = list(game.methods[init_idx].block.statements)
        for si, stmt in enumerate(init_stmts):
            if (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is None
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field_name
            ):
                if has_nondeterministic_call(
                    stmt.value, self.ctx.proof_namespace, self.ctx.proof_let_types
                ):
                    return None
                return si, stmt.value
        return None

    @staticmethod
    def _free_vars_stable_after_base(
        game: frog_ast.Game,
        init_idx: int,
        base_assign_idx: int,
        names: set[str],
    ) -> bool:
        if not names:
            return True

        def writes_any(node: frog_ast.ASTNode) -> bool:
            hits: list[bool] = []

            def _visit(n: frog_ast.ASTNode) -> bool:
                if isinstance(
                    n,
                    (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample),
                ):
                    if isinstance(n.var, frog_ast.Variable) and n.var.name in names:
                        hits.append(True)
                    else:
                        # ``arr[i] = v`` / ``M[k] = v`` mutates the base
                        # container named by the root Variable — treat as a
                        # write to that name.
                        root = n.var
                        while isinstance(root, frog_ast.ArrayAccess):
                            root = root.the_array
                        if isinstance(root, frog_ast.Variable) and root.name in names:
                            hits.append(True)
                return False

            SearchVisitor(_visit).visit(node)
            return bool(hits)

        init_stmts = game.methods[init_idx].block.statements
        for si in range(base_assign_idx + 1, len(init_stmts)):
            if writes_any(init_stmts[si]):
                return False
        for mi, method in enumerate(game.methods):
            if mi == init_idx:
                continue
            for stmt in method.block.statements:
                if writes_any(stmt):
                    return False
        return True

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def _build_hoisted_game(
        self,
        game: frog_ast.Game,
        init_idx: int,
        base_assign_idx: int,
        base_rhs: frog_ast.Expression,
        exp_x: frog_ast.Expression,
        fresh_name: str,
        target_method_idx: int,
        target_node: frog_ast.BinaryOperation,
    ) -> frog_ast.Game:
        new_game = copy.deepcopy(game)
        # Append field declaration.
        new_field = frog_ast.Field(
            the_type=frog_ast.GroupElemType(
                copy.deepcopy(_first_group_arg(base_rhs, exp_x))
            ),
            name=fresh_name,
            value=None,
        )
        new_game.fields = list(new_game.fields) + [new_field]
        # Insert assignment in Initialize right after base's def.
        init = new_game.methods[init_idx]
        init_stmts = list(init.block.statements)
        new_assign = frog_ast.Assignment(
            the_type=None,
            var=frog_ast.Variable(fresh_name),
            value=frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                copy.deepcopy(base_rhs),
                copy.deepcopy(exp_x),
            ),
        )
        init_stmts.insert(base_assign_idx + 1, new_assign)
        init.block = frog_ast.Block(init_stmts)
        # Replace the matched expression in the target method with the new
        # field reference.  Re-find by structural equality (target_node was
        # found on the original `game`, not on `new_game`).
        target_method = new_game.methods[target_method_idx]

        def _matches_target(n: frog_ast.ASTNode) -> bool:
            return isinstance(n, frog_ast.BinaryOperation) and n == target_node

        match = SearchVisitor(_matches_target).visit(target_method.block)
        if match is not None:
            target_method.block = ReplaceTransformer(
                match, frog_ast.Variable(fresh_name)
            ).transform(target_method.block)
        return new_game


def _first_group_arg(
    *exprs: frog_ast.Expression,
) -> frog_ast.Expression:
    """Best-effort: extract the ``G`` from a ``GroupGenerator(G)`` if any of
    *exprs* contains one; else default to ``Variable('G')``.

    The new field's type only needs to be a syntactic ``GroupElem<G>`` for
    the typechecker; later passes infer types from context.
    """
    for e in exprs:

        def _find(n: frog_ast.ASTNode) -> bool:
            return isinstance(n, frog_ast.GroupGenerator)

        gen = SearchVisitor(_find).visit(e)
        if isinstance(gen, frog_ast.GroupGenerator):
            return copy.deepcopy(gen.group)
    return frog_ast.Variable("G")


class HoistGroupExpToInitialize(TransformPass):
    name = "Hoist GroupElem Exponent To Initialize"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return HoistGroupExpToInitializeTransformer(ctx).transform(game)


# ---------------------------------------------------------------------------
# RefactorGroupElemFieldExp — rewrite ``g^(a*b)`` field RHS as ``F^b`` when
# another field already holds ``g^a``.
# ---------------------------------------------------------------------------


def _exp_with_generator_base(
    expr: frog_ast.Expression,
) -> Optional[frog_ast.Expression]:
    """If *expr* is ``<group>.generator ^ <e>``, return ``<e>``."""
    if not isinstance(expr, frog_ast.BinaryOperation):
        return None
    if expr.operator != frog_ast.BinaryOperators.EXPONENTIATE:
        return None
    base = expr.left_expression
    if (
        isinstance(base, frog_ast.FieldAccess)
        and base.name == "generator"
        and isinstance(base.the_object, frog_ast.Variable)
    ):
        return expr.right_expression
    if isinstance(base, frog_ast.GroupGenerator):
        return expr.right_expression
    return None


class RefactorGroupElemFieldExpTransformer:
    """Express ``Field1 = g^(a*b)`` as ``Field1 = Field2 ^ b`` when there
    is a separate ``Field2 = g^a`` already, both assigned at top level of
    ``Initialize`` and ``Field2`` defined first.

    Bridges otherwise-canonical games where one side directly uses
    ``Field1`` in a comparison against ``c^b`` and the other side has the
    comparison structurally eliminated.  After refactoring, the
    :class:`InjectiveEqualitySimplify` field-RHS substitution path can
    re-express the comparison using cross-method-visible fields only.

    Soundness: ``g^(a*b) = (g^a)^b = Field2^b`` and both fields'
    Initialize-time values are otherwise identical to before.
    """

    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        result = game
        changed = True
        while changed:
            changed = False
            new_game = self._try_one(result)
            if new_game is not None:
                result = new_game
                changed = True
        return result

    def _try_one(self, game: frog_ast.Game) -> frog_ast.Game | None:
        init_idx: int | None = None
        for mi, method in enumerate(game.methods):
            if method.signature.name == "Initialize":
                init_idx = mi
                break
        if init_idx is None:
            return None
        init_stmts = list(game.methods[init_idx].block.statements)
        gen_field_assigns: dict[str, tuple[int, frog_ast.Expression]] = {}
        for si, stmt in enumerate(init_stmts):
            if not (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is None
                and isinstance(stmt.var, frog_ast.Variable)
            ):
                continue
            name = stmt.var.name
            fld = next((f for f in game.fields if f.name == name), None)
            if fld is None or not isinstance(fld.type, frog_ast.GroupElemType):
                continue
            total = sum(_count_assigns_recursive(m.block, name) for m in game.methods)
            if total != 1:
                continue
            exponent = _exp_with_generator_base(stmt.value)
            if exponent is None:
                continue
            gen_field_assigns[name] = (si, exponent)

        for f1_name, (f1_idx, f1_exp) in gen_field_assigns.items():
            if not isinstance(f1_exp, frog_ast.BinaryOperation):
                continue
            if f1_exp.operator != frog_ast.BinaryOperators.MULTIPLY:
                continue
            for f2_name, (f2_idx, f2_exp) in gen_field_assigns.items():
                if f2_name == f1_name:
                    continue
                a, b = f1_exp.left_expression, f1_exp.right_expression
                other: Optional[frog_ast.Expression] = None
                if f2_exp == a:
                    other = b
                elif f2_exp == b:
                    other = a
                if other is None:
                    continue
                # Soundness: at f1's def, f2 must already hold its value.
                # If f2 is currently after f1, try to move f2 just before f1
                # — provided f2's free vars are all defined strictly before
                # f1's current position.
                stmts = list(init_stmts)
                f1_target_idx = f1_idx
                if f2_idx > f1_idx:
                    f2_free = {
                        v.name
                        for v in VariableCollectionVisitor().visit(
                            copy.deepcopy(stmts[f2_idx])
                        )
                    }
                    f2_free.discard(f2_name)
                    if not self._defined_before(stmts, f1_idx, f2_free):
                        continue
                    f2_stmt = stmts.pop(f2_idx)
                    # f2 was after f1; insert before f1 at f1_idx (new index).
                    stmts.insert(f1_idx, f2_stmt)
                    f1_target_idx = f1_idx + 1
                new_assign = copy.deepcopy(stmts[f1_target_idx])
                assert isinstance(new_assign, frog_ast.Assignment)
                new_assign.value = frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.EXPONENTIATE,
                    frog_ast.Variable(f2_name),
                    copy.deepcopy(other),
                )
                stmts[f1_target_idx] = new_assign
                new_game = copy.deepcopy(game)
                new_game.methods[init_idx].block = frog_ast.Block(stmts)
                return new_game
        return None

    @staticmethod
    def _defined_before(
        stmts: list[frog_ast.Statement], idx: int, names: set[str]
    ) -> bool:
        """True if every name in *names* is assigned by some statement in
        ``stmts[:idx]``."""
        if not names:
            return True
        remaining = set(names)
        for i in range(idx):
            stmt = stmts[i]
            if (
                isinstance(
                    stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
                )
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in remaining
            ):
                remaining.remove(stmt.var.name)
                if not remaining:
                    return True
        return not remaining


class RefactorGroupElemFieldExp(TransformPass):
    name = "Refactor GroupElem Field Exponent"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return RefactorGroupElemFieldExpTransformer(ctx).transform(game)


class _DeterministicCallCollector(Visitor[list[frog_ast.FuncCall]]):
    """Collect all FuncCall nodes that call deterministic primitive methods.

    When *function_var_names* is non-empty, also collect FuncCall nodes whose
    callee is a ``Variable(name)`` with ``name in function_var_names`` — these
    represent calls to ``Function<D, R>`` variables, which FrogLang treats as
    deterministic (SEMANTICS.md: calling a sampled Function<D,R> twice with
    the same input returns the same output).
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace,
        function_var_names: set[str] | None = None,
    ) -> None:
        self._proof_namespace = proof_namespace
        self._function_var_names = function_var_names or set()
        self._calls: list[frog_ast.FuncCall] = []

    def result(self) -> list[frog_ast.FuncCall]:
        return self._calls

    def visit_func_call(self, node: frog_ast.FuncCall) -> None:
        m = _lookup_primitive_method(node.func, self._proof_namespace)
        if m is not None and m.deterministic:
            self._calls.append(node)
            return
        if (
            isinstance(node.func, frog_ast.Variable)
            and node.func.name in self._function_var_names
        ):
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

    Scans top-level statements *and* if-statement conditions. If-conditions
    are always evaluated when the if-statement is reached, so extracting a
    deterministic call from a condition to a let-binding immediately before
    the if-statement is semantics-preserving (under argument stability) — the
    call evaluates the same number of times and on the same argument values.
    If-statement *bodies* are not scanned at this level; they are nested
    blocks handled by ``BlockTransformer`` recursion.

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
        function_var_names: set[str] | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self.proof_namespace = proof_namespace
        self._ctx = ctx
        self._function_var_names = function_var_names or set()
        self._proof_let_types = proof_let_types
        self.counter = 0

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        # Collect all deterministic calls from top-level statements, plus
        # if-statement *conditions* (always evaluated when the if is reached,
        # so extracting a deterministic call from a condition to a top-level
        # let preserves the number of evaluations and the value, given
        # argument stability). If-statement *bodies* are not scanned here:
        # BlockTransformer recurses into them as their own blocks.
        all_calls: list[frog_ast.FuncCall] = []
        for statement in block.statements:
            collector = _DeterministicCallCollector(
                self.proof_namespace, self._function_var_names
            )
            if isinstance(statement, frog_ast.IfStatement):
                for condition in statement.conditions:
                    collector.visit(condition)
            else:
                collector.visit(statement)
            all_calls.extend(collector.result())

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
        if m is not None:
            return_type = copy.deepcopy(m.return_type)
        elif (
            isinstance(representative.func, frog_ast.Variable)
            and representative.func.name in self._function_var_names
            and self._proof_let_types is not None
        ):
            ftype = self._proof_let_types.get(representative.func.name)
            assert isinstance(ftype, frog_ast.FunctionType)
            return_type = copy.deepcopy(ftype.range_type)
        else:
            # Should not happen — collector only emits primitive-deterministic
            # or function-var calls.
            return block

        # Advance counter past any existing __determ_N__ names in the block
        # to avoid colliding with names created by earlier pipeline iterations.
        for stmt in block.statements:
            if isinstance(
                stmt, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            ) and isinstance(stmt.var, frog_ast.Variable):
                existing = stmt.var.name
                if existing.startswith("__determ_") and existing.endswith("__"):
                    try:
                        n = int(existing[len("__determ_") : -len("__")])
                    except ValueError:
                        continue
                    if n >= self.counter:
                        self.counter = n + 1

        var_name = f"__determ_{self.counter}__"
        self.counter += 1

        # Create the new assignment statement
        new_assignment = frog_ast.Assignment(
            return_type,  # type: ignore[arg-type]
            frog_ast.Variable(var_name),
            copy.deepcopy(representative),
        )

        # Find the first statement containing a duplicate call (in a top-level
        # statement or an if-condition) and insert before it.
        insert_index: int | None = None
        for index, statement in enumerate(block.statements):
            collector = _DeterministicCallCollector(
                self.proof_namespace, self._function_var_names
            )
            if isinstance(statement, frog_ast.IfStatement):
                for condition in statement.conditions:
                    collector.visit(condition)
            else:
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

        # Find first and last statement indices containing a call from the
        # group. Scan top-level statements and if-conditions.
        first_idx: int | None = None
        last_idx: int | None = None
        for idx, stmt in enumerate(block.statements):
            collector = _DeterministicCallCollector(
                self.proof_namespace, self._function_var_names
            )
            if isinstance(stmt, frog_ast.IfStatement):
                for cond in stmt.conditions:
                    collector.visit(cond)
            else:
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

        # The intermediate region (between the first and last call's evaluation
        # points) excludes the call statements themselves. When the first
        # statement is an IfStatement with the call in its condition, the
        # if-body executes *after* the condition's call but *before* any
        # subsequent call, so include those branch blocks in the scan.
        intermediate_stmts: list[frog_ast.Statement] = list(
            block.statements[first_idx + 1 : last_idx]
        )
        first_stmt = block.statements[first_idx]
        if isinstance(first_stmt, frog_ast.IfStatement):
            for branch in first_stmt.blocks:
                intermediate_stmts.extend(branch.statements)
        intermediate = frog_ast.Block(intermediate_stmts)
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
            collector = _AllPrimitiveFuncCallCollector(self.proof_namespace)
            if isinstance(statement, frog_ast.IfStatement):
                for condition in statement.conditions:
                    collector.visit(condition)
            else:
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


def _is_stable_arg(  # pylint: disable=too-many-arguments, too-many-positional-arguments
    expr: frog_ast.Expression,
    field_names: set[str],
    param_names: set[str],
    proof_namespace: frog_ast.Namespace | None = None,
    function_var_names: set[str] | None = None,
    proof_let_names: set[str] | None = None,
    local_alias_names: set[str] | None = None,
) -> bool:
    """Return True if *expr* is stable across method invocations.

    An expression is stable if it depends only on game fields, game parameters,
    constants, and deterministic calls whose arguments are themselves stable.

    When *proof_namespace* / *function_var_names* are provided, nested
    ``FuncCall`` nodes are accepted as stable iff the callee is a primitive
    method annotated ``deterministic`` or a ``Function<D, R>`` variable named
    in *function_var_names*, and every argument is recursively stable.

    When *proof_let_names* is provided, ``Variable`` nodes whose name appears
    in that set are treated as stable: proof-level ``let:`` bindings are
    compile-time constants from the game's perspective.

    When *local_alias_names* is provided, ``Variable`` nodes whose name appears
    in that set are treated as stable. The caller is responsible for ensuring
    each name in this set is bound exactly once (in the relevant method's top
    level) to an expression that is itself stable, so that the variable's value
    is invariant across the lifetime of the game state it depends on.
    """
    if isinstance(
        expr,
        (
            frog_ast.Integer,
            frog_ast.Boolean,
            frog_ast.BitStringLiteral,
            frog_ast.NoneExpression,
        ),
    ):
        return True

    def _recurse(sub: frog_ast.Expression) -> bool:
        return _is_stable_arg(
            sub,
            field_names,
            param_names,
            proof_namespace,
            function_var_names,
            proof_let_names,
            local_alias_names,
        )

    if isinstance(expr, frog_ast.Variable):
        return (
            expr.name in field_names
            or expr.name in param_names
            or (proof_let_names is not None and expr.name in proof_let_names)
            or (local_alias_names is not None and expr.name in local_alias_names)
        )
    if isinstance(expr, frog_ast.FieldAccess):
        return _recurse(expr.the_object)
    if isinstance(expr, frog_ast.BinaryOperation):
        return _recurse(expr.left_expression) and _recurse(expr.right_expression)
    if isinstance(expr, frog_ast.UnaryOperation):
        return _recurse(expr.expression)
    if isinstance(expr, frog_ast.ArrayAccess):
        return _recurse(expr.the_array) and _recurse(expr.index)
    if isinstance(expr, frog_ast.Slice):
        return _recurse(expr.the_array) and _recurse(expr.start) and _recurse(expr.end)
    if isinstance(expr, frog_ast.FuncCall):
        is_det_primitive = False
        if proof_namespace is not None:
            m = _lookup_primitive_method(expr.func, proof_namespace)
            if m is not None and m.deterministic:
                is_det_primitive = True
        is_function_var = (
            function_var_names is not None
            and isinstance(expr.func, frog_ast.Variable)
            and expr.func.name in function_var_names
        )
        if not (is_det_primitive or is_function_var):
            return False
        return all(_recurse(a) for a in expr.args)
    return False


def _collect_field_names_in_args(
    expr: frog_ast.Expression, field_names: set[str]
) -> set[str]:
    """Return the set of field names referenced in *expr*.

    Descends through field accesses, unary/binary operators, and nested
    ``FuncCall`` nodes (including the callee variable itself, so that a
    ``Function<D, R>`` game field used as a nested callee is reported).
    """
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
    if isinstance(expr, frog_ast.ArrayAccess):
        return _collect_field_names_in_args(
            expr.the_array, field_names
        ) | _collect_field_names_in_args(expr.index, field_names)
    if isinstance(expr, frog_ast.Slice):
        return (
            _collect_field_names_in_args(expr.the_array, field_names)
            | _collect_field_names_in_args(expr.start, field_names)
            | _collect_field_names_in_args(expr.end, field_names)
        )
    if isinstance(expr, frog_ast.FuncCall):
        result: set[str] = set()
        if isinstance(expr.func, frog_ast.Variable) and expr.func.name in field_names:
            result.add(expr.func.name)
        for a in expr.args:
            result |= _collect_field_names_in_args(a, field_names)
        return result
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


def _build_local_stable_alias_map(  # pylint: disable=too-many-arguments, too-many-positional-arguments
    method: frog_ast.Method,
    field_names: set[str],
    param_names: set[str],
    proof_namespace: frog_ast.Namespace | None,
    function_var_names: set[str] | None,
    proof_let_names: set[str] | None,
) -> dict[str, frog_ast.Expression]:
    """Return a map from local variable name -> RHS expression for top-level
    single-assignment locals in *method* whose RHS is stable.

    "Stable" means the RHS depends only on game fields, parameters, proof-level
    let-bindings, constants, deterministic primitive calls (over stable args),
    Function<D,R> calls (over stable args), and other locals already proven
    stable. Iterates to a fixed point so chains like ``a = NG.Generator();
    b = NG.Exp(a, field2);`` produce both ``a`` and ``b`` as aliases.

    Excluded:
    - Locals re-assigned more than once.
    - Sampled / UniqueSample-bound locals (their value is non-deterministic).
    - Locals shadowed by fields or parameters.
    - Self-assignments (``x = x``), which are no-ops left by other transforms.
    """
    counts: dict[str, int] = {}
    bindings: dict[str, frog_ast.Expression] = {}
    sampled: set[str] = set()
    for stmt in method.block.statements:
        if isinstance(stmt, (frog_ast.Sample, frog_ast.UniqueSample)) and isinstance(
            stmt.var, frog_ast.Variable
        ):
            sampled.add(stmt.var.name)
            counts[stmt.var.name] = counts.get(stmt.var.name, 0) + 1
            continue
        if not isinstance(stmt, frog_ast.Assignment):
            continue
        if not isinstance(stmt.var, frog_ast.Variable):
            continue
        name = stmt.var.name
        if name in field_names or name in param_names:
            continue
        if isinstance(stmt.value, frog_ast.Variable) and stmt.value.name == name:
            # Skip self-assignments.
            continue
        counts[name] = counts.get(name, 0) + 1
        bindings[name] = stmt.value

    aliases: dict[str, frog_ast.Expression] = {}
    while True:
        changed = False
        for name, expr in bindings.items():
            if name in aliases:
                continue
            if counts.get(name, 0) != 1:
                continue
            if name in sampled:
                continue
            if _is_stable_arg(
                expr,
                field_names,
                param_names,
                proof_namespace,
                function_var_names,
                proof_let_names,
                local_alias_names=set(aliases),
            ):
                aliases[name] = expr
                changed = True
        if not changed:
            break
    return aliases


def _expand_aliases(
    expr: frog_ast.ASTNode,
    aliases: dict[str, frog_ast.Expression],
) -> frog_ast.ASTNode:
    """Recursively expand local stable aliases in *expr* to a fixed point.

    Pure substitution. No side-effects on the input.
    """
    if not aliases:
        return expr
    prev: frog_ast.ASTNode | None = None
    current: frog_ast.ASTNode = expr
    for _ in range(32):  # bound in case of pathological aliases
        if prev is not None and prev == current:
            break
        prev = current
        sm: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=False)
        for n, v in aliases.items():
            sm.set(frog_ast.Variable(n), copy.deepcopy(v))
        current = SubstitutionTransformer(sm).transform(current)
    return current


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
        proof_let_types: NameTypeMap | None = None,
        function_var_names: set[str] | None = None,
    ) -> None:
        self.proof_namespace = proof_namespace
        self._ctx = ctx
        self._proof_let_types = proof_let_types
        self._function_var_names = function_var_names or set()

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        field_names = {f.name for f in game.fields}
        param_names = {p.name for p in game.parameters}
        proof_let_names: set[str] = (
            {pair.name for pair in self._proof_let_types.type_map}
            if self._proof_let_types is not None
            else set()
        )

        # Build per-method stable-alias maps once. A "stable alias" is a
        # top-level single-assignment local whose RHS depends only on stable
        # things (fields, params, let-bindings, constants, deterministic
        # calls over stable args, and other already-stable aliases).
        # Common case: CSE introduces ``v1 = NG.Generator();`` and reuses v1
        # in multiple field RHSs and oracle expressions; expanding through v1
        # makes the cross-method match succeed.
        method_aliases: list[dict[str, frog_ast.Expression]] = [
            _build_local_stable_alias_map(
                m,
                field_names,
                param_names,
                self.proof_namespace,
                None,
                proof_let_names,
            )
            for m in game.methods
        ]

        # Phase 1: Collect field assignments with deterministic RHS
        # (field_name, det_call, method_idx, expanded_call)
        field_aliases: list[tuple[str, frog_ast.FuncCall, int, frog_ast.FuncCall]] = []
        for midx, method in enumerate(game.methods):
            init_aliases = method_aliases[midx]
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
                    _is_stable_arg(
                        a,
                        field_names,
                        param_names,
                        proof_namespace=self.proof_namespace,
                        proof_let_names=proof_let_names,
                        local_alias_names=set(init_aliases),
                    )
                    for a in call.args
                ):
                    continue

                # Soundness check: the alias must be in Initialize.
                # If it's in an oracle, the adversary could call the
                # replacement-target oracle before the alias-source oracle,
                # reading an uninitialized field.
                if method.signature.name != "Initialize":
                    continue

                # Compute the expanded form of the call (with stable locals
                # resolved). Use this for downstream cross-method matching
                # and for collecting the underlying field dependencies, so
                # that the no-reassignment guards apply to the real fields.
                expanded_call_node = _expand_aliases(copy.deepcopy(call), init_aliases)
                assert isinstance(expanded_call_node, frog_ast.FuncCall)
                expanded_call = expanded_call_node

                # Soundness check: the alias field and all argument fields
                # must not be reassigned after the alias statement in this
                # method, and must not be assigned in any other method.
                arg_fields: set[str] = set()
                for a in expanded_call.args:
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

                field_aliases.append((stmt.var.name, call, midx, expanded_call))

        if not field_aliases:
            return game

        # Phase 2: For each field alias, check if the same call (modulo local
        # alias expansion) appears in other methods and replace it.
        for alias_field_name, alias_call, alias_midx, expanded_call in field_aliases:
            result = self._try_replace(
                game,
                alias_field_name,
                alias_call,
                alias_midx,
                expanded_call,
                method_aliases,
            )
            if result is not None:
                return result

        return game

    def _try_replace(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        game: frog_ast.Game,
        alias_field_name: str,
        alias_call: frog_ast.FuncCall,
        alias_midx: int,
        expanded_call: frog_ast.FuncCall,
        method_aliases: list[dict[str, frog_ast.Expression]],
    ) -> frog_ast.Game | None:
        """Try to replace *alias_call* with *alias_field_name* in another method.

        Matches calls modulo stable-local-alias expansion: a target call ``c``
        matches if either ``c == alias_call`` literally, or
        ``expand(c, target_aliases) == expand(alias_call, init_aliases)``.
        """
        del alias_call  # alias_call is referenced only via expanded_call now
        for midx, method in enumerate(game.methods):
            if midx == alias_midx:
                continue
            target_aliases = method_aliases[midx]
            collector = _DeterministicCallCollector(
                self.proof_namespace, self._function_var_names
            )
            collector.visit(method.block)
            target_call = next(
                (
                    c
                    for c in collector.result()
                    if _expand_aliases(copy.deepcopy(c), target_aliases)
                    == expanded_call
                ),
                None,
            )
            if target_call is None:
                continue
            # Found a match — replace and return
            new_game = copy.deepcopy(game)
            new_collector = _DeterministicCallCollector(
                self.proof_namespace, self._function_var_names
            )
            new_collector.visit(new_game.methods[midx].block)
            for new_call in new_collector.result():
                if (
                    _expand_aliases(copy.deepcopy(new_call), target_aliases)
                    == expanded_call
                ):
                    new_game.methods[midx] = ReplaceTransformer(
                        new_call,
                        frog_ast.Variable(alias_field_name),
                    ).transform(new_game.methods[midx])
                    return new_game
        return None


class _AliasAwareReplacer(ReplaceTransformer):
    """Replace any node whose alias-expanded form equals *match_node*.

    Used by HoistDeterministicCallToInitialize to rewrite occurrences of a
    hoisted call in Initialize's return expression even when the candidate
    is reached only through one or more local-variable aliases defined
    earlier in Initialize.
    """

    def __init__(
        self,
        match_node: frog_ast.ASTNode,
        replacement: frog_ast.ASTNode,
        expand: Callable[[frog_ast.ASTNode], frog_ast.ASTNode],
    ) -> None:
        super().__init__(match_node, replacement)
        self._match_expanded = match_node
        self._expand = expand

    def transform_ast_node(self, exp: frog_ast.ASTNode) -> Optional[frog_ast.ASTNode]:
        # Cheap pre-check: avoid expanding leaves that clearly can't match.
        if isinstance(exp, (frog_ast.FuncCall, frog_ast.Variable)):
            if self._expand(exp) == self._match_expanded:
                return copy.deepcopy(self.replace_with)
        return None


def _has_early_return_in_init(stmts: Sequence[frog_ast.Statement]) -> bool:
    """Return True if *stmts* contains a ReturnStatement that is not the
    terminal top-level statement. Any return nested inside an if/for block
    counts as "early"; a ReturnStatement at the end of the top-level list
    does not.
    """
    for i, stmt in enumerate(stmts):
        if isinstance(stmt, frog_ast.ReturnStatement):
            if i != len(stmts) - 1:
                return True
            continue
        if isinstance(stmt, frog_ast.IfStatement):
            for blk in stmt.blocks:
                if _contains_return(blk.statements):
                    return True
        elif isinstance(stmt, (frog_ast.NumericFor, frog_ast.GenericFor)):
            if _contains_return(stmt.block.statements):
                return True
    return False


def _contains_return(stmts: Sequence[frog_ast.Statement]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, frog_ast.ReturnStatement):
            return True
        if isinstance(stmt, frog_ast.IfStatement):
            for blk in stmt.blocks:
                if _contains_return(blk.statements):
                    return True
        elif isinstance(stmt, (frog_ast.NumericFor, frog_ast.GenericFor)):
            if _contains_return(stmt.block.statements):
                return True
    return False


class HoistDeterministicCallToInitializeTransformer:
    """Hoist a deterministic call into Initialize and cache it in a new field.

    When a deterministic call ``f(stable_args)`` appears in a non-Initialize
    method and none of its fields are reassigned outside Initialize, introduce
    a new field ``<fresh> = f(stable_args);`` at the end of Initialize and
    replace every structurally-equal occurrence of the call with ``<fresh>``.

    This is the create-field counterpart of ``CrossMethodFieldAlias``, which
    only reuses fields that already exist.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace,
        ctx: PipelineContext | None = None,
        proof_let_types: NameTypeMap | None = None,
    ) -> None:
        self.proof_namespace = proof_namespace
        self._ctx = ctx
        self._proof_let_types = proof_let_types

    def _function_var_types(self, game: frog_ast.Game) -> dict[str, frog_ast.Type]:
        """Return name->range_type for every Function<D,R> variable in scope.

        Includes game fields, game parameters, and proof-level let-bindings.
        """
        out: dict[str, frog_ast.Type] = {}
        for f in game.fields:
            if isinstance(f.type, frog_ast.FunctionType):
                out[f.name] = f.type.range_type
        for p in game.parameters:
            if isinstance(p.type, frog_ast.FunctionType):
                out[p.name] = p.type.range_type
        if self._proof_let_types is not None:
            for pair in self._proof_let_types.type_map:
                if isinstance(pair.type, frog_ast.FunctionType):
                    out[pair.name] = pair.type.range_type
        return out

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        field_names = {f.name for f in game.fields}
        param_names = {p.name for p in game.parameters}
        function_var_return_types = self._function_var_types(game)
        function_var_names = set(function_var_return_types)
        proof_let_names: set[str] = (
            {pair.name for pair in self._proof_let_types.type_map}
            if self._proof_let_types is not None
            else set()
        )

        init_idx: int | None = None
        for midx, method in enumerate(game.methods):
            if method.signature.name == "Initialize":
                init_idx = midx
                break
        if init_idx is None:
            return game

        # Soundness guard: an "early" return (nested inside if/for) would
        # skip an appended hoisted assignment and leave the new field
        # uninitialized while oracles still read it. A terminal top-level
        # return (the common case for non-Void Initialize in composed
        # reductions) is safe: we insert the hoisted assignment *before* it.
        init_block_stmts = list(game.methods[init_idx].block.statements)
        if _has_early_return_in_init(init_block_stmts):
            if self._ctx is not None:
                self._ctx.near_misses.append(
                    NearMiss(
                        transform_name=("Hoist Deterministic Call to Initialize"),
                        reason=(
                            "Initialize has an early return (nested in "
                            "if/for); appending a hoisted assignment would "
                            "be skipped on the early-return path"
                        ),
                        location=None,
                        suggestion=(
                            "Restructure Initialize so any return is the "
                            "terminal top-level statement"
                        ),
                        variable=None,
                        method="Initialize",
                    )
                )
            return game
        # Locate the terminal return (if present). Any hoisted assignment
        # will be spliced just before it.
        init_terminal_return_idx: int | None = None
        if init_block_stmts and isinstance(
            init_block_stmts[-1], frog_ast.ReturnStatement
        ):
            init_terminal_return_idx = len(init_block_stmts) - 1

        existing_aliased_calls: list[frog_ast.FuncCall] = []
        for stmt in game.methods[init_idx].block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is None
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name in field_names
                and isinstance(stmt.value, frog_ast.FuncCall)
            ):
                existing_aliased_calls.append(stmt.value)

        candidate: frog_ast.FuncCall | None = None
        candidate_return_type: frog_ast.Type | None = None
        for midx, method in enumerate(game.methods):
            if midx == init_idx:
                continue
            collector = _DeterministicCallCollector(
                self.proof_namespace, function_var_names=function_var_names
            )
            collector.visit(method.block)
            for call in collector.result():
                # Resolve return type: primitive method or Function<D,R> variable
                return_type: frog_ast.Type | None = None
                m = _lookup_primitive_method(call.func, self.proof_namespace)
                if m is not None:
                    return_type = m.return_type
                elif (
                    isinstance(call.func, frog_ast.Variable)
                    and call.func.name in function_var_return_types
                ):
                    return_type = function_var_return_types[call.func.name]
                if return_type is None:
                    continue
                if not call.args:
                    continue
                if not all(
                    _is_stable_arg(
                        a,
                        field_names,
                        param_names,
                        proof_namespace=self.proof_namespace,
                        function_var_names=function_var_names,
                        proof_let_names=proof_let_names,
                    )
                    for a in call.args
                ):
                    continue
                if any(call == ea for ea in existing_aliased_calls):
                    continue
                arg_fields: set[str] = set()
                for a in call.args:
                    arg_fields |= _collect_field_names_in_args(a, field_names)
                # For Function<D,R> calls, the callee variable itself is state
                # we depend on — if it's a game field it must not be mutated
                # outside Initialize, same requirement as the arguments.
                if (
                    isinstance(call.func, frog_ast.Variable)
                    and call.func.name in field_names
                ):
                    arg_fields.add(call.func.name)
                mutated = self._fields_mutated_outside_init(game, init_idx, arg_fields)
                if mutated:
                    if self._ctx is not None:
                        self._ctx.near_misses.append(
                            NearMiss(
                                transform_name=(
                                    "Hoist Deterministic Call to Initialize"
                                ),
                                reason=(
                                    f"Cannot hoist call: field "
                                    f"{sorted(mutated)[0]!r} is reassigned "
                                    "outside Initialize"
                                ),
                                location=call.origin,
                                suggestion=(
                                    "Stop reassigning the field, or move the "
                                    "call into the same method that reassigns it"
                                ),
                                variable=sorted(mutated)[0],
                                method=method.signature.name,
                            )
                        )
                    continue
                candidate = call
                candidate_return_type = return_type
                break
            if candidate is not None:
                break

        if candidate is None or candidate_return_type is None:
            return game

        new_name = self._fresh_field_name(field_names)
        new_game = copy.deepcopy(game)
        new_game.fields.append(frog_ast.Field(candidate_return_type, new_name, None))
        # Pin the newly introduced field so ``Inline Single-Use Field`` leaves
        # it alone on subsequent iterations — inlining it back would just
        # re-expose the pattern and cause this pass to re-fire, preventing
        # the fixed-point loop from converging.
        if self._ctx is not None:
            self._ctx.pinned_fields.add(new_name)
        init_method = new_game.methods[init_idx]
        hoisted_stmt = frog_ast.Assignment(
            None, frog_ast.Variable(new_name), copy.deepcopy(candidate)
        )
        init_stmts = list(init_method.block.statements)
        if init_terminal_return_idx is not None:
            # Insert just before the terminal return so the new field is set
            # on every path that reaches the return.
            init_stmts.insert(init_terminal_return_idx, hoisted_stmt)
        else:
            init_stmts.append(hoisted_stmt)
        init_method.block = frog_ast.Block(init_stmts)

        # When Initialize has a terminal return, rewrite matches of the
        # candidate inside that return expression — including through local
        # aliases defined earlier in Initialize (e.g. ``x = e; return f(x);``
        # where f(expand(x)) == candidate). Without this, the hoisted field
        # has only a single use on one side of an interchangeability hop,
        # allowing Inline Single-Use Field to fold it back and introducing
        # asymmetry.
        if init_terminal_return_idx is not None:
            new_init = new_game.methods[init_idx]
            new_stmts = list(new_init.block.statements)
            ret_stmt = new_stmts[-1]
            assert isinstance(ret_stmt, frog_ast.ReturnStatement)
            # Build alias map: local single-assignment bindings in Initialize
            # (before the hoisted/terminal statements).
            aliases: dict[str, frog_ast.Expression] = {}
            alias_assign_counts: dict[str, int] = {}
            for stmt in new_stmts[:-1]:
                if stmt is hoisted_stmt:
                    continue
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name not in field_names
                    and stmt.var.name not in param_names
                ):
                    # Ignore self-assignments (``x = x;``) which are no-ops
                    # that other transforms sometimes leave behind; counting
                    # them would disqualify x from being treated as a stable
                    # alias.
                    if (
                        isinstance(stmt.value, frog_ast.Variable)
                        and stmt.value.name == stmt.var.name
                    ):
                        continue
                    name = stmt.var.name
                    alias_assign_counts[name] = alias_assign_counts.get(name, 0) + 1
                    aliases[name] = stmt.value
            # Only use aliases for variables assigned exactly once.
            stable_aliases = {
                n: v for n, v in aliases.items() if alias_assign_counts[n] == 1
            }

            def _expand(expr: frog_ast.ASTNode) -> frog_ast.ASTNode:
                """Recursively expand local aliases in *expr* to a fixed point."""
                prev: frog_ast.ASTNode | None = None
                current: frog_ast.ASTNode = expr
                for _ in range(32):  # bound in case of pathological aliases
                    if prev is not None and prev == current:
                        break
                    prev = current
                    sm: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(
                        identity=False
                    )
                    for n, v in stable_aliases.items():
                        sm.set(frog_ast.Variable(n), copy.deepcopy(v))
                    current = SubstitutionTransformer(sm).transform(current)
                return current

            expanded_candidate = _expand(copy.deepcopy(candidate))

            replacer = _AliasAwareReplacer(
                match_node=expanded_candidate,
                replacement=frog_ast.Variable(new_name),
                expand=_expand,
            )
            new_ret_expr = replacer.transform(ret_stmt.expression)
            new_stmts[-1] = frog_ast.ReturnStatement(new_ret_expr)
            new_init.block = frog_ast.Block(new_stmts)

        for midx, _ in enumerate(new_game.methods):
            if midx == init_idx:
                continue
            while True:
                collector = _DeterministicCallCollector(
                    self.proof_namespace, function_var_names=function_var_names
                )
                collector.visit(new_game.methods[midx].block)
                target = next((c for c in collector.result() if c == candidate), None)
                if target is None:
                    break
                new_game.methods[midx] = ReplaceTransformer(
                    target, frog_ast.Variable(new_name)
                ).transform(new_game.methods[midx])

        return new_game

    @staticmethod
    def _fields_mutated_outside_init(
        game: frog_ast.Game, init_idx: int, fields: set[str]
    ) -> set[str]:
        mutated: set[str] = set()
        if not fields:
            return mutated
        for midx, method in enumerate(game.methods):
            if midx == init_idx:
                continue
            mutated |= _fields_assigned_in_block(method.block, fields)
        return mutated

    @staticmethod
    def _fresh_field_name(existing: set[str]) -> str:
        i = 0
        while f"_hoisted_{i}" in existing:
            i += 1
        return f"_hoisted_{i}"


class HoistDeterministicCallToInitialize(TransformPass):
    name = "Hoist Deterministic Call to Initialize"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return HoistDeterministicCallToInitializeTransformer(
            proof_namespace=ctx.proof_namespace,
            ctx=ctx,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class CrossMethodFieldAlias(TransformPass):
    name = "Cross-Method Field Alias"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        function_var_names: set[str] = set()
        if ctx.proof_let_types is not None:
            for pair in ctx.proof_let_types.type_map:
                if isinstance(pair.type, frog_ast.FunctionType):
                    function_var_names.add(pair.name)
        return CrossMethodFieldAliasTransformer(
            proof_namespace=ctx.proof_namespace,
            ctx=ctx,
            proof_let_types=ctx.proof_let_types,
            function_var_names=function_var_names,
        ).transform(game)


class SplitOpaqueTupleFieldTransformer:
    """Split a tuple-typed field whose RHS is an opaque (non-literal) call.

    Symmetrises canonical forms across reductions where a tuple-returning
    deterministic call is stored in a field and only individual components
    are projected. ``ExtractRepeatedTupleAccess`` and ``TupleIndexFolding``
    handle tuple *literals* (``[a, b]``); they do not see through opaque
    function-call RHSs that happen to return a tuple, e.g.
    ``pq_keys = challenger.Generate();`` where ``pq_keys`` is later used
    only as ``pq_keys[0]`` and ``pq_keys[1]``.
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self._ctx = ctx

    def transform(self, game: frog_ast.Game) -> frog_ast.Game:
        # Iterate over a copy of the field list since we mutate fields.
        for field in list(game.fields):
            if not isinstance(field.type, frog_ast.ProductType):
                continue
            new_game = self._try_split_field(game, field)
            if new_game is not None:
                # Splitting one field per pass keeps the diff small and
                # lets the fixed-point loop reach this transform again
                # on the next iteration to handle further fields.
                return new_game
        return game

    def _try_split_field(
        self, game: frog_ast.Game, field: frog_ast.Field
    ) -> frog_ast.Game | None:
        # 1. Find every assignment to *field* across all methods. Reject if
        # any sits at non-top level (inside if/for) or if there is more than
        # one top-level assignment in total.
        top_level_assigns: list[tuple[int, int, frog_ast.Assignment]] = []
        total_assigns = 0
        for midx, method in enumerate(game.methods):
            for sidx, stmt in enumerate(method.block.statements):
                if (
                    isinstance(stmt, frog_ast.Assignment)
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name == field.name
                ):
                    top_level_assigns.append((midx, sidx, stmt))
            nested_match = SearchVisitor(
                functools.partial(_is_field_assignment, field.name)
            ).visit(method.block)
            # Count of assignments to field anywhere in the method. We use a
            # second scan to compute the total because SearchVisitor.visit
            # returns only the first hit.
            total_assigns += _count_field_assignments(method.block, field.name)
            if nested_match is None:
                continue
        if total_assigns != len(top_level_assigns):
            # Some assignment is inside a nested block.
            return None
        if len(top_level_assigns) != 1:
            return None
        assign_midx, assign_sidx, assignment = top_level_assigns[0]

        # 2. Reject literal-tuple RHS: existing TupleIndexFolding handles it.
        if isinstance(assignment.value, frog_ast.Tuple):
            return None

        # 3. Reject if RHS references the field itself (would create a dangling
        # reference once the field is removed).
        if _VarCountVisitor(field.name).visit(assignment.value) > 0:
            return None

        # 4. Collect all read-uses of *field*. Every read must be of the
        # form ``field[k]`` with constant integer ``k``. Whole-tuple reads
        # (``return field;``, ``field == other_field``) disqualify.
        used_indices: set[int] = set()
        if not _all_reads_are_const_indexed(
            game, field.name, assign_midx, assign_sidx, used_indices
        ):
            return None
        if not used_indices:
            # No reads at all -- leave it for RemoveUnnecessaryFields.
            return None

        # 4. Soundness guard: if the assignment lives in Initialize and
        # Initialize has an early return, splitting could leave per-index
        # fields uninitialized while other methods still read them.
        if game.methods[assign_midx].signature.name == "Initialize":
            init_stmts = list(game.methods[assign_midx].block.statements)
            if _has_early_return_in_init(init_stmts):
                if self._ctx is not None:
                    self._ctx.near_misses.append(
                        NearMiss(
                            transform_name="Split Opaque Tuple Field",
                            reason=(
                                "Initialize has an early return (nested in "
                                "if/for); splitting would leave per-index "
                                "fields uninitialized on the early-return path"
                            ),
                            location=assignment.origin,
                            suggestion=(
                                "Restructure Initialize so any return is the "
                                "terminal top-level statement"
                            ),
                            variable=field.name,
                            method="Initialize",
                        )
                    )
                return None

        # 5. Build the rewritten game.
        assert isinstance(field.type, frog_ast.ProductType)
        component_types = field.type.types
        new_field_names: dict[int, str] = {}
        existing_names = {f.name for f in game.fields}
        for k in sorted(used_indices):
            new_field_names[k] = self._fresh_name(f"{field.name}_{k}", existing_names)
            existing_names.add(new_field_names[k])

        new_game = copy.deepcopy(game)
        # Replace the original field with per-index fields (preserve order).
        new_fields: list[frog_ast.Field] = []
        for f in new_game.fields:
            if f.name == field.name:
                for k in sorted(used_indices):
                    new_fields.append(
                        frog_ast.Field(component_types[k], new_field_names[k], None)
                    )
            else:
                new_fields.append(f)
        new_game.fields = new_fields

        # Pin the new fields to prevent oscillation with InlineSingleUseField.
        if self._ctx is not None:
            for k in sorted(used_indices):
                self._ctx.pinned_fields.add(new_field_names[k])

        # Rewrite the assignment site: introduce ``_tup`` local, then set
        # each per-index field. ``_tup`` name avoids collision with fields
        # and existing method-locals.
        method = new_game.methods[assign_midx]
        local_names = _collect_local_names(method.block)
        tup_name = self._fresh_name("_tup", existing_names | local_names)
        new_stmts = list(method.block.statements)
        # Keep the same RHS expression (deepcopy via the new_game copy).
        original_assign = new_stmts[assign_sidx]
        assert isinstance(original_assign, frog_ast.Assignment)
        rhs = original_assign.value
        replacement_stmts: list[frog_ast.Statement] = [
            frog_ast.Assignment(
                copy.deepcopy(field.type),
                frog_ast.Variable(tup_name),
                rhs,
            )
        ]
        for k in sorted(used_indices):
            replacement_stmts.append(
                frog_ast.Assignment(
                    None,
                    frog_ast.Variable(new_field_names[k]),
                    frog_ast.ArrayAccess(
                        frog_ast.Variable(tup_name), frog_ast.Integer(k)
                    ),
                )
            )
        new_stmts = (
            new_stmts[:assign_sidx] + replacement_stmts + new_stmts[assign_sidx + 1 :]
        )
        method.block = frog_ast.Block(new_stmts)

        # Rewrite every ``field[k]`` read across all methods to ``field_k``.
        # The replacement statements we just inserted contain no references
        # to the original field (RHS guard above), so no skip is needed.
        for m in new_game.methods:
            new_block = _rewrite_indexed_reads(m.block, field.name, new_field_names)
            if new_block is not m.block:
                m.block = new_block

        return new_game

    @staticmethod
    def _fresh_name(prefix: str, existing: set[str]) -> str:
        if prefix not in existing:
            return prefix
        i = 0
        while f"{prefix}_{i}" in existing:
            i += 1
        return f"{prefix}_{i}"


def _is_field_assignment(field_name: str, node: frog_ast.ASTNode) -> bool:
    return (
        isinstance(node, frog_ast.Assignment)
        and isinstance(node.var, frog_ast.Variable)
        and node.var.name == field_name
    )


def _count_field_assignments(node: frog_ast.ASTNode, field_name: str) -> int:
    count = 0

    def visit(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if _is_field_assignment(field_name, n):
            count += 1
        return False

    SearchVisitor(visit).visit(node)
    return count


def _all_reads_are_const_indexed(
    game: frog_ast.Game,
    field_name: str,
    assign_midx: int,
    assign_sidx: int,
    used_indices: set[int],
) -> bool:
    """Return True if every read of ``field_name`` is ``field_name[k]`` for
    integer-constant ``k`` (and record those ``k`` in *used_indices*).

    The unique top-level assignment at (assign_midx, assign_sidx) is excluded
    from the scan: it writes the field, and a write inside its own RHS is not
    a read of the field for our purposes (and the RHS being a non-literal
    is enforced separately).
    """
    for midx, method in enumerate(game.methods):
        for sidx, stmt in enumerate(method.block.statements):
            if midx == assign_midx and sidx == assign_sidx:
                # The assignment statement itself: scan only its RHS.
                assert isinstance(stmt, frog_ast.Assignment)
                if not _check_reads_in(stmt.value, field_name, used_indices):
                    return False
                continue
            if not _check_reads_in(stmt, field_name, used_indices):
                return False
    return True


def _check_reads_in(
    node: frog_ast.ASTNode, field_name: str, used_indices: set[int]
) -> bool:
    """Walk *node*; for every Variable(field_name) ensure its parent is
    ArrayAccess(_, Integer(k)) and record k. Return False on any other
    occurrence.
    """
    # We do this by looking for every Variable occurrence and walking the
    # parent chain via a custom recursive descent: instead, simpler is to
    # find every Variable and require that occurrence to be inside an
    # ArrayAccess whose base is that variable. Implementation: scan all
    # ArrayAccess(field, Integer(k)) and record; then count remaining
    # Variable(field) occurrences and compare.
    indexed_count = 0

    def collect_indexed(n: frog_ast.ASTNode) -> bool:
        nonlocal indexed_count
        if (
            isinstance(n, frog_ast.ArrayAccess)
            and isinstance(n.the_array, frog_ast.Variable)
            and n.the_array.name == field_name
            and isinstance(n.index, frog_ast.Integer)
        ):
            used_indices.add(n.index.num)
            indexed_count += 1
        return False

    SearchVisitor(collect_indexed).visit(node)

    # Now count all Variable occurrences with this name.
    total = _VarCountVisitor(field_name).visit(node)
    # Each indexed access contains one Variable(field) occurrence. If the
    # count of bare Variable occurrences exceeds the indexed-access count,
    # there's a non-projection use.
    return total == indexed_count


def _collect_local_names(block: frog_ast.Block) -> set[str]:
    names: set[str] = set()

    def visit(n: frog_ast.ASTNode) -> bool:
        if isinstance(n, frog_ast.Variable):
            names.add(n.name)
        return False

    SearchVisitor(visit).visit(block)
    return names


def _rewrite_indexed_reads(
    block: frog_ast.Block,
    field_name: str,
    new_field_names: dict[int, str],
) -> frog_ast.Block:
    """Replace every ``field_name[k]`` (constant ``k``) with
    ``Variable(new_field_names[k])`` everywhere in *block*.
    """
    changed = False
    new_stmts: list[frog_ast.Statement] = []
    for stmt in block.statements:
        new_stmt: frog_ast.Statement = stmt
        while True:
            target = SearchVisitor(
                functools.partial(_match_indexed_read, field_name, set(new_field_names))
            ).visit(new_stmt)
            if target is None:
                break
            assert isinstance(target, frog_ast.ArrayAccess)
            assert isinstance(target.index, frog_ast.Integer)
            new_stmt = ReplaceTransformer(
                target, frog_ast.Variable(new_field_names[target.index.num])
            ).transform(new_stmt)
            changed = True
        new_stmts.append(new_stmt)
    if not changed:
        return block
    return frog_ast.Block(new_stmts)


def _match_indexed_read(
    field_name: str, valid_indices: set[int], node: frog_ast.ASTNode
) -> bool:
    return (
        isinstance(node, frog_ast.ArrayAccess)
        and isinstance(node.the_array, frog_ast.Variable)
        and node.the_array.name == field_name
        and isinstance(node.index, frog_ast.Integer)
        and node.index.num in valid_indices
    )


class SplitOpaqueTupleField(TransformPass):
    name = "Split Opaque Tuple Field"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SplitOpaqueTupleFieldTransformer(ctx=ctx).transform(game)
