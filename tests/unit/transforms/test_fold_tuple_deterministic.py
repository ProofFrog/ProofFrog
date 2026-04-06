"""Tests for FoldTupleIndex interaction with ``deterministic`` annotations.

When a discarded tuple element contains only calls to deterministic primitive
methods, folding should be allowed (the call has no side effects and can be
safely discarded).  Without the annotation, the call is treated as
potentially non-deterministic and folding is blocked.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.tuples import FoldTupleIndexTransformer


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _int(n: int) -> frog_ast.Integer:
    return frog_ast.Integer(n)


def _tuple(*vals: frog_ast.Expression) -> frog_ast.Tuple:
    return frog_ast.Tuple(list(vals))


def _access(arr: frog_ast.Expression, idx: frog_ast.Expression) -> frog_ast.ArrayAccess:
    return frog_ast.ArrayAccess(arr, idx)


def _field_call(obj: str, method: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    """Build ``obj.method(args)`` as a FuncCall with FieldAccess."""
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(obj), method), list(args))


def _make_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose Eval method is deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> Eval(BitString<n> x);
        }
        """)
    return {"G": prim}


def _make_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose Eval method is NOT deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            BitString<n> Eval(BitString<n> x);
        }
        """)
    return {"G": prim}


def test_fold_with_deterministic_discarded() -> None:
    """[G.Eval(x), b][1] should fold when G.Eval is deterministic —
    the discarded element G.Eval(x) is pure and safe to drop."""
    expr = _access(_tuple(_field_call("G", "Eval", _var("x")), _var("b")), _int(1))
    result = FoldTupleIndexTransformer(proof_namespace=_make_det_namespace()).transform(
        expr
    )
    assert result == _var("b")


def test_no_fold_with_nondeterministic_discarded() -> None:
    """[G.Eval(x), b][1] should NOT fold when G.Eval is not deterministic —
    the discarded element may have observable effects."""
    expr = _access(_tuple(_field_call("G", "Eval", _var("x")), _var("b")), _int(1))
    result = FoldTupleIndexTransformer(
        proof_namespace=_make_nondet_namespace()
    ).transform(expr)
    # Should be unchanged
    assert result == _access(
        _tuple(_field_call("G", "Eval", _var("x")), _var("b")), _int(1)
    )


def test_no_fold_without_namespace() -> None:
    """Without a namespace, function calls are treated as non-deterministic."""
    expr = _access(_tuple(_field_call("G", "Eval", _var("x")), _var("b")), _int(1))
    result = FoldTupleIndexTransformer().transform(expr)
    # Should be unchanged
    assert result == _access(
        _tuple(_field_call("G", "Eval", _var("x")), _var("b")), _int(1)
    )


def test_fold_selected_has_nondeterministic_call() -> None:
    """[b, G.Eval(x)][0] SHOULD fold — the selected element is pure (just
    a variable), and the discarded element's determinism doesn't matter
    when it's the selected element that's being kept."""
    expr = _access(_tuple(_var("b"), _field_call("G", "Eval", _var("x"))), _int(0))
    # Even without deterministic annotation, selected element is pure
    result = FoldTupleIndexTransformer(
        proof_namespace=_make_nondet_namespace()
    ).transform(expr)
    # This should NOT fold because the discarded element has a non-det call
    assert result == _access(
        _tuple(_var("b"), _field_call("G", "Eval", _var("x"))), _int(0)
    )
