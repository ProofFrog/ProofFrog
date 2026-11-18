# pylint: disable=duplicate-code
# Operator dispatch table is structurally similar to visitors.Z3FormulaVisitor.
"""Symbolic computation pass using SymPy.

Dispatches arithmetic sub-expressions to SymPy for symbolic simplification,
enabling the engine to reason about parameterized type sizes (e.g.,
``BitString<n + n>`` becoming ``BitString<2*n>``).
"""

from __future__ import annotations

import operator
from typing import List, Optional

import sympy
from sympy import Symbol
from sympy.printing.str import StrPrinter

from .. import frog_ast
from .. import frog_parser
from ..visitors import (
    NameTypeMap,
    Transformer,
    build_method_type_map,
    expression_type,
    referenced_variable_names,
    with_proof_let_types,
)
from ._base import NearMiss, TransformPass, PipelineContext
from ._definedness import note_redeclared_name, redeclared_names

# The nodes whose transform pushes their own value.  Any other node leaves
# what its children pushed: the length of ``1^2``, the ``3`` of ``-3``.
_VALUED_NODES = (frog_ast.Integer, frog_ast.Variable, frog_ast.BinaryOperation)

# The SymPy nodes a folded value may be built from: each has FrogLang text
# with the same Int meaning (F-392).
_PRINTABLE = (sympy.Integer, sympy.Symbol, sympy.Add, sympy.Mul, sympy.Pow)


class _FrogLangPrinter(StrPrinter):  # type: ignore[misc]
    """SymPy's ``str`` with a power written ``(b ^ e)``, FrogLang's
    exponentiation: ``kl**2`` is not FrogLang (F-392)."""

    def _print_Pow(  # pylint: disable=invalid-name
        self, expr: sympy.Pow, rational: bool = False
    ) -> str:
        del rational
        base, exponent = expr.args
        return f"({self._operand(base)} ^ {self._operand(exponent)})"

    def _operand(self, expr: sympy.Expr) -> str:
        text = str(self._print(expr))
        if isinstance(expr, sympy.Symbol) or (
            isinstance(expr, sympy.Integer) and expr >= 0
        ):
            return text
        return f"({text})"


def _is_natural(value: object) -> bool:
    """A known integer >= 0 (a Python or SymPy integer)."""
    return (
        isinstance(value, (int, sympy.Integer))
        and not isinstance(value, bool)
        and value >= 0
    )


def _is_zero(value: object) -> bool:
    """The known integer 0 (a Python or SymPy integer)."""
    return (
        isinstance(value, (int, sympy.Integer))
        and not isinstance(value, bool)
        and value == 0
    )


def froglang_text(value: object, fractions: bool = False) -> Optional[str]:
    """FrogLang text for a value Symbolic Computation folded to, or None when
    it has none with the same Int meaning: anything but an integer
    polynomial whose powers have exponents that are integers >= 0 (SymPy
    prints ``k ** -1`` as the division ``1/k``, and a fraction or float has
    no Int literal) (F-392).

    With *fractions*, a rational coefficient is printed as SymPy prints it,
    as a division (``lambda/2``): the length computations of the type
    checker and the sample passes read ``/`` in a length as rational
    division and print their results that way."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, sympy.Basic):
        return None
    for node in sympy.preorder_traversal(value):
        if not isinstance(node, _PRINTABLE) and not (
            fractions and isinstance(node, sympy.Rational)
        ):
            return None
        if isinstance(node, sympy.Pow) and not _is_natural(node.exp):
            return None
    return str(_FrogLangPrinter().doprint(value))


def sympy_to_expression(
    value: object, fractions: bool = False
) -> Optional[frog_ast.Expression]:
    """The FrogLang expression for a SymPy (or Python int) value, or None
    when it has no FrogLang text (:func:`froglang_text`, which also explains
    *fractions*). Every place that turns a SymPy value back into FrogLang
    goes through here: SymPy's ``str`` writes a power ``k**2``, which is not
    FrogLang (F-392)."""
    text = froglang_text(value, fractions)
    return None if text is None else frog_parser.parse_expression(text)


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

    One rewrite needs no value for an operand: ``e + 0`` and ``0 + e``
    become ``e`` when ``e`` is an ``Int``, by its declared type
    (:meth:`_fold_add_zero`).  The types come from *game* (its fields) and
    the method being transformed (its parameters and locals), with the
    proof's ``let:`` types from *ctx* underneath.
    """

    def __init__(
        self,
        variables: dict[str, Symbol | frog_ast.Expression],
        ctx: PipelineContext | None = None,
        game: frog_ast.Game | None = None,
    ) -> None:
        self.variables = variables
        self.ctx = ctx
        self.computation_stack: List[Symbol | int | None] = []
        self._method_name: str | None = None
        self._game = game
        # Outside a method (a field's type or initializer) only the fields
        # and the proof's let: names are in scope.
        field_types = NameTypeMap()
        for field in game.fields if game is not None else []:
            field_types.set(field.name, field.type)
        self._types: NameTypeMap = with_proof_let_types(
            field_types, ctx.proof_let_types if ctx is not None else None
        )
        self._redeclared: set[str] = set()

    def transform_method(self, method: frog_ast.Method) -> frog_ast.Method:
        saved = (self._method_name, self._types, self._redeclared)
        self._method_name = method.signature.name
        game = self._game
        if game is None:
            game = frog_ast.Game(("", [], [], [method]))
        self._types = build_method_type_map(
            game, method, self.ctx.proof_let_types if self.ctx is not None else None
        )
        # The map gives a name one type for the whole method.
        self._redeclared = redeclared_names(self._game, method)
        try:
            return self._transform_children(method)
        finally:
            self._method_name, self._types, self._redeclared = saved

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
            folded = self._fold_add_zero(
                binary_operation,
                (transformed_left, left_val),
                (transformed_right, right_val),
            )
            if folded is not None:
                # Its value is still not known.
                self.computation_stack.append(None)
                return folded
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
            elif (
                binary_operation.operator == frog_ast.BinaryOperators.DIVIDE
                and right_val == 0
            ):
                # Division by zero is an unspecified value determined by its
                # operands (it does not fail), so ``c / 0`` has no literal to
                # fold to.  Python's floor division would raise here.
                self._note_division_by_zero(binary_operation)
            elif (
                binary_operation.operator == frog_ast.BinaryOperators.EXPONENTIATE
                and (not _is_natural(right_val))
            ):
                # SymPy's power laws (``k^a * k^b == k^(a + b)``, ``k^-1``
                # as ``1/k``) hold for Int only with exponents >= 0, and
                # Python's ``2 ** -1`` is a float (F-392).  So only a power
                # with such an exponent is evaluated, and every power in a
                # folded value has one.
                self._note_unprintable(binary_operation, f"{left_val} ** {right_val}")
            else:
                simplified_expression = operators[binary_operation.operator](
                    left_val, right_val
                )
        text = None
        if simplified_expression is not None:
            text = froglang_text(simplified_expression)
            if text is None:
                self._note_unprintable(binary_operation, str(simplified_expression))
                simplified_expression = None
        self.computation_stack.append(simplified_expression)
        if text is not None:
            return frog_parser.parse_expression(text)
        return frog_ast.BinaryOperation(
            binary_operation.operator, transformed_left, transformed_right
        )

    def _fold_add_zero(
        self,
        binary_operation: frog_ast.BinaryOperation,
        left: tuple[frog_ast.Expression, Symbol | int | None],
        right: tuple[frog_ast.Expression, Symbol | int | None],
    ) -> frog_ast.Expression | None:
        """``e`` for ``e + 0`` or ``0 + e`` when ``e`` is an ``Int`` whose
        value the pass does not know (a field, a local, a call); None
        otherwise.  Each pair is an operand after its own transform and its
        value.

        ``e + 0 == e`` for every Int ``e``, and dropping the literal leaves
        every evaluation of ``e`` in place.  A ``ModInt`` or ``BitString``
        ``e`` keeps its form: an integer literal next to a ``ModInt`` is an
        Int (F-357), and ``+`` on a bit string is XOR.  The type is read from
        the declarations in scope, so an operand reading a name the method
        binds more than once, or one shadowing a field, is not folded."""
        if binary_operation.operator != frog_ast.BinaryOperators.ADD:
            return None
        (left_expr, left_val), (right_expr, right_val) = left, right
        if _is_zero(right_val) and left_val is None:
            operand = left_expr
        elif _is_zero(left_val) and right_val is None:
            operand = right_expr
        else:
            return None
        redeclared = sorted(referenced_variable_names(operand) & self._redeclared)
        if redeclared:
            note_redeclared_name(
                self.ctx, "Symbolic Computation", redeclared[0], self._method_name
            )
            return None
        operand_type = expression_type(
            operand,
            self._types,
            self.ctx.proof_namespace if self.ctx is not None else None,
        )
        if isinstance(operand_type, frog_ast.IntType):
            return operand
        self._note_zero_kept(binary_operation, operand, operand_type)
        return None

    def _note_zero_kept(
        self,
        binary_operation: frog_ast.BinaryOperation,
        operand: frog_ast.Expression,
        operand_type: frog_ast.Type | None,
    ) -> None:
        """Records an addition of 0 left unfolded because the other operand
        is not known to be an Int."""
        if self.ctx is None:
            return
        if operand_type is None:
            why = f"the type of '{operand}' is not known"
        else:
            why = f"'{operand}' is a {operand_type}"
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Symbolic Computation",
                reason=(
                    f"'{binary_operation}' not folded: {why}, and '+ 0' is "
                    "dropped only next to an Int (an integer literal next to "
                    "a ModInt is an Int, and + on a BitString is XOR)"
                ),
                location=binary_operation.origin,
                suggestion=(
                    "Write the same addition in the other game, or give the "
                    "operand a declared Int type (a typed local)"
                ),
                variable=None,
                method=self._method_name,
            )
        )

    def _note_unprintable(
        self, binary_operation: frog_ast.BinaryOperation, value: str
    ) -> None:
        """Records arithmetic left unfolded because SymPy's value for it has
        no FrogLang text with the same Int meaning (F-392)."""
        if self.ctx is None:
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Symbolic Computation",
                reason=(
                    f"'{binary_operation}' not folded: its value '{value}' is "
                    "not an integer polynomial with exponents known to be "
                    ">= 0, the only Int powers SymPy's laws are exact for"
                ),
                location=binary_operation.origin,
                suggestion=(
                    "Use an exponent that is a literal >= 0, or write the "
                    "same power in the other game"
                ),
                variable=None,
                method=self._method_name,
            )
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

    def _note_division_by_zero(
        self, binary_operation: frog_ast.BinaryOperation
    ) -> None:
        """Records a division by the literal 0 left unfolded."""
        if self.ctx is None:
            return
        self.ctx.near_misses.append(
            NearMiss(
                transform_name="Symbolic Computation",
                reason=(
                    f"'{binary_operation}' not folded: division by zero has an "
                    "unspecified value, not a literal one"
                ),
                location=binary_operation.origin,
                suggestion=(
                    "Divide by a value that is nonzero, or write the same "
                    "division in the other game; two divisions by zero are "
                    "equal only when their operands are"
                ),
                variable=None,
                method=self._method_name,
            )
        )

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
                    "is a negation, which the pass does not evaluate (it may "
                    "be written in the game or left by an earlier fold, e.g. "
                    "'3 - 5' becoming '-2')"
                ),
                location=binary_operation.origin,
                suggestion=(
                    "Make both games reach the same arithmetic here: compare "
                    "with the other game's canonical form, and write the "
                    "subtraction or folded value it has"
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
        return SymbolicComputationTransformer(ctx.variables, ctx, game).transform(game)
