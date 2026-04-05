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
from ._base import TransformPass, PipelineContext

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
    populating the dict.
    """

    def __init__(self, variables: dict[str, Symbol | frog_ast.Expression]) -> None:
        self.variables = variables
        self.computation_stack: List[Symbol | int | None] = []

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
        transformed_right = self.transform(binary_operation.right_expression)
        if len(self.computation_stack) == 2 + old_len:
            simplified_expression = None
            operators = {
                frog_ast.BinaryOperators.ADD: operator.add,
                frog_ast.BinaryOperators.SUBTRACT: operator.sub,
                frog_ast.BinaryOperators.MULTIPLY: operator.mul,
                frog_ast.BinaryOperators.DIVIDE: operator.floordiv,
                frog_ast.BinaryOperators.EXPONENTIATE: operator.pow,
            }
            if (
                binary_operation.operator in operators
                and self.computation_stack[-1] is not None
                and self.computation_stack[-2] is not None
            ):
                left_val = self.computation_stack[-2]
                right_val = self.computation_stack[-1]
                # For division, only simplify when both operands are
                # concrete integers.  Symbolic floor division produces
                # floor(expr) which has no FrogLang representation, and
                # rational arithmetic would violate integer semantics.
                if (
                    binary_operation.operator == frog_ast.BinaryOperators.DIVIDE
                    and not (isinstance(left_val, int) and isinstance(right_val, int))
                ):
                    pass  # leave symbolic divisions unsimplified
                else:
                    simplified_expression = operators[binary_operation.operator](
                        left_val, right_val
                    )
            self.computation_stack.pop()
            self.computation_stack.pop()
            if simplified_expression is not None:
                self.computation_stack.append(simplified_expression)
                return frog_parser.parse_expression(str(simplified_expression))
            self.computation_stack.append(None)

        return frog_ast.BinaryOperation(
            binary_operation.operator, transformed_left, transformed_right
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
        return SymbolicComputationTransformer(ctx.variables).transform(game)
