import pytest
from proof_frog import frog_parser
from proof_frog.transforms.algebraic import NormalizeCommutativeChainsTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Commutativity: b + a -> a + b
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return b + a;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b;
            }
            """,
        ),
        # Already sorted: a + b unchanged
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b;
            }
            """,
        ),
        # Associativity: a + (b + c) -> (a + b) + c (left-assoc after sort)
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + (b + c);
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Both: (c + a) + b -> (a + b) + c
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return (c + a) + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c;
            }
            """,
        ),
        # Multiplication: b * a -> a * b
        (
            """
            Int f(Int a, Int b) {
                return b * a;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a * b;
            }
            """,
        ),
        # Non-commutative operator left alone: a - b unchanged
        (
            """
            Int f(Int a, Int b) {
                return a - b;
            }
            """,
            """
            Int f(Int a, Int b) {
                return a - b;
            }
            """,
        ),
        # Mixed: (d + b) + (c + a) -> a + b + c + d
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c, BitString<lambda> d) {
                return (d + b) + (c + a);
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c, BitString<lambda> d) {
                return a + b + c + d;
            }
            """,
        ),
        # Nested in assignment context
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> x = b + a;
                return x;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                BitString<lambda> x = a + b;
                return x;
            }
            """,
        ),
        # Equality: b == a -> a == b
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return b == a;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
        ),
        # Equality: already sorted unchanged
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a == b;
            }
            """,
        ),
        # Inequality: b != a -> a != b
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return b != a;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
        ),
        # F-260: a `==` containing a NON-deterministic call is left in place.
        # With the empty namespace here `f(a)` is a non-deterministic call, so
        # swapping it (to canonicalize FuncCall-after-Variable) is declined --
        # reordering could change side-effect order. (A deterministic call still
        # swaps; see test_f260_deterministic_call_still_reorders.)
        (
            """
            Bool f(Int a, Int b) {
                return f(a) == a;
            }
            """,
            """
            Bool f(Int a, Int b) {
                return f(a) == a;
            }
            """,
        ),
    ],
)
def test_normalize_commutative_chains(method: str, expected: str) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed = NormalizeCommutativeChainsTransformer().transform(method_ast)

    print("EXPECTED:", expected_ast)
    print("TRANSFORMED:", transformed)
    assert expected_ast == transformed


def _det_namespace():
    prim = frog_parser.parse_primitive_file(
        """
        Primitive P(Int n) {
            deterministic Int det(Int x);
        }
        """
    )
    return {"F": prim}


def test_f260_two_stateful_calls_not_reordered() -> None:
    """F-260: two non-deterministic calls in a `+` chain must NOT be reordered --
    swapping `challenger.Inc() + challenger.Get()` changes which side effect
    fires first, so two distinguishable expressions would collapse to one."""
    method = frog_parser.parse_method(
        """
        Int f(Int a) {
            return challenger.Inc() + challenger.Get();
        }
        """
    )
    result = NormalizeCommutativeChainsTransformer().transform(method)
    assert result == method, "chain with stateful calls must keep source order"


def test_f260_pure_chain_still_reorders() -> None:
    """F-260 positive control: a chain with no calls is reordered as before."""
    method = frog_parser.parse_method(
        """
        Int f(Int a, Int b, Int c) {
            return c + a + b;
        }
        """
    )
    expected = frog_parser.parse_method(
        """
        Int f(Int a, Int b, Int c) {
            return a + b + c;
        }
        """
    )
    result = NormalizeCommutativeChainsTransformer().transform(method)
    assert result == expected


def test_f260_deterministic_call_still_reorders() -> None:
    """F-260: a DETERMINISTIC call has no side effect, so the structural swap
    (FuncCall sorts after Variable) still fires -- only non-deterministic calls
    block the reorder."""
    method = frog_parser.parse_method(
        """
        Bool f(Int a) {
            return F.det(a) == a;
        }
        """
    )
    expected = frog_parser.parse_method(
        """
        Bool f(Int a) {
            return a == F.det(a);
        }
        """
    )
    result = NormalizeCommutativeChainsTransformer(
        proof_namespace=_det_namespace()
    ).transform(method)
    assert result == expected


# ---------------------------------------------------------------------------
# G1: abstract primitive calls touch no game state, so they reorder
# ---------------------------------------------------------------------------


def _primitive_namespace():
    prim = frog_parser.parse_primitive_file(
        """
        Primitive P(Int n) {
            Int KeyGen();
            BitString<n> Samp();
            deterministic Int det(Int x);
        }
        """
    )
    return {"F": prim}


def test_g1_reorders_equality_with_nondeterministic_primitive_call() -> None:
    """An abstract primitive call touches no game state (FROGLANG_REFERENCE,
    evaluation order), so moving it past another operand changes nothing:
    `F.KeyGen() != v` and `v != F.KeyGen()` are the same program."""
    method = frog_parser.parse_method(
        "Bool f(Int v) {\n return F.KeyGen() != v;\n}"
    )
    expected = frog_parser.parse_method(
        "Bool f(Int v) {\n return v != F.KeyGen();\n}"
    )
    result = NormalizeCommutativeChainsTransformer(
        proof_namespace=_primitive_namespace()
    ).transform(method)
    assert result == expected


def test_g1_reorders_xor_chain_with_primitive_calls() -> None:
    method = frog_parser.parse_method(
        "BitString<n> f(BitString<n> a) {\n return F.Samp() + a;\n}"
    )
    expected = frog_parser.parse_method(
        "BitString<n> f(BitString<n> a) {\n return a + F.Samp();\n}"
    )
    result = NormalizeCommutativeChainsTransformer(
        proof_namespace=_primitive_namespace()
    ).transform(method)
    assert result == expected


def test_g1_reorders_with_let_function_call() -> None:
    from proof_frog.visitors import NameTypeMap
    from proof_frog import frog_ast

    lets = NameTypeMap()
    lets.set("H", frog_ast.FunctionType(frog_ast.IntType(), frog_ast.IntType()))
    method = frog_parser.parse_method("Bool f(Int a) {\n return H(a) == a;\n}")
    expected = frog_parser.parse_method("Bool f(Int a) {\n return a == H(a);\n}")
    result = NormalizeCommutativeChainsTransformer(
        proof_namespace=_primitive_namespace(), proof_let_types=lets
    ).transform(method)
    assert result == expected


def test_g1_keeps_order_with_challenger_call() -> None:
    """A challenger call may read or write the challenger's state: with a
    primitive call beside it the chain keeps its order (F-260)."""
    for source in (
        # Sorting would put the variable first (Variable < FuncCall).
        "Bool f(Int k) {\n return challenger.Get() == k;\n}",
        # The flattened chain [challenger.Get(), F.KeyGen(), k] would sort.
        "Int f(Int k) {\n return challenger.Get() + F.KeyGen() + k;\n}",
    ):
        method = frog_parser.parse_method(source)
        result = NormalizeCommutativeChainsTransformer(
            proof_namespace=_primitive_namespace()
        ).transform(method)
        assert result == method, source


def test_g1_keeps_order_with_uninlined_scheme_call() -> None:
    """A scheme method left uninlined is not an abstract primitive call: it
    is treated as touching state."""
    scheme = frog_parser.parse_scheme_file(
        """
        Scheme S() extends P {
            Int Enc(Int k) {
                return k;
            }
        }
        """
    )
    namespace = _primitive_namespace()
    namespace["T"] = scheme
    method = frog_parser.parse_method("Bool f(Int k) {\n return T.Enc(k) == k;\n}")
    result = NormalizeCommutativeChainsTransformer(proof_namespace=namespace).transform(
        method
    )
    assert result == method
