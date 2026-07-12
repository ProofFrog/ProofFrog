"""Tests for Z3FormulaVisitor's handling of ProductType-as-expression nodes.

Instantiation converts an all-variable tuple literal into a ProductType
node (Variable is both Expression and Type). Before the
``leave_product_type`` handler existed, such a node's visited children
leaked onto the visitor stack, so ``[a, b] == [c, d]`` (with ProductType
literals) encoded as the WRONG formula ``c == d`` — an actively unsound
input for RemoveUnreachable's dead-branch solver. The handler must encode
it exactly like a Tuple literal.

Also covers the ``|...|`` stack-discipline fix: the SIZE operand's visited
item must be popped, not leaked beneath the appended None.
"""

import z3

from proof_frog import frog_ast, frog_parser, visitors


def _parse_expr(src: str) -> frog_ast.Expression:
    return frog_parser.parse_expression(src)


def _empty_type_map() -> visitors.NameTypeMap:
    return visitors.NameTypeMap()


def _product(*names: str) -> frog_ast.ProductType:
    return frog_ast.ProductType([frog_ast.Variable(n) for n in names])


def _equiv(f1: z3.AstRef, f2: z3.AstRef) -> bool:
    solver = z3.Solver()
    solver.add(z3.Not(f1 == f2))
    return solver.check() == z3.unsat


def test_product_type_equality_encodes_componentwise() -> None:
    # [a, b] == [c, d] with ProductType literals must encode identically to
    # the same equality with genuine Tuple literals.
    mangled = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, _product("a", "b"), _product("c", "d")
    )
    tuple_form = _parse_expr("[a, b] == [c, d]")
    f_mangled = visitors.Z3FormulaVisitor(_empty_type_map()).visit(mangled)
    f_tuple = visitors.Z3FormulaVisitor(_empty_type_map()).visit(tuple_form)
    assert f_mangled is not None
    assert f_tuple is not None
    assert _equiv(f_mangled, f_tuple)


def test_product_type_equality_is_not_the_old_garbage_formula() -> None:
    # Regression: the leaked-children encoding produced `c == d`. The fixed
    # encoding must NOT be equivalent to that.
    mangled = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, _product("a", "b"), _product("c", "d")
    )
    f_mangled = visitors.Z3FormulaVisitor(_empty_type_map()).visit(mangled)
    garbage = visitors.Z3FormulaVisitor(_empty_type_map()).visit(_parse_expr("c == d"))
    assert f_mangled is not None
    assert garbage is not None
    assert not _equiv(f_mangled, garbage)


def test_product_type_indexing_encodes_component() -> None:
    # [a, b][1] == b must be tautologically true.
    expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        frog_ast.ArrayAccess(_product("a", "b"), frog_ast.Integer(1)),
        frog_ast.Variable("b"),
    )
    formula = visitors.Z3FormulaVisitor(_empty_type_map()).visit(expr)
    assert formula is not None
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    assert solver.check() == z3.unsat


def test_size_operand_is_popped_not_leaked() -> None:
    # `|a| == |b|` is untranslatable (None), and must not leave leaked
    # operand items behind that a later visit could mis-pop.
    visitor = visitors.Z3FormulaVisitor(_empty_type_map())
    assert visitor.visit(_parse_expr("|a| == |b|")) is None
    # A subsequent, unrelated visit on the same visitor must be unaffected.
    formula = visitor.visit(_parse_expr("x == x"))
    assert formula is not None
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    assert solver.check() == z3.unsat


def test_tuple_containing_size_is_none_not_garbage() -> None:
    # [|a|, b] == [c, d]: the size member is untranslatable, so the whole
    # comparison must be None — never a partial/garbage equality.
    left = frog_ast.Tuple(
        [
            frog_ast.UnaryOperation(
                frog_ast.UnaryOperators.SIZE, frog_ast.Variable("a")
            ),
            frog_ast.Variable("b"),
        ]
    )
    expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS, left, _product("c", "d")
    )
    assert visitors.Z3FormulaVisitor(_empty_type_map()).visit(expr) is None
