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
                if term == existing and not has_nondeterministic_call(term, proof_ns):
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
    return None


def _is_integer_literal(expr: frog_ast.Expression, value: int) -> bool:
    """Check if an expression is an integer literal with a specific value."""
    return isinstance(expr, frog_ast.Integer) and expr.num == value


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
    ) -> None:
        self.type_map = type_map
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

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
                left, self._proof_namespace
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

    def __init__(self, proof_namespace: frog_ast.Namespace | None = None) -> None:
        self._proof_namespace: frog_ast.Namespace = proof_namespace or {}

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
                transformed.left_expression, self._proof_namespace
            )
        ):
            return frog_ast.Boolean(True)
        if (
            transformed.operator == frog_ast.BinaryOperators.NOTEQUALS
            and transformed.left_expression == transformed.right_expression
            and not has_nondeterministic_call(
                transformed.left_expression, self._proof_namespace
            )
        ):
            return frog_ast.Boolean(False)
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


class SimplifyNotPass(TransformPass):
    name = "Simplify Nots"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return SimplifyNot().transform(game)


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
            type_map, proof_namespace=ctx.proof_namespace
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


class ReflexiveComparison(TransformPass):
    name = "Reflexive Comparison"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        return ReflexiveComparisonTransformer(
            proof_namespace=ctx.proof_namespace
        ).transform(game)
