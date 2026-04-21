"""Tests for the structural AST sort key (node_sort_key)."""

import inspect

import pytest

from proof_frog import frog_ast
from proof_frog.transforms._ordering import node_sort_key


# ---------------------------------------------------------------------------
# Completeness: every concrete ASTNode subclass is covered
# ---------------------------------------------------------------------------

def _concrete_subclasses(base: type) -> set[type]:
    """Recursively collect all non-abstract concrete subclasses of *base*."""
    result: set[type] = set()
    for cls in base.__subclasses__():
        if not inspect.isabstract(cls):
            result.add(cls)
        result |= _concrete_subclasses(cls)
    return result


# Nodes that are containers / non-canonical and not expected in sort contexts.
_EXCLUDED = {
    # Abstract base classes
    frog_ast.Expression,
    frog_ast.Type,
    frog_ast.Statement,
    # Top-level containers (not part of game ASTs)
    frog_ast.Root,
    frog_ast.Primitive,
    frog_ast.Scheme,
    frog_ast.Game,
    frog_ast.Reduction,
    frog_ast.GameFile,
    frog_ast.Method,
    frog_ast.MethodSignature,
    frog_ast.Field,
    frog_ast.Parameter,
    frog_ast.Import,
    # Proof-file-level nodes (never appear inside game canonicalization)
    frog_ast.ProofFile,
    frog_ast.Step,
    frog_ast.StepAssumption,
    frog_ast.Induction,
    frog_ast.Lemma,
    frog_ast.StructuralRequirement,
}

# Factory functions that build a minimal instance of each covered type.
_FACTORIES: dict[type, frog_ast.ASTNode] = {
    frog_ast.Variable: frog_ast.Variable("x"),
    frog_ast.Integer: frog_ast.Integer(0),
    frog_ast.Boolean: frog_ast.Boolean(True),
    frog_ast.NoneExpression: frog_ast.NoneExpression(),
    frog_ast.BinaryNum: frog_ast.BinaryNum(0, 1),
    frog_ast.BitStringLiteral: frog_ast.BitStringLiteral(0, frog_ast.Variable("n")),
    frog_ast.GroupGenerator: frog_ast.GroupGenerator(frog_ast.Variable("G")),
    frog_ast.GroupOrder: frog_ast.GroupOrder(frog_ast.Variable("G")),
    frog_ast.FieldAccess: frog_ast.FieldAccess(frog_ast.Variable("x"), "f"),
    frog_ast.ArrayAccess: frog_ast.ArrayAccess(
        frog_ast.Variable("arr"), frog_ast.Integer(0)
    ),
    frog_ast.Slice: frog_ast.Slice(
        frog_ast.Variable("arr"), frog_ast.Integer(0), frog_ast.Integer(1)
    ),
    frog_ast.UnaryOperation: frog_ast.UnaryOperation(
        frog_ast.UnaryOperators.NOT, frog_ast.Boolean(True)
    ),
    frog_ast.BinaryOperation: frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Variable("b")
    ),
    frog_ast.FuncCall: frog_ast.FuncCall(frog_ast.Variable("f"), []),
    frog_ast.Tuple: frog_ast.Tuple([frog_ast.Integer(1)]),
    frog_ast.Set: frog_ast.Set([]),
    frog_ast.ParameterizedGame: frog_ast.ParameterizedGame("G", []),
    frog_ast.ConcreteGame: frog_ast.ConcreteGame(
        frog_ast.ParameterizedGame("G", []), "Left"
    ),
    # Types
    frog_ast.IntType: frog_ast.IntType(),
    frog_ast.BoolType: frog_ast.BoolType(),
    frog_ast.Void: frog_ast.Void(),
    frog_ast.BitStringType: frog_ast.BitStringType(frog_ast.Variable("n")),
    frog_ast.ModIntType: frog_ast.ModIntType(frog_ast.Variable("q")),
    frog_ast.GroupType: frog_ast.GroupType(),
    frog_ast.GroupElemType: frog_ast.GroupElemType(frog_ast.Variable("G")),
    frog_ast.ArrayType: frog_ast.ArrayType(frog_ast.IntType(), frog_ast.Integer(10)),
    frog_ast.MapType: frog_ast.MapType(frog_ast.IntType(), frog_ast.BoolType()),
    frog_ast.SetType: frog_ast.SetType(frog_ast.IntType()),
    frog_ast.FunctionType: frog_ast.FunctionType(frog_ast.IntType(), frog_ast.BoolType()),
    frog_ast.OptionalType: frog_ast.OptionalType(frog_ast.IntType()),
    frog_ast.ProductType: frog_ast.ProductType([frog_ast.IntType()]),
    # Statements
    frog_ast.Assignment: frog_ast.Assignment(
        frog_ast.IntType(), frog_ast.Variable("x"), frog_ast.Integer(1)
    ),
    frog_ast.Sample: frog_ast.Sample(
        frog_ast.BitStringType(frog_ast.Variable("n")),
        frog_ast.Variable("r"),
        frog_ast.BitStringType(frog_ast.Variable("n")),
    ),
    frog_ast.UniqueSample: frog_ast.UniqueSample(
        frog_ast.BitStringType(frog_ast.Variable("n")),
        frog_ast.Variable("r"),
        frog_ast.Variable("S"),
        frog_ast.BitStringType(frog_ast.Variable("n")),
    ),
    frog_ast.ReturnStatement: frog_ast.ReturnStatement(frog_ast.Integer(0)),
    frog_ast.IfStatement: frog_ast.IfStatement(
        [frog_ast.Boolean(True)],
        [frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(0))])],
    ),
    frog_ast.NumericFor: frog_ast.NumericFor(
        "i",
        frog_ast.Integer(0),
        frog_ast.Integer(10),
        frog_ast.Block([]),
    ),
    frog_ast.GenericFor: frog_ast.GenericFor(
        frog_ast.IntType(),
        "x",
        frog_ast.Variable("S"),
        frog_ast.Block([]),
    ),
    frog_ast.VariableDeclaration: frog_ast.VariableDeclaration(
        frog_ast.IntType(), "x"
    ),
    frog_ast.Block: frog_ast.Block([]),
}


def test_completeness() -> None:
    """Every concrete ASTNode subclass should be covered by node_sort_key."""
    all_concrete = _concrete_subclasses(frog_ast.ASTNode) - _EXCLUDED
    covered = set(_FACTORIES.keys())
    missing = all_concrete - covered
    assert not missing, f"node_sort_key has no test factory for: {missing}"

    # Verify none of the covered types fall through to the (999, ...) fallback.
    for cls, instance in _FACTORIES.items():
        key = node_sort_key(instance)
        assert key[0] != 999, f"{cls.__name__} fell through to fallback"


# ---------------------------------------------------------------------------
# Structural ordering: tag determines primary order
# ---------------------------------------------------------------------------

def test_expression_tag_ordering() -> None:
    """Simpler expression types sort before complex ones."""
    var = frog_ast.Variable("z")
    integer = frog_ast.Integer(0)
    binop = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Variable("b")
    )
    func = frog_ast.FuncCall(frog_ast.Variable("f"), [frog_ast.Variable("x")])

    assert node_sort_key(var) < node_sort_key(integer)
    assert node_sort_key(integer) < node_sort_key(binop)
    assert node_sort_key(binop) < node_sort_key(func)


def test_type_tag_ordering() -> None:
    """Type nodes sort by tag."""
    assert node_sort_key(frog_ast.IntType()) < node_sort_key(
        frog_ast.BitStringType(frog_ast.Variable("n"))
    )
    assert node_sort_key(frog_ast.BitStringType(frog_ast.Variable("n"))) < node_sort_key(
        frog_ast.GroupElemType(frog_ast.Variable("G"))
    )


def test_statement_tag_ordering() -> None:
    """Statement nodes sort by tag."""
    assign = frog_ast.Assignment(
        frog_ast.IntType(), frog_ast.Variable("x"), frog_ast.Integer(1)
    )
    sample = frog_ast.Sample(
        frog_ast.BitStringType(frog_ast.Variable("n")),
        frog_ast.Variable("r"),
        frog_ast.BitStringType(frog_ast.Variable("n")),
    )
    ret = frog_ast.ReturnStatement(frog_ast.Integer(0))

    assert node_sort_key(assign) < node_sort_key(sample)
    assert node_sort_key(sample) < node_sort_key(ret)


# ---------------------------------------------------------------------------
# Same-type tiebreaking
# ---------------------------------------------------------------------------

def test_variable_name_tiebreaking() -> None:
    assert node_sort_key(frog_ast.Variable("a")) < node_sort_key(frog_ast.Variable("b"))


def test_integer_value_tiebreaking() -> None:
    assert node_sort_key(frog_ast.Integer(1)) < node_sort_key(frog_ast.Integer(2))


def test_boolean_value_tiebreaking() -> None:
    # False (0) < True (1)
    assert node_sort_key(frog_ast.Boolean(False)) < node_sort_key(
        frog_ast.Boolean(True)
    )


# ---------------------------------------------------------------------------
# Recursive structure
# ---------------------------------------------------------------------------

def test_recursive_binop_ordering() -> None:
    """a + b < a + c because b < c."""
    ab = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Variable("b")
    )
    ac = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Variable("c")
    )
    assert node_sort_key(ab) < node_sort_key(ac)


def test_operator_name_ordering() -> None:
    """Different operators on same operands: sorted by operator name string."""
    add = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD, frog_ast.Variable("a"), frog_ast.Variable("b")
    )
    mul = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.Variable("a"),
        frog_ast.Variable("b"),
    )
    # "ADD" < "MULTIPLY"
    assert node_sort_key(add) < node_sort_key(mul)


def test_funccall_arg_ordering() -> None:
    """FuncCalls with same function sorted by arguments."""
    f_a = frog_ast.FuncCall(frog_ast.Variable("f"), [frog_ast.Variable("a")])
    f_b = frog_ast.FuncCall(frog_ast.Variable("f"), [frog_ast.Variable("b")])
    assert node_sort_key(f_a) < node_sort_key(f_b)


# ---------------------------------------------------------------------------
# Motivating case: structural complexity beats name
# ---------------------------------------------------------------------------

def test_variable_sorts_before_complex_expression() -> None:
    """Variable("field2") < BinaryOp(EXPONENTIATE, Variable("field1"), Variable("aprime")).

    This is the motivating case: a simple variable should sort before a
    complex expression regardless of the variable names involved.
    """
    simple = frog_ast.Variable("field2")
    complex_expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EXPONENTIATE,
        frog_ast.Variable("field1"),
        frog_ast.Variable("aprime"),
    )
    assert node_sort_key(simple) < node_sort_key(complex_expr)


# ---------------------------------------------------------------------------
# Cross-category ordering: expressions < types < statements
# ---------------------------------------------------------------------------

def test_expression_sorts_before_type() -> None:
    assert node_sort_key(frog_ast.Variable("x")) < node_sort_key(frog_ast.IntType())


def test_type_sorts_before_statement() -> None:
    assign = frog_ast.Assignment(
        frog_ast.IntType(), frog_ast.Variable("x"), frog_ast.Integer(1)
    )
    assert node_sort_key(frog_ast.IntType()) < node_sort_key(assign)


# ---------------------------------------------------------------------------
# Optional / None fields
# ---------------------------------------------------------------------------

def test_bitstring_type_unparameterized() -> None:
    """Unparameterized BitStringType produces a shorter tuple."""
    unparameterized = frog_ast.BitStringType()
    parameterized = frog_ast.BitStringType(frog_ast.Variable("n"))
    # (33,) < (33, (0, "n"))
    assert node_sort_key(unparameterized) < node_sort_key(parameterized)


def test_set_type_unparameterized() -> None:
    unparameterized = frog_ast.SetType()
    parameterized = frog_ast.SetType(frog_ast.IntType())
    assert node_sort_key(unparameterized) < node_sort_key(parameterized)


# ---------------------------------------------------------------------------
# Determinism: same node always produces the same key
# ---------------------------------------------------------------------------

def test_determinism() -> None:
    """Calling node_sort_key twice on the same node produces identical keys."""
    for instance in _FACTORIES.values():
        assert node_sort_key(instance) == node_sort_key(instance)
