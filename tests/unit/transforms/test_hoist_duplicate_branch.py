"""Tests for HoistDuplicateBranchCall.

A deterministic call that is the entire expression of a `return` in several
exclusive branches is extracted to a single local computed before the
branches. Calls in non-return positions, single occurrences, and
non-deterministic calls are left untouched.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import HoistDuplicateBranchCallTransformer


def _det_namespace() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


def _nondet_namespace() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


def _apply(method_src: str, namespace: frog_ast.Namespace) -> frog_ast.Method:
    method = frog_parser.parse_method(method_src)
    return HoistDuplicateBranchCallTransformer(proof_namespace=namespace).transform(
        method
    )


def test_hoists_duplicate_return_call() -> None:
    result = _apply(
        """
        BitString<n> f(Bool P, BitString<n> x) {
            if (P) {
                return G.evaluate(x);
            }
            return G.evaluate(x);
        }
        """,
        _det_namespace(),
    )
    expected = frog_parser.parse_method(
        """
        BitString<n> f(Bool P, BitString<n> x) {
            BitString<n> __hoist_0__ = G.evaluate(x);
            if (P) {
                return __hoist_0__;
            }
            return __hoist_0__;
        }
        """
    )
    assert result == expected, f"\nGot:\n{result}\nExpected:\n{expected}"


def test_single_occurrence_unchanged() -> None:
    src = """
        BitString<n> f(Bool P, BitString<n> x) {
            if (P) {
                return G.evaluate(x);
            }
            return x;
        }
        """
    result = _apply(src, _det_namespace())
    assert result == frog_parser.parse_method(src)


def test_nondeterministic_call_unchanged() -> None:
    src = """
        BitString<n> f(Bool P, BitString<n> x) {
            if (P) {
                return G.evaluate(x);
            }
            return G.evaluate(x);
        }
        """
    result = _apply(src, _nondet_namespace())
    assert result == frog_parser.parse_method(src)


def test_non_return_position_unchanged() -> None:
    # The duplicate call is not the entire expression of a return, so it is
    # left in place (hoisting an arbitrary in-branch call could change branch
    # simplification).
    src = """
        BitString<n> f(Bool P, BitString<n> x) {
            if (P) {
                BitString<n> a = G.evaluate(x);
                return a;
            }
            BitString<n> b = G.evaluate(x);
            return b;
        }
        """
    result = _apply(src, _det_namespace())
    assert result == frog_parser.parse_method(src)


def test_f211_mints_fresh_name_over_preexisting_hoist_local() -> None:
    """F-211(a): when a local named `__hoist_0__` already exists (e.g. minted
    by an earlier fixed-point iteration and preserved downstream), the pass
    must mint a FRESH name for the new group rather than emitting a second,
    differently-valued `__hoist_0__` declaration (a capture-unsafe clobber)."""
    method = _apply(
        """
        BitString<n> O(Bool b, Bool c, BitString<n> x, BitString<n> y) {
            BitString<n> __hoist_0__ = G.evaluate(x);
            if (b) { return G.evaluate(y); }
            if (c) { return G.evaluate(y); }
            return __hoist_0__;
        }
        """,
        _det_namespace(),
    )
    decls = [
        s
        for s in method.block.statements
        if isinstance(s, frog_ast.Assignment)
        and isinstance(s.var, frog_ast.Variable)
        and s.var.name == "__hoist_0__"
    ]
    # The pre-existing `__hoist_0__` is preserved exactly once; the new group
    # is named `__hoist_1__`, so its value is not confused with `G.evaluate(x)`.
    assert len(decls) == 1
    assert "__hoist_1__" in str(method)
