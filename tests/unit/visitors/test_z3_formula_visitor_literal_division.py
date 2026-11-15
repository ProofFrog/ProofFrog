"""Z3FormulaVisitor on a division of two integer literals.

Two Python integers were divided with Python's true division: `6 / 3` became
the float 2.0, not FrogLang's integer division, and `0 / 0` raised
ZeroDivisionError, which aborted the whole proof. Symbolic Computation folds
every such division except one by zero, whose value is unspecified, so the
visitor does not model it: None by default, a memoized opaque atom with the
fallback on (the same operands give the same atom).
"""

import pytest
import z3

from proof_frog import frog_ast, frog_parser, visitors


def _visit(
    src: str, fallback: bool = False, types: visitors.NameTypeMap | None = None
) -> object:
    return visitors.Z3FormulaVisitor(
        types or visitors.NameTypeMap(), opaque_func_call_fallback=fallback
    ).visit(frog_parser.parse_expression(src))


def _int_types(*names: str) -> visitors.NameTypeMap:
    types = visitors.NameTypeMap()
    for name in names:
        types.set(name, frog_ast.IntType())
    return types


@pytest.mark.parametrize("src", ["0 / 0", "5 / 0", "6 / 3", "0 / 0 == a"])
def test_literal_division_not_modelled(src: str) -> None:
    assert _visit(src, types=_int_types("a")) is None


def test_literal_division_by_zero_opaque_with_fallback() -> None:
    formula = _visit("0 / 0 == 0 / 0", fallback=True)
    assert isinstance(formula, z3.BoolRef)
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    assert solver.check() == z3.unsat


def test_distinct_divisions_by_zero_distinct_atoms() -> None:
    formula = _visit("0 / 0 == 1 / 0", fallback=True)
    assert isinstance(formula, z3.BoolRef)
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    assert solver.check() == z3.sat


def test_variable_division_still_modelled() -> None:
    """A division with an Int variable operand is Z3 integer division."""
    formula = _visit("n / 2 == m", types=_int_types("n", "m"))
    assert isinstance(formula, z3.BoolRef)
