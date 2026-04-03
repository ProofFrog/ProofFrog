"""Tests for ``deterministic`` annotation effects on inlining transforms.

Each transform that previously skipped ALL function calls now allows calls
to methods annotated ``deterministic`` in the proof namespace.  These tests
verify both the positive case (deterministic call allowed) and the negative
case (non-deterministic call still blocked).
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    CollapseAssignmentTransformer,
    ForwardExpressionAliasTransformer,
    HoistFieldPureAliasTransformer,
    InlineSingleUseFieldTransformer,
)


def _make_det_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is deterministic."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


def _make_nondet_namespace() -> frog_ast.Namespace:
    """Namespace with primitive G whose ``evaluate`` is NOT deterministic."""
    prim = frog_parser.parse_primitive_file(
        """
        Primitive G(Int n) {
            BitString<n> evaluate(BitString<n> x);
        }
        """
    )
    return {"G": prim}


# ---- ForwardExpressionAlias ----


class TestForwardExpressionAliasDeterministic:
    """ForwardExpressionAlias should alias deterministic function calls."""

    def test_deterministic_call_aliased(self) -> None:
        """v = G.evaluate(x); ... G.evaluate(x) -> v when G.evaluate is
        deterministic."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + v;
            }
            """
        )
        result = ForwardExpressionAliasTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_nondeterministic_call_not_aliased(self) -> None:
        """v = G.evaluate(x); ... G.evaluate(x) should NOT be aliased when
        G.evaluate is not deterministic."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """
        )
        result = ForwardExpressionAliasTransformer(
            proof_namespace=_make_nondet_namespace()
        ).transform(method)
        assert result == expected

    def test_no_namespace_call_not_aliased(self) -> None:
        """Without namespace, function calls are not aliased (conservative)."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int v = G.evaluate(x);
                return v + G.evaluate(x);
            }
            """
        )
        result = ForwardExpressionAliasTransformer().transform(method)
        assert result == expected


# ---- CollapseAssignment ----


class TestCollapseAssignmentDeterministic:
    """CollapseAssignment should allow collapsing when initial value is a
    deterministic call that is never read."""

    def test_deterministic_initial_collapsed(self) -> None:
        """Int a = G.evaluate(x); a = 3; -> Int a = 3; when G.evaluate is
        deterministic (the initial call is discarded safely)."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int a = G.evaluate(x);
                a = 3;
                return a;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int a = 3;
                return a;
            }
            """
        )
        result = CollapseAssignmentTransformer(
            proof_namespace=_make_det_namespace()
        ).transform(method)
        assert result == expected

    def test_nondeterministic_initial_not_collapsed(self) -> None:
        """Int a = G.evaluate(x); a = 3; should NOT collapse when G.evaluate
        is not deterministic (the initial call may have side effects)."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int a = G.evaluate(x);
                a = 3;
                return a;
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int a = G.evaluate(x);
                a = 3;
                return a;
            }
            """
        )
        result = CollapseAssignmentTransformer(
            proof_namespace=_make_nondet_namespace()
        ).transform(method)
        assert result == expected

    def test_no_namespace_not_collapsed(self) -> None:
        """Without namespace, calls block collapsing (conservative)."""
        method = frog_parser.parse_method(
            """
            Int f(Int x) {
                Int a = G.evaluate(x);
                a = 3;
                return a;
            }
            """
        )
        result = CollapseAssignmentTransformer().transform(method)
        # Should be unchanged
        assert result == method


# ---- HoistFieldPureAlias ----


def _hoist_transform(source: str, ns: frog_ast.Namespace) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return HoistFieldPureAliasTransformer(proof_namespace=ns).transform(game)


class TestHoistFieldPureAliasDeterministic:
    """HoistFieldPureAlias should hoist field assignments of deterministic
    function call results, but not non-deterministic ones."""

    def test_deterministic_array_access_hoisted(self) -> None:
        """field = v4 (a local) should be hoisted before v4's use in a
        deterministic function call."""
        source = """
        Game Test() {
            Int field7;
            Void Initialize() {
                [Int, Int] pair = G.evaluate(1);
                Int v4 = pair[0];
                Int result = v4 + 1;
                field7 = v4;
            }
        }
        """
        expected = """
        Game Test() {
            Int field7;
            Void Initialize() {
                [Int, Int] pair = G.evaluate(1);
                Int v4 = pair[0];
                field7 = v4;
                Int result = field7 + 1;
            }
        }
        """
        ns = _make_det_namespace()
        result = _hoist_transform(source, ns)
        expected_ast = frog_parser.parse_game(expected)
        assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


# ---- InlineSingleUseField ----


def _inline_field_transform(
    source: str, ns: frog_ast.Namespace
) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return InlineSingleUseFieldTransformer(proof_namespace=ns).transform(game)


class TestInlineSingleUseFieldDeterministic:
    """InlineSingleUseField should inline multi-use field assignments when
    the expression is a deterministic call (safe to duplicate)."""

    def test_deterministic_multi_use_inlined(self) -> None:
        """field = G.evaluate(x) used twice should be inlined when
        G.evaluate is deterministic."""
        source = """
        Game Test() {
            Int field1;
            Void Initialize() {
                field1 = G.evaluate(1);
            }
            Int PK() {
                return field1;
            }
            Int CT() {
                return field1;
            }
        }
        """
        ns = _make_det_namespace()
        result = _inline_field_transform(source, ns)
        # field1 is used in two methods — it should NOT be inlined
        # because cross-method inlining of multi-use fields is not safe
        # (field values are stored once in Initialize, read in oracles).
        # InlineSingleUseField only inlines when total_uses == 1.
        expected_ast = frog_parser.parse_game(source)
        assert result == expected_ast

    def test_deterministic_single_use_inlined(self) -> None:
        """field = G.evaluate(x) used once should be inlined when
        G.evaluate is deterministic."""
        source = """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = G.evaluate(1);
                field2 = field1 + 1;
            }
            Int PK() {
                return field2;
            }
        }
        """
        expected = """
        Game Test() {
            Int field2;
            Void Initialize() {
                field2 = G.evaluate(1) + 1;
            }
            Int PK() {
                return field2;
            }
        }
        """
        ns = _make_det_namespace()
        result = _inline_field_transform(source, ns)
        expected_ast = frog_parser.parse_game(expected)
        assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"

    def test_nondeterministic_single_use_still_inlined(self) -> None:
        """field = G.evaluate(x) used once should STILL be inlined even
        when non-deterministic — single-use inlining is always safe."""
        source = """
        Game Test() {
            Int field1;
            Int field2;
            Void Initialize() {
                field1 = G.evaluate(1);
                field2 = field1 + 1;
            }
            Int PK() {
                return field2;
            }
        }
        """
        expected = """
        Game Test() {
            Int field2;
            Void Initialize() {
                field2 = G.evaluate(1) + 1;
            }
            Int PK() {
                return field2;
            }
        }
        """
        ns = _make_nondet_namespace()
        result = _inline_field_transform(source, ns)
        expected_ast = frog_parser.parse_game(expected)
        assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"
