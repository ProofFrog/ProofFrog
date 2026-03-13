"""Tests for Phase 6: proof engine type-aware canonicalization for ModInt<q>.

Covers:
- XOR transformer type guards (don't fire on ModInt)
- ModIntSimplificationTransformer identities
- UniformModIntSimplificationTransformer
- SymbolicComputationTransformer with EXPONENTIATE
- Z3FormulaVisitor with ModInt variables
- build_game_type_map helper
"""

import pytest
import z3

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import (
    XorCancellationTransformer,
    XorIdentityTransformer,
    ModIntSimplificationTransformer,
    UniformModIntSimplificationTransformer,
    ReflexiveComparisonTransformer,
)
from proof_frog.transforms.symbolic import SymbolicComputationTransformer
from proof_frog.visitors import (
    Z3FormulaVisitor,
    NameTypeMap,
    build_game_type_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _int(n: int) -> frog_ast.Integer:
    return frog_ast.Integer(n)


def _modint(modulus: frog_ast.Expression) -> frog_ast.ModIntType:
    return frog_ast.ModIntType(modulus)


def _type_map_with(**entries: frog_ast.Type) -> NameTypeMap:
    """Build a NameTypeMap from keyword arguments."""
    tm = NameTypeMap()
    for name, the_type in entries.items():
        tm.set(name, the_type)
    return tm


# ---------------------------------------------------------------------------
# build_game_type_map
# ---------------------------------------------------------------------------


class TestBuildGameTypeMap:
    def test_collects_field_types(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                ModInt<q> x;
                Void Initialize() { }
            }
        """)
        tm = build_game_type_map(game)
        assert isinstance(tm.get("x"), frog_ast.ModIntType)

    def test_collects_parameter_types(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                Void Initialize() { }
                ModInt<q> Foo(ModInt<q> a) {
                    return a;
                }
            }
        """)
        tm = build_game_type_map(game)
        assert isinstance(tm.get("a"), frog_ast.ModIntType)
        assert isinstance(tm.get("q"), frog_ast.IntType)

    def test_collects_local_variable_types(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                Void Initialize() { }
                ModInt<q> Foo() {
                    ModInt<q> r <- ModInt<q>;
                    return r;
                }
            }
        """)
        tm = build_game_type_map(game)
        assert isinstance(tm.get("r"), frog_ast.ModIntType)

    def test_merges_proof_let_types(self) -> None:
        game = frog_parser.parse_game("""
            Game G(Int q) {
                Void Initialize() { }
            }
        """)
        proof_types = _type_map_with(n=frog_ast.IntType())
        tm = build_game_type_map(game, proof_types)
        assert isinstance(tm.get("n"), frog_ast.IntType)
        assert isinstance(tm.get("q"), frog_ast.IntType)


# ---------------------------------------------------------------------------
# XOR transformer type guards (Step 6.2)
# ---------------------------------------------------------------------------


class TestXorCancellationTypeGuard:
    def test_cancels_bitstring_add(self) -> None:
        """XOR cancellation still works on BitString: k + k + m -> m."""
        method = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return k + k + m;
            }
        """)
        expected = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return m;
            }
        """)
        tm = _type_map_with(
            k=frog_ast.BitStringType(_var("lambda")),
            m=frog_ast.BitStringType(_var("lambda")),
        )
        result = method
        while True:
            new = XorCancellationTransformer(tm).transform(result)
            if new == result:
                break
            result = new
        assert result == expected

    def test_does_not_cancel_modint_add(self) -> None:
        """a + a should NOT cancel when a is ModInt (it's 2a, not 0)."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a + a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = XorCancellationTransformer(tm).transform(method)
        # Should be unchanged
        assert result == method

    def test_does_not_cancel_modint_three_terms(self) -> None:
        """a + b + a should NOT cancel when operands are ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a, ModInt<q> b) {
                return a + b + a;
            }
        """)
        tm = _type_map_with(
            a=_modint(_var("q")),
            b=_modint(_var("q")),
        )
        result = XorCancellationTransformer(tm).transform(method)
        assert result == method

    def test_no_type_map_defaults_to_cancellation(self) -> None:
        """Without type map, backward-compatible behavior (cancels)."""
        method = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return k + k + m;
            }
        """)
        expected = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> k, BitString<lambda> m) {
                return m;
            }
        """)
        result = method
        while True:
            new = XorCancellationTransformer().transform(result)
            if new == result:
                break
            result = new
        assert result == expected


class TestXorIdentityTypeGuard:
    def test_removes_zero_bitstring_from_xor(self) -> None:
        """x + 0^lambda -> x still works for BitString."""
        method = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return x + 0^lambda;
            }
        """)
        expected = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> x) {
                return x;
            }
        """)
        tm = _type_map_with(x=frog_ast.BitStringType(_var("lambda")))
        result = XorIdentityTransformer(tm).transform(method)
        assert result == expected

    def test_does_not_fire_on_modint_add(self) -> None:
        """ModInt add with integer 0 is NOT handled by XorIdentityTransformer.

        (ModInt additive identity is handled by ModIntSimplificationTransformer.)
        """
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a + 0;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = XorIdentityTransformer(tm).transform(method)
        # Unchanged — no BitStringLiteral(0) to remove
        assert result == method


# ---------------------------------------------------------------------------
# ModIntSimplificationTransformer (Step 6.3)
# ---------------------------------------------------------------------------


class TestModIntSimplificationAdditive:
    def test_add_zero_right(self) -> None:
        """a + 0 -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a + 0;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_add_zero_left(self) -> None:
        """0 + a -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0 + a;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_subtract_zero(self) -> None:
        """a - 0 -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a - 0;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_subtract_self(self) -> None:
        """a - a -> 0 for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a - a;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected


class TestModIntSimplificationMultiplicative:
    def test_multiply_one_right(self) -> None:
        """a * 1 -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a * 1;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_multiply_one_left(self) -> None:
        """1 * a -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 1 * a;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_multiply_zero_right(self) -> None:
        """a * 0 -> 0 for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a * 0;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_multiply_zero_left(self) -> None:
        """0 * a -> 0 for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0 * a;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected


class TestModIntSimplificationExponentiation:
    def test_exponentiate_zero(self) -> None:
        """a ^ 0 -> 1 for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a ^ 0;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 1;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected

    def test_exponentiate_one(self) -> None:
        """a ^ 1 -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a ^ 1;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected


class TestModIntSimplificationNegation:
    def test_double_negation(self) -> None:
        """-(-a) -> a for ModInt."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return -(-a);
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return a;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == expected


class TestModIntSimplificationNoFalsePositive:
    def test_does_not_simplify_non_modint_add(self) -> None:
        """a + 0 where a is BitString should NOT be simplified by ModInt transformer."""
        method = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> a) {
                return a + 0;
            }
        """)
        tm = _type_map_with(a=frog_ast.BitStringType(_var("lambda")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == method

    def test_does_not_simplify_int_multiply(self) -> None:
        """a * 1 where a is Int should NOT be simplified by ModInt transformer."""
        method = frog_parser.parse_method("""
            Int f(Int a) {
                return a * 1;
            }
        """)
        tm = _type_map_with(a=frog_ast.IntType())
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == method

    def test_noop_on_general_modint_expression(self) -> None:
        """a + b where both are ModInt should NOT be simplified (no identity applies)."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a, ModInt<q> b) {
                return a + b;
            }
        """)
        tm = _type_map_with(
            a=_modint(_var("q")),
            b=_modint(_var("q")),
        )
        result = ModIntSimplificationTransformer(tm).transform(method)
        assert result == method


# ---------------------------------------------------------------------------
# UniformModIntSimplificationTransformer (Step 6.4)
# ---------------------------------------------------------------------------


class TestUniformModIntSimplification:
    def test_simplifies_uniform_plus_value(self) -> None:
        """ModInt<q> r <- ModInt<q>; return r + m; -> return r;"""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r + m;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == expected

    def test_simplifies_value_plus_uniform(self) -> None:
        """ModInt<q> r <- ModInt<q>; return m + r; -> return r;"""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return m + r;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == expected

    def test_does_not_simplify_multiple_uses(self) -> None:
        """If the uniform variable is used more than once, don't simplify."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                ModInt<q> x = r + m;
                return r;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == method

    def test_does_not_fire_on_bitstring_sample(self) -> None:
        """Should not fire on BitString samples (that's the XOR transformer's job)."""
        method = frog_parser.parse_method("""
            BitString<lambda> f(BitString<lambda> m) {
                BitString<lambda> r <- BitString<lambda>;
                return r + m;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == method

    def test_simplifies_uniform_minus_value(self) -> None:
        """ModInt<q> r <- ModInt<q>; return r - m; -> return r;"""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r - m;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == expected

    def test_simplifies_value_minus_uniform(self) -> None:
        """ModInt<q> r <- ModInt<q>; return m - r; -> return r;"""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return m - r;
            }
        """)
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == expected

    def test_does_not_simplify_multiply(self) -> None:
        """Uniform + anything is uniform, but uniform * anything is NOT uniform."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                ModInt<q> r <- ModInt<q>;
                return r * m;
            }
        """)
        result = UniformModIntSimplificationTransformer().transform(method)
        assert result == method


# ---------------------------------------------------------------------------
# SymbolicComputationTransformer with EXPONENTIATE (Step 6.5)
# ---------------------------------------------------------------------------


class TestSymbolicComputationExponentiate:
    def test_simplifies_constant_exponentiation(self) -> None:
        """2 ^ 3 -> 8 when both are integer constants."""
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            _int(2),
            _int(3),
        )
        result = SymbolicComputationTransformer({}).transform(expr)
        assert result == _int(8)

    def test_preserves_variable_exponentiation(self) -> None:
        """a ^ n where a is not a known constant is left unchanged."""
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            _var("a"),
            _int(3),
        )
        result = SymbolicComputationTransformer({}).transform(expr)
        assert isinstance(result, frog_ast.BinaryOperation)
        assert result.operator == frog_ast.BinaryOperators.EXPONENTIATE


# ---------------------------------------------------------------------------
# Z3FormulaVisitor with ModInt (Step 6.6)
# ---------------------------------------------------------------------------


class TestZ3FormulaVisitorModInt:
    def test_modint_variable_maps_to_z3_int(self) -> None:
        """ModInt<q> variables should be mapped to Z3 Int sort."""
        tm = _type_map_with(x=_modint(_var("q")))
        visitor = Z3FormulaVisitor(tm)
        expr = _var("x")
        result = visitor.visit(expr)
        assert result is not None
        assert isinstance(result, z3.ArithRef)

    def test_modint_equality_produces_z3_formula(self) -> None:
        """x == y where both are ModInt should produce a Z3 boolean formula."""
        tm = _type_map_with(
            x=_modint(_var("q")),
            y=_modint(_var("q")),
        )
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EQUALS,
            _var("x"),
            _var("y"),
        )
        result = Z3FormulaVisitor(tm).visit(expr)
        assert result is not None
        assert z3.is_bool(result)

    def test_modint_addition_produces_z3_arith(self) -> None:
        """x + y where both are ModInt should produce Z3 arithmetic."""
        tm = _type_map_with(
            x=_modint(_var("q")),
            y=_modint(_var("q")),
        )
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.ADD,
            _var("x"),
            _var("y"),
        )
        result = Z3FormulaVisitor(tm).visit(expr)
        assert result is not None
        assert isinstance(result, z3.ArithRef)

    def test_exponentiate_returns_none(self) -> None:
        """Exponentiation is not supported in Z3; should return None."""
        tm = _type_map_with(
            x=_modint(_var("q")),
        )
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EXPONENTIATE,
            _var("x"),
            _int(3),
        )
        result = Z3FormulaVisitor(tm).visit(expr)
        assert result is None

    def test_reflexive_comparison_on_modint(self) -> None:
        """x == x with ModInt type should still simplify via Z3."""
        tm = _type_map_with(x=_modint(_var("q")))
        expr = frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.EQUALS,
            _var("x"),
            _var("x"),
        )
        result = Z3FormulaVisitor(tm).visit(expr)
        assert result is not None
        solver = z3.Solver()
        solver.add(z3.Not(result))
        assert solver.check() == z3.unsat


# ---------------------------------------------------------------------------
# Combined / integration-style tests
# ---------------------------------------------------------------------------


class TestModIntReflexiveComparison:
    def test_reflexive_equality_modint(self) -> None:
        """x == x -> true for ModInt (ReflexiveComparisonTransformer)."""
        method = frog_parser.parse_method("""
            Bool f(ModInt<q> x) {
                return x == x;
            }
        """)
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> x) {
                return true;
            }
        """)
        result = ReflexiveComparisonTransformer().transform(method)
        assert result == expected

    def test_modint_subtract_then_reflexive(self) -> None:
        """Combined: a - a == 0 should simplify.

        ModIntSimplification: a - a -> 0
        Then 0 == 0 -> true via ReflexiveComparison.
        """
        method = frog_parser.parse_method("""
            Bool f(ModInt<q> a) {
                return a - a == 0;
            }
        """)
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> a) {
                return true;
            }
        """)
        tm = _type_map_with(a=_modint(_var("q")))
        result = ModIntSimplificationTransformer(tm).transform(method)
        result = ReflexiveComparisonTransformer().transform(result)
        assert result == expected
