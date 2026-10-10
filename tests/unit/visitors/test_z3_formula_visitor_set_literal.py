"""Tests for Z3FormulaVisitor's handling of set literals.

Without a ``leave_set`` handler a literal's elements leaked onto the visitor
stack, and an enclosing operation popped them as its operands.
``{a, b} == {c, b}`` encoded as ``c == b``, and ``({3} \\ 3) == {t, t}`` as
``t == t``. A set literal now encodes as one opaque atom, or as None when an
element doesn't translate.
"""

import pytest
import z3

from proof_frog import frog_ast, frog_parser, visitors


def _type_map(**types: frog_ast.Type) -> visitors.NameTypeMap:
    type_map = visitors.NameTypeMap()
    for name, the_type in types.items():
        type_map.set(name, the_type)
    return type_map


def _ints(*names: str) -> visitors.NameTypeMap:
    return _type_map(**{name: frog_ast.IntType() for name in names})


def _encode(
    src: str, type_map: visitors.NameTypeMap, fallback: bool = False
) -> z3.AstRef | None:
    return visitors.Z3FormulaVisitor(
        type_map, variable_version_map={}, opaque_func_call_fallback=fallback
    ).visit(frog_parser.parse_expression(src))


def _valid(formula: z3.AstRef) -> bool:
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    return solver.check() == z3.unsat


def _satisfiable(*formulas: z3.AstRef) -> bool:
    solver = z3.Solver()
    solver.add(*formulas)
    return solver.check() == z3.sat


# ---------------------------------------------------------------------------
# Soundness: a set literal must not encode as its elements
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fallback", [False, True])
def test_set_equality_does_not_entail_last_elements_equal(fallback: bool) -> None:
    # {0, -1} == {0, -1} holds with a = 0, b = -1, c = 0, yet c != b.
    formula = _encode("{a, b} == {c, b}", _ints("a", "b", "c"), fallback)
    assert formula is not None
    assert _satisfiable(formula, z3.Int("c") != z3.Int("b"))


@pytest.mark.parametrize(
    "src",
    [
        "({3} \\ 3) == {t, t}",
        "{3} == {t, t}",
        "{t, t} == {1, 1}",
        "{2, 3} == {1, 1}",
    ],
)
@pytest.mark.parametrize("fallback", [False, True])
def test_set_comparison_is_not_a_tautology(src: str, fallback: bool) -> None:
    formula = _encode(src, _ints("t"), fallback)
    assert formula is None or not _valid(formula)


@pytest.mark.parametrize("fallback", [False, True])
def test_membership_in_literal_keeps_conjunct(fallback: bool) -> None:
    # The leaked `x` became the left operand of `&&`, dropping `!c`.
    bools = _type_map(
        c=frog_ast.BoolType(),
        x=frog_ast.BoolType(),
        y=frog_ast.BoolType(),
        z=frog_ast.BoolType(),
    )
    formula = _encode("!c && (x in {y, z})", bools, fallback)
    assert formula is not None
    assert not _satisfiable(formula, z3.Bool("c"))


def test_set_minus_refuses() -> None:
    assert _encode("({3} \\ 3) == {t, t}", _ints("t")) is None


def test_call_element_refuses() -> None:
    assert _encode("{F.f(x)} == {F.f(x)}", _ints("x")) is None


# ---------------------------------------------------------------------------
# Completeness: comparisons Z3 decides correctly still translate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fallback", [False, True])
def test_identical_literals_are_equal(fallback: bool) -> None:
    formula = _encode("{a, b} == {a, b}", _ints("a", "b"), fallback)
    assert formula is not None
    assert _valid(formula)


@pytest.mark.parametrize("fallback", [False, True])
def test_membership_in_literal_is_an_atom(fallback: bool) -> None:
    formula = _encode("(x in {a, b}) || !(x in {a, b})", _ints("x", "a", "b"), fallback)
    assert formula is not None
    assert _valid(formula)


def test_set_variable_equality() -> None:
    sets = _type_map(
        S=frog_ast.SetType(frog_ast.IntType()), T=frog_ast.SetType(frog_ast.IntType())
    )
    same = _encode("S == S", sets)
    other = _encode("S == T", sets)
    assert same is not None and _valid(same)
    assert other is not None and not _valid(other)
