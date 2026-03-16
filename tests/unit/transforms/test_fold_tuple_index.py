from proof_frog import frog_ast
from proof_frog.transforms.tuples import FoldTupleIndexTransformer


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _int(n: int) -> frog_ast.Integer:
    return frog_ast.Integer(n)


def _tuple(*vals: frog_ast.Expression) -> frog_ast.Tuple:
    return frog_ast.Tuple(list(vals))


def _access(arr: frog_ast.Expression, idx: frog_ast.Expression) -> frog_ast.ArrayAccess:
    return frog_ast.ArrayAccess(arr, idx)


def _call(func_name: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(_var(func_name), list(args))


def test_basic_index_0() -> None:
    """[a, b][0] -> a"""
    expr = _access(_tuple(_var("a"), _var("b")), _int(0))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _var("a")


def test_basic_index_1() -> None:
    """[a, b][1] -> b"""
    expr = _access(_tuple(_var("a"), _var("b")), _int(1))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _var("b")


def test_three_element_index_2() -> None:
    """[a, b, c][2] -> c"""
    expr = _access(_tuple(_var("a"), _var("b"), _var("c")), _int(2))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _var("c")


def test_nested_tuple() -> None:
    """[[a, b], [c, d]][0] -> [a, b]"""
    inner0 = _tuple(_var("a"), _var("b"))
    inner1 = _tuple(_var("c"), _var("d"))
    expr = _access(_tuple(inner0, inner1), _int(0))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _tuple(_var("a"), _var("b"))


def test_no_fold_discarded_has_func_call() -> None:
    """[a, G(b)][0] should NOT fold (discarded element has function call)"""
    expr = _access(_tuple(_var("a"), _call("G", _var("b"))), _int(0))
    result = FoldTupleIndexTransformer().transform(expr)
    # Should be unchanged
    assert result == _access(_tuple(_var("a"), _call("G", _var("b"))), _int(0))


def test_fold_selected_has_func_call() -> None:
    """[G(a), b][0] SHOULD fold (selected element has func call, discarded is pure)"""
    expr = _access(_tuple(_call("G", _var("a")), _var("b")), _int(0))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _call("G", _var("a"))


def test_no_fold_non_constant_index() -> None:
    """[a, b][i] should NOT fold (index is not a constant)"""
    expr = _access(_tuple(_var("a"), _var("b")), _var("i"))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _access(_tuple(_var("a"), _var("b")), _var("i"))


def test_no_fold_not_tuple() -> None:
    """v[0] should NOT fold (array is not a tuple literal)"""
    expr = _access(_var("v"), _int(0))
    result = FoldTupleIndexTransformer().transform(expr)
    assert result == _access(_var("v"), _int(0))


def test_recursive_in_assignment() -> None:
    """Folding works inside assignments."""
    assign = frog_ast.Assignment(
        frog_ast.IntType(),
        _var("x"),
        _access(_tuple(_var("a"), _var("b")), _int(0)),
    )
    result = FoldTupleIndexTransformer().transform(assign)
    expected = frog_ast.Assignment(frog_ast.IntType(), _var("x"), _var("a"))
    assert result == expected
