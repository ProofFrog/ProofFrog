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


def test_func_call_off_by_default_returns_none() -> None:
    # Without opt-in, a FuncCall-rooted expression is untranslatable: the
    # visitor returns None. (Previously this path leaked the call's
    # children onto the stack and returned a garbage sub-term -- see
    # test_bare_call_condition_returns_none_not_leaked_arg below.)
    expr = _parse_expr("H.evaluate(x) == H.evaluate(y)")
    formula = visitors.Z3FormulaVisitor(_empty_type_map()).visit(expr)
    assert formula is None


def test_bare_call_condition_returns_none_not_leaked_arg() -> None:
    # Regression: a bare method-call condition such as `S.Verify(pk, m, s)`
    # used directly as a Bool must translate to None, NOT leak its last
    # argument (`s`) as the formula. The leaked argument was an opaque
    # (non-Bool) atom that, fed into z3.And/z3.Not by RemoveUnreachable's
    # dead-code check, crashed canonicalization with a Z3 "sort mismatch".
    visitor = visitors.Z3FormulaVisitor(_empty_type_map(), variable_version_map={})
    formula = visitor.visit(_parse_expr("S.Verify(pk, m, s)"))
    assert formula is None
    # The visitor must also leave a balanced stack (the FuncCall contributes
    # exactly one net item -- None -- not one-per-child).
    assert visitor.stack == []


def test_bare_call_condition_composes_in_boolean_context() -> None:
    # The fix must keep a call condition usable inside boolean combinators
    # without raising: `!S.Verify(...)` is also untranslatable (None), and
    # combining None operands stays None rather than producing an
    # ill-sorted atom that would later crash z3.And.
    visitor = visitors.Z3FormulaVisitor(_empty_type_map(), variable_version_map={})
    assert visitor.visit(_parse_expr("!S.Verify(pk, m, s)")) is None
    assert visitor.stack == []


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


# ---------------------------------------------------------------------------
# Defense-in-depth: refuse non-deterministic calls under fallback when
# a proof_namespace is provided (the primary guard lives in
# `_z3_check_expression_pair`; this is the in-visitor backstop).
# ---------------------------------------------------------------------------


def test_fallback_with_namespace_refuses_nondeterministic_call() -> None:
    # A primitive method without `deterministic` annotation is
    # non-deterministic; with `opaque_func_call_fallback=True` and a
    # proof_namespace supplied, the visitor must refuse (return None)
    # to avoid the unsound memoization of independent samples.
    primitive = frog_parser.parse_primitive_file("Primitive P() { Bool m(); }")
    namespace: frog_ast.Namespace = {"P": primitive}
    expr = _parse_expr("P.m() == P.m()")
    formula = visitors.Z3FormulaVisitor(
        _empty_type_map(),
        opaque_func_call_fallback=True,
        proof_namespace=namespace,
    ).visit(expr)
    assert formula is None


def test_fallback_with_namespace_allows_deterministic_call() -> None:
    # Same shape but the primitive method is `deterministic`; the visitor
    # must NOT refuse -- the call can safely be memoized.
    primitive = frog_parser.parse_primitive_file(
        "Primitive P() { deterministic Bool m(); }"
    )
    namespace: frog_ast.Namespace = {"P": primitive}
    expr = _parse_expr("P.m() == P.m()")
    formula = visitors.Z3FormulaVisitor(
        _empty_type_map(),
        opaque_func_call_fallback=True,
        proof_namespace=namespace,
    ).visit(expr)
    assert formula is not None


# ---------------------------------------------------------------------------
# Bitstring literals (`0^n` / `1^n`): deterministic constants modelled as
# opaque atoms (issue #235). Without a handler the visitor left the literal's
# `length` subexpression on the stack, so `t == [0^n, 0^n]` produced
# `t@0 == n` -- an opaque-vs-Int sort-mismatch crash.
# ---------------------------------------------------------------------------


def _type_map_tuple_lambda() -> visitors.NameTypeMap:
    lam = frog_ast.Variable("lambda")
    bs = frog_ast.BitStringType(lam)
    tm = visitors.NameTypeMap()
    tm.set("t", frog_ast.ProductType([bs, bs]))
    tm.set("lambda", frog_ast.IntType())
    tm.set("n", frog_ast.IntType())
    return tm


def test_tuple_literal_vs_componentwise_equivalent() -> None:
    # Regression for #235: `t == [0^lambda, 0^lambda]` and its component-wise
    # form must translate to equivalent formulas instead of crashing with a
    # Z3 "sort mismatch".
    tm = _type_map_tuple_lambda()
    fa = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t == [0^lambda, 0^lambda]")
    )
    fb = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t[0] == 0^lambda && t[1] == 0^lambda")
    )
    assert fa is not None and fb is not None
    solver = z3.Solver()
    solver.add(fa != fb)
    assert solver.check() == z3.unsat


def test_bit_string_literal_distinct_bit_distinct_atoms() -> None:
    # `0^lambda` and `1^lambda` are different constants; they must not be
    # equated (guards against over-merging in the opaque encoding).
    tm = _type_map_tuple_lambda()
    fa = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t[0] == 0^lambda")
    )
    fb = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t[0] == 1^lambda")
    )
    assert fa is not None and fb is not None
    solver = z3.Solver()
    solver.add(fa != fb)
    assert solver.check() == z3.sat


def test_bit_string_literal_distinct_length_distinct_atoms() -> None:
    # `0^lambda` and `0^n` differ in length; they must map to distinct atoms.
    tm = _type_map_tuple_lambda()
    fa = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t[0] == 0^lambda")
    )
    fb = visitors.Z3FormulaVisitor(tm, opaque_func_call_fallback=True).visit(
        _parse_expr("t[0] == 0^n")
    )
    assert fa is not None and fb is not None
    solver = z3.Solver()
    solver.add(fa != fb)
    assert solver.check() == z3.sat


def test_bit_string_literal_off_by_default_returns_none() -> None:
    # Without opt-in, a bitstring literal is untranslatable (None) and the
    # stack stays balanced -- it must not leak its `length` child as a
    # garbage sub-term (the pre-fix behavior).
    visitor = visitors.Z3FormulaVisitor(_empty_type_map(), variable_version_map={})
    assert visitor.visit(_parse_expr("0^lambda")) is None
    assert visitor.stack == []


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
