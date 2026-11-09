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

    def test_f296_leading_literal_does_not_drop_modint_operand(self) -> None:
        """F-296: `0^n + m` with `m: ModInt<q>` must NOT drop the `0^n` literal.

        XorIdentity gates on `_is_bitstring_add_chain`, which used to return on
        the FIRST evidence term -- the leading `BitStringLiteral` `0^n` -- and
        wrongly classified the chain as XOR, rewriting `0^n + m` to `m`. Closed
        by the F-264 shared-helper fix: `_is_bitstring_add_chain` now scans all
        terms and lets the ModInt operand override the leading literal, so the
        chain is not treated as bitstring XOR and the pass declines."""
        method = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> m) {
                return 0^n + m;
            }
        """)
        tm = _type_map_with(m=_modint(_var("q")))
        result = XorIdentityTransformer(tm).transform(method)
        assert result == method, "leading literal must not drop a ModInt operand"


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


def _simplify_method(source: str, **types: frog_ast.Type) -> frog_ast.Method:
    method = frog_parser.parse_method(source)
    return ModIntSimplificationTransformer(_type_map_with(**types)).transform(method)


_Q = _modint(_var("q"))


class TestModIntPowerOfZeroKeepsItsType:
    """F-364: `a ^ 0` on ModInt<q> is the ModInt one, which is 0 when q = 1
    and adds to 0 with itself when q = 2. The Int literal 1 stands for it
    only where the value is converted to ModInt<q> again."""

    def test_f364_power_zero_in_comparison_kept(self) -> None:
        """Rewritten to `1 + 1 == 0`, Symbolic Computation would fold it to
        the false `2 == 0`; the powers stay."""
        result = _simplify_method(
            """
            Bool f(ModInt<q> a) {
                return a ^ 0 + a ^ 0 == a - a;
            }
            """,
            a=_Q,
        )
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> a) {
                return a ^ 0 + a ^ 0 == 0;
            }
        """)
        assert result == expected

    def test_f364_power_zero_inside_returned_sum_kept(self) -> None:
        """Only the whole returned value is converted: inside `a ^ 0 + b`
        the literal would be a mixed Int operand."""
        source = """
            ModInt<q> f(ModInt<q> a, ModInt<q> b) {
                return a ^ 0 + b;
            }
        """
        assert _simplify_method(source, a=_Q, b=_Q) == frog_parser.parse_method(source)

    def test_f364_zero_base_keeps_base(self) -> None:
        """`(a - a) ^ 0` must not become the Int `0 ^ 0`, which Symbolic
        Computation folds to the Int 1."""
        result = _simplify_method(
            """
            Bool f(ModInt<q> a) {
                return (a - a) ^ 0 == a - a;
            }
            """,
            a=_Q,
        )
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> a) {
                return (a - a) ^ 0 == 0;
            }
        """)
        assert result == expected

    def test_f364_zero_base_power_one_is_zero(self) -> None:
        result = _simplify_method(
            """
            ModInt<q> f(ModInt<q> a) {
                return (a - a) ^ 1;
            }
            """,
            a=_Q,
        )
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 0;
            }
        """)
        assert result == expected

    def test_f364_zero_base_returned_becomes_one(self) -> None:
        """A returned power of zero is converted to ModInt<q> by the return,
        whatever its base."""
        result = _simplify_method(
            """
            ModInt<q> f(ModInt<q> a) {
                return (a - a) ^ 0;
            }
            """,
            a=_Q,
        )
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                return 1;
            }
        """)
        assert result == expected

    def test_f364_power_zero_typed_store_becomes_one(self) -> None:
        result = _simplify_method(
            """
            ModInt<q> f(ModInt<q> a) {
                ModInt<q> one = a ^ 0;
                return one + a;
            }
            """,
            a=_Q,
            one=_Q,
        )
        expected = frog_parser.parse_method("""
            ModInt<q> f(ModInt<q> a) {
                ModInt<q> one = 1;
                return one + a;
            }
        """)
        assert result == expected

    def test_f364_power_zero_plain_store_becomes_one(self) -> None:
        result = _simplify_method(
            """
            Void f(ModInt<q> a) {
                s = a ^ 0;
            }
            """,
            a=_Q,
            s=_Q,
        )
        expected = frog_parser.parse_method("""
            Void f(ModInt<q> a) {
                s = 1;
            }
        """)
        assert result == expected

    def test_f364_power_zero_store_of_other_modulus_kept(self) -> None:
        """The conversion reduces mod the target's modulus, so the target
        must have the power's own type."""
        source = """
            ModInt<p> f(ModInt<q> a) {
                return a ^ 0;
            }
        """
        assert _simplify_method(source, a=_Q) == frog_parser.parse_method(source)

    def test_f364_power_zero_store_to_non_modint_kept(self) -> None:
        source = """
            Bool f(ModInt<q> a) {
                Bool b = a ^ 0 == a;
                return b;
            }
        """
        assert _simplify_method(source, a=_Q, b=frog_ast.BoolType()) == (
            frog_parser.parse_method(source)
        )

    @pytest.mark.parametrize("product", ["a ^ 0 * b", "b * a ^ 0"])
    def test_f364_power_zero_absorbed_by_product(self, product: str) -> None:
        result = _simplify_method(
            f"""
            Bool f(ModInt<q> a, ModInt<q> b, ModInt<q> c) {{
                return {product} == c;
            }}
            """,
            a=_Q,
            b=_Q,
            c=_Q,
        )
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> a, ModInt<q> b, ModInt<q> c) {
                return b == c;
            }
        """)
        assert result == expected

    def test_f364_power_zero_times_zero_is_zero(self) -> None:
        result = _simplify_method(
            """
            Bool f(ModInt<q> a, ModInt<q> c) {
                return (c - c) * a ^ 0 == c;
            }
            """,
            a=_Q,
            c=_Q,
        )
        expected = frog_parser.parse_method("""
            Bool f(ModInt<q> a, ModInt<q> c) {
                return 0 == c;
            }
        """)
        assert result == expected

    def test_f364_power_zero_not_absorbed_by_other_modulus(self) -> None:
        source = """
            Bool f(ModInt<q> a, ModInt<p> b, ModInt<p> c) {
                return a ^ 0 * b == c;
            }
        """
        p = _modint(_var("p"))
        result = _simplify_method(source, a=_Q, b=p, c=p)
        assert result == frog_parser.parse_method(source)


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
    def test_modint_variable_maps_to_opaque_const(self) -> None:
        """F-106: ModInt<q> variables must NOT be mapped to Z3 Int sort -- mod-q
        arithmetic differs from unbounded Int, so a ModInt is interned as an
        opaque (uninterpreted) const.  Modelling it as z3.Int let wraparound-
        true conditions be falsely proven unsat."""
        tm = _type_map_with(x=_modint(_var("q")))
        visitor = Z3FormulaVisitor(tm)
        expr = _var("x")
        result = visitor.visit(expr)
        assert result is not None
        # Opaque const, NOT an arithmetic (integer) term.
        assert not isinstance(result, z3.ArithRef)

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

    def test_modint_addition_is_untranslatable(self) -> None:
        """F-106: x + y over ModInt must NOT be modelled as Z3 integer
        arithmetic (that ignores the mod-q reduction).  With ModInt interned
        as an opaque const, ``+`` over two opaque consts raises in Z3 and the
        visitor falls back to None ("untranslatable"), the sound choice."""
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
        assert result is None

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
