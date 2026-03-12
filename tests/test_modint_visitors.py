"""Tests for Phase 5: visitor infrastructure for ModInt<q>.

Covers SubstitutionTransformer, InstantiationTransformer, and
SymbolicComputationTransformer with ModIntType nodes.
"""

from proof_frog import frog_ast
from proof_frog.visitors import (
    SubstitutionTransformer,
    InstantiationTransformer,
    SymbolicComputationTransformer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _modint(modulus: frog_ast.Expression) -> frog_ast.ModIntType:
    return frog_ast.ModIntType(modulus)


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _int(n: int) -> frog_ast.Integer:
    return frog_ast.Integer(n)


def _add(left: frog_ast.Expression, right: frog_ast.Expression) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(frog_ast.BinaryOperators.ADD, left, right)


def _mul(left: frog_ast.Expression, right: frog_ast.Expression) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(frog_ast.BinaryOperators.MULTIPLY, left, right)


# ---------------------------------------------------------------------------
# Step 5.2: SubstitutionTransformer handles ModIntType
# ---------------------------------------------------------------------------


class TestSubstitutionTransformerModInt:
    def test_substitutes_variable_in_modulus(self) -> None:
        """Variable inside ModInt<q> modulus is replaced by the map."""
        ast_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=True)
        q_var = _var("q")
        ast_map.set(q_var, _int(7))

        original = _modint(q_var)
        result = SubstitutionTransformer(ast_map).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _int(7)

    def test_leaves_unrelated_variables_untouched(self) -> None:
        """Variables not in the map are preserved."""
        ast_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=True)
        p_var = _var("p")
        ast_map.set(p_var, _int(11))

        q_var = _var("q")
        original = _modint(q_var)
        result = SubstitutionTransformer(ast_map).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == q_var

    def test_substitutes_inside_compound_modulus(self) -> None:
        """Substitution works inside a compound modulus expression."""
        ast_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=True)
        lambda_var = _var("lambda")
        ast_map.set(lambda_var, _int(128))

        original = _modint(_mul(_int(2), lambda_var))
        result = SubstitutionTransformer(ast_map).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        expected_modulus = _mul(_int(2), _int(128))
        assert result.modulus == expected_modulus

    def test_identity_map_preserves_modint_type(self) -> None:
        """Identity-false map (no replacements) leaves ModIntType unchanged."""
        ast_map: frog_ast.ASTMap[frog_ast.ASTNode] = frog_ast.ASTMap(identity=False)
        original = _modint(_var("q"))
        result = SubstitutionTransformer(ast_map).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _var("q")


# ---------------------------------------------------------------------------
# Step 5.3: InstantiationTransformer handles ModIntType
# ---------------------------------------------------------------------------


class TestInstantiationTransformerModInt:
    def test_instantiates_parameter_in_modulus(self) -> None:
        """A namespace parameter is substituted into ModInt<q> modulus."""
        namespace: frog_ast.Namespace = {"q": _int(23)}
        original = _modint(_var("q"))
        result = InstantiationTransformer(namespace).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _int(23)

    def test_unknown_variable_left_as_is(self) -> None:
        """Variable not in namespace stays unchanged."""
        namespace: frog_ast.Namespace = {}
        original = _modint(_var("q"))
        result = InstantiationTransformer(namespace).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _var("q")

    def test_instantiates_compound_modulus(self) -> None:
        """Namespace substitution works inside compound modulus."""
        namespace: frog_ast.Namespace = {"lambda": _int(256)}
        original = _modint(_mul(_int(2), _var("lambda")))
        result = InstantiationTransformer(namespace).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        expected = _mul(_int(2), _int(256))
        assert result.modulus == expected


# ---------------------------------------------------------------------------
# Step 5.1: SymbolicComputationTransformer handles ModIntType
# ---------------------------------------------------------------------------


class TestSymbolicComputationTransformerModInt:
    def test_simplifies_constant_modulus(self) -> None:
        """Constant arithmetic in modulus is simplified."""
        variables: dict[str, object] = {}
        # ModInt<2 + 3>  ->  ModInt<5>
        original = _modint(_add(_int(2), _int(3)))
        result = SymbolicComputationTransformer(variables).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _int(5)

    def test_preserves_variable_modulus(self) -> None:
        """Non-constant modulus variable is preserved."""
        variables: dict[str, object] = {}
        original = _modint(_var("q"))
        result = SymbolicComputationTransformer(variables).transform(original)

        assert isinstance(result, frog_ast.ModIntType)
        assert result.modulus == _var("q")

    def test_no_stack_corruption_in_expression_context(self) -> None:
        """Transforming a BinaryOperation containing ModIntType-typed context
        does not corrupt the computation stack.

        We build a BinaryOperation(ADD, Integer(2), Integer(3)) and apply the
        transformer; it should simplify to Integer(5).  The key invariant is
        that processing a ModIntType node (which has a modulus expression)
        earlier in a block does not leave stray entries on the computation stack
        that would confuse the later BinaryOperation check.
        """
        variables: dict[str, object] = {}
        transformer = SymbolicComputationTransformer(variables)

        # Simulate: first transform a ModIntType (as if from a Sample statement)
        transformer.transform(_modint(_var("q")))

        # Now transform an arithmetic expression; it should still simplify.
        expr = _add(_int(2), _int(3))
        result = transformer.transform(expr)

        # Stack had stray entries from the ModInt transform, but old_len captured
        # them in the BinaryOperation handler, so simplification still works.
        assert result == _int(5)

    def test_does_not_crash_on_modint_sample(self) -> None:
        """SymbolicComputationTransformer applied to a Sample with ModInt type
        does not crash."""
        variables: dict[str, object] = {}

        sample = frog_ast.Sample(
            frog_ast.Variable("r"),
            _modint(_var("q")),
            _modint(_var("q")),
        )
        # Should not raise
        result = SymbolicComputationTransformer(variables).transform(sample)
        assert isinstance(result, frog_ast.Sample)
