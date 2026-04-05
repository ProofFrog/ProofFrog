import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import (
    XorCancellationTransformer,
    ReflexiveComparisonTransformer,
)


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: k + k + m -> m
        (
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return k + k + m;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return m;
            }
            """,
        ),
        # Just XOR cancellation: a + b + a -> b
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return b;
            }
            """,
        ),
        # Three terms, middle cancels: a + b + c + b -> a + c
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + b + c + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b, BitString<lambda> c) {
                return a + c;
            }
            """,
        ),
        # No cancellation: a + b (different terms)
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
        # XOR cancellation does not inline variables (engine does that separately)
        (
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                BitString<lambda> x = k + m;
                BitString<lambda> y = k + x;
                return y;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                BitString<lambda> x = k + m;
                BitString<lambda> y = k + x;
                return y;
            }
            """,
        ),
        # Multiple pairs cancel: a + b + a + b -> all cancel.
        # Without type_map, the result is unchanged (can't produce 0^n).
        (
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a + b;
            }
            """,
            """
            BitString<lambda> f(BitString<lambda> a, BitString<lambda> b) {
                return a + b + a + b;
            }
            """,
        ),
    ],
)
def test_xor_cancellation(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    # Apply repeatedly to handle iterative cancellation
    transformed_ast = method_ast
    while True:
        new_ast = XorCancellationTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


@pytest.mark.parametrize(
    "method,expected",
    [
        # Reflexive equality: m == m -> true
        (
            """
            Bool f(BitString<lambda> m) {
                return m == m;
            }
            """,
            """
            Bool f(BitString<lambda> m) {
                return true;
            }
            """,
        ),
        # Reflexive inequality: m != m -> false
        (
            """
            Bool f(BitString<lambda> m) {
                return m != m;
            }
            """,
            """
            Bool f(BitString<lambda> m) {
                return false;
            }
            """,
        ),
        # Non-reflexive equality: should NOT simplify
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
        # Complex equal expressions: (a + b) == (a + b) -> true
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a + b == a + b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return true;
            }
            """,
        ),
        # Non-reflexive inequality: should NOT simplify
        (
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
            """
            Bool f(BitString<lambda> a, BitString<lambda> b) {
                return a != b;
            }
            """,
        ),
        # Reflexive equality on Int: x == x -> true
        (
            """
            Bool f(Int x) {
                return x == x;
            }
            """,
            """
            Bool f(Int x) {
                return true;
            }
            """,
        ),
    ],
)
def test_reflexive_comparison(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = ReflexiveComparisonTransformer().transform(method_ast)

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def test_xor_all_terms_cancel_returns_zero() -> None:
    """When all terms cancel (k + k), the result should be 0^n, not the
    original expression unchanged."""
    from proof_frog.visitors import build_game_type_map

    game_ast = frog_parser.parse_game("""
        Game G(Int lambda) {
            BitString<lambda> f(BitString<lambda> k) {
                return k + k;
            }
        }
    """)
    expected_ast = frog_parser.parse_game("""
        Game G(Int lambda) {
            BitString<lambda> f(BitString<lambda> k) {
                return 0^lambda;
            }
        }
    """)

    type_map = build_game_type_map(game_ast)
    transformed_ast = game_ast
    while True:
        new_ast = XorCancellationTransformer(type_map).transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    assert expected_ast == transformed_ast, (
        "k + k should simplify to 0^lambda"
    )


def test_no_cancellation_without_type_evidence() -> None:
    """When the type map exists but has no evidence for the ADD chain terms
    (e.g. all terms are complex expressions like function calls), XOR
    cancellation must NOT fire. The default-True fallback is unsound
    because the chain could be ModInt addition where a + a = 2a, not 0."""
    from proof_frog.transforms.algebraic import _is_bitstring_add_chain

    # Simulate an ADD chain where all terms are FuncCalls — the type map
    # has no entry for them, so the loop finds no evidence.
    func_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("G"), "f"),
        [frog_ast.Variable("a")],
    )
    add_chain = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD,
        func_call,
        func_call,
    )
    # Empty type map — no evidence about any variable
    empty_map: dict[str, frog_ast.Type] = {}
    result = _is_bitstring_add_chain(add_chain, empty_map)
    assert result is False, (
        "_is_bitstring_add_chain should default to False (conservative) "
        "when no type evidence is found, not True"
    )


def test_reflexive_comparison_skips_nondeterministic_calls() -> None:
    """F.eval(x) == F.eval(x) must NOT simplify to true when F.eval is
    non-deterministic, because each call may return a different value."""
    # Build: F.eval(x) == F.eval(x) where F.eval is non-deterministic
    func_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
        [frog_ast.Variable("x")],
    )
    eq_expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        func_call,
        func_call,
    )
    method_ast = frog_ast.Method(
        frog_ast.MethodSignature(
            "f",
            frog_ast.Variable("Bool"),
            [frog_ast.Parameter(frog_ast.Variable("Int"), "x")],
        ),
        frog_ast.Block([frog_ast.ReturnStatement(eq_expr)]),
    )
    # F is a primitive with a non-deterministic eval method
    f_primitive = frog_ast.Primitive(
        "F_Prim",
        [frog_ast.Parameter(frog_ast.Variable("Int"), "n")],
        [],
        [
            frog_ast.MethodSignature(
                "eval",
                frog_ast.Variable("Int"),
                [frog_ast.Parameter(frog_ast.Variable("Int"), "x")],
            ),
        ],
    )
    proof_namespace: frog_ast.Namespace = {"F": f_primitive}

    transformed = ReflexiveComparisonTransformer(
        proof_namespace=proof_namespace
    ).transform(method_ast)

    # The expression should NOT have been simplified to true
    ret_stmt = transformed.block.statements[0]
    assert isinstance(ret_stmt, frog_ast.ReturnStatement)
    assert not isinstance(ret_stmt.expression, frog_ast.Boolean), (
        "F.eval(x) == F.eval(x) should NOT simplify to true when F.eval is "
        "non-deterministic"
    )


def test_reflexive_comparison_allows_deterministic_calls() -> None:
    """F.eval(x) == F.eval(x) SHOULD simplify to true when F.eval is
    annotated as deterministic."""
    func_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
        [frog_ast.Variable("x")],
    )
    eq_expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.EQUALS,
        func_call,
        func_call,
    )
    method_ast = frog_ast.Method(
        frog_ast.MethodSignature(
            "f",
            frog_ast.Variable("Bool"),
            [frog_ast.Parameter(frog_ast.Variable("Int"), "x")],
        ),
        frog_ast.Block([frog_ast.ReturnStatement(eq_expr)]),
    )
    # F is a primitive with a deterministic eval method
    f_primitive = frog_ast.Primitive(
        "F_Prim",
        [frog_ast.Parameter(frog_ast.Variable("Int"), "n")],
        [],
        [
            frog_ast.MethodSignature(
                "eval",
                frog_ast.Variable("Int"),
                [frog_ast.Parameter(frog_ast.Variable("Int"), "x")],
                deterministic=True,
            ),
        ],
    )
    proof_namespace: frog_ast.Namespace = {"F": f_primitive}

    transformed = ReflexiveComparisonTransformer(
        proof_namespace=proof_namespace
    ).transform(method_ast)

    ret_stmt = transformed.block.statements[0]
    assert isinstance(ret_stmt, frog_ast.ReturnStatement)
    assert isinstance(ret_stmt.expression, frog_ast.Boolean) and ret_stmt.expression.bool


def test_xor_cancellation_with_reflexive_comparison() -> None:
    """Combined: k + k + m == m -> true (XOR cancellation then reflexive comparison)."""
    method_ast = frog_parser.parse_method("""
        Bool f(BitString<lambda> k, BitString<lambda> m) {
            return k + k + m == m;
        }
    """)
    expected_ast = frog_parser.parse_method("""
        Bool f(BitString<lambda> k, BitString<lambda> m) {
            return true;
        }
    """)

    transformed_ast = method_ast
    while True:
        new_ast = XorCancellationTransformer().transform(transformed_ast)
        new_ast = ReflexiveComparisonTransformer().transform(new_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    assert expected_ast == transformed_ast


def test_xor_cancellation_skips_nondeterministic_pairs() -> None:
    """F.eval(x) + v + F.eval(x) must NOT cancel F.eval(x) when F.eval is
    non-deterministic — the two calls may return different values."""
    from proof_frog.transforms._base import PipelineContext
    from proof_frog.visitors import build_game_type_map

    func_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
        [frog_ast.Variable("x")],
    )
    game_ast = frog_parser.parse_game("""
        Game G(Int n) {
            BitString<n> f(BitString<n> v, Int x) {
                return v;
            }
        }
    """)
    # Manually build: F.eval(x) + v + F.eval(x)
    xor_expr = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD,
        frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            func_call,
            frog_ast.Variable("v"),
        ),
        func_call,
    )
    game_ast.methods[0].block.statements[0] = frog_ast.ReturnStatement(xor_expr)

    type_map = build_game_type_map(game_ast)

    # F has a non-deterministic eval method
    f_primitive = frog_ast.Primitive(
        "F_Prim",
        [frog_ast.Parameter(frog_ast.Variable("Int"), "n")],
        [],
        [
            frog_ast.MethodSignature(
                "eval",
                frog_ast.BitStringType(frog_ast.Variable("n")),
                [frog_ast.Parameter(frog_ast.Variable("Int"), "x")],
            ),
        ],
    )
    proof_namespace: frog_ast.Namespace = {"F": f_primitive}
    ctx = PipelineContext(
        variables={},
        proof_let_types={},
        proof_namespace=proof_namespace,
        subsets_pairs=[],
    )

    transformed = XorCancellationTransformer(type_map, ctx).transform(game_ast)

    # The F.eval(x) terms should NOT have been cancelled
    ret_stmt = transformed.methods[0].block.statements[0]
    assert isinstance(ret_stmt, frog_ast.ReturnStatement)
    # If cancelled incorrectly, result would be just `v`
    assert not (
        isinstance(ret_stmt.expression, frog_ast.Variable)
        and ret_stmt.expression.name == "v"
    ), (
        "F.eval(x) + v + F.eval(x) should NOT cancel F.eval(x) terms when "
        "F.eval is non-deterministic"
    )
