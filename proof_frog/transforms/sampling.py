"""Sampling-related passes: splice, merge/split uniform, product samples.

These passes normalize how uniform random sampling is represented, ensuring
that equivalent sampling patterns (split, merged, or spliced) converge to the
same canonical form.
"""

from __future__ import annotations

import copy
import functools
from typing import Optional, cast

from sympy import Symbol, simplify as sympy_simplify

from .. import frog_ast
from .. import frog_parser
from ..visitors import (
    Transformer,
    BlockTransformer,
    SearchVisitor,
    ReplaceTransformer,
    VariableCollectionVisitor,
    FrogToSympyVisitor,
)
from ._base import TransformPass, PipelineContext, NearMiss

# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class SimplifySpliceTransformer(BlockTransformer):
    """Replaces slice accesses on a concatenated variable with the originals.

    When a variable is assigned as a concatenation of other variables
    (e.g., ``z = x || y``), subsequent slices that correspond to the
    original components are replaced with direct references to those
    component variables.

    Example::

        z = x || y;
        return z[0 : len1];
      becomes:
        z = x || y;
        return x;
    """

    def __init__(self, variables: dict[str, Symbol | frog_ast.Expression]) -> None:
        self.variables = variables

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        def is_all_concatenated(node: frog_ast.ASTNode) -> bool:
            if isinstance(node, frog_ast.Variable):
                return True
            if not isinstance(node, frog_ast.BinaryOperation):
                return False
            if node.operator is not frog_ast.BinaryOperators.OR:
                return False

            return is_all_concatenated(node.left_expression) and is_all_concatenated(
                node.right_expression
            )

        for index, statement in enumerate(block.statements):
            if not isinstance(statement, frog_ast.Assignment):
                continue
            if not isinstance(statement.var, frog_ast.Variable):
                continue
            if not isinstance(statement.value, frog_ast.BinaryOperation):
                continue

            if not is_all_concatenated(statement.value):
                continue

            # Get variables all concatenated together
            concatenated_var_names = VariableCollectionVisitor().visit(statement.value)

            def find_declaration(variable: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, (frog_ast.Assignment, frog_ast.Sample))
                    and isinstance(node.var, frog_ast.Variable)
                    and node.var.name == variable
                    and isinstance(node.the_type, frog_ast.BitStringType)
                    and node.the_type.parameterization is not None
                )

            # Step 1, find type of variables (to get lengths)

            lengths: list[Symbol] = []
            for var in concatenated_var_names:
                declaration = SearchVisitor(
                    functools.partial(find_declaration, var.name)
                ).visit(block)
                if declaration is None:
                    break
                assert isinstance(declaration, (frog_ast.Assignment, frog_ast.Sample))
                assert isinstance(declaration.the_type, frog_ast.BitStringType)
                assert declaration.the_type.parameterization is not None
                variables_used = VariableCollectionVisitor().visit(
                    declaration.the_type.parameterization
                )
                if len(variables_used) != 1:
                    break
                if variables_used[0].name not in self.variables:
                    break
                lengths.append(
                    FrogToSympyVisitor(self.variables).visit(
                        declaration.the_type.parameterization
                    )
                )

            # We quit because we weren't able to find the length of some variable in our concatenation
            if len(lengths) != len(concatenated_var_names):
                continue

            # Step 2, create slices that map to these vars
            partial_sum = 0
            slices = []
            for length in lengths:
                slices.append(
                    frog_ast.Slice(
                        frog_ast.Variable(statement.var.name),
                        frog_parser.parse_expression(str(partial_sum)),
                        frog_parser.parse_expression(str(partial_sum + length)),
                    )
                )
                partial_sum += length

            # Step 3, replace, so long as none of the variables are changed

            remaining_block = frog_ast.Block(block.statements[index + 1 :])

            def use_or_reassignment(
                no_touch_vars: list[frog_ast.Variable],
                slices: list[frog_ast.Slice],
                node: frog_ast.ASTNode,
            ) -> bool:
                return (
                    isinstance(node, (frog_ast.Assignment, frog_ast.Sample))
                    and (node.var in no_touch_vars)
                ) or node in slices

            made_transformation = False
            while True:
                to_transform = SearchVisitor[
                    frog_ast.Assignment | frog_ast.Sample | frog_ast.Slice
                ](
                    functools.partial(
                        use_or_reassignment,
                        [statement.var] + concatenated_var_names,
                        slices,
                    )
                ).visit(
                    remaining_block
                )

                if (
                    isinstance(to_transform, (frog_ast.Assignment, frog_ast.Sample))
                    or to_transform is None
                ):
                    break

                made_transformation = True

                associated_var = concatenated_var_names[slices.index(to_transform)]

                remaining_block = ReplaceTransformer(
                    to_transform, associated_var
                ).transform(remaining_block)
            if not made_transformation:
                continue
            return self.transform_block(
                frog_ast.Block(copy.deepcopy(block.statements[: index + 1]))
                + remaining_block
            )

        return block


class MergeUniformSamplesTransformer(BlockTransformer):
    """Merges independent uniform BitString samples that are concatenated.

    Transforms:
        BitString<len1> x <- BitString<len1>;
        BitString<len2> y <- BitString<len2>;
        return x || y;
    Into:
        BitString<len1 + len2> x <- BitString<len1 + len2>;
        return x;

    This captures the mathematical fact that concatenating independent
    uniform random bitstrings produces a uniform random bitstring of the
    combined length.
    """

    def __init__(
        self,
        variables: dict[str, Symbol | frog_ast.Expression],
        ctx: PipelineContext | None = None,
    ) -> None:
        self.variables = variables
        self.ctx = ctx

    @staticmethod
    def _flatten_concat(
        node: frog_ast.Expression,
    ) -> list[frog_ast.Variable] | None:
        """Flatten a tree of || operations into a list of leaf variables."""
        if isinstance(node, frog_ast.Variable):
            return [node]
        if (
            isinstance(node, frog_ast.BinaryOperation)
            and node.operator is frog_ast.BinaryOperators.OR
        ):
            left = MergeUniformSamplesTransformer._flatten_concat(node.left_expression)
            right = MergeUniformSamplesTransformer._flatten_concat(
                node.right_expression
            )
            if left is not None and right is not None:
                return left + right
        return None

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            # Find concatenation expressions in returns or assignments
            concat_expr: frog_ast.Expression | None = None
            if isinstance(statement, frog_ast.ReturnStatement):
                concat_expr = statement.expression
            elif (
                isinstance(statement, frog_ast.Assignment)
                and statement.the_type is not None
            ):
                concat_expr = statement.value
            else:
                continue

            if not isinstance(concat_expr, frog_ast.BinaryOperation):
                continue
            if concat_expr.operator is not frog_ast.BinaryOperators.OR:
                continue

            # Flatten the concatenation tree to get leaf variables
            leaf_vars = self._flatten_concat(concat_expr)
            if leaf_vars is None or len(leaf_vars) < 2:
                continue

            # All leaf variables must be distinct (independent samples)
            leaf_names = [v.name for v in leaf_vars]
            if len(leaf_names) != len(set(leaf_names)):
                continue

            # For each leaf variable, find its Sample declaration
            sample_indices: list[int] = []
            lengths: list[Symbol | int] = []
            all_valid = True

            for var in leaf_vars:
                found = False
                for si in range(index):
                    s = block.statements[si]
                    if not (
                        isinstance(s, frog_ast.Sample)
                        and isinstance(s.var, frog_ast.Variable)
                        and s.var.name == var.name
                        and isinstance(s.the_type, frog_ast.BitStringType)
                        and s.the_type.parameterization is not None
                        and isinstance(s.sampled_from, frog_ast.BitStringType)
                        and s.sampled_from.parameterization is not None
                    ):
                        continue

                    # Verify uniform sampling: type param == sampled_from param
                    type_len = FrogToSympyVisitor(self.variables).visit(
                        s.the_type.parameterization
                    )
                    sample_len = FrogToSympyVisitor(self.variables).visit(
                        s.sampled_from.parameterization
                    )
                    if type_len is None or sample_len is None or type_len != sample_len:
                        all_valid = False
                        break

                    sample_indices.append(si)
                    lengths.append(type_len)
                    found = True
                    break

                if not found or not all_valid:
                    all_valid = False
                    break

            if not all_valid:
                continue

            # Check each variable is used only in the concatenation
            all_single_use = True
            sample_index_set = set(sample_indices)
            for vi, var in enumerate(leaf_vars):

                def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == name

                # Check all statements except the sample declaration and
                # the concatenation statement itself
                other_stmts = [
                    s
                    for si, s in enumerate(block.statements)
                    if si not in (sample_indices[vi], index)
                ]
                other_block = frog_ast.Block(other_stmts)
                if (
                    SearchVisitor(functools.partial(uses_var, var.name)).visit(
                        other_block
                    )
                    is not None
                ):
                    all_single_use = False
                    break

            if not all_single_use:
                if self.ctx is not None and len(leaf_vars) >= 2:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Merge Uniform Samples",
                            reason=(
                                f"Samples '{leaf_vars[0].name}' and "
                                f"'{leaf_vars[1].name}' not merged: not "
                                f"used exclusively via concatenation"
                            ),
                            location=None,
                            suggestion=None,
                            variable=leaf_vars[0].name,
                            method=None,
                        )
                    )
                continue

            # Compute combined length
            combined_length = sum(lengths[1:], lengths[0])
            combined_length_expr = frog_parser.parse_expression(str(combined_length))
            combined_type = frog_ast.BitStringType(combined_length_expr)
            # Build new block
            new_var = frog_ast.Variable(leaf_vars[0].name)
            new_sample = frog_ast.Sample(
                combined_type,
                new_var,
                cast(
                    frog_ast.Expression,
                    frog_ast.BitStringType(
                        frog_parser.parse_expression(str(combined_length))
                    ),
                ),
            )

            new_statements: list[frog_ast.Statement] = []
            for si, s in enumerate(block.statements):
                if si in sample_index_set:
                    continue  # Remove individual samples
                if si == index:
                    # Insert merged sample, then the statement with concat replaced
                    new_statements.append(new_sample)
                    if isinstance(statement, frog_ast.ReturnStatement):
                        new_statements.append(
                            frog_ast.ReturnStatement(copy.deepcopy(new_var))
                        )
                    elif isinstance(statement, frog_ast.Assignment):
                        new_statements.append(
                            frog_ast.Assignment(
                                statement.the_type,
                                copy.deepcopy(statement.var),
                                copy.deepcopy(new_var),
                            )
                        )
                else:
                    new_statements.append(s)

            return self.transform_block(frog_ast.Block(new_statements))

        return block


class MergeProductSamplesTransformer(BlockTransformer):
    """Merges independent uniform samples combined into a tuple into a single
    product-type sample.

    Transforms:
        A a <- A;
        B b <- B;
        return [a, b];
    Into:
        A * B a <- A * B;
        return a;

    This captures the mathematical fact that sampling each component of a
    product type independently and combining them is equivalent to sampling
    the product type jointly.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            # Find tuple expressions in return statements only.
            # We do not merge in assignments because the assigned variable
            # may be accessed via element indices (e.g. k[0], k[1]), which
            # would prevent other simplifications like XOR simplification.
            if not isinstance(statement, frog_ast.ReturnStatement):
                continue
            tuple_expr = statement.expression

            if not isinstance(tuple_expr, frog_ast.Tuple):
                continue
            if len(tuple_expr.values) < 2:
                continue

            # Each element must be a distinct variable
            leaf_vars: list[frog_ast.Variable] = []
            all_vars = True
            for val in tuple_expr.values:
                if not isinstance(val, frog_ast.Variable):
                    all_vars = False
                    break
                leaf_vars.append(val)
            if not all_vars:
                continue

            leaf_names = [v.name for v in leaf_vars]
            if len(leaf_names) != len(set(leaf_names)):
                continue

            # For each leaf variable, find its Sample declaration
            sample_indices: list[int] = []
            component_types: list[frog_ast.Type] = []
            all_valid = True

            for var in leaf_vars:
                found = False
                for si in range(index):
                    s = block.statements[si]
                    if not (
                        isinstance(s, frog_ast.Sample)
                        and isinstance(s.var, frog_ast.Variable)
                        and s.var.name == var.name
                        and s.the_type is not None
                        and isinstance(s.the_type, frog_ast.Type)
                    ):
                        continue

                    # Verify uniform sampling: declared type == sampled-from type
                    if s.the_type != s.sampled_from:
                        all_valid = False
                        break

                    sample_indices.append(si)
                    component_types.append(s.the_type)
                    found = True
                    break

                if not found or not all_valid:
                    all_valid = False
                    break

            if not all_valid:
                continue

            # Check each variable is used only in the tuple
            all_single_use = True
            for vi, var in enumerate(leaf_vars):

                def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                    return isinstance(node, frog_ast.Variable) and node.name == name

                other_stmts = [
                    s
                    for si, s in enumerate(block.statements)
                    if si not in (sample_indices[vi], index)
                ]
                other_block = frog_ast.Block(other_stmts)
                if (
                    SearchVisitor(functools.partial(uses_var, var.name)).visit(
                        other_block
                    )
                    is not None
                ):
                    all_single_use = False
                    break

            if not all_single_use:
                continue

            product_type: frog_ast.Type = frog_ast.ProductType(
                [copy.deepcopy(t) for t in component_types]
            )

            new_var = frog_ast.Variable(leaf_vars[0].name)
            new_sample = frog_ast.Sample(
                product_type,
                new_var,
                frog_ast.Tuple(
                    [
                        cast(frog_ast.Expression, copy.deepcopy(t))
                        for t in component_types
                    ]
                ),
            )

            # Build new block
            sample_index_set = set(sample_indices)
            new_statements: list[frog_ast.Statement] = []
            for si, s in enumerate(block.statements):
                if si in sample_index_set:
                    continue  # Remove individual samples
                if si == index:
                    new_statements.append(new_sample)
                    new_statements.append(
                        frog_ast.ReturnStatement(copy.deepcopy(new_var))
                    )
                else:
                    new_statements.append(s)

            return self.transform_block(frog_ast.Block(new_statements))

        return block


class _SliceReplacer(Transformer):
    """Replaces Slice nodes of a specific variable with new variables,
    matching by sympy-resolved bounds rather than object identity."""

    def __init__(
        self,
        var_name: str,
        bound_to_var: list[tuple[Symbol | int, Symbol | int, frog_ast.Variable]],
        variables: dict[str, Symbol | frog_ast.Expression],
    ) -> None:
        self.var_name = var_name
        self.bound_to_var = bound_to_var
        self.variables = variables

    def transform_slice(self, node: frog_ast.Slice) -> Optional[frog_ast.ASTNode]:
        if not (
            isinstance(node.the_array, frog_ast.Variable)
            and node.the_array.name == self.var_name
        ):
            return None
        start = FrogToSympyVisitor(self.variables).visit(node.start)
        end = FrogToSympyVisitor(self.variables).visit(node.end)
        if start is None or end is None:
            return None
        for b_start, b_end, new_var in self.bound_to_var:
            if (
                sympy_simplify(start - b_start) == 0
                and sympy_simplify(end - b_end) == 0
            ):
                return copy.deepcopy(new_var)
        return None


class SplitUniformSampleTransformer(BlockTransformer):
    """Splits a uniform BitString sample accessed only via non-overlapping
    slices into multiple independent samples.

    Transforms:
        BitString<len1 + len2> z <- BitString<len1 + len2>;
        ... z[0 : len1] ... z[len1 : len1 + len2] ...
    Into:
        BitString<len1> z_0 <- BitString<len1>;
        BitString<len2> z_1 <- BitString<len2>;
        ... z_0 ... z_1 ...

    The slices do not need to cover the full range. Unused portions of the
    sample are simply discarded, which is sound because unused random bits
    do not affect the distribution of the used bits.
    """

    def __init__(
        self,
        variables: dict[str, Symbol | frog_ast.Expression],
        ctx: PipelineContext | None = None,
    ) -> None:
        self.variables = variables
        self.ctx = ctx

    @staticmethod
    def _pos(expr: Symbol | int, pos_subs: dict[Symbol, Symbol]) -> Symbol | int:
        """Substitute positive symbol assumptions if expr is symbolic."""
        if pos_subs and hasattr(expr, "subs"):
            return expr.subs(pos_subs)
        return expr

    @staticmethod
    def _check_overlaps(
        slice_bounds: list[tuple[Symbol | int, Symbol | int]],
        pos_subs: dict[Symbol, Symbol],
    ) -> bool:
        """Check if any pair of slices overlap, using positive substitutions."""
        pos = SplitUniformSampleTransformer._pos
        for i, (start_i, end_i) in enumerate(slice_bounds):
            for j in range(i + 1, len(slice_bounds)):
                start_j, end_j = slice_bounds[j]
                # No overlap if end_i <= start_j or end_j <= start_i
                gap_ij = sympy_simplify(pos(start_j, pos_subs) - pos(end_i, pos_subs))
                gap_ji = sympy_simplify(pos(start_i, pos_subs) - pos(end_j, pos_subs))
                if not gap_ij.is_nonnegative and not gap_ji.is_nonnegative:
                    return True
        return False

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for sample_idx, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Sample)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.the_type, frog_ast.BitStringType)
                and statement.the_type.parameterization is not None
                and isinstance(statement.sampled_from, frog_ast.BitStringType)
                and statement.sampled_from.parameterization is not None
            ):
                continue

            var_name = statement.var.name

            # Check it's uniform sampling
            total_len = FrogToSympyVisitor(self.variables).visit(
                statement.the_type.parameterization
            )
            sample_len = FrogToSympyVisitor(self.variables).visit(
                statement.sampled_from.parameterization
            )
            if total_len is None or sample_len is None or total_len != sample_len:
                continue

            # Collect all usages of this variable in the rest of the block
            remaining_stmts = block.statements[sample_idx + 1 :]

            # Find all Slice nodes that reference this variable
            slices: list[frog_ast.Slice] = []

            def collect_slices(
                name: str,
                node: frog_ast.ASTNode,
            ) -> bool:
                return isinstance(node, frog_ast.Slice) and (
                    isinstance(node.the_array, frog_ast.Variable)
                    and node.the_array.name == name
                )

            def is_bare_var_use(
                name: str,
                node: frog_ast.ASTNode,
            ) -> bool:
                """Check if a variable is used outside of a Slice context."""
                return isinstance(node, frog_ast.Variable) and node.name == name

            remaining_block = frog_ast.Block(remaining_stmts)

            # Collect all slices of this variable from the original block.
            # We search, collect (by identity), then replace-in-copy to
            # find the next one, but track the originals for later replacement.
            replaced_block = remaining_block
            while True:
                found_slice = SearchVisitor(
                    functools.partial(collect_slices, var_name)
                ).visit(replaced_block)
                if found_slice is None:
                    break
                assert isinstance(found_slice, frog_ast.Slice)
                slices.append(found_slice)
                # Replace found slice in search copy to find next one
                replaced_block = ReplaceTransformer(
                    found_slice, frog_ast.Variable("__placeholder__")
                ).transform(replaced_block)

            if not slices:
                continue

            # Check there are no bare variable uses (non-slice uses)
            # After replacing all slices, any remaining use of var_name
            # means it's used in a non-slice context
            if (
                SearchVisitor(functools.partial(is_bare_var_use, var_name)).visit(
                    replaced_block
                )
                is not None
            ):
                continue

            # Resolve slice bounds to sympy
            slice_bounds: list[tuple[Symbol | int, Symbol | int]] = []
            all_resolved = True
            for s in slices:
                start = FrogToSympyVisitor(self.variables).visit(s.start)
                end = FrogToSympyVisitor(self.variables).visit(s.end)
                if start is None or end is None:
                    all_resolved = False
                    break
                slice_bounds.append((start, end))

            if not all_resolved:
                continue

            # Deduplicate slices with identical bounds. Multiple occurrences
            # of the same slice (e.g. v[n:2n] used twice) should map to one
            # replacement variable, since non-overlapping slices of a uniform
            # sample are independent.
            unique_bounds: list[tuple[Symbol | int, Symbol | int]] = []
            for sb in slice_bounds:
                if not any(
                    sympy_simplify(sb[0] - ub[0]) == 0
                    and sympy_simplify(sb[1] - ub[1]) == 0
                    for ub in unique_bounds
                ):
                    unique_bounds.append(sb)

            # BitString parameters are always non-negative. Create
            # positive symbol substitutions for sympy sign reasoning.
            all_syms: set[Symbol] = set()
            for sb in unique_bounds:
                for expr in sb:
                    if hasattr(expr, "free_symbols"):
                        all_syms.update(expr.free_symbols)
            pos_subs = {
                s: Symbol(s.name, positive=True) for s in all_syms if not s.is_positive
            }

            # Check unique slices are non-overlapping. Two slices [a,b) and
            # [c,d) don't overlap if b <= c or d <= a. Gaps are allowed
            # (unused portions are discarded).
            overlaps = self._check_overlaps(unique_bounds, pos_subs)
            if overlaps:
                if self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Split Uniform Samples",
                            reason=(
                                f"Sample '{var_name}' not split: "
                                f"slices are overlapping or incomplete"
                            ),
                            location=statement.origin,
                            suggestion=None,
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            # All checks pass - create replacement samples and substitution map
            new_samples: list[frog_ast.Sample] = []
            # Map from (start_sympy, end_sympy) -> new variable
            bound_to_var: list[tuple[Symbol | int, Symbol | int, frog_ast.Variable]] = (
                []
            )

            for i, (start, end) in enumerate(unique_bounds):
                part_len = end - start
                part_len_expr = frog_parser.parse_expression(str(part_len))
                part_type = frog_ast.BitStringType(part_len_expr)
                new_var_name = f"{var_name}_{i}"
                new_var = frog_ast.Variable(new_var_name)
                new_sample = frog_ast.Sample(
                    part_type,
                    new_var,
                    cast(
                        frog_ast.Expression,
                        frog_ast.BitStringType(
                            frog_parser.parse_expression(str(part_len))
                        ),
                    ),
                )
                new_samples.append(new_sample)
                bound_to_var.append((start, end, new_var))

            # Build new block: replace original sample with new samples
            new_statements: list[frog_ast.Statement] = []
            for si, stmt in enumerate(block.statements):
                if si == sample_idx:
                    new_statements.extend(new_samples)
                else:
                    new_statements.append(stmt)

            new_block = frog_ast.Block(new_statements)

            # Replace slice usages by matching on bounds
            new_block = _SliceReplacer(
                var_name, bound_to_var, self.variables
            ).transform(new_block)

            return self.transform_block(new_block)

        return block


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


def _single_call_field_to_local(game: frog_ast.Game) -> frog_ast.Game:
    """When each oracle is called at most once, push field-initialized uniform
    samples down to local variables in the oracle that uses them.

    A field is eligible if:
    - It is uniformly sampled (<-) in Initialize
    - That sample is the only statement in Initialize that references the field
    - The field is referenced in exactly one non-Initialize method
    - The field is not written to in that method
    """
    if not game.has_method("Initialize"):
        return game

    init_method = game.get_method("Initialize")

    # Collect eligible fields: (field, init_sample_idx, init_sample, target_method_name)
    eligible: list[tuple[frog_ast.Field, int, frog_ast.Sample, str]] = []

    for field in game.fields:
        # Skip fields with structured types (RandomFunctions, Sets, Maps)
        # that interact with other transforms in ways that depend on being fields
        if isinstance(
            field.type,
            (frog_ast.RandomFunctionType, frog_ast.SetType, frog_ast.MapType),
        ):
            continue

        # Step 1: Find the uniform sample of this field in Initialize
        init_sample: Optional[frog_ast.Sample] = None
        init_sample_idx: Optional[int] = None
        init_sample_count = 0
        field_used_elsewhere_in_init = False

        for idx, stmt in enumerate(init_method.block.statements):
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field.name
                and stmt.the_type is None
            ):
                init_sample = stmt
                init_sample_idx = idx
                init_sample_count += 1
            elif _references_name(stmt, field.name):
                field_used_elsewhere_in_init = True

        # Reject if no sample, multiple samples, or field used elsewhere
        if init_sample is None or init_sample_count > 1 or field_used_elsewhere_in_init:
            continue

        # Step 2: Find which non-Initialize methods reference this field
        using_methods: list[str] = []
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            if _references_name(method.block, field.name):
                using_methods.append(method.signature.name)

        if len(using_methods) != 1:
            continue

        # Step 3: Check the field is not written to in the using method
        # (recursive check to catch assignments inside if-branches etc.)
        target_method_name = using_methods[0]
        target_method = game.get_method(target_method_name)
        if _is_written_in_recursive(target_method.block, field.name):
            continue

        assert init_sample_idx is not None
        eligible.append((field, init_sample_idx, init_sample, target_method_name))

    if not eligible:
        return game

    # Apply all transformations at once
    eligible_names = {f.name for f, _, _, _ in eligible}
    init_remove_indices = {idx for _, idx, _, _ in eligible}

    new_game = copy.deepcopy(game)
    new_game.fields = [f for f in new_game.fields if f.name not in eligible_names]

    # Remove the samples from Initialize
    new_init = new_game.get_method("Initialize")
    new_init.block = frog_ast.Block(
        [
            s
            for i, s in enumerate(new_init.block.statements)
            if i not in init_remove_indices
        ]
    )

    # Group eligible fields by target method and prepend local samples
    by_method: dict[str, list[frog_ast.Sample]] = {}
    for field, _, init_sample, target_method_name in eligible:
        local_sample = frog_ast.Sample(
            copy.deepcopy(field.type),
            frog_ast.Variable(field.name),
            copy.deepcopy(init_sample.sampled_from),
        )
        by_method.setdefault(target_method_name, []).append(local_sample)

    for method_name, samples in by_method.items():
        target = new_game.get_method(method_name)
        target.block = frog_ast.Block(samples) + target.block

    return new_game


def _references_name(node: frog_ast.ASTNode, name: str) -> bool:
    """Check if an AST node contains any reference to a variable name."""

    def check(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == name

    return SearchVisitor(check).visit(node) is not None


class SingleCallFieldToLocal(TransformPass):
    """When max_calls == 1, push field-initialized uniform samples to locals."""

    name = "Single Call Field To Local"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        if ctx.max_calls is None or ctx.max_calls > 1:
            return game
        return _single_call_field_to_local(game)


def _localize_init_only_field_samples(game: frog_ast.Game) -> frog_ast.Game:
    """Convert field samples to typed local samples when the field is only
    used within Initialize.

    A field is eligible if:
    - It is uniformly sampled (<-) in Initialize (exactly once)
    - It is NOT referenced in any non-Initialize method
    - Initialize is called at most once (which is always true)

    The sample ``fieldX <- Type;`` becomes ``Type fieldX <- Type;`` (a typed
    local sample) and the field declaration is removed.
    """
    if not game.has_method("Initialize"):
        return game

    init_method = game.get_method("Initialize")
    eligible: list[tuple[frog_ast.Field, int]] = []

    for field in game.fields:
        # Find the sample of this field in Initialize
        init_sample_idx: Optional[int] = None
        sample_count = 0

        for idx, stmt in enumerate(init_method.block.statements):
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field.name
                and stmt.the_type is None
            ):
                init_sample_idx = idx
                sample_count += 1

        if sample_count != 1 or init_sample_idx is None:
            continue

        # Check: field NOT referenced in any non-Initialize method
        used_outside = False
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            if _references_name(method.block, field.name):
                used_outside = True
                break

        if used_outside:
            continue

        eligible.append((field, init_sample_idx))

    if not eligible:
        return game

    eligible_names = {f.name for f, _ in eligible}

    new_game = copy.deepcopy(game)
    new_game.fields = [f for f in new_game.fields if f.name not in eligible_names]

    # Convert untyped field samples to typed local samples
    new_init = new_game.get_method("Initialize")
    new_stmts = list(new_init.block.statements)
    for f, idx in eligible:
        stmt = new_stmts[idx]
        assert isinstance(stmt, frog_ast.Sample)
        new_stmts[idx] = frog_ast.Sample(
            copy.deepcopy(f.type),
            frog_ast.Variable(f.name),
            copy.deepcopy(stmt.sampled_from),
        )
    new_init.block = frog_ast.Block(new_stmts)

    return new_game


class LocalizeInitOnlyFieldSample(TransformPass):
    """Convert field samples to local samples when the field is only used
    in Initialize."""

    name = "Localize Init-Only Field Sample"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _localize_init_only_field_samples(game)


# ---------------------------------------------------------------------------
# Counter-guarded field to local
# ---------------------------------------------------------------------------


def _find_counter_fields(game: frog_ast.Game) -> set[str]:
    """Find Int fields that are initialized to 0."""
    if not game.has_method("Initialize"):
        return set()
    init_method = game.get_method("Initialize")
    counter_fields: set[str] = set()
    int_field_names = {
        f.name for f in game.fields if isinstance(f.type, frog_ast.IntType)
    }
    for stmt in init_method.block.statements:
        if (
            isinstance(stmt, frog_ast.Assignment)
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in int_field_names
            and isinstance(stmt.value, frog_ast.Integer)
            and stmt.value.num == 0
        ):
            counter_fields.add(stmt.var.name)
    return counter_fields


def _has_counter_increment(
    block: frog_ast.Block, counter_names: set[str]
) -> Optional[str]:
    """Check if a block contains ``counter = counter + 1`` and return the name."""
    for stmt in block.statements:
        if (
            isinstance(stmt, frog_ast.Assignment)
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name in counter_names
            and stmt.the_type is None
            and isinstance(stmt.value, frog_ast.BinaryOperation)
            and stmt.value.operator is frog_ast.BinaryOperators.ADD
            and isinstance(stmt.value.left_expression, frog_ast.Variable)
            and stmt.value.left_expression.name == stmt.var.name
            and isinstance(stmt.value.right_expression, frog_ast.Integer)
            and stmt.value.right_expression.num == 1
        ):
            return stmt.var.name
    return None


def _all_refs_in_counter_guarded_branches(
    block: frog_ast.Block,
    field_name: str,
    counter_name: str,
    mutable_names: set[str],
) -> bool:
    """Check that every reference to *field_name* is inside a branch guarded
    by ``counter_name == <expr>`` where ``<expr>`` is constant across calls.

    Returns ``False`` if:
    - the field is referenced outside counter-guarded branches or in an else block
    - more than one counter-guarded branch references the field (the field
      would be read on multiple calls with different counter values)
    - any if-condition references the field (conditions are evaluated every call)
    - the guard expression references mutable state (fields or method params),
      which could let the branch fire on multiple calls

    *mutable_names* is the set of variable names that can change between oracle
    calls (game fields and method parameters).
    """
    past_increment = False
    guarded_branch_count = 0
    for stmt in block.statements:
        # Track whether we've passed the counter increment
        if (
            isinstance(stmt, frog_ast.Assignment)
            and isinstance(stmt.var, frog_ast.Variable)
            and stmt.var.name == counter_name
        ):
            past_increment = True
            continue

        if isinstance(stmt, frog_ast.IfStatement) and past_increment:
            # Reject if *any* condition references the field — conditions
            # are evaluated on every oracle call, so the field would be read
            # on every call rather than just the guarded one.
            for condition in stmt.conditions:
                if _references_name(condition, field_name):
                    return False

            for cond_idx, condition in enumerate(stmt.conditions):
                branch_block = stmt.blocks[cond_idx]
                if not _references_name(branch_block, field_name):
                    continue
                # Branch uses the field — condition must be counter == expr
                if not (
                    isinstance(condition, frog_ast.BinaryOperation)
                    and condition.operator is frog_ast.BinaryOperators.EQUALS
                    and isinstance(condition.left_expression, frog_ast.Variable)
                    and condition.left_expression.name == counter_name
                ):
                    return False
                # The guard expression (RHS of counter == expr) must be
                # constant across oracle calls.  Reject if it references
                # any game field or method parameter, since those can differ
                # between calls and would let the branch fire multiple times.
                guard_expr = condition.right_expression
                for mname in mutable_names:
                    if _references_name(guard_expr, mname):
                        return False
                guarded_branch_count += 1
            # Else block must not reference the field
            if stmt.has_else_block() and _references_name(stmt.blocks[-1], field_name):
                return False
            continue

        # Reference outside an if-statement
        if _references_name(stmt, field_name):
            return False

    # The field must be read in at most one counter-guarded branch across
    # the entire method.  Multiple branches (even with different counter
    # values) means the field is read on multiple calls — unsound.
    if guarded_branch_count > 1:
        return False

    return past_increment


def _is_written_in_recursive(node: frog_ast.ASTNode, name: str) -> bool:
    """Check if a variable is assigned or sampled anywhere in the AST."""

    def check(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        )

    return SearchVisitor(check).visit(node) is not None


def _count_assignments_recursive(node: frog_ast.ASTNode, name: str) -> int:
    """Count how many times *name* is assigned or sampled anywhere in the AST."""
    count = 0

    def counter(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        ):
            count += 1
        return False

    SearchVisitor(counter).visit(node)
    return count


def _counter_guarded_field_to_local(game: frog_ast.Game) -> frog_ast.Game:
    """Convert fields to locals when only read inside counter-guarded branches.

    A field is eligible if:

    - It is uniformly sampled (``<-``) in Initialize (bare sample, no type)
    - That sample is the only reference to the field in Initialize
    - The field is referenced in exactly one non-Initialize method
    - The field is not written to in that method
    - All references are inside if-branches guarded by ``counter == <expr>``,
      where *counter* is an Int field initialized to 0 and incremented by 1
      before the if-statement

    Since each ``counter == val`` branch fires at most once (counter is
    strictly increasing), the field is read at most once total, making the
    conversion to a local sample sound.
    """
    if not game.has_method("Initialize"):
        return game

    counter_fields = _find_counter_fields(game)
    if not counter_fields:
        return game

    init_method = game.get_method("Initialize")

    eligible: list[tuple[frog_ast.Field, int, frog_ast.Sample, str]] = []

    for field in game.fields:
        if field.name in counter_fields:
            continue

        # Step 1: Find the uniform sample of this field in Initialize
        init_sample: Optional[frog_ast.Sample] = None
        init_sample_idx: Optional[int] = None
        init_sample_count = 0
        field_used_elsewhere_in_init = False

        for idx, stmt in enumerate(init_method.block.statements):
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field.name
                and stmt.the_type is None
            ):
                init_sample = stmt
                init_sample_idx = idx
                init_sample_count += 1
            elif _references_name(stmt, field.name):
                field_used_elsewhere_in_init = True

        # Reject if no sample, multiple samples, or field used elsewhere
        if init_sample is None or init_sample_count > 1 or field_used_elsewhere_in_init:
            continue

        # Step 2: Find which non-Initialize methods reference this field
        using_methods: list[str] = []
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            if _references_name(method.block, field.name):
                using_methods.append(method.signature.name)

        if len(using_methods) != 1:
            continue

        # Step 3: Check the field is not written to in the using method
        target_method_name = using_methods[0]
        target_method = game.get_method(target_method_name)
        if _is_written_in_recursive(target_method.block, field.name):
            continue

        # Step 4: Check counter is incremented and not modified elsewhere
        counter_name = _has_counter_increment(target_method.block, counter_fields)
        if counter_name is None:
            continue

        # The counter must only be assigned once in the target method (the
        # increment).  If the counter is reset or modified elsewhere (even
        # inside branches), the guard branch could fire multiple times,
        # making field-to-local unsound.
        counter_assign_count = _count_assignments_recursive(
            target_method.block, counter_name
        )
        if counter_assign_count != 1:
            continue

        # The counter must not be written in any other oracle method.
        # If another method resets or modifies the counter, the
        # monotonicity argument breaks and the guarded branch could
        # fire on multiple calls.
        counter_modified_elsewhere = False
        for method in game.methods:
            if method.signature.name in ("Initialize", target_method_name):
                continue
            if _is_written_in_recursive(method.block, counter_name):
                counter_modified_elsewhere = True
                break
        if counter_modified_elsewhere:
            continue

        # Step 5: Check all references are inside counter-guarded branches
        # with constant guard expressions (no fields or method params)
        mutable_names = {f.name for f in game.fields} | {
            p.name for p in target_method.signature.parameters
        }
        if not _all_refs_in_counter_guarded_branches(
            target_method.block, field.name, counter_name, mutable_names
        ):
            continue

        assert init_sample_idx is not None
        eligible.append((field, init_sample_idx, init_sample, target_method_name))

    if not eligible:
        return game

    # Apply transformations (same pattern as _single_call_field_to_local)
    eligible_names = {f.name for f, _, _, _ in eligible}
    init_remove_indices = {idx for _, idx, _, _ in eligible}

    new_game = copy.deepcopy(game)
    new_game.fields = [f for f in new_game.fields if f.name not in eligible_names]

    new_init = new_game.get_method("Initialize")
    new_init.block = frog_ast.Block(
        [
            s
            for i, s in enumerate(new_init.block.statements)
            if i not in init_remove_indices
        ]
    )

    by_method: dict[str, list[frog_ast.Sample]] = {}
    for field, _, init_sample, target_method_name in eligible:
        local_sample = frog_ast.Sample(
            copy.deepcopy(field.type),
            frog_ast.Variable(field.name),
            copy.deepcopy(init_sample.sampled_from),
        )
        by_method.setdefault(target_method_name, []).append(local_sample)

    for method_name, samples in by_method.items():
        target = new_game.get_method(method_name)
        target.block = frog_ast.Block(samples) + target.block

    return new_game


class CounterGuardedFieldToLocal(TransformPass):
    """Push field samples to locals when only used in counter-guarded branches."""

    name = "Counter Guarded Field To Local"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _counter_guarded_field_to_local(game)


class SinkUniformSampleTransformer(BlockTransformer):
    """Move a uniform sample from before an if/else into the branch that uses it.

    When a uniformly sampled variable is only referenced inside a single
    branch of a following if/else (and not in any condition or after the
    if/else), the sample is moved inside that branch.  This is always
    sound because uniform sampling is independent of the branch condition.
    """

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for idx, stmt in enumerate(block.statements):
            if not (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.the_type is not None
            ):
                continue

            var_name = stmt.var.name

            # The very next non-sample statement must be an IfStatement,
            # and no intermediate statement may reference the variable.
            next_idx = idx + 1
            intermediate_refs_var = False
            while next_idx < len(block.statements) and isinstance(
                block.statements[next_idx], frog_ast.Sample
            ):
                if _references_name(block.statements[next_idx], var_name):
                    intermediate_refs_var = True
                    break
                next_idx += 1
            if intermediate_refs_var:
                continue
            if next_idx >= len(block.statements):
                continue
            next_stmt = block.statements[next_idx]
            if not isinstance(next_stmt, frog_ast.IfStatement):
                continue

            # Check var is not used in the condition or after the if
            used_in_condition = any(
                _references_name(c, var_name) for c in next_stmt.conditions
            )
            if used_in_condition:
                continue

            after_if = frog_ast.Block(block.statements[next_idx + 1 :])
            if _references_name(after_if, var_name):
                continue

            # Find which branches reference the variable
            using_branches: list[int] = []
            for bi, branch_block in enumerate(next_stmt.blocks):
                if _references_name(branch_block, var_name):
                    using_branches.append(bi)

            if len(using_branches) != 1:
                continue

            # Move sample into the one branch
            target_bi = using_branches[0]
            new_if = copy.deepcopy(next_stmt)
            new_if.blocks[target_bi] = (
                frog_ast.Block([copy.deepcopy(stmt)]) + new_if.blocks[target_bi]
            )

            new_stmts = (
                list(block.statements[:idx])
                + list(block.statements[idx + 1 : next_idx])
                + [new_if]
                + list(block.statements[next_idx + 1 :])
            )
            return self.transform_block(frog_ast.Block(new_stmts))

        return block


class SinkUniformSample(TransformPass):
    """Sink uniform samples into if-branches when only used in one branch."""

    name = "Sink Uniform Sample"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SinkUniformSampleTransformer().transform(game)


class SimplifySplice(TransformPass):
    name = "Simplifying Splices"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifySpliceTransformer(ctx.variables).transform(game)


class MergeUniformSamples(TransformPass):
    name = "Merge Uniform Samples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return MergeUniformSamplesTransformer(ctx.variables, ctx).transform(game)


class MergeProductSamples(TransformPass):
    name = "Merge Product Samples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return MergeProductSamplesTransformer().transform(game)


class SplitUniformSamples(TransformPass):
    name = "Split Uniform Samples"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SplitUniformSampleTransformer(ctx.variables, ctx).transform(game)
