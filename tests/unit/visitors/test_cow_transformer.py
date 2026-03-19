"""Tests for copy-on-write Transformer behaviour.

The Transformer default traversal uses copy-on-write: unchanged nodes are
returned by identity, and only nodes with modified children are copied.
These tests verify correctness and document known interactions with
``copy.deepcopy`` and identity-based operations.
"""

import copy

import pytest
from proof_frog import frog_ast, frog_parser, visitors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _IdentityTransformer(visitors.Transformer):
    """A transformer that does nothing — exercises the COW default path."""


class _RenameVarTransformer(visitors.Transformer):
    """Renames a single variable by name (equality, not identity)."""

    def __init__(self, old_name: str, new_name: str) -> None:
        self.old_name = old_name
        self.new_name = new_name

    def transform_variable(self, var: frog_ast.Variable) -> frog_ast.Variable:
        if var.name == self.old_name:
            return frog_ast.Variable(self.new_name)
        return var


def _parse_method(src: str) -> frog_ast.Method:
    return frog_parser.parse_method(src)


# ---------------------------------------------------------------------------
# Identity / structural sharing
# ---------------------------------------------------------------------------


class TestCOWIdentity:
    """When nothing changes, the Transformer should return the same object."""

    def test_unchanged_node_is_same_object(self) -> None:
        method = _parse_method(
            """
            Void f() {
                return true;
            }
            """
        )
        result = _IdentityTransformer().transform(method)
        assert result is method

    def test_unchanged_block_is_same_object(self) -> None:
        method = _parse_method(
            """
            Void f(Int x) {
                Int y = x;
                return y;
            }
            """
        )
        result = _IdentityTransformer().transform(method)
        assert result.block is method.block

    def test_changed_child_produces_new_parent(self) -> None:
        method = _parse_method(
            """
            Void f() {
                Int a = x;
                return a;
            }
            """
        )
        result = _RenameVarTransformer("x", "y").transform(method)
        assert result is not method
        assert result == _parse_method(
            """
            Void f() {
                Int a = y;
                return a;
            }
            """
        )

    def test_unmodified_sibling_shared_with_original(self) -> None:
        """Siblings that weren't modified share the same object."""
        method = _parse_method(
            """
            Void f() {
                Int a = x;
                return true;
            }
            """
        )
        result = _RenameVarTransformer("x", "y").transform(method)
        # The return statement was not affected by the rename
        original_return = method.block.statements[1]
        new_return = result.block.statements[1]
        assert new_return is original_return


# ---------------------------------------------------------------------------
# COW + deepcopy interaction
# ---------------------------------------------------------------------------


class TestCOWDeepCopyInteraction:
    """copy.deepcopy on COW trees merges shared references via its memo
    dict.  These tests document the known behaviour and verify that
    the _VarCountVisitor counting approach is immune to it."""

    def test_deepcopy_merges_shared_leaf_nodes(self) -> None:
        """When COW returns the same Variable in two places, deepcopy
        produces a tree where both references point to the same new
        object (memo-based deduplication)."""
        var = frog_ast.Variable("x")
        # A block that references the same Variable twice
        a1 = frog_ast.Assignment(None, frog_ast.Variable("a"), var)
        a2 = frog_ast.Assignment(None, frog_ast.Variable("b"), var)
        block = frog_ast.Block([a1, a2])

        dc = copy.deepcopy(block)
        # deepcopy merges the shared leaf
        assert dc.statements[0].value is dc.statements[1].value

    def test_replace_transformer_on_shared_tree_replaces_both(self) -> None:
        """ReplaceTransformer uses identity (``is``), so shared references
        are replaced in a single pass — the root cause of the counting bug
        that _VarCountVisitor fixes."""
        var = frog_ast.Variable("x")
        a1 = frog_ast.Assignment(None, frog_ast.Variable("a"), var)
        a2 = frog_ast.Assignment(None, frog_ast.Variable("b"), var)
        block = frog_ast.Block([a1, a2])
        dc = copy.deepcopy(block)

        # Both statements' value should be the same object after deepcopy
        target = dc.statements[0].value
        replacement = frog_ast.Variable("replaced")
        result = visitors.ReplaceTransformer(target, replacement).transform(dc)

        # Both are replaced (because they were the same object)
        assert str(result.statements[0].value) == "replaced"
        assert str(result.statements[1].value) == "replaced"


# ---------------------------------------------------------------------------
# COW + mutation safety
# ---------------------------------------------------------------------------


class TestCOWMutationSafety:
    """Callers that mutate transform results must shallow-copy first,
    because COW may return objects whose attributes (especially lists)
    are shared with the original."""

    def test_shared_list_after_cow_transform(self) -> None:
        """A transform that changes one method leaves the fields list
        shared between original and result."""
        game = frog_parser.parse_game(
            """
            Game G() {
                Int x;

                Void Initialize() {
                    x = 0;
                }

                Int Query(Int a) {
                    return a;
                }
            }
            """
        )
        result = _RenameVarTransformer("a", "b").transform(game)
        # Result is a new Game (Query method changed), but fields list
        # is shared because it wasn't modified
        assert result is not game
        assert result.fields is game.fields

    def test_safe_mutation_pattern(self) -> None:
        """Demonstrate the correct pattern: copy.copy + reassign before
        mutating."""
        game = frog_parser.parse_game(
            """
            Game G() {
                Int x;

                Void Initialize() {
                    x = 0;
                }

                Int Query(Int a) {
                    return a;
                }
            }
            """
        )
        result = _RenameVarTransformer("a", "b").transform(game)
        # Safe mutation: copy before clearing
        result = copy.copy(result)
        result.fields = []
        # Original is not affected
        assert len(game.fields) == 1
