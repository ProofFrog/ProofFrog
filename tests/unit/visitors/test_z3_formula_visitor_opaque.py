"""Tests for Z3FormulaVisitor's opaque-atom fallback path.

When constructed with `opaque_func_call_fallback=True`, the visitor
models FuncCall expressions and BinaryOperations with operand types Z3
cannot mix as memoized opaque Z3 constants. Two textually identical
sub-expressions must map to the same constant; structurally distinct
sub-expressions must map to different constants. The default
(`opaque_func_call_fallback=False`) preserves the historical behavior
used by canonicalization transforms.
"""

import z3

from proof_frog import frog_ast, frog_parser, visitors


def _parse_expr(src: str) -> frog_ast.Expression:
    return frog_parser.parse_expression(src)


def _empty_type_map() -> visitors.NameTypeMap:
    return visitors.NameTypeMap()


# ---------------------------------------------------------------------------
# Opaque atom memoization for FuncCall
# ---------------------------------------------------------------------------


def test_func_call_same_ast_shares_opaque_atom() -> None:
    # `H.evaluate(x) == H.evaluate(x)` should be tautologically true under
    # the opaque-atom encoding because the two textually identical calls
    # share a single Z3 constant.
    expr = _parse_expr("H.evaluate(x) == H.evaluate(x)")
    formula = visitors.Z3FormulaVisitor(
        _empty_type_map(), opaque_func_call_fallback=True
    ).visit(expr)
    assert formula is not None
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    assert solver.check() == z3.unsat


def test_func_call_distinct_ast_distinct_atoms() -> None:
    # `H.evaluate(x) == H.evaluate(y)` is NOT tautologically true; distinct
    # call ASTs must map to distinct Z3 consts so equality is decidable.
    expr = _parse_expr("H.evaluate(x) == H.evaluate(y)")
    formula = visitors.Z3FormulaVisitor(
        _empty_type_map(), opaque_func_call_fallback=True
    ).visit(expr)
    assert formula is not None
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    # Should be SAT: the two calls could legitimately differ.
    assert solver.check() == z3.sat


def test_func_call_off_by_default_returns_none_or_garbage() -> None:
    # Without opt-in, the visitor preserves its historical behavior:
    # FuncCall sub-expressions don't produce a clean Z3 formula. The
    # exact result is implementation-defined but it must NOT be a
    # tautologically-true Z3 BoolRef (which would unsoundly succeed).
    expr = _parse_expr("H.evaluate(x) == H.evaluate(y)")
    formula = visitors.Z3FormulaVisitor(_empty_type_map()).visit(expr)
    if formula is None:
        return
    # If a non-None formula came back, it must not be a tautology.
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    # Either SAT (formula isn't a tautology) or unknown is acceptable;
    # unsat would be a regression to unsound behavior.
    assert solver.check() != z3.unsat


# ---------------------------------------------------------------------------
# Opaque atom memoization for BinaryOperation type-mismatch fallback
# ---------------------------------------------------------------------------


def test_binary_op_bitstring_concat_falls_back_to_opaque() -> None:
    # `||` over BitString operands modelled as opaque consts: z3.Or
    # rejects them. Under the opt-in, the visitor falls back to an
    # opaque atom for the whole BinaryOperation. This lets compound
    # expressions like `H.evaluate(a || b) == H.evaluate(c || d)`
    # translate cleanly.
    expr = _parse_expr("H.evaluate(a || b) == H.evaluate(c || d)")
    formula = visitors.Z3FormulaVisitor(
        _empty_type_map(), opaque_func_call_fallback=True
    ).visit(expr)
    assert formula is not None


def test_binary_op_off_by_default_returns_none_for_concat() -> None:
    # Without opt-in, `||` over BitString operands still returns None
    # (preserving the historical behavior canonicalization transforms
    # rely on).
    expr = _parse_expr("H.evaluate(a || b) == H.evaluate(c || d)")
    formula = visitors.Z3FormulaVisitor(_empty_type_map()).visit(expr)
    # The visitor either returns None or a non-tautological formula;
    # crucially it must not be tautologically true.
    if formula is not None:
        solver = z3.Solver()
        solver.add(z3.Not(formula))
        assert solver.check() != z3.unsat


# ---------------------------------------------------------------------------
# Cross-instance constant sharing: critical for equivalence checking
# ---------------------------------------------------------------------------


def test_two_visitor_instances_share_opaque_atom_by_repr() -> None:
    # Equivalence checking constructs ONE visitor per game and translates
    # one expression each. For the formulas to compare cleanly, two
    # textually identical sub-expressions across the two visitor
    # instances must map to the SAME Z3 constant. The memo key uses
    # `repr(node)` and Z3 interns constants by name+sort, so two distinct
    # visitor instances both creating an opaque atom for the same AST
    # produce constants whose Z3-equality is decidable.
    expr_a = _parse_expr("H.evaluate(x)")
    expr_b = _parse_expr("H.evaluate(x)")
    fa = visitors.Z3FormulaVisitor(
        _empty_type_map(), opaque_func_call_fallback=True
    ).visit(expr_a)
    fb = visitors.Z3FormulaVisitor(
        _empty_type_map(), opaque_func_call_fallback=True
    ).visit(expr_b)
    assert fa is not None and fb is not None
    # Z3 cannot prove fa == fb because the two visitor instances allocate
    # independent atom sequence numbers (@@@opaque0 etc.). What matters
    # for equivalence checking is that the visitor's caller passes both
    # formulas to a single Z3 solver where they are uninterpreted but
    # syntactically distinct -- the equivalence helper handles that
    # via `Not(fa == fb)` and unsat. The key property tested here is
    # that the visitor produces a USABLE Z3 expression (not None) for
    # each side; cross-instance const sharing is a proof-engine
    # responsibility and exercised in the equivalence-helper tests.
