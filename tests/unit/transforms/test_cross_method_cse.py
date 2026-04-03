"""Tests for CrossMethodFieldAlias transform.

Verifies that deterministic calls stored in fields are propagated to other
methods, while calls with local arguments, non-deterministic calls, and
calls without field assignments are left alone.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import (
    CrossMethodFieldAliasTransformer,
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


class TestCrossMethodFieldAlias:
    """Tests for CrossMethodFieldAliasTransformer."""

    def test_field_assignment_replaces_call_in_other_method(self) -> None:
        """field = GG.evaluate(k) in Initialize, GG.evaluate(k) in Oracle -> replaced."""
        game = frog_parser.parse_game(
            """
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """
        )
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(
            proof_namespace=ns
        ).transform(game)
        # Oracle should now return the field, not the call
        oracle = result.methods[1]
        ret = oracle.block.statements[0]
        assert isinstance(ret, frog_ast.ReturnStatement)
        assert isinstance(ret.expression, frog_ast.Variable)
        assert ret.expression.name == "stored"

    def test_no_field_assignment_no_replacement(self) -> None:
        """Without field = det_call, no replacement even if call appears twice."""
        game = frog_parser.parse_game(
            """
            Game Foo(G GG) {
                BitString<n> k;
                Void Initialize() {
                    BitString<n> local = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """
        )
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(
            proof_namespace=ns
        ).transform(game)
        # No change -- Initialize has a typed local assignment, not a field assignment
        assert result == game

    def test_nondeterministic_field_not_aliased(self) -> None:
        """Non-deterministic field assignment should not be aliased."""
        game = frog_parser.parse_game(
            """
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                }
                BitString<n> Oracle() {
                    return GG.evaluate(k);
                }
            }
            """
        )
        ns = _make_nondet_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(
            proof_namespace=ns
        ).transform(game)
        assert result == game

    def test_does_not_replace_in_same_method(self) -> None:
        """Field alias should only replace in OTHER methods."""
        game = frog_parser.parse_game(
            """
            Game Foo(G GG) {
                BitString<n> k;
                BitString<n> stored;
                Void Initialize() {
                    stored = GG.evaluate(k);
                    BitString<n> x = GG.evaluate(k);
                }
            }
            """
        )
        ns = _make_det_namespace()
        ns["GG"] = ns["G"]
        result = CrossMethodFieldAliasTransformer(
            proof_namespace=ns
        ).transform(game)
        # Same method -- should not replace (that's DeduplicateDeterministicCalls' job)
        assert result == game
