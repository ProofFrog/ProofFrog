# pylint: disable=duplicate-code
# Operator dispatch table is structurally similar to visitors.Z3FormulaVisitor.
"""Symbolic computation pass using SymPy.

Dispatches arithmetic sub-expressions to SymPy for symbolic simplification,
enabling the engine to reason about parameterized type sizes (e.g.,
``BitString<n + n>`` becoming ``BitString<2*n>``).
"""

from __future__ import annotations

import operator
from typing import List

from sympy import Symbol

from .. import frog_ast
from .. import frog_parser
from ..visitors import Transformer
from ._base import NearMiss, TransformPass, PipelineContext

# The nodes whose transform pushes their own value.  Any other node leaves
# what its children pushed: the length of ``1^2``, the ``3`` of ``-3``.
_VALUED_NODES = (frog_ast.Integer, frog_ast.Variable, frog_ast.BinaryOperation)

# ---------------------------------------------------------------------------
# Transformer class (moved from visitors.py)
# ---------------------------------------------------------------------------


class SymbolicComputationTransformer(Transformer):
    """Evaluates arithmetic sub-expressions symbolically using SymPy.

    Tracks a computation stack while traversing the AST.  When both operands
    of an arithmetic binary operation (+, -, *, /, ^) resolve to known
    symbolic or integer values, the expression is replaced with the
    simplified result.

    **Soundness invariant:** The ``variables`` dict must contain only ``Int``
    typed proof parameters (not ``BitString`` or other types).  This is
    critical because the transform treats ``ADD`` as arithmetic addition, but
    in FrogLang ``ADD`` on ``BitString`` is XOR.  The proof engine enforces
    this by gating on ``isinstance(let.type, frog_ast.IntType)`` when
    populating the dict.  Likewise, only an ``Integer``, a ``Variable`` or
    a ``BinaryOperation`` operand has a value, so a bit-string literal or a
    negation is never read as an Int.
    """

    def __init__(
        self,
        variables: dict[str, Symbol | frog_ast.Expression],
        ctx: PipelineContext | None = None,
    ) -> None:
        self.variables = variables
        self.ctx = ctx
        self.computation_stack: List[Symbol | int | None] = []
        self._method_name: str | None = None

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        saved = self._method_name
        self._method_name = method.signature.name
        try:
            return self._transform_children(method)
        finally:
            self._method_name = saved

    def transform_variable(self, variable: frog_ast.Variable) -> frog_ast.Variable:
        if variable.name in self.variables:
            val = self.variables[variable.name]
            assert isinstance(val, Symbol)
            self.computation_stack.append(val)
        else:
            self.computation_stack.append(None)
        return variable

    def transform_integer(self, integer: frog_ast.Integer) -> frog_ast.Integer:
        self.computation_stack.append(integer.num)
        return integer

    def transform_bit_string_type(
        self, bs_type: frog_ast.BitStringType
    ) -> frog_ast.BitStringType:
        new_bs = frog_ast.BitStringType(
            self.transform(bs_type.parameterization)
            if bs_type.parameterization
            else bs_type.parameterization
        )
        self.computation_stack.append(None)
        return new_bs

    def transform_mod_int_type(
        self, mod_int_type: frog_ast.ModIntType
    ) -> frog_ast.ModIntType:
        new_modulus = self.transform(mod_int_type.modulus)
        self.computation_stack.append(None)
        return frog_ast.ModIntType(new_modulus)

    def transform_binary_operation(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> frog_ast.ASTNode:
        old_len = len(self.computation_stack)
        transformed_left = self.transform(binary_operation.left_expression)
        left_val = self._pop_value(binary_operation.left_expression, old_len)
        transformed_right = self.transform(binary_operation.right_expression)
        right_val = self._pop_value(binary_operation.right_expression, old_len)
        simplified_expression = None
        operators = {
            frog_ast.BinaryOperators.ADD: operator.add,
            frog_ast.BinaryOperators.SUBTRACT: operator.sub,
            frog_ast.BinaryOperators.MULTIPLY: operator.mul,
            frog_ast.BinaryOperators.DIVIDE: operator.floordiv,
            frog_ast.BinaryOperators.EXPONENTIATE: operator.pow,
        }
        if binary_operation.operator in operators:
            if left_val is None or right_val is None:
                self._note_negated_operand(binary_operation, left_val, right_val)
            # For division, only simplify when both operands are
            # concrete integers.  Symbolic floor division produces
            # floor(expr) which has no FrogLang representation, and
            # rational arithmetic would violate integer semantics.
            elif binary_operation.operator == frog_ast.BinaryOperators.DIVIDE and not (
                isinstance(left_val, int) and isinstance(right_val, int)
            ):
                pass  # leave symbolic divisions unsimplified
            else:
                simplified_expression = operators[binary_operation.operator](
                    left_val, right_val
                )
        self.computation_stack.append(simplified_expression)
        if simplified_expression is not None:
            return frog_parser.parse_expression(str(simplified_expression))
        return frog_ast.BinaryOperation(
            binary_operation.operator, transformed_left, transformed_right
        )

    def _pop_value(
        self, operand: frog_ast.Expression, base: int
    ) -> Symbol | int | None:
        """Pops what transforming ``operand`` pushed and returns its value."""
        pushed = self.computation_stack[base:]
        del self.computation_stack[base:]
        if isinstance(operand, _VALUED_NODES) and len(pushed) == 1:
            return pushed[0]
        return None

    def _is_negated_constant(self, operand: frog_ast.Expression) -> bool:
        """``-c`` for an Int literal or Int parameter ``c``."""
        if not (
            isinstance(operand, frog_ast.UnaryOperation)
            and operand.operator == frog_ast.UnaryOperators.MINUS
        ):
            return False
        inner = operand.expression
        return isinstance(inner, frog_ast.Integer) or (
            isinstance(inner, frog_ast.Variable) and inner.name in self.variables
        )

    def _note_negated_operand(
        self,
        binary_operation: frog_ast.BinaryOperation,
        left_val: Symbol | int | None,
        right_val: Symbol | int | None,
    ) -> None:
        """Records arithmetic left unfolded only because an operand is ``-c``."""
        if self.ctx is None:
            return
        unknown = [
            operand
            for operand, value in (
                (binary_operation.left_expression, left_val),
                (binary_operation.right_expression, right_val),
            )
            if value is None
        ]
        if not all(self._is_negated_constant(operand) for operand in unknown):
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Symbolic Computation",
                reason=(
                    f"'{binary_operation}' not folded: operand '{unknown[0]}' "
                    "is a negation, which the pass does not evaluate"
                ),
                location=binary_operation.origin,
                suggestion=(
                    "Write the folded value, or the same expression in both "
                    "games, so both canonicalize alike"
                ),
                variable=None,
                method=self._method_name,
            )
        )


# ---------------------------------------------------------------------------
# TransformPass wrapper
# ---------------------------------------------------------------------------


class SymbolicComputation(TransformPass):
    name = "Symbolic Computation"

    def apply(self, game: frog_ast.Game, ctx: PipelineContext) -> frog_ast.Game:
        # Soundness check: all variables must be Int-typed (Symbol or Integer
        # literal).  Non-Int values (e.g. BitString) would cause ADD to be
        # incorrectly treated as arithmetic addition instead of XOR.
        for name, val in ctx.variables.items():
            assert isinstance(val, (Symbol, frog_ast.Integer)), (
                f"SymbolicComputation variable '{name}' has type "
                f"{type(val).__name__}, expected Symbol or Integer.  "
                f"Only Int-typed proof parameters may enter the variables dict."
            )
        return SymbolicComputationTransformer(ctx.variables, ctx).transform(game)
