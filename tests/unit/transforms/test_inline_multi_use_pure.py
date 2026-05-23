import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import InlineMultiUsePureExpressionTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Expression with ArrayAccess is NOT inlined (contains indexing)
        (
            """
            Int f([Int, Int] v1, [Int, Int] v2) {
                Int v3 = v1[0] + v2[0];
                return v3 + v3;
            }
            """,
            """
            Int f([Int, Int] v1, [Int, Int] v2) {
                Int v3 = v1[0] + v2[0];
                return v3 + v3;
            }
            """,
        ),
        # Pure expression without ArrayAccess IS inlined
        (
            """
            Int f(Int a, Int b) {
                Int v3 = a + b;
                return v3 + v3;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a + b + (a + b);
            }
            """,
        ),
        # Should NOT inline: expression contains function call
        (
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + v;
            }
            """,
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + v;
            }
            """,
        ),
        # Should NOT inline: free variable is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v1 = [2, 3];
                return v3 + v3;
            }
            """,
        ),
        # Should NOT inline: alias variable is reassigned
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                v3 = 99;
                return v3;
            }
            """,
        ),
        # Should NOT inline: plain variable (handled by RedundantCopy)
        (
            """
            Int f(Int a) {
                Int b = a;
                return b + b;
            }
            """,
            """
            Int f(Int a) {
                Int b = a;
                return b + b;
            }
            """,
        ),
        # Array access: v3 = v1[0] is NOT inlined (contains ArrayAccess)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                Int a = v3 + v3;
                return a + v3;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return v3 + v3 + v3;
            }
            """,
        ),
        # Variable not used — no change (other passes clean up)
        (
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return 42;
            }
            """,
            """
            Int f([Int, Int] v1) {
                Int v3 = v1[0];
                return 42;
            }
            """,
        ),
    ],
)
def test_inline_multi_use_pure(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = InlineMultiUsePureExpressionTransformer().transform(game_ast)
    assert expected_ast == transformed_ast


# Regression for `9b9a75d`: a sampled ``Function<D, R>`` proof-let is
# deterministic in FrogLang semantics (same input -> same output), so the
# pass MUST inline a multi-use binding whose RHS is a call to such a
# Function — even though all other FuncCall RHSs are skipped. A non-let
# FuncCall (e.g. an unannotated scheme method) must still be skipped.

def _run_with_function_names(method_src: str, function_var_names: set[str]) -> str:
    method = frog_parser.parse_method(method_src)
    out = InlineMultiUsePureExpressionTransformer(
        function_var_names=function_var_names
    ).transform(method)
    return str(out)


def test_inlines_call_to_proof_let_function() -> None:
    """``H`` is a proof-let ``Function<D,R>``; ``v = H(x)`` is multi-use
    pure and must be inlined at both use sites."""
    before = """
        BitString<8> f(BitString<8> x) {
            BitString<8> v = H(x);
            return v + v;
        }
    """
    expected = """
        BitString<8> f(BitString<8> x) {
            return H(x) + H(x);
        }
    """
    got = _run_with_function_names(before, {"H"})
    assert got == str(frog_parser.parse_method(expected))


def test_does_not_inline_call_when_function_not_in_let_set() -> None:
    """If the callee is *not* a known ``Function<D,R>`` proof-let, the
    pass falls back to its conservative no-FuncCall rule."""
    before = """
        BitString<8> f(BitString<8> x) {
            BitString<8> v = H(x);
            return v + v;
        }
    """
    got = _run_with_function_names(before, set())
    assert got == str(frog_parser.parse_method(before))


def test_does_not_inline_when_function_call_has_array_access_arg() -> None:
    """Even with a Function<D,R> RHS, ArrayAccess inside the expression
    still triggers the indexing-spread guard."""
    before = """
        BitString<8> f(Array<BitString<8>, 2> arr) {
            BitString<8> v = H(arr[0]);
            return v + v;
        }
    """
    got = _run_with_function_names(before, {"H"})
    assert got == str(frog_parser.parse_method(before))
