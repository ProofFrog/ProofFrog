"""Unit tests for the EasyCrypt ExpressionTranslator."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt.expr_translator import ExpressionTranslator
from proof_frog.export.easycrypt.type_collector import TypeCollector


def _make(
    local_types: dict[str, frog_ast.Type] | None = None,
    known_abstract: set[str] | None = None,
    types: TypeCollector | None = None,
) -> ExpressionTranslator:
    if types is None:
        types = TypeCollector(known_abstract_types=known_abstract)
    local = local_types or {}

    def type_of(e: frog_ast.Expression) -> frog_ast.Type:
        if isinstance(e, frog_ast.Variable) and e.name in local:
            return local[e.name]
        raise KeyError(e)

    return ExpressionTranslator(types, type_of)


def test_translate_tuple_literal() -> None:
    tr = _make()
    t = frog_ast.Tuple([frog_ast.Variable("a"), frog_ast.Variable("b")])
    assert tr.translate(t) == "(a, b)"


def test_translate_indexed_tuple_access() -> None:
    tr = _make()
    access = frog_ast.ArrayAccess(frog_ast.Variable("t"), frog_ast.Integer(0))
    assert tr.translate(access) == "t.`1"
    access2 = frog_ast.ArrayAccess(frog_ast.Variable("t"), frog_ast.Integer(1))
    assert tr.translate(access2) == "t.`2"


def test_translate_variable() -> None:
    tr = _make()
    assert tr.translate(frog_ast.Variable("x")) == "x"


def test_translate_random_function_application() -> None:
    """``RF(rest)`` -- application of a sampled random function -- renders as
    EC's juxtaposition application ``RF rest``."""
    tr = _make()
    call = frog_ast.FuncCall(frog_ast.Variable("RF"), [frog_ast.Variable("rest")])
    assert tr.translate(call) == "RF rest"


def test_field_rename_applies_to_references() -> None:
    """An uppercase-initial field (EC requires lowercase-initial module
    variables) is renamed consistently at its reference sites."""
    types = TypeCollector()

    def _no_type(e: frog_ast.Expression) -> frog_ast.Type:
        raise KeyError(e)

    tr = ExpressionTranslator(types, _no_type, field_renames={"RF": "rF"})
    call = frog_ast.FuncCall(frog_ast.Variable("RF"), [frog_ast.Variable("rest")])
    assert tr.translate(call) == "rF rest"


def test_translate_boolean_literal() -> None:
    tr = _make()
    assert tr.translate(frog_ast.Boolean(True)) == "true"
    assert tr.translate(frog_ast.Boolean(False)) == "false"


def _binop(
    op: frog_ast.BinaryOperators, left: frog_ast.Expression, right: frog_ast.Expression
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(op, left, right)


def test_translate_group_multiplication() -> None:
    """``*`` on GroupElem operands renders as the stdlib ``G.( * )`` op."""
    g = frog_ast.GroupElemType(frog_ast.Variable("G"))
    tr = _make({"a": g, "b": g})
    expr = _binop(
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    assert tr.translate(expr) == "G.( * ) a b"


def test_translate_group_division() -> None:
    """``/`` on GroupElem operands renders as ``G.( / )``."""
    g = frog_ast.GroupElemType(frog_ast.Variable("G"))
    tr = _make({"a": g, "b": g})
    expr = _binop(
        frog_ast.BinaryOperators.DIVIDE,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    assert tr.translate(expr) == "G.( / ) a b"


def test_translate_group_exponentiation_general() -> None:
    """``g ^ x`` (general group) renders as the base integer power over the
    ring representative: ``G.( ^ ) a (G_Exp.asint e)``."""
    g = frog_ast.GroupElemType(frog_ast.Variable("G"))
    x = frog_ast.ModIntType(frog_ast.FieldAccess(frog_ast.Variable("G"), "order"))
    tr = _make({"a": g, "e": x})
    expr = _binop(
        frog_ast.BinaryOperators.EXPONENTIATE,
        frog_ast.Variable("a"),
        frog_ast.Variable("e"),
    )
    assert tr.translate(expr) == "G.( ^ ) a (G_Exp.asint e)"


def test_translate_group_exponentiation_prime() -> None:
    """``g ^ x`` (prime group) uses the ergonomic PowZMod field power
    ``G_P.( ^ ) a e`` (no asint)."""
    g = frog_ast.GroupElemType(frog_ast.Variable("G"))
    x = frog_ast.ModIntType(frog_ast.FieldAccess(frog_ast.Variable("G"), "order"))
    types = TypeCollector(prime_group_names={"G"})
    tr = _make({"a": g, "e": x}, types=types)
    expr = _binop(
        frog_ast.BinaryOperators.EXPONENTIATE,
        frog_ast.Variable("a"),
        frog_ast.Variable("e"),
    )
    assert tr.translate(expr) == "G_P.( ^ ) a e"


def test_translate_group_generator_constant() -> None:
    """``G.generator`` renders as the stdlib generator ``G.g``."""
    types = TypeCollector()

    def type_of(e: frog_ast.Expression) -> frog_ast.Type:
        if isinstance(e, frog_ast.FieldAccess):
            return frog_ast.GroupElemType(frog_ast.Variable("G"))
        raise KeyError(e)

    tr = ExpressionTranslator(types, type_of)
    gen = frog_ast.FieldAccess(frog_ast.Variable("G"), "generator")
    assert tr.translate(gen) == "G.g"


def test_translate_modint_multiplication_is_ring_op() -> None:
    """``*`` on ModInt operands renders as the stdlib ring ``ModInt_q.( * )``."""
    q = frog_ast.ModIntType(frog_ast.Variable("q"))
    tr = _make({"a": q, "b": q})
    expr = _binop(
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    assert tr.translate(expr) == "ModInt_q.( * ) a b"


def test_translate_modint_zero_literal() -> None:
    """An integer ``0`` in a ModInt subtraction position renders as the stdlib
    ring zero ``ModInt_q.zero`` (the engine collapses ``x - x`` to ``0``)."""
    q = frog_ast.ModIntType(frog_ast.Variable("q"))
    tr = _make({"a": q})
    expr = _binop(
        frog_ast.BinaryOperators.SUBTRACT,
        frog_ast.Variable("a"),
        frog_ast.Integer(0),
    )
    assert tr.translate(expr) == "ModInt_q.( - ) a ModInt_q.zero"


def test_translate_equality() -> None:
    """``==`` / ``!=`` render as EC's ``=`` / ``<>``."""
    tr = _make()
    eq = _binop(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    assert tr.translate(eq) == "a = b"
    ne = _binop(
        frog_ast.BinaryOperators.NOTEQUALS,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    assert tr.translate(ne) == "a <> b"
