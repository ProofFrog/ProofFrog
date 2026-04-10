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
    build_game_type_map,
)
from ._base import TransformPass, PipelineContext, NearMiss, has_nondeterministic_call

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


class NormalizeCommutativeChainsTransformer(Transformer):
    """Sort operands of commutative+associative operator chains.

    Flattens chains like ``(c + a) + b`` into ``[a, b, c]`` (sorted by
    ``str()``), then rebuilds left-associatively as ``(a + b) + c``.
    This normalizes both operand order (commutativity) and parenthesization
    (associativity) in a single pass.
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

        if transformed.operator not in _COMMUTATIVE_ASSOCIATIVE_OPS:
            return transformed

        terms = _flatten_chain(transformed, transformed.operator)
        if len(terms) < 2:
            return transformed

        sorted_terms = sorted(terms, key=str)
        rebuilt = _rebuild_chain(sorted_terms, transformed.operator)
        if rebuilt == transformed:
            return transformed  # already in canonical form

        return rebuilt


class NormalizeCommutativeChains(TransformPass):
    name = "Normalize Commutative Chains"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return NormalizeCommutativeChainsTransformer().transform(game)


class _NormalizeEqualityTransformer(Transformer):
    """Sort operands of ``==`` and ``!=`` by (length, string).

    Shorter expressions come first so that a bare field variable precedes
    a compound expression like ``field ^ aprime``.  This is a separate
    pass from ``NormalizeCommutativeChains`` because it must run in the
    **standardization** pipeline (after field names are set) to ensure
    consistent field numbering.
    """

    def transform_binary_operation(
        self, expr: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            expr.operator,
            self.transform(expr.left_expression),
            self.transform(expr.right_expression),
        )
        if transformed.operator not in (
            frog_ast.BinaryOperators.EQUALS,
            frog_ast.BinaryOperators.NOTEQUALS,
        ):
            return transformed
        left_str = str(transformed.left_expression)
        right_str = str(transformed.right_expression)
        left_key = (len(left_str), left_str)
        right_key = (len(right_str), right_str)
        if left_key > right_key:
            return frog_ast.BinaryOperation(
                transformed.operator,
                transformed.right_expression,
                transformed.left_expression,
            )
        return transformed


class NormalizeEquality(TransformPass):
    """Sort ``==`` / ``!=`` operands by (length, string)."""

    name = "Normalize Equality"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _NormalizeEqualityTransformer().transform(game)


class ReflexiveComparison(TransformPass):
    name = "Reflexive Comparison"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ReflexiveComparisonTransformer(
            proof_namespace=ctx.proof_namespace,
            proof_let_types=ctx.proof_let_types,
        ).transform(game)


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


# ---------------------------------------------------------------------------
# Field expression materialization
# ---------------------------------------------------------------------------


def _is_generator_power(
    expr: frog_ast.Expression,
) -> Optional[tuple[frog_ast.Expression, frog_ast.Expression]]:
    """If *expr* is ``G.generator ^ exp``, return ``(G_var, exp)``.

    Handles both ``GroupGenerator(G)`` and ``FieldAccess(G, "generator")``
    representations of the group generator.
    """
    if not (
        isinstance(expr, frog_ast.BinaryOperation)
        and expr.operator == frog_ast.BinaryOperators.EXPONENTIATE
    ):
        return None
    base = expr.left_expression
    if isinstance(base, frog_ast.GroupGenerator):
        return (base.group, expr.right_expression)
    if isinstance(base, frog_ast.FieldAccess) and base.name == "generator":
        return (base.the_object, expr.right_expression)
    return None


def _extract_field_factor(
    exponent: frog_ast.Expression,
    field_name: str,
) -> Optional[frog_ast.Expression]:
    """If *exponent* is ``field * rest`` or ``rest * field``, return *rest*.

    If *exponent* is exactly ``field``, return ``None`` (caller should use
    the dedicated "direct" branch).  If field does not appear as a top-level
    multiplicative factor, return ``None``.
    """
    if not (
        isinstance(exponent, frog_ast.BinaryOperation)
        and exponent.operator == frog_ast.BinaryOperators.MULTIPLY
    ):
        return None
    left = exponent.left_expression
    right = exponent.right_expression
    if isinstance(left, frog_ast.Variable) and left.name == field_name:
        return right
    if isinstance(right, frog_ast.Variable) and right.name == field_name:
        return left
    return None


def _references_variable(node: frog_ast.ASTNode, name: str) -> bool:
    """Check if *node* contains any ``Variable`` with the given *name*."""

    def check(n: frog_ast.ASTNode) -> bool:
        return isinstance(n, frog_ast.Variable) and n.name == name

    return SearchVisitor(check).visit(node) is not None


def _is_written_in(node: frog_ast.ASTNode, name: str) -> bool:
    """Check if *name* is assigned or sampled anywhere inside *node*."""

    def check(n: frog_ast.ASTNode) -> bool:
        return (
            isinstance(n, (frog_ast.Assignment, frog_ast.Sample))
            and isinstance(n.var, frog_ast.Variable)
            and n.var.name == name
        )

    return SearchVisitor(check).visit(node) is not None


class _GeneratorPowerReplacer(Transformer):
    """Replace ``G.generator ^ field`` and ``G.generator ^ (field * e)``
    with a new GroupElem field variable (and ``new_field ^ e``)."""

    def __init__(
        self,
        group_var: frog_ast.Expression,
        field_name: str,
        new_field_name: str,
    ) -> None:
        self._group_var = group_var
        self._field_name = field_name
        self._new_field_name = new_field_name

    def transform_binary_operation(
        self, node: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        # First recurse into children
        transformed = frog_ast.BinaryOperation(
            node.operator,
            self.transform(node.left_expression),
            self.transform(node.right_expression),
        )
        if transformed.operator != frog_ast.BinaryOperators.EXPONENTIATE:
            return transformed

        gp = _is_generator_power(transformed)
        if gp is None:
            return transformed
        g_var, exponent = gp
        if g_var != self._group_var:
            return transformed

        # Direct: G.generator ^ field  -->  new_field
        if (
            isinstance(exponent, frog_ast.Variable)
            and exponent.name == self._field_name
        ):
            return frog_ast.Variable(self._new_field_name)

        # Factored: G.generator ^ (field * expr)  -->  new_field ^ expr
        rest = _extract_field_factor(exponent, self._field_name)
        if rest is not None:
            return frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.Variable(self._new_field_name),
                rest,
            )

        return transformed


def _find_field_power_in_oracles(
    game: frog_ast.Game,
    base_field_name: str,
    exp_field_name: str,
) -> bool:
    """Check if ``base_field ^ exp_field`` appears in a non-Initialize method."""

    def check(n: frog_ast.ASTNode) -> bool:
        if not (
            isinstance(n, frog_ast.BinaryOperation)
            and n.operator == frog_ast.BinaryOperators.EXPONENTIATE
        ):
            return False
        return (
            isinstance(n.left_expression, frog_ast.Variable)
            and n.left_expression.name == base_field_name
            and isinstance(n.right_expression, frog_ast.Variable)
            and n.right_expression.name == exp_field_name
        )

    for method in game.methods:
        if method.signature.name == "Initialize":
            continue
        if SearchVisitor(check).visit(method.block) is not None:
            return True
    return False


class _FieldPowerReplacer(Transformer):
    """Replace ``base_field ^ exp_field`` with a new field variable."""

    def __init__(
        self,
        base_field_name: str,
        exp_field_name: str,
        new_field_name: str,
    ) -> None:
        self._base_name = base_field_name
        self._exp_name = exp_field_name
        self._new_name = new_field_name

    def transform_binary_operation(
        self, node: frog_ast.BinaryOperation
    ) -> frog_ast.Expression:
        transformed = frog_ast.BinaryOperation(
            node.operator,
            self.transform(node.left_expression),
            self.transform(node.right_expression),
        )
        if (
            transformed.operator == frog_ast.BinaryOperators.EXPONENTIATE
            and isinstance(transformed.left_expression, frog_ast.Variable)
            and transformed.left_expression.name == self._base_name
            and isinstance(transformed.right_expression, frog_ast.Variable)
            and transformed.right_expression.name == self._exp_name
        ):
            return frog_ast.Variable(self._new_name)
        return transformed


def _materialize_field_exponentiation(
    game: frog_ast.Game, ctx: PipelineContext
) -> frog_ast.Game:
    """Introduce GroupElem fields for exponentiation patterns involving fields.

    Handles two cases:
    1. ``G.generator ^ modint_field`` -> new GroupElem field
    2. ``groupelem_field ^ modint_field`` -> new GroupElem field (second-order)

    For each eligible field, creates a new GroupElem field in Initialize and
    replaces all occurrences.  Processes one candidate per invocation.
    """
    if not game.has_method("Initialize"):
        return game

    init_method = game.get_method("Initialize")
    field_names = {f.name for f in game.fields}
    all_names = field_names | {
        p.name for m in game.methods for p in m.signature.parameters
    }

    # --- Case 1: G.generator ^ modint_field ---
    for field in game.fields:
        if not isinstance(field.type, frog_ast.ModIntType):
            continue
        modulus = field.type.modulus
        if isinstance(modulus, frog_ast.GroupOrder):
            group_var = modulus.group
        elif isinstance(modulus, frog_ast.FieldAccess) and modulus.name == "order":
            group_var = modulus.the_object
        else:
            continue

        # Must be uniformly sampled exactly once in Initialize, with no other
        # assignments to this field in Initialize
        sample_idx: Optional[int] = None
        sample_count = 0
        assigned_elsewhere_in_init = False
        for idx, stmt in enumerate(init_method.block.statements):
            if (
                isinstance(stmt, frog_ast.Sample)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field.name
                and stmt.the_type is None
            ):
                sample_idx = idx
                sample_count += 1
            elif (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == field.name
            ):
                assigned_elsewhere_in_init = True

        if sample_count != 1 or assigned_elsewhere_in_init:
            for method in game.methods:
                if method.signature.name == "Initialize":
                    continue
                if _has_generator_power_of(method.block, group_var, field.name):
                    ctx.near_misses.append(
                        NearMiss(
                            transform_name="Materialize Field Exponentiation",
                            reason=(
                                f"ModInt field '{field.name}' appears as "
                                f"G.generator ^ {field.name} in oracle but "
                                f"is not a single uniform sample in Initialize"
                            ),
                            location=None,
                            suggestion=(
                                "Ensure the field is sampled exactly once with "
                                "no other assignments in Initialize"
                            ),
                            variable=field.name,
                            method=None,
                        )
                    )
                    break
            continue

        oracle_reassigned = False
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            if _is_written_in(method.block, field.name):
                oracle_reassigned = True
                break
        if oracle_reassigned:
            ctx.near_misses.append(
                NearMiss(
                    transform_name="Materialize Field Exponentiation",
                    reason=(
                        f"ModInt field '{field.name}' is reassigned in an "
                        f"oracle method, preventing materialization"
                    ),
                    location=None,
                    suggestion="Remove or avoid reassigning the field in oracles",
                    variable=field.name,
                    method=None,
                )
            )
            continue

        used_in_oracle = False
        for method in game.methods:
            if method.signature.name == "Initialize":
                continue
            if _has_generator_power_of(method.block, group_var, field.name):
                used_in_oracle = True
                break
        if not used_in_oracle:
            continue

        # --- All preconditions met: convert ModInt field to GroupElem ---
        # Convert the field from ModInt to GroupElem and localize the
        # sample to a typed local variable.  Using a local prevents
        # InlineSingleUseField from inlining the field back (it requires
        # all free variables in the RHS to be fields for cross-method
        # inlining, and locals are out of scope).
        assert sample_idx is not None

        new_game = copy.deepcopy(game)

        # 1. Replace G.generator ^ field in all methods (before modifying
        #    the Initialize block so the replacer sees the original state)
        replacer = _GeneratorPowerReplacer(group_var, field.name, field.name)
        for method in new_game.methods:
            method.block = replacer.transform(method.block)

        # 2. Change the field declaration type from ModInt to GroupElem
        for f in new_game.fields:
            if f.name == field.name:
                f.type = frog_ast.GroupElemType(copy.deepcopy(group_var))
                break

        # 3. In Initialize, convert the untyped field sample
        #    ``field <- ModInt<G.order>;`` to a typed local sample
        #    ``ModInt<G.order> field_exp <- ModInt<G.order>;``
        #    and add an assignment ``field = G.generator ^ field_exp;``
        new_init = new_game.get_method("Initialize")
        old_sample = new_init.block.statements[sample_idx]
        assert isinstance(old_sample, frog_ast.Sample)

        # Choose a unique name for the local exponent variable
        local_name = f"{field.name}_exp"
        suffix = 0
        while local_name in all_names:
            local_name = f"{field.name}_exp_{suffix}"
            suffix += 1

        local_sample = frog_ast.Sample(
            copy.deepcopy(field.type),  # original ModInt type
            frog_ast.Variable(local_name),
            copy.deepcopy(old_sample.sampled_from),
        )
        field_assign = frog_ast.Assignment(
            None,
            frog_ast.Variable(field.name),
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.FieldAccess(copy.deepcopy(group_var), "generator"),
                frog_ast.Variable(local_name),
            ),
        )
        stmts = list(new_init.block.statements)
        stmts[sample_idx] = local_sample
        stmts.insert(sample_idx + 1, field_assign)
        new_init.block = frog_ast.Block(stmts)

        return new_game

    # --- Case 2: groupelem_field ^ modint_field ---
    # After case 1, expressions like ``ge_field ^ mi_field`` may remain in
    # oracles.  Trace back through ge_field's assignment in Initialize to
    # find the underlying exponent local (from case 1's conversion), then
    # express the product field as ``G.generator ^ (local_exp * mi_field)``.
    # Since local_exp is a local variable, InlineSingleUseField cannot
    # inline the new field cross-method.
    for ge_field in game.fields:
        if not isinstance(ge_field.type, frog_ast.GroupElemType):
            continue
        # Find ge_field's assignment in Initialize: ge_field = base ^ exp
        ge_assign_idx: Optional[int] = None
        ge_assign_base: Optional[frog_ast.Expression] = None
        ge_assign_exp: Optional[frog_ast.Expression] = None
        for idx, stmt in enumerate(init_method.block.statements):
            if (
                isinstance(stmt, frog_ast.Assignment)
                and isinstance(stmt.var, frog_ast.Variable)
                and stmt.var.name == ge_field.name
                and stmt.the_type is None
            ):
                ge_assign_idx = idx
                pair = _get_exponent_base(stmt.value)
                if pair is not None:
                    ge_assign_base, ge_assign_exp = pair
        if ge_assign_idx is None or ge_assign_base is None:
            continue
        if any(
            _is_written_in(m.block, ge_field.name)
            for m in game.methods
            if m.signature.name != "Initialize"
        ):
            continue

        for mi_field in game.fields:
            if not isinstance(mi_field.type, frog_ast.ModIntType):
                continue
            if mi_field.name == ge_field.name:
                continue
            if any(
                _is_written_in(m.block, mi_field.name)
                for m in game.methods
                if m.signature.name != "Initialize"
            ):
                continue
            if not _find_field_power_in_oracles(game, ge_field.name, mi_field.name):
                continue

            mi_set_idx: Optional[int] = None
            for idx, stmt in enumerate(init_method.block.statements):
                if (
                    isinstance(stmt, (frog_ast.Sample, frog_ast.Assignment))
                    and isinstance(stmt.var, frog_ast.Variable)
                    and stmt.var.name == mi_field.name
                ):
                    mi_set_idx = idx
            if mi_set_idx is None:
                continue

            insert_after = max(ge_assign_idx, mi_set_idx)

            new_name = f"__gp_{ge_field.name}_{mi_field.name}"
            suffix = 0
            while new_name in all_names:
                new_name = f"__gp_{ge_field.name}_{mi_field.name}_{suffix}"
                suffix += 1

            new_game = copy.deepcopy(game)

            replacer2 = _FieldPowerReplacer(ge_field.name, mi_field.name, new_name)
            for method in new_game.methods:
                method.block = replacer2.transform(method.block)

            new_field_decl = frog_ast.Field(
                copy.deepcopy(ge_field.type),
                new_name,
                None,
            )
            new_game.fields.append(new_field_decl)

            # Express as base ^ (exp * mi_field) using the underlying
            # exponent from ge_field's assignment, keeping the local
            # variable reference that prevents cross-method inlining.
            assert ge_assign_exp is not None
            new_init = new_game.get_method("Initialize")
            assign_stmt = frog_ast.Assignment(
                None,
                frog_ast.Variable(new_name),
                frog_ast.BinaryOperation(
                    frog_ast.BinaryOperators.EXPONENTIATE,
                    copy.deepcopy(ge_assign_base),
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.MULTIPLY,
                        copy.deepcopy(ge_assign_exp),
                        frog_ast.Variable(mi_field.name),
                    ),
                ),
            )
            stmts = list(new_init.block.statements)
            stmts.insert(insert_after + 1, assign_stmt)
            new_init.block = frog_ast.Block(stmts)

            return new_game

    return game


def _has_generator_power_of(
    node: frog_ast.ASTNode,
    group_var: frog_ast.Expression,
    field_name: str,
) -> bool:
    """Check if *node* contains ``G.generator ^ field`` or
    ``G.generator ^ (field * ...)``."""

    def check(n: frog_ast.ASTNode) -> bool:
        if not isinstance(n, frog_ast.BinaryOperation):
            return False
        gp = _is_generator_power(n)
        if gp is None:
            return False
        g_var, exponent = gp
        if g_var != group_var:
            return False
        if isinstance(exponent, frog_ast.Variable) and exponent.name == field_name:
            return True
        if _extract_field_factor(exponent, field_name) is not None:
            return True
        return False

    return SearchVisitor(check).visit(node) is not None


class MaterializeFieldExponentiation(TransformPass):
    """Introduce GroupElem fields for ``G.generator ^ modint_field`` patterns.

    When a ``ModInt<G.order>`` field ``f`` is uniformly sampled in Initialize
    and the expression ``G.generator ^ f`` (or ``G.generator ^ (f * expr)``)
    appears in a non-Initialize method, this transform introduces a new
    ``GroupElem<G>`` field initialized to ``G.generator ^ f`` and replaces all
    occurrences:

    - ``G.generator ^ f``           -> ``new_field``
    - ``G.generator ^ (f * expr)``  -> ``new_field ^ expr``
    """

    name = "Materialize Field Exponentiation"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return _materialize_field_exponentiation(game, ctx)
