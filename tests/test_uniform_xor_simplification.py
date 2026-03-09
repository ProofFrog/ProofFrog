import pytest
from proof_frog import visitors, frog_parser


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: uniform + m -> uniform
        (
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                return u + m;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                return u;
            }
            """,
        ),
        # Reversed operand order: m + uniform -> uniform
        (
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                return m + u;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                return u;
            }
            """,
        ),
        # In assignment context: x = u + m -> x = u
        (
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> x = u + m;
                return x;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> x = u;
                return x;
            }
            """,
        ),
        # Multi-use of uniform variable: should NOT transform
        (
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> x = u + m;
                return x + u;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> x = u + m;
                return x + u;
            }
            """,
        ),
        # Non-sample variable: should NOT transform
        (
            """
            BitString<lambda> f(BitString<lambda> m, BitString<lambda> v) {
                return v + m;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> m, BitString<lambda> v) {
                return v + m;
            }
            """,
        ),
        # Uniform not used in XOR: should NOT transform
        (
            """
            BitString<lambda> f() {
                BitString<lambda> u <- BitString<lambda>;
                return u;
            }
            """,
            """
            BitString<lambda> f() {
                BitString<lambda> u <- BitString<lambda>;
                return u;
            }
            """,
        ),
        # Nested XOR: (u + a) + b -> u (after repeated application)
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> u <- BitString<lambda>;
                return u + a + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> u <- BitString<lambda>;
                return u;
            }
            """,
        ),
        # Multiple independent samples: both should simplify
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> v <- BitString<lambda>;
                BitString<lambda> x = u + a;
                return v + x;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> u <- BitString<lambda>;
                BitString<lambda> v <- BitString<lambda>;
                BitString<lambda> x = u;
                return v;
            }
            """,
        ),
        # Non-bitstring sample: should NOT transform (Int)
        (
            """
            Int f(Int m) {
                Int u <- Int;
                return u + m;
            }
            """,
            """
            Int f(Int m) {
                Int u <- Int;
                return u + m;
            }
            """,
        ),
        # Non-bitstring sample: should NOT transform (Bool)
        (
            """
            Bool f(Bool m) {
                Bool u <- Bool;
                return u + m;
            }
            """,
            """
            Bool f(Bool m) {
                Bool u <- Bool;
                return u + m;
            }
            """,
        ),
    ],
)
def test_uniform_xor_simplification(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    # Apply repeatedly to handle nested XOR (mirroring engine's iterative pipeline)
    transformed_ast = method_ast
    while True:
        new_ast = visitors.UniformXorSimplificationTransformer().transform(
            transformed_ast
        )
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast
