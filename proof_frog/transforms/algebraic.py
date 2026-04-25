# pylint: disable=duplicate-code
# Uniform sampling transformers share counting/search patterns with inlining.
"""Algebraic simplification passes: XOR, ModInt, reflexive comparison.

These passes exploit mathematical identities (self-inverse properties of XOR,
group properties of ModInt arithmetic, reflexive comparisons) to simplify
expressions during canonicalization.
"""

from __future__ import annotations

import copy
import functools
from typing import Optional

from .. import frog_ast
from ..visitors import (
    Transformer,
    BlockTransformer,
    SearchVisitor,
    ReplaceTransformer,
    NameTypeMap,
    VariableCollectionVisitor,
    build_game_type_map,
)
from ._base import (
    TransformPass,
    PipelineContext,
    NearMiss,
    has_nondeterministic_call,
    _lookup_primitive_method,
)
from ._ordering import node_sort_key
from ._wrappers import GroupExponentWrapper, WrapperShape, _GroupExpShape


def _count_field_assigns(node: frog_ast.ASTNode, name: str) -> int:
    """Count assignments/samples to *name* recursively in *node*."""
    count = 0

    def _visit(n: frog_ast.ASTNode) -> bool:
        nonlocal count
        if (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        ):
            count += 1
        return False

    SearchVisitor(_visit).visit(node)
    return count


# ---------------------------------------------------------------------------
# Transformer classes (moved from visitors.py)
# ---------------------------------------------------------------------------


class UniformXorSimplificationTransformer(BlockTransformer):
    """Simplifies expressions where a uniformly sampled variable is XORed
    with another value.  Since uniform XOR anything is still uniform, we
    can drop the other operand.

    Requires the sampled variable to be used exactly once so that the
    distributional equivalence holds (no correlation issues).

    Example:
        BitString<n> u <- BitString<n>;
        return u + m;
    becomes:
        BitString<n> u <- BitString<n>;
        return u;
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Sample)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.the_type, frog_ast.BitStringType)
                and isinstance(statement.sampled_from, frog_ast.BitStringType)
            ):
                continue

            var_name = statement.var.name

            remaining_block = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            # Count uses of var_name — must be exactly 1
            def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == name

            total_uses = 0
            count_block = copy.deepcopy(remaining_block)
            while True:
                found = SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    count_block
                )
                if found is None:
                    break
                total_uses += 1
                if total_uses > 1:
                    break
                count_block = ReplaceTransformer(
                    found, frog_ast.Variable(var_name + "__counted__")
                ).transform(count_block)

            if total_uses != 1:
                if total_uses > 1 and self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Uniform XOR Simplification",
                            reason=(
                                f"XOR-with-uniform did not fire for '{var_name}': "
                                f"used {total_uses} times (need exactly 1)"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Isolate the use of '{var_name}' so it appears "
                                f"only once after the sample"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            # Find a BinaryOperation(ADD, ...) where one operand is our variable
            def is_xor_with_uniform(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.BinaryOperation)
                    and node.operator == frog_ast.BinaryOperators.ADD
                    and (
                        (
                            isinstance(node.left_expression, frog_ast.Variable)
                            and node.left_expression.name == name
                        )
                        or (
                            isinstance(node.right_expression, frog_ast.Variable)
                            and node.right_expression.name == name
                        )
                    )
                )

            xor_node = SearchVisitor(
                functools.partial(is_xor_with_uniform, var_name)
            ).visit(remaining_block)
            if xor_node is None:
                continue

            # Replace the BinaryOperation with just the uniform variable
            assert isinstance(xor_node, frog_ast.BinaryOperation)
            if (
                isinstance(xor_node.left_expression, frog_ast.Variable)
                and xor_node.left_expression.name == var_name
            ):
                uniform_var = xor_node.left_expression
            else:
                uniform_var = xor_node.right_expression

            remaining_block = ReplaceTransformer(
                xor_node, copy.deepcopy(uniform_var)
            ).transform(remaining_block)

            new_block = frog_ast.Block(
                list(block.statements[: index + 1]) + list(remaining_block.statements)
            )
            return self.transform_block(new_block)

        return block


class UniformModIntSimplificationTransformer(BlockTransformer):
    """Simplifies expressions where a uniformly sampled ModInt variable is
    combined additively with another value.  Since uniform +/- anything
    is still uniform in a group (and anything - uniform is also uniform),
    we can drop the other operand.

    Requires the sampled variable to be used exactly once so that the
    distributional equivalence holds (no correlation issues).

    Examples:
        ModInt<q> u <- ModInt<q>;    ModInt<q> u <- ModInt<q>;
        return u + m;                return u - m;
    both become:
        ModInt<q> u <- ModInt<q>;
        return u;
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Sample)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.the_type, frog_ast.ModIntType)
                and isinstance(statement.sampled_from, frog_ast.ModIntType)
            ):
                continue

            var_name = statement.var.name

            remaining_block = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            # Count uses of var_name — must be exactly 1
            def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == name

            total_uses = 0
            count_block = copy.deepcopy(remaining_block)
            while True:
                found = SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    count_block
                )
                if found is None:
                    break
                total_uses += 1
                if total_uses > 1:
                    break
                count_block = ReplaceTransformer(
                    found, frog_ast.Variable(var_name + "__counted__")
                ).transform(count_block)

            if total_uses != 1:
                if total_uses > 1 and self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Uniform ModInt Simplification",
                            reason=(
                                f"Uniform-ModInt did not fire for '{var_name}': "
                                f"used {total_uses} times (need exactly 1)"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Isolate the use of '{var_name}' so it appears "
                                f"only once after the sample"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            # Find a BinaryOperation(ADD or SUBTRACT, ...) where one operand
            # is our variable.  In a group, uniform +/- anything = uniform
            # and anything - uniform = uniform.
            def is_additive_with_uniform(name: str, node: frog_ast.ASTNode) -> bool:
                return (
                    isinstance(node, frog_ast.BinaryOperation)
                    and node.operator
                    in (
                        frog_ast.BinaryOperators.ADD,
                        frog_ast.BinaryOperators.SUBTRACT,
                    )
                    and (
                        (
                            isinstance(node.left_expression, frog_ast.Variable)
                            and node.left_expression.name == name
                        )
                        or (
                            isinstance(node.right_expression, frog_ast.Variable)
                            and node.right_expression.name == name
                        )
                    )
                )

            add_node = SearchVisitor(
                functools.partial(is_additive_with_uniform, var_name)
            ).visit(remaining_block)
            if add_node is None:
                continue

            # Replace the BinaryOperation with just the uniform variable
            assert isinstance(add_node, frog_ast.BinaryOperation)
            if (
                isinstance(add_node.left_expression, frog_ast.Variable)
                and add_node.left_expression.name == var_name
            ):
                uniform_var = add_node.left_expression
            else:
                uniform_var = add_node.right_expression

            remaining_block = ReplaceTransformer(
                add_node, copy.deepcopy(uniform_var)
            ).transform(remaining_block)

            new_block = frog_ast.Block(
                list(block.statements[: index + 1]) + list(remaining_block.statements)
            )
            return self.transform_block(new_block)

        return block


class SimplifyNot(Transformer):
    """Rewrites ``!(a == b)`` as ``a != b``."""

    def transform_unary_operation(
        self, unary_op: frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        if (
            unary_op.operator == frog_ast.UnaryOperators.NOT
            and isinstance(unary_op.expression, frog_ast.BinaryOperation)
            and unary_op.expression.operator == frog_ast.BinaryOperators.EQUALS
        ):
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.NOTEQUALS,
                unary_op.expression.left_expression,
                unary_op.expression.right_expression,
            )
        return unary_op


def _is_bitstring_add_chain(
    expr: frog_ast.Expression, type_map: Optional[NameTypeMap]
) -> bool:
    """Check if an ADD chain is a bitstring XOR operation (vs. ModInt addition).

    Returns True if evidence indicates bitstring context, False if evidence
    indicates ModInt context. Defaults to True (backward compatibility) when
    there is no type information.
    """
    if type_map is None:
        return True
    terms = _flatten_add_chain(expr)
    for term in terms:
        if isinstance(term, frog_ast.BitStringLiteral):
            return True
        if isinstance(term, frog_ast.Variable):
            var_type = type_map.get(term.name)
            if isinstance(var_type, frog_ast.ModIntType):
                return False
            if isinstance(var_type, frog_ast.BitStringType):
                return True
    return False


def _flatten_add_chain(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """Flatten a left-associative chain of ADD operations into a list of terms."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.ADD
    ):
        return _flatten_add_chain(expr.left_expression) + _flatten_add_chain(
            expr.right_expression
        )
    return [expr]


def _has_duplicate_terms(terms: list[frog_ast.Expression]) -> bool:
    """Check if any two terms in the list are structurally equal."""
    for i, t in enumerate(terms):
        for j in range(i + 1, len(terms)):
            if t == terms[j]:
                return True
    return False


def _rebuild_add_chain(terms: list[frog_ast.Expression]) -> frog_ast.Expression:
    """Rebuild a left-associative ADD chain from a list of terms."""
    result = terms[0]
    for term in terms[1:]:
        result = frog_ast.BinaryOperation(frog_ast.BinaryOperators.ADD, result, term)
    return result


class XorCancellationTransformer(Transformer):
    """Cancels pairs of identical terms in XOR (ADD on bitstrings) chains.

    Since XOR is self-inverse (a ^ a = 0) and associative/commutative,
    pairs of identical terms cancel out.  Only fires when the ADD chain
    is in a bitstring context (not ModInt addition).

    Example:
        k + k + m  ->  m
        a + b + a  ->  b
    """

    def __init__(
        self,
        type_map: Optional[NameTypeMap] = None,
        ctx: PipelineContext | None = None,
    ) -> None:
        self.type_map = type_map
        self.ctx = ctx
        self._reported_modint_near_miss = False

    def _maybe_report_modint_near_miss(
        self, transformed: frog_ast.BinaryOperation
    ) -> None:
        """Report a near-miss if the ADD chain has duplicate terms in ModInt context."""
        if self.ctx is None or self._reported_modint_near_miss:
            return
        terms = _flatten_add_chain(transformed)
        if len(terms) >= 2 and _has_duplicate_terms(terms):
            self._reported_modint_near_miss = True
            self.ctx.near_misses.append(
                NearMiss(
                    transform_name="XOR Cancellation",
                    reason=(
                        "XOR cancellation does not apply to this "
                        "ADD chain: operands are in modular "
                        "arithmetic context, not bitstring XOR"
                    ),
                    location=None,
                    suggestion=None,
                    variable=None,
                    method=None,
                )
            )

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        if binary_operation.operator != frog_ast.BinaryOperators.ADD:
            return frog_ast.BinaryOperation(
                binary_operation.operator,
                self.transform(binary_operation.left_expression),
                self.transform(binary_operation.right_expression),
            )

        if not _is_bitstring_add_chain(binary_operation, self.type_map):
            transformed = frog_ast.BinaryOperation(
                binary_operation.operator,
                self.transform(binary_operation.left_expression),
                self.transform(binary_operation.right_expression),
            )
            self._maybe_report_modint_near_miss(transformed)
            return transformed

        # Flatten the full ADD chain from the ORIGINAL expression (before
        # recursing into sub-ADD-expressions).  This ensures multi-term
        # chains like (k + k) + m are flattened to [k, k, m] and cancelled
        # as a whole, rather than the inner (k + k) being processed first.
        terms = _flatten_add_chain(binary_operation)
        if len(terms) < 2:
            return self.transform(terms[0]) if terms else binary_operation

        # Transform each leaf term (non-ADD sub-expressions) individually
        transformed_terms = [self.transform(t) for t in terms]

        # Cancel pairs of identical terms (only when both are pure/deterministic)
        proof_ns = self.ctx.proof_namespace if self.ctx is not None else {}
        remaining: list[frog_ast.Expression] = []
        for term in transformed_terms:
            found = False
            for i, existing in enumerate(remaining):
                if term == existing and not has_nondeterministic_call(
                    term,
                    proof_ns,
                    self.ctx.proof_let_types if self.ctx else None,
                ):
                    remaining.pop(i)
                    found = True
                    break
            if not found:
                remaining.append(term)

        if len(remaining) == len(transformed_terms):
            return _rebuild_add_chain(transformed_terms)
        if not remaining:
            # All terms cancelled — return 0^n if we can determine the
            # bitstring length, otherwise return unchanged.
            zero_len = self._get_bitstring_length(transformed_terms)
            if zero_len is not None:
                return frog_ast.BitStringLiteral(0, zero_len)
            return _rebuild_add_chain(transformed_terms)
        return _rebuild_add_chain(remaining)

    def _get_bitstring_length(
        self, terms: list[frog_ast.Expression]
    ) -> frog_ast.Expression | None:
        """Determine the bitstring length from the terms or type map."""
        if self.type_map is not None:
            for term in terms:
                if isinstance(term, frog_ast.Variable):
                    var_type = self.type_map.get(term.name)
                    if (
                        isinstance(var_type, frog_ast.BitStringType)
                        and var_type.parameterization is not None
                    ):
                        return copy.deepcopy(var_type.parameterization)
        for term in terms:
            if isinstance(term, frog_ast.BitStringLiteral):
                return copy.deepcopy(term.length)
        return None


class XorIdentityTransformer(Transformer):
    """Removes 0^n terms from XOR (ADD) chains, since x XOR 0 = x.

    Only fires when the ADD chain is in a bitstring context (not ModInt
    addition).

    Example:
        x + 0^lambda  ->  x
        0^3 + y + z   ->  y + z
    """

    def __init__(self, type_map: Optional[NameTypeMap] = None) -> None:
        self.type_map = type_map

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        if transformed.operator != frog_ast.BinaryOperators.ADD:
            return transformed

        if not _is_bitstring_add_chain(transformed, self.type_map):
            return transformed

        terms = _flatten_add_chain(transformed)
        remaining = [
            t
            for t in terms
            if not (isinstance(t, frog_ast.BitStringLiteral) and t.bit == 0)
        ]

        if len(remaining) == len(terms):
            return transformed
        if not remaining:
            # All terms were 0^n; return the first zero literal
            return terms[0]
        return _rebuild_add_chain(remaining)


def _get_expression_type(
    expr: frog_ast.Expression, type_map: NameTypeMap
) -> Optional[frog_ast.Type]:
    """Infer the type of an expression from a type map.

    Returns the type if it can be determined, None otherwise.
    """
    if isinstance(expr, frog_ast.Variable):
        return type_map.get(expr.name)
    if isinstance(expr, frog_ast.Integer):
        return frog_ast.IntType()
    if isinstance(expr, frog_ast.Boolean):
        return frog_ast.BoolType()
    if isinstance(expr, frog_ast.BitStringLiteral):
        return frog_ast.BitStringType(expr.length)
    if isinstance(expr, frog_ast.UnaryOperation):
        return _get_expression_type(expr.expression, type_map)
    if isinstance(expr, frog_ast.BinaryOperation):
        if expr.operator == frog_ast.BinaryOperators.EXPONENTIATE:
            return _get_expression_type(expr.left_expression, type_map)
        if expr.operator in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
            frog_ast.BinaryOperators.LT,
            frog_ast.BinaryOperators.GT,
            frog_ast.BinaryOperators.LEQ,
            frog_ast.BinaryOperators.GEQ,
            frog_ast.BinaryOperators.AND,
            frog_ast.BinaryOperators.OR,
        ):
            return frog_ast.BoolType()
        # For arithmetic ops, type comes from left operand
        return _get_expression_type(expr.left_expression, type_map)
    if isinstance(expr, frog_ast.GroupGenerator):
        return frog_ast.GroupElemType(expr.group)
    # G.generator and G.identity are parsed as FieldAccess(Variable("G"), ...)
    if (
        isinstance(expr, frog_ast.FieldAccess)
        and expr.name in ("generator", "identity")
        and isinstance(expr.the_object, frog_ast.Variable)
    ):
        obj_type = type_map.get(expr.the_object.name)
        if isinstance(obj_type, frog_ast.GroupType):
            return frog_ast.GroupElemType(expr.the_object)
    return None


def _is_integer_literal(expr: frog_ast.Expression, value: int) -> bool:
    """Check if an expression is an integer literal with a specific value."""
    return isinstance(expr, frog_ast.Integer) and expr.num == value


def _exponents_compatible(
    e1: frog_ast.Expression,
    e2: frog_ast.Expression,
    type_map: Optional[NameTypeMap],
) -> bool:
    """Check that two exponents have compatible types for arithmetic.

    Returns True if both are ModInt (same modulus) or both are Int.
    Also returns True if type information is unavailable (optimistic).
    """
    if type_map is None:
        return True
    t1 = _get_expression_type(e1, type_map)
    t2 = _get_expression_type(e2, type_map)
    if t1 is None or t2 is None:
        return True
    if isinstance(t1, frog_ast.ModIntType) and isinstance(t2, frog_ast.ModIntType):
        return True
    if isinstance(t1, frog_ast.IntType) and isinstance(t2, frog_ast.IntType):
        return True
    return False


def _is_group_identity(expr: frog_ast.Expression) -> bool:
    """Check if an expression is a group identity element (G.identity)."""
    return (
        isinstance(expr, frog_ast.FieldAccess)
        and expr.name == "identity"
        and isinstance(expr.the_object, frog_ast.Variable)
    )


def _make_group_identity(group_var: frog_ast.Expression) -> frog_ast.FieldAccess:
    """Construct a G.identity expression for the given group variable."""
    return frog_ast.FieldAccess(copy.deepcopy(group_var), "identity")


def _get_group_var_from_type(
    expr: frog_ast.Expression, type_map: Optional[NameTypeMap]
) -> Optional[frog_ast.Expression]:
    """Extract the group variable from a GroupElem-typed expression."""
    if type_map is None:
        return None
    expr_type = _get_expression_type(expr, type_map)
    if isinstance(expr_type, frog_ast.GroupElemType):
        return expr_type.group
    return None


class ModIntSimplificationTransformer(Transformer):
    """Applies algebraic identities for ModInt arithmetic.

    Requires a type map to determine when operands are ModInt.

    Identities applied:
    - Additive identity: a + 0 = a, 0 + a = a
    - Multiplicative identity: a * 1 = a, 1 * a = a
    - Multiplicative zero: a * 0 = 0, 0 * a = 0
    - Additive inverse: a - a = 0 (only when a is pure/deterministic)
    - Double negation: -(-a) = a
    - Exponentiation: a ^ 0 = 1, a ^ 1 = a
    """

    def __init__(
        self,
        type_map: NameTypeMap,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: Optional[NameTypeMap] = None,
    ) -> None:
        self.type_map = type_map
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def _is_modint_expr(self, expr: frog_ast.Expression) -> bool:
        return isinstance(
            _get_expression_type(expr, self.type_map), frog_ast.ModIntType
        )

    def transform_unary_operation(
        self, unary_operation: frog_ast.UnaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.UnaryOperation(
            unary_operation.operator,
            self.transform(unary_operation.expression),
        )
        if transformed.operator != frog_ast.UnaryOperators.MINUS:
            return transformed
        if not self._is_modint_expr(transformed.expression):
            return transformed
        # -(-a) = a
        if (
            isinstance(transformed.expression, frog_ast.UnaryOperation)
            and transformed.expression.operator == frog_ast.UnaryOperators.MINUS
        ):
            return transformed.expression.expression
        return transformed

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        left = transformed.left_expression
        right = transformed.right_expression
        op = transformed.operator

        if not self._is_modint_expr(left) and not self._is_modint_expr(right):
            # Check for exponentiation where base is ModInt
            if op != frog_ast.BinaryOperators.EXPONENTIATE:
                return transformed
            if not self._is_modint_expr(left):
                return transformed

        # Additive identity: a + 0 = a, 0 + a = a
        if op == frog_ast.BinaryOperators.ADD:
            if _is_integer_literal(right, 0):
                return left
            if _is_integer_literal(left, 0):
                return right

        # Subtractive identity: a - 0 = a
        if op == frog_ast.BinaryOperators.SUBTRACT:
            if _is_integer_literal(right, 0):
                return left
            # a - a = 0 (only when a is pure/deterministic)
            if left == right and not has_nondeterministic_call(
                left, self._proof_namespace, self._proof_let_types
            ):
                return frog_ast.Integer(0)

        # Multiplicative identity: a * 1 = a, 1 * a = a
        if op == frog_ast.BinaryOperators.MULTIPLY:
            if _is_integer_literal(right, 1):
                return left
            if _is_integer_literal(left, 1):
                return right
            # Multiplicative zero: a * 0 = 0, 0 * a = 0
            if _is_integer_literal(right, 0):
                return frog_ast.Integer(0)
            if _is_integer_literal(left, 0):
                return frog_ast.Integer(0)

        # Exponentiation identities: a ^ 0 = 1, a ^ 1 = a
        if op == frog_ast.BinaryOperators.EXPONENTIATE:
            if _is_integer_literal(right, 0):
                return frog_ast.Integer(1)
            if _is_integer_literal(right, 1):
                return left

        return transformed


class ReflexiveComparisonTransformer(Transformer):
    """Simplifies reflexive comparisons: x == x -> true, x != x -> false.

    Only fires when the repeated sub-expression is pure (no non-deterministic
    function calls).  Non-deterministic calls may return different values on
    each invocation, so structural equality of AST nodes does not imply
    runtime equality.
    """

    def __init__(
        self,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: Optional[NameTypeMap] = None,
    ) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        if (
            transformed.operator == frog_ast.BinaryOperators.EQUALS
            and transformed.left_expression == transformed.right_expression
            and not has_nondeterministic_call(
                transformed.left_expression,
                self._proof_namespace,
                self._proof_let_types,
            )
        ):
            return frog_ast.Boolean(True)
        if (
            transformed.operator == frog_ast.BinaryOperators.NOTEQUALS
            and transformed.left_expression == transformed.right_expression
            and not has_nondeterministic_call(
                transformed.left_expression,
                self._proof_namespace,
                self._proof_let_types,
            )
        ):
            return frog_ast.Boolean(False)
        return transformed


class BooleanIdentityTransformer(Transformer):
    """Simplifies boolean AND/OR with literal true/false operands.

    OR rules (only when at least one operand is a Boolean literal,
    to avoid firing on BitString concatenation):
      false || false -> false
      x || false / false || x -> x
      x || true  / true || x  -> true

    AND rules (AND is always boolean):
      true && true -> true
      x && true / true && x -> x
      x && false / false && x -> false
    """

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        left = transformed.left_expression
        right = transformed.right_expression

        if transformed.operator == frog_ast.BinaryOperators.OR:
            # Only simplify when at least one operand is a Boolean literal
            # (BitString concatenation uses || but never has Boolean literals)
            if isinstance(left, frog_ast.Boolean) and left.bool:
                return frog_ast.Boolean(True)  # true || x -> true
            if isinstance(right, frog_ast.Boolean) and right.bool:
                return frog_ast.Boolean(True)  # x || true -> true
            if isinstance(left, frog_ast.Boolean) and not left.bool:
                return right  # false || x -> x
            if isinstance(right, frog_ast.Boolean) and not right.bool:
                return left  # x || false -> x

        if transformed.operator == frog_ast.BinaryOperators.AND:
            if isinstance(left, frog_ast.Boolean) and not left.bool:
                return frog_ast.Boolean(False)  # false && x -> false
            if isinstance(right, frog_ast.Boolean) and not right.bool:
                return frog_ast.Boolean(False)  # x && false -> false
            if isinstance(left, frog_ast.Boolean) and left.bool:
                return right  # true && x -> x
            if isinstance(right, frog_ast.Boolean) and right.bool:
                return left  # x && true -> x

        return transformed


# ---------------------------------------------------------------------------
# TransformPass wrappers
# ---------------------------------------------------------------------------


class UniformXorSimplification(TransformPass):
    name = "Uniform XOR Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return UniformXorSimplificationTransformer(ctx).transform(game)


class UniformModIntSimplification(TransformPass):
    name = "Uniform ModInt Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return UniformModIntSimplificationTransformer(ctx).transform(game)


class UniformGroupElemSimplificationTransformer(BlockTransformer):
    """Simplifies expressions where a uniformly sampled GroupElem variable is
    combined with another value via group multiplication or division.
    Since uniform * anything = uniform in an abelian group (and
    anything / uniform = uniform), we can drop the other operand.

    Requires the sampled variable to be used exactly once.

    Examples:
        GroupElem<G> u <- GroupElem<G>;    GroupElem<G> u <- GroupElem<G>;
        return u * m;                      return m / u;
    both become:
        GroupElem<G> u <- GroupElem<G>;
        return u;
    """

    def __init__(self, ctx: PipelineContext | None = None) -> None:
        self.ctx = ctx

    def _transform_block_wrapper(self, block: frog_ast.Block) -> frog_ast.Block:
        for index, statement in enumerate(block.statements):
            if not (
                isinstance(statement, frog_ast.Sample)
                and isinstance(statement.var, frog_ast.Variable)
                and isinstance(statement.the_type, frog_ast.GroupElemType)
                and isinstance(statement.sampled_from, frog_ast.GroupElemType)
            ):
                continue

            var_name = statement.var.name

            remaining_block = frog_ast.Block(
                copy.deepcopy(list(block.statements[index + 1 :]))
            )

            def uses_var(name: str, node: frog_ast.ASTNode) -> bool:
                return isinstance(node, frog_ast.Variable) and node.name == name

            total_uses = 0
            count_block = copy.deepcopy(remaining_block)
            while True:
                found = SearchVisitor(functools.partial(uses_var, var_name)).visit(
                    count_block
                )
                if found is None:
                    break
                total_uses += 1
                if total_uses > 1:
                    break
                count_block = ReplaceTransformer(
                    found, frog_ast.Variable(var_name + "__counted__")
                ).transform(count_block)

            if total_uses != 1:
                if total_uses > 1 and self.ctx is not None:
                    self.ctx.near_misses.append(
                        NearMiss(
                            transform_name="Uniform GroupElem Simplification",
                            reason=(
                                f"Uniform-GroupElem did not fire for '{var_name}': "
                                f"used {total_uses} times (need exactly 1)"
                            ),
                            location=statement.origin,
                            suggestion=(
                                f"Isolate the use of '{var_name}' so it appears "
                                f"only once after the sample"
                            ),
                            variable=var_name,
                            method=None,
                        )
                    )
                continue

            def is_multiplicative_with_uniform(
                name: str, node: frog_ast.ASTNode
            ) -> bool:
                return (
                    isinstance(node, frog_ast.BinaryOperation)
                    and node.operator
                    in (
                        frog_ast.BinaryOperators.MULTIPLY,
                        frog_ast.BinaryOperators.DIVIDE,
                    )
                    and (
                        (
                            isinstance(node.left_expression, frog_ast.Variable)
                            and node.left_expression.name == name
                        )
                        or (
                            isinstance(node.right_expression, frog_ast.Variable)
                            and node.right_expression.name == name
                        )
                    )
                )

            mul_node = SearchVisitor(
                functools.partial(is_multiplicative_with_uniform, var_name)
            ).visit(remaining_block)
            if mul_node is None:
                continue

            assert isinstance(mul_node, frog_ast.BinaryOperation)
            if (
                isinstance(mul_node.left_expression, frog_ast.Variable)
                and mul_node.left_expression.name == var_name
            ):
                uniform_var = mul_node.left_expression
            else:
                uniform_var = mul_node.right_expression

            remaining_block = ReplaceTransformer(
                mul_node, copy.deepcopy(uniform_var)
            ).transform(remaining_block)

            new_block = frog_ast.Block(
                list(block.statements[: index + 1]) + list(remaining_block.statements)
            )
            return self.transform_block(new_block)

        return block


class UniformGroupElemSimplification(TransformPass):
    name = "Uniform GroupElem Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return UniformGroupElemSimplificationTransformer(ctx).transform(game)


class SimplifyNotPass(TransformPass):
    name = "Simplify Nots"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyNot().transform(game)


class BooleanIdentity(TransformPass):
    name = "Boolean Identity"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return BooleanIdentityTransformer().transform(game)


class XorCancellation(TransformPass):
    name = "XOR Cancellation"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return XorCancellationTransformer(type_map, ctx).transform(game)


class XorIdentity(TransformPass):
    name = "XOR Identity"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return XorIdentityTransformer(type_map).transform(game)


class ModIntSimplification(TransformPass):
    name = "ModInt Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return ModIntSimplificationTransformer(
            type_map,
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


def _flatten_chain(
    expr: frog_ast.Expression, op: frog_ast.BinaryOperators
) -> list[frog_ast.Expression]:
    """Flatten an associative chain of *op* into a list of operands."""
    if isinstance(expr, frog_ast.BinaryOperation) and expr.operator == op:
        return _flatten_chain(expr.left_expression, op) + _flatten_chain(
            expr.right_expression, op
        )
    return [expr]


def _rebuild_chain(
    terms: list[frog_ast.Expression], op: frog_ast.BinaryOperators
) -> frog_ast.Expression:
    """Rebuild a left-associative chain from sorted operands."""
    result = terms[0]
    for term in terms[1:]:
        result = frog_ast.BinaryOperation(op, result, term)
    return result


# Operators that are commutative + associative for all types they apply to.
# OR (||) is excluded because it means concatenation on BitString.
_COMMUTATIVE_ASSOCIATIVE_OPS = frozenset(
    {frog_ast.BinaryOperators.ADD, frog_ast.BinaryOperators.MULTIPLY}
)

# Operators that are commutative but NOT associative.
# ==  and != are commutative (a == b iff b == a) but chaining them
# ((a == b) == c) is not meaningful, so we only swap the two operands.
_COMMUTATIVE_ONLY_OPS = frozenset(
    {frog_ast.BinaryOperators.EQUALS, frog_ast.BinaryOperators.NOTEQUALS}
)


class NormalizeCommutativeChainsTransformer(Transformer):
    """Sort operands of commutative operator chains.

    For commutative+associative operators (``+``, ``*``): flattens chains
    like ``(c + a) + b`` into ``[a, b, c]`` (sorted by structural key),
    then rebuilds left-associatively as ``(a + b) + c``.

    For commutative-only operators (``==``, ``!=``): swaps operands so the
    structurally smaller one is on the left.
    """

    def transform_binary_operation(
        self, expr: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        # First, recursively transform children
        transformed = frog_ast.BinaryOperation(
            expr.operator,
            self.transform(expr.left_expression),
            self.transform(expr.right_expression),
        )

        # Commutative + associative: flatten and sort the full chain.
        if transformed.operator in _COMMUTATIVE_ASSOCIATIVE_OPS:
            terms = _flatten_chain(transformed, transformed.operator)
            if len(terms) < 2:
                return transformed

            sorted_terms = sorted(terms, key=node_sort_key)
            rebuilt = _rebuild_chain(sorted_terms, transformed.operator)
            if rebuilt == transformed:
                return transformed
            return rebuilt

        # Commutative only (== / !=): swap if left > right.
        if transformed.operator in _COMMUTATIVE_ONLY_OPS:
            left_key = node_sort_key(transformed.left_expression)
            right_key = node_sort_key(transformed.right_expression)
            if left_key > right_key:
                return frog_ast.BinaryOperation(
                    transformed.operator,
                    transformed.right_expression,
                    transformed.left_expression,
                )

        return transformed


class NormalizeCommutativeChains(TransformPass):
    name = "Normalize Commutative Chains"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return NormalizeCommutativeChainsTransformer().transform(game)


class FlattenConcatChainTransformer(Transformer):
    """Left-associate ``||`` chains.

    ``||`` is the OR operator in FrogLang, overloaded between Boolean OR
    (associative + commutative) and BitString concatenation (associative,
    NOT commutative). Both readings are associative, so left-associating
    is semantics-preserving in either case. We rewrite
    ``a || (b || c)`` to ``(a || b) || c`` recursively to a fixed point so
    inliner-introduced right-grouped concat chains canonicalize to the
    parser's natural left-associative shape.
    """

    def transform_binary_operation(
        self, expr: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            expr.operator,
            self.transform(expr.left_expression),
            self.transform(expr.right_expression),
        )
        if transformed.operator != frog_ast.BinaryOperators.OR:
            return transformed
        terms = _flatten_chain(transformed, frog_ast.BinaryOperators.OR)
        if len(terms) < 2:
            return transformed
        rebuilt = _rebuild_chain(terms, frog_ast.BinaryOperators.OR)
        if rebuilt == transformed:
            return transformed
        return rebuilt


class FlattenConcatChain(TransformPass):
    name = "Flatten Concat Chain"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return FlattenConcatChainTransformer().transform(game)


class ReflexiveComparison(TransformPass):
    name = "Reflexive Comparison"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ReflexiveComparisonTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


class InjectiveEqualitySimplifyTransformer(Transformer):
    """Rewrites ``f(a1,...,an) == f(b1,...,bn)`` to ``(a1==b1) && ... && (an==bn)``
    when ``f`` is a primitive method annotated ``deterministic injective``.

    The ``!=`` variant becomes the corresponding disjunction of per-argument
    ``!=`` comparisons.  Zero-argument calls are left to ``ReflexiveComparison``.
    """

    def __init__(self, ctx: PipelineContext, game: frog_ast.Game) -> None:
        self.ctx = ctx
        self.game = game

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        op = transformed.operator
        if op not in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            return transformed
        left = transformed.left_expression
        right = transformed.right_expression
        if not (
            isinstance(left, frog_ast.FuncCall) and isinstance(right, frog_ast.FuncCall)
        ):
            return self._try_wrapper_simplification(transformed, op, left, right)
        # I-1: callees must be structurally equal.
        if left.func != right.func:
            return transformed
        # I-3: arg list lengths must match.
        if len(left.args) != len(right.args):
            return transformed
        # Zero-arg: f() == f() -> reflexive; let ReflexiveComparison handle it.
        if not left.args:
            return transformed
        # I-2: resolve primitive method; must be deterministic + injective.
        method = _lookup_primitive_method(left.func, self.ctx.proof_namespace)
        if method is None:
            return transformed
        if not (method.deterministic and method.injective):
            self.ctx.near_misses.append(
                NearMiss(
                    transform_name="Injective Equality Simplify",
                    reason=(
                        f"comparison of calls to '{method.name}' did not simplify: "
                        "method is not annotated 'deterministic injective'"
                    ),
                    location=binary_operation.origin,
                    suggestion=(
                        "If distinct inputs must map to distinct outputs, "
                        "annotate the primitive method 'deterministic injective'."
                    ),
                    variable=None,
                    method=method.name,
                )
            )
            return transformed
        pair_op = op  # EQUALS or NOTEQUALS
        combiner = (
            frog_ast.BinaryOperators.AND
            if op == frog_ast.BinaryOperators.EQUALS
            else frog_ast.BinaryOperators.OR
        )
        pairs = [
            frog_ast.BinaryOperation(pair_op, a, b)
            for a, b in zip(left.args, right.args)
        ]
        result: frog_ast.Expression = pairs[0]
        for pair in pairs[1:]:
            result = frog_ast.BinaryOperation(combiner, result, pair)
        return result

    def _try_wrapper_simplification(
        self,
        transformed: frog_ast.BinaryOperation,
        op: frog_ast.BinaryOperators,
        left: frog_ast.Expression,
        right: frog_ast.Expression,
    ) -> frog_ast.Expression:
        """Wrapper-protocol fallback: ``wrap(a) op wrap(b) → a op b`` when
        both sides are recognized as the same injective wrapper shape.

        Currently consults :class:`GroupExponentWrapper` only (the
        primitive-call case is already covered by the FuncCall branch
        above).  Two preprocessing steps before the wrapper match:

        1. **Field RHS substitution**: ``Variable(F) → F.rhs`` when ``F`` is
           a single-write Init-only pure-deterministic ``GroupElem<G>``
           field.  Closes the gap where one side of the equality is held in
           a hoisted field.
        2. **Exponent factoring**: ``base ^ (k * x)`` viewed as
           ``(base ^ x) ^ k`` when ``k`` matches the wrapper exponent on
           the other side.  Closes the gap where ``GroupElem
           Simplification`` has already power-of-power-folded one side.
        """
        recognizer = GroupExponentWrapper()
        left_resolved = self._resolve_field_rhs(left)
        right_resolved = self._resolve_field_rhs(right)
        match = self._match_with_factoring(recognizer, left_resolved, right_resolved)
        if match is None:
            return transformed
        left_resolved, right_resolved, left_shape, right_shape = match
        # Preconditions (prime-order + nonzero exponent) — emit near-miss if
        # the shape was recognized but a precondition blocks the rewrite.
        misses = left_shape.precondition_misses(self.game, self.ctx)
        if misses:
            for miss in misses:
                self.ctx.near_misses.append(
                    NearMiss(
                        transform_name="Injective Equality Simplify",
                        reason=(f"{left_shape.recognizer_label}: {miss}"),
                        location=transformed.origin,
                        suggestion=(
                            "Declare `requires <group>.order is prime;` and "
                            "sample the exponent via `<-uniq[{0}] T` (or "
                            "`<- T \\ {0}`) so the engine treats x^k as "
                            "injective."
                        ),
                        variable=None,
                        method=None,
                    )
                )
            return transformed
        left_varying = left_shape.varying_at(left_resolved)
        right_varying = right_shape.varying_at(right_resolved)
        if left_varying is None or right_varying is None:
            return transformed
        return frog_ast.BinaryOperation(op, left_varying, right_varying)

    def _match_with_factoring(
        self,
        recognizer: GroupExponentWrapper,
        left: frog_ast.Expression,
        right: frog_ast.Expression,
    ) -> Optional[
        tuple[
            frog_ast.Expression,
            frog_ast.Expression,
            WrapperShape,
            WrapperShape,
        ]
    ]:
        """Try to match both sides as the same group-exp wrapper, possibly
        factoring one side's exponent.

        Returns ``(left_resolved, right_resolved, left_shape, right_shape)``
        on success; ``None`` if no consistent shape pair is found.
        """
        l0 = recognizer.match_whole(left, self.ctx, self.game)
        r0 = recognizer.match_whole(right, self.ctx, self.game)
        # Direct agreement.
        if l0 is not None and r0 is not None and l0.identity_key == r0.identity_key:
            return left, right, l0, r0
        # Try each candidate k_expr (from whichever side matched first) and
        # attempt to refactor the other side to match.
        candidates: list[frog_ast.Expression] = []
        if isinstance(l0, _GroupExpShape):
            candidates.append(l0.k_expr)
        if isinstance(r0, _GroupExpShape):
            candidates.append(r0.k_expr)
        for k in candidates:
            l_try = (
                left
                if (isinstance(l0, _GroupExpShape) and l0.k_expr == k)
                else (self._try_factor_exponent(left, k) or left)
            )
            r_try = (
                right
                if (isinstance(r0, _GroupExpShape) and r0.k_expr == k)
                else (self._try_factor_exponent(right, k) or right)
            )
            ls = recognizer.match_whole(l_try, self.ctx, self.game)
            rs = recognizer.match_whole(r_try, self.ctx, self.game)
            if ls is not None and rs is not None and ls.identity_key == rs.identity_key:
                return l_try, r_try, ls, rs
        return None

    def _resolve_field_rhs(self, expr: frog_ast.Expression) -> frog_ast.Expression:
        """If *expr* is ``Variable(F)`` where ``F`` is a single-write
        Init-only ``GroupElem<G>`` field with a pure deterministic RHS
        whose free variables are all cross-method-visible
        (fields/parameters), return that RHS.  Otherwise return *expr*
        unchanged.

        The cross-method-visibility check is mandatory: the resolved
        expression replaces *expr* in a comparison whose surrounding
        context might be in a non-Init method, where Init-local variables
        are out of scope.
        """
        if not isinstance(expr, frog_ast.Variable):
            return expr
        name = expr.name
        fld = next((f for f in self.game.fields if f.name == name), None)
        if fld is None or not isinstance(fld.type, frog_ast.GroupElemType):
            return expr
        init = next(
            (m for m in self.game.methods if m.signature.name == "Initialize"),
            None,
        )
        if init is None:
            return expr
        rhs: Optional[frog_ast.Expression] = None
        for stmt in init.block.statements:
            if (
                isinstance(stmt, frog_ast.Assignment)
                and stmt.the_type is None
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == name
            ):
                if rhs is not None:
                    return expr  # multiple top-level assignments
                rhs = stmt.value
        if rhs is None:
            return expr
        # No assignment may exist anywhere else in the game.
        for method in self.game.methods:
            if method is init:
                continue
            if _count_field_assigns(method.block, name) > 0:
                return expr
        if has_nondeterministic_call(
            rhs, self.ctx.proof_namespace, self.ctx.proof_let_types
        ):
            return expr
        # Free vars in rhs must be cross-method visible.  Anything else
        # (Init-local declarations) cannot legally be referenced from the
        # site where this resolved expression will be substituted in.
        visible = {f.name for f in self.game.fields} | {
            p.name for p in self.game.parameters
        }
        free = {v.name for v in VariableCollectionVisitor().visit(copy.deepcopy(rhs))}
        if not free.issubset(visible):
            return expr
        return rhs

    @staticmethod
    def _try_factor_exponent(
        expr: frog_ast.Expression,
        k_expr: Optional[frog_ast.Expression],
    ) -> Optional[frog_ast.Expression]:
        """If *expr* is ``base ^ (k * x)`` or ``base ^ (x * k)`` with ``k``
        equal to *k_expr*, return ``(base ^ x) ^ k_expr``.  Else None."""
        if k_expr is None:
            return None
        if not isinstance(expr, frog_ast.BinaryOperation):
            return None
        if expr.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return None
        right = expr.right_expression
        if not isinstance(right, frog_ast.BinaryOperation):
            return None
        if right.operator != frog_ast.BinaryOperators.MULTIPLY:
            return None
        a, b = right.left_expression, right.right_expression
        if a == k_expr:
            other = b
        elif b == k_expr:
            other = a
        else:
            return None
        return frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                copy.deepcopy(expr.left_expression),
                copy.deepcopy(other),
            ),
            copy.deepcopy(k_expr),
        )


class InjectiveEqualitySimplify(TransformPass):
    name = "Injective Equality Simplify"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return InjectiveEqualitySimplifyTransformer(ctx, game).transform(game)


# ---------------------------------------------------------------------------
# Concat-equality decomposition
# ---------------------------------------------------------------------------


def _flatten_concat(expr: frog_ast.Expression) -> list[frog_ast.Expression]:
    """Flatten a left- or right-nested ``||`` (BitString concat) chain.

    ``a || b || c`` returns ``[a, b, c]`` regardless of associativity.
    Non-concat expressions return a singleton list.
    """
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.OR
    ):
        return _flatten_concat(expr.left_expression) + _flatten_concat(
            expr.right_expression
        )
    return [expr]


def _bitstring_length(
    expr: frog_ast.Expression,
    ctx: PipelineContext,
    type_map: NameTypeMap,
) -> Optional[frog_ast.Expression]:
    """Return the BitString length of *expr* as a length Expression, or None.

    Handles slices (``end - start``), variables/parameters with declared
    ``BitString<L>`` type, calls to primitive methods returning
    ``BitString<L>``, and concatenations (sum of part lengths). Returns
    ``None`` for any expression whose length cannot be statically derived
    from these sources.
    """
    if isinstance(expr, frog_ast.Slice):
        return frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SUBTRACT,
            copy.deepcopy(expr.end),
            copy.deepcopy(expr.start),
        )
    if isinstance(expr, frog_ast.Variable):
        t = type_map.get(expr.name)
        if isinstance(t, frog_ast.BitStringType) and t.parameterization is not None:
            return copy.deepcopy(t.parameterization)
        return None
    if isinstance(expr, frog_ast.FuncCall):
        method = _lookup_primitive_method(expr.func, ctx.proof_namespace)
        if method is None:
            return None
        rt = method.return_type
        if isinstance(rt, frog_ast.BitStringType) and rt.parameterization is not None:
            return copy.deepcopy(rt.parameterization)
        return None
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.OR
    ):
        left = _bitstring_length(expr.left_expression, ctx, type_map)
        right = _bitstring_length(expr.right_expression, ctx, type_map)
        if left is None or right is None:
            return None
        return frog_ast.BinaryOperation(frog_ast.BinaryOperators.ADD, left, right)
    return None


class ConcatEqualityDecomposeTransformer(Transformer):
    """Rewrites ``x == (a1 || a2 || ... || ak)`` (or the mirror form)
    to ``x[0:n1] == a1 && x[n1:n1+n2] == a2 && ... && x[s:s+nk] == ak``,
    where ``ni`` is the statically-derivable BitString length of ``ai``.

    The ``!=`` variant becomes the disjunction of per-slice disequalities.

    The rewrite fires only when every concatenation term has a derivable
    length (via :func:`_bitstring_length`) AND the concat contains at
    least two terms. The other side of the equality must NOT itself be a
    concat (which would already be handled by ``SimplifySplice`` or by
    term-wise matching); if both sides are concats, no rewrite happens.
    """

    def __init__(self, ctx: PipelineContext, type_map: NameTypeMap) -> None:
        self.ctx = ctx
        self.type_map = type_map

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        op = transformed.operator
        if op not in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            return transformed
        left = transformed.left_expression
        right = transformed.right_expression

        def is_concat(e: frog_ast.Expression) -> bool:
            return (
                isinstance(e, frog_ast.BinaryOperation)
                and e.operator == frog_ast.BinaryOperators.OR
            )

        if is_concat(left) and is_concat(right):
            # Ambiguous; leave for term-wise matching via other passes.
            return transformed
        if is_concat(right):
            concat_expr, other = right, left
        elif is_concat(left):
            concat_expr, other = left, right
        else:
            return transformed

        terms = _flatten_concat(concat_expr)
        if len(terms) < 2:
            return transformed
        lengths: list[frog_ast.Expression] = []
        for term in terms:
            length = _bitstring_length(term, self.ctx, self.type_map)
            if length is None:
                self.ctx.near_misses.append(
                    NearMiss(
                        transform_name="Concat Equality Decompose",
                        reason=(
                            f"concatenation term '{term}' has no "
                            "statically-derivable BitString length; "
                            "decomposition requires every term to be a "
                            "slice, a typed BitString variable, a primitive "
                            "method returning BitString<L>, or a concat of "
                            "such terms"
                        ),
                        location=binary_operation.origin,
                        suggestion=(
                            "Annotate or wrap the term so its BitString "
                            "length is derivable (e.g., declare a typed "
                            "local, or ensure the primitive method's "
                            "return type is BitString<L>)."
                        ),
                        variable=None,
                        method=None,
                    )
                )
                return transformed
            lengths.append(length)

        combiner = (
            frog_ast.BinaryOperators.AND
            if op == frog_ast.BinaryOperators.EQUALS
            else frog_ast.BinaryOperators.OR
        )
        # Build slice pairs.  Partial sum is accumulated as a syntactic
        # ADD chain; SymbolicComputation / NormalizeCommutativeChains
        # will collapse it on subsequent iterations.
        acc: Optional[frog_ast.Expression] = None
        pairs: list[frog_ast.Expression] = []
        for term, length in zip(terms, lengths):
            start = frog_ast.Integer(0) if acc is None else copy.deepcopy(acc)
            end = (
                copy.deepcopy(length)
                if acc is None
                else frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.ADD,
                    copy.deepcopy(acc),
                    copy.deepcopy(length),
                )
            )
            slice_expr = frog_ast.Slice(copy.deepcopy(other), start, end)
            pairs.append(frog_ast.BinaryOperation(op, slice_expr, copy.deepcopy(term)))
            acc = (
                copy.deepcopy(length)
                if acc is None
                else frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.ADD,
                    acc,
                    copy.deepcopy(length),
                )
            )
        result: frog_ast.Expression = pairs[0]
        for p in pairs[1:]:
            result = frog_ast.BinaryOperation(combiner, result, p)
        return result


class ConcatEqualityDecompose(TransformPass):
    name = "Concat Equality Decompose"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return ConcatEqualityDecomposeTransformer(ctx, type_map).transform(game)


# ---------------------------------------------------------------------------
# GroupElem algebra transforms
# ---------------------------------------------------------------------------


class GroupElemSimplificationTransformer(Transformer):
    """Simplifies GroupElem expressions using group algebra identities.

    Rules:
    - Power-of-power: ``(base ^ e1) ^ e2`` -> ``base ^ (e1 * e2)``
    - Exponent zero: ``g ^ 0`` -> ``G.identity``
    - Exponent one: ``g ^ 1`` -> ``g``
    - Multiplicative identity: ``identity * g`` -> ``g``, ``g * identity`` -> ``g``
    - Division by identity: ``g / identity`` -> ``g``
    """

    def __init__(self, type_map: Optional[NameTypeMap] = None) -> None:
        self.type_map = type_map

    def _is_groupelem_expr(self, expr: frog_ast.Expression) -> bool:
        if self.type_map is not None:
            expr_type = _get_expression_type(expr, self.type_map)
            if isinstance(expr_type, frog_ast.GroupElemType):
                return True
        return isinstance(expr, frog_ast.GroupGenerator)

    def _exponents_multipliable(
        self, e1: frog_ast.Expression, e2: frog_ast.Expression
    ) -> bool:
        """Check that e1 * e2 is well-typed (both ModInt or both Int)."""
        return _exponents_compatible(e1, e2, self.type_map)

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )
        op = transformed.operator
        left = transformed.left_expression
        right = transformed.right_expression

        # --- Exponentiation rules ---
        if op == frog_ast.BinaryOperators.EXPONENTIATE and self._is_groupelem_expr(
            left
        ):
            # g ^ 0  -->  G.identity
            if _is_integer_literal(right, 0):
                group_var = _get_group_var_from_type(left, self.type_map)
                if group_var is not None:
                    return _make_group_identity(group_var)
            # g ^ 1  -->  g
            if _is_integer_literal(right, 1):
                return left

        # Power-of-power: (base ^ e1) ^ e2  -->  base ^ (e1 * e2)
        if (
            op == frog_ast.BinaryOperators.EXPONENTIATE
            and isinstance(left, frog_ast.BinaryOperation)
            and left.operator == frog_ast.BinaryOperators.EXPONENTIATE
            and self._is_groupelem_expr(left.left_expression)
            and self._exponents_multipliable(left.right_expression, right)
        ):
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                left.left_expression,
                frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.MULTIPLY,
                    left.right_expression,
                    right,
                ),
            )

        # --- Multiplicative identity rules ---
        if op == frog_ast.BinaryOperators.MULTIPLY:
            # identity * g  -->  g
            if _is_group_identity(left):
                return right
            # g * identity  -->  g
            if _is_group_identity(right):
                return left

        if op == frog_ast.BinaryOperators.DIVIDE:
            # g / identity  -->  g
            if _is_group_identity(right):
                return left

        return transformed


class GroupElemSimplification(TransformPass):
    name = "GroupElem Simplification"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return GroupElemSimplificationTransformer(type_map).transform(game)


def _flatten_mul_div_chain(
    expr: frog_ast.Expression,
) -> tuple[list[frog_ast.Expression], list[frog_ast.Expression]]:
    """Flatten a MULTIPLY/DIVIDE chain into (positive_terms, negative_terms).

    MULTIPLY adds to positive; DIVIDE moves right operand to negative.
    Left-associativity is respected: ``a * b / c`` flattens to
    positives=[a, b], negatives=[c].
    """
    if isinstance(expr, frog_ast.BinaryOperation):
        if expr.operator == frog_ast.BinaryOperators.MULTIPLY:
            lp, ln = _flatten_mul_div_chain(expr.left_expression)
            rp, rn = _flatten_mul_div_chain(expr.right_expression)
            return lp + rp, ln + rn
        if expr.operator == frog_ast.BinaryOperators.DIVIDE:
            lp, ln = _flatten_mul_div_chain(expr.left_expression)
            rp, rn = _flatten_mul_div_chain(expr.right_expression)
            return lp + rn, ln + rp
    return [expr], []


def _rebuild_mul_div_chain(
    positives: list[frog_ast.Expression],
    negatives: list[frog_ast.Expression],
) -> frog_ast.Expression:
    """Rebuild a left-associative MULTIPLY/DIVIDE chain."""
    assert positives, "Cannot rebuild chain with no positive terms"
    result = positives[0]
    for term in positives[1:]:
        result = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.MULTIPLY, result, term
        )
    for term in negatives:
        result = frog_ast.BinaryOperation(frog_ast.BinaryOperators.DIVIDE, result, term)
    return result


def _is_groupelem_mul_div_chain(
    expr: frog_ast.BinaryOperation, type_map: Optional[NameTypeMap]
) -> bool:
    """Check whether a MULTIPLY or DIVIDE chain involves GroupElem types."""
    if expr.operator not in (
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.BinaryOperators.DIVIDE,
    ):
        return False
    if type_map is None:
        return False
    left_type = _get_expression_type(expr.left_expression, type_map)
    return isinstance(left_type, frog_ast.GroupElemType)


class GroupElemCancellationTransformer(Transformer):
    """Cancels matching terms in GroupElem MULTIPLY/DIVIDE chains.

    In an abelian group, ``x * m / x`` simplifies to ``m`` when ``x``
    is a pure (deterministic) expression.

    Analogous to ``XorCancellationTransformer`` for bitstring XOR.
    """

    def __init__(
        self,
        type_map: Optional[NameTypeMap] = None,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: Optional[NameTypeMap] = None,
    ) -> None:
        self.type_map = type_map
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        # Recurse into children first
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )

        if not _is_groupelem_mul_div_chain(transformed, self.type_map):
            return transformed

        positives, negatives = _flatten_mul_div_chain(transformed)
        if not negatives:
            return transformed

        remaining_pos = list(positives)
        remaining_neg = list(negatives)

        for ni in range(len(remaining_neg) - 1, -1, -1):
            neg_term = remaining_neg[ni]
            if has_nondeterministic_call(
                neg_term, self._proof_namespace, self._proof_let_types
            ):
                continue
            for pi, pos_term in enumerate(remaining_pos):
                if pos_term == neg_term and not has_nondeterministic_call(
                    pos_term, self._proof_namespace, self._proof_let_types
                ):
                    remaining_pos.pop(pi)
                    remaining_neg.pop(ni)
                    break

        if len(remaining_pos) == len(positives):
            return transformed

        if not remaining_pos:
            # All positive terms cancelled — return group identity
            group_var = _get_group_var_from_type(positives[0], self.type_map)
            if group_var is not None:
                identity = _make_group_identity(group_var)
                if remaining_neg:
                    return _rebuild_mul_div_chain([identity], remaining_neg)
                return identity
            return transformed  # can't determine group — return unchanged

        return _rebuild_mul_div_chain(remaining_pos, remaining_neg)


class GroupElemCancellation(TransformPass):
    name = "GroupElem Cancellation"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return GroupElemCancellationTransformer(
            type_map,
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


def _get_exponent_base(
    expr: frog_ast.Expression,
) -> Optional[tuple[frog_ast.Expression, frog_ast.Expression]]:
    """If expr is ``base ^ exp``, return (base, exp). Otherwise None."""
    if (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
    ):
        return (expr.left_expression, expr.right_expression)
    return None


class GroupElemExponentCombinationTransformer(Transformer):
    """Combines same-base exponentiations in GroupElem multiply/divide chains.

    ``g^a * g^b`` -> ``g^(a + b)``
    ``g^a / g^b`` -> ``g^(a - b)``

    Only fires when the bases are structurally identical and deterministic.
    """

    def __init__(
        self,
        type_map: Optional[NameTypeMap] = None,
        proof_namespace: frog_ast.Namespace | None = None,
        proof_let_types: Optional[NameTypeMap] = None,
    ) -> None:
        self.type_map = type_map
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}
        self._proof_let_types = proof_let_types

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            binary_operation.operator,
            self.transform(binary_operation.left_expression),
            self.transform(binary_operation.right_expression),
        )

        if not _is_groupelem_mul_div_chain(transformed, self.type_map):
            return transformed

        positives, negatives = _flatten_mul_div_chain(transformed)
        if len(positives) + len(negatives) < 2:
            return transformed

        changed = False

        # Combine same-base terms within positives: g^a * g^b -> g^(a+b)
        new_pos: list[frog_ast.Expression] = []
        for term in positives:
            merged = False
            pair = _get_exponent_base(term)
            if pair is not None:
                base, exp = pair
                if not has_nondeterministic_call(
                    base, self._proof_namespace, self._proof_let_types
                ):
                    for i, existing in enumerate(new_pos):
                        ex_pair = _get_exponent_base(existing)
                        if (
                            ex_pair is not None
                            and ex_pair[0] == base
                            and _exponents_compatible(ex_pair[1], exp, self.type_map)
                        ):
                            new_pos[i] = frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.EXPONENTIATE,
                                copy.deepcopy(base),
                                frog_ast.BinaryOperation(
                                    frog_ast.BinaryOperators.ADD,
                                    ex_pair[1],
                                    exp,
                                ),
                            )
                            merged = True
                            changed = True
                            break
            if not merged:
                new_pos.append(term)

        # Combine same-base terms between positives and negatives:
        # g^a / g^b -> g^(a-b)
        new_neg: list[frog_ast.Expression] = []
        for neg_term in negatives:
            merged = False
            neg_pair = _get_exponent_base(neg_term)
            if neg_pair is not None:
                neg_base, neg_exp = neg_pair
                if not has_nondeterministic_call(
                    neg_base, self._proof_namespace, self._proof_let_types
                ):
                    for i, pos_term in enumerate(new_pos):
                        pos_pair = _get_exponent_base(pos_term)
                        if (
                            pos_pair is not None
                            and pos_pair[0] == neg_base
                            and _exponents_compatible(
                                pos_pair[1], neg_exp, self.type_map
                            )
                        ):
                            new_pos[i] = frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.EXPONENTIATE,
                                copy.deepcopy(neg_base),
                                frog_ast.BinaryOperation(
                                    frog_ast.BinaryOperators.SUBTRACT,
                                    pos_pair[1],
                                    neg_exp,
                                ),
                            )
                            merged = True
                            changed = True
                            break
            if not merged:
                new_neg.append(neg_term)

        if not changed:
            return transformed

        if not new_pos:
            return transformed  # shouldn't happen but be safe

        return _rebuild_mul_div_chain(new_pos, new_neg)


class GroupElemExponentCombination(TransformPass):
    name = "GroupElem Exponent Combination"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        type_map = build_game_type_map(game, ctx.proof_let_types)
        return GroupElemExponentCombinationTransformer(
            type_map,
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)
