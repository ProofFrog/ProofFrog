import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        # Core case: variable used in a larger return expression (not directly returned)
        (
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2, BitString<lambda> mL) {
                BitString<lambda> v3 = v1 + G.evaluate(v2);
                return v3 + mL;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2, BitString<lambda> mL) {
                return v1 + G.evaluate(v2) + mL;
            }
            """,
        ),
        # Simple expression (no function call) used in a return expression
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                BitString<lambda> tmp = a + b;
                return tmp + c;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Variable used once in a non-return statement; recursion handles both levels
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                BitString<lambda> tmp = a + b;
                BitString<lambda> result = tmp + c;
                return result;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Should NOT inline when variable is used twice
        (
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2) {
                BitString<lambda> v3 = v1 + G.evaluate(v2);
                return v3 + v3;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2) {
                BitString<lambda> v3 = v1 + G.evaluate(v2);
                return v3 + v3;
            }
            """,
        ),
        # Should NOT inline when a free variable in expr is modified before use
        (
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2, BitString<lambda> mL) {
                BitString<lambda> v3 = v1 + v2;
                v1 = mL;
                return v3 + mL;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2, BitString<lambda> mL) {
                BitString<lambda> v3 = v1 + v2;
                v1 = mL;
                return v3 + mL;
            }
            """,
        ),
        # Should NOT inline simple variable copies — those are RedundantCopyTransformer's job,
        # and this transformer explicitly skips them (value is a plain Variable)
        (
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> mL) {
                BitString<lambda> v3 = v1;
                return v3 + mL;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> mL) {
                BitString<lambda> v3 = v1;
                return v3 + mL;
            }
            """,
        ),
        # Intermediate statement sampling an unrelated variable: still safe to inline
        (
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2) {
                BitString<lambda> v3 = v1 + G.evaluate(v2);
                BitString<lambda> other <- BitString<lambda>;
                return v3 + other;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v1, BitString<lambda> v2) {
                BitString<lambda> other <- BitString<lambda>;
                return v1 + G.evaluate(v2) + other;
            }
            """,
        ),
        # Should NOT inline when a free variable is sampled (overwritten) before use
        (
            """
            BitString<lambda> f(BitString<lambda> v2) {
                BitString<lambda> v1 <- BitString<lambda>;
                BitString<lambda> v3 = v1 + v2;
                v1 <- BitString<lambda>;
                return v3 + v1;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> v2) {
                BitString<lambda> v1 <- BitString<lambda>;
                BitString<lambda> v3 = v1 + v2;
                v1 <- BitString<lambda>;
                return v3 + v1;
            }
            """,
        ),
        # Should NOT inline when the value is a Tuple literal (ExpandTupleTransformer
        # needs to see the pattern `c = [a, b]; return c[0]` intact)
        (
            """
            Int * Int f(Int a, Int b) {
                Int * Int c = [a, b];
                return c[0];
            }
            """,
            """
            Int * Int f(Int a, Int b) {
                Int * Int c = [a, b];
                return c[0];
            }
            """,
        ),
        # Works inside if-statement blocks
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                if (True) {
                    BitString<lambda> tmp = a + b;
                    return tmp + c;
                }
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                if (True) {
                    return a + b + c;
                }
            }
            """,
        ),
        # Int arithmetic: inline tmp used in subtraction
        (
            """
            Int f(Int a, Int b, Int c) {
                Int tmp = a + b;
                return tmp - c;
            }
            """,
            """
            Int f(Int a, Int b, Int c) {
                return a + b - c;
            }
            """,
        ),
        # Int arithmetic: inline a product used as a factor
        (
            """
            Int f(Int a, Int b, Int c) {
                Int tmp = a + b;
                return tmp * c;
            }
            """,
            """
            Int f(Int a, Int b, Int c) {
                return (a + b) * c;
            }
            """,
        ),
        # Int: chain of three intermediate variables
        (
            """
            Int f(Int a, Int b, Int c, Int d) {
                Int t1 = a + b;
                Int t2 = t1 * c;
                return t2 - d;
            }
            """,
            """
            Int f(Int a, Int b, Int c, Int d) {
                return (a + b) * c - d;
            }
            """,
        ),
        # Int: should NOT inline when variable is used twice
        (
            """
            Int f(Int a, Int b) {
                Int tmp = a + b;
                return tmp * tmp;
            }
            """,
            """
            Int f(Int a, Int b) {
                Int tmp = a + b;
                return tmp * tmp;
            }
            """,
        ),
        # Int: should NOT inline when a free variable is overwritten before use
        (
            """
            Int f(Int a, Int b, Int c) {
                Int tmp = a + b;
                a = 0;
                return tmp + c;
            }
            """,
            """
            Int f(Int a, Int b, Int c) {
                Int tmp = a + b;
                a = 0;
                return tmp + c;
            }
            """,
        ),
        # Bool: inline a conjunction used inside a disjunction
        (
            """
            Bool f(Bool a, Bool b, Bool c) {
                Bool tmp = a && b;
                return tmp || c;
            }
            """,
            """
            Bool f(Bool a, Bool b, Bool c) {
                return a && b || c;
            }
            """,
        ),
        # Bool: inline a comparison into a return
        (
            """
            Bool f(Int a, Int b, Bool c) {
                Bool tmp = a < b;
                return tmp && c;
            }
            """,
            """
            Bool f(Int a, Int b, Bool c) {
                return a < b && c;
            }
            """,
        ),
        # Bool: should NOT inline when used twice
        (
            """
            Bool f(Bool a, Bool b) {
                Bool tmp = a && b;
                return tmp || tmp;
            }
            """,
            """
            Bool f(Bool a, Bool b) {
                Bool tmp = a && b;
                return tmp || tmp;
            }
            """,
        ),
        # Int function call: inline a function result used in an expression
        (
            """
            Int f(Int a, Int b) {
                Int tmp = h(a);
                return tmp + b;
            }
            """,
            """
            Int f(Int a, Int b) {
                return h(a) + b;
            }
            """,
        ),
        # Int with intermediate unrelated sampling: still safe to inline
        (
            """
            Int f(Int a, Int b) {
                Int tmp = a + b;
                Int other <- Int;
                return tmp + other;
            }
            """,
            """
            Int f(Int a, Int b) {
                Int other <- Int;
                return a + b + other;
            }
            """,
        ),
    ],
)
def test_inline_single_use_variable(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)
    transformed_ast = visitors.InlineSingleUseVariableTransformer().transform(method_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
