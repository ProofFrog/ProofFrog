"""Tests that ``has_nondeterministic_call`` correctly handles Function variables.

Function<D, R> variables in ``proof_let_types`` should be treated as
deterministic (same input always yields same output), while scheme/primitive
method calls follow the usual deterministic-annotation logic.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import has_nondeterministic_call
from proof_frog.visitors import NameTypeMap


def _make_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive F whose ``eval`` is deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive F(Int n) {
            deterministic BitString<n> eval(BitString<n> x);
        }
        """)
    return {"F": prim}


def _make_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive F whose ``eval`` is NOT deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive F(Int n) {
            BitString<n> eval(BitString<n> x);
        }
        """)
    return {"F": prim}


class TestFunctionVariableDeterminism:
    """has_nondeterministic_call should treat Function<D,R> vars as pure."""

    def test_function_var_call_is_deterministic(self) -> None:
        """H(x) where H is a Function<D, R> should be deterministic."""
        # Build AST for H(x)
        expr = frog_ast.FuncCall(
            frog_ast.Variable("H"),
            [frog_ast.Variable("x")],
        )
        let_types = NameTypeMap()
        let_types.set(
            "H",
            frog_ast.FunctionType(
                frog_ast.BitStringType(frog_ast.Integer(8)),
                frog_ast.BitStringType(frog_ast.Integer(16)),
            ),
        )
        result = has_nondeterministic_call(
            expr, proof_namespace={}, proof_let_types=let_types
        )
        assert result is False

    def test_function_var_without_let_types_is_nondeterministic(self) -> None:
        """H(x) with no proof_let_types should be treated as non-deterministic."""
        expr = frog_ast.FuncCall(
            frog_ast.Variable("H"),
            [frog_ast.Variable("x")],
        )
        result = has_nondeterministic_call(expr, proof_namespace={})
        assert result is True

    def test_non_function_var_call_is_nondeterministic(self) -> None:
        """H(x) where H is NOT a FunctionType should be non-deterministic."""
        expr = frog_ast.FuncCall(
            frog_ast.Variable("H"),
            [frog_ast.Variable("x")],
        )
        let_types = NameTypeMap()
        let_types.set(
            "H",
            frog_ast.BitStringType(frog_ast.Integer(8)),
        )
        result = has_nondeterministic_call(
            expr, proof_namespace={}, proof_let_types=let_types
        )
        assert result is True


class TestPrimitiveMethodDeterminism:
    """has_nondeterministic_call respects the deterministic annotation."""

    def test_nondet_primitive_call_is_nondeterministic(self) -> None:
        """F.eval(x) without deterministic annotation -> non-deterministic."""
        expr = frog_ast.FuncCall(
            frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
            [frog_ast.Variable("x")],
        )
        result = has_nondeterministic_call(
            expr, proof_namespace=_make_nondet_namespace()
        )
        assert result is True

    def test_det_primitive_call_is_deterministic(self) -> None:
        """F.eval(x) with deterministic annotation -> deterministic."""
        expr = frog_ast.FuncCall(
            frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
            [frog_ast.Variable("x")],
        )
        result = has_nondeterministic_call(expr, proof_namespace=_make_det_namespace())
        assert result is False
