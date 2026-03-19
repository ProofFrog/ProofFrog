"""Tests for _VarCountVisitor used by InlineSingleUseVariable.

The visitor counts occurrences of a variable name in an AST subtree.
It replaced a fragile deepcopy + ReplaceTransformer counting loop
that broke under copy-on-write Transformer sharing.
"""

import copy

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import _VarCountVisitor


def _count(var_name: str, method_src: str) -> int:
    """Parse a method and count occurrences of *var_name* in its body."""
    method = frog_parser.parse_method(method_src)
    return _VarCountVisitor(var_name).visit(method.block)


class TestBasicCounting:
    def test_single_use_in_return(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x) {
                return x;
            }
            """,
            )
            == 1
        )

    def test_two_uses_in_same_statement(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x) {
                return x + x;
            }
            """,
            )
            == 2
        )

    def test_two_uses_across_statements(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x) {
                Int a = x;
                return x;
            }
            """,
            )
            == 2
        )

    def test_zero_uses(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int y) {
                return y;
            }
            """,
            )
            == 0
        )

    def test_does_not_count_different_names(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x, Int xy) {
                return xy;
            }
            """,
            )
            == 0
        )


class TestNestedBlocks:
    def test_counts_inside_if_block(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x, Bool c) {
                if (c) {
                    return x;
                }
                return x;
            }
            """,
            )
            == 2
        )

    def test_counts_inside_else_block(self) -> None:
        assert (
            _count(
                "x",
                """
            Int f(Int x, Bool c) {
                if (c) {
                    return 0;
                } else {
                    return x;
                }
            }
            """,
            )
            == 1
        )


class TestCOWSharedReferences:
    """Verify that _VarCountVisitor correctly counts variables even when
    copy-on-write sharing causes the same Variable object to appear at
    multiple AST positions."""

    def test_counts_shared_variable_independently(self) -> None:
        """When the same Variable object appears twice in a block (via
        COW sharing), the counter must count both occurrences."""
        var_x = frog_ast.Variable("x")
        # Same object used twice — simulates COW sharing
        a1 = frog_ast.Assignment(None, frog_ast.Variable("a"), var_x)
        ret = frog_ast.ReturnStatement(var_x)
        block = frog_ast.Block([a1, ret])

        assert _VarCountVisitor("x").visit(block) == 2

    def test_counts_after_deepcopy_of_shared_tree(self) -> None:
        """After deepcopy of a COW-shared tree, the counter still works
        even though deepcopy merges shared references."""
        var_x = frog_ast.Variable("x")
        a1 = frog_ast.Assignment(None, frog_ast.Variable("a"), var_x)
        ret = frog_ast.ReturnStatement(var_x)
        block = frog_ast.Block([a1, ret])

        dc = copy.deepcopy(block)
        # deepcopy merges shared refs, but visitor counts by name
        assert _VarCountVisitor("x").visit(dc) == 2

    def test_multi_use_not_inlined(self) -> None:
        """End-to-end: a variable used twice must not be inlined, even
        if the underlying AST has COW-shared Variable nodes."""
        from proof_frog.transforms.inlining import InlineSingleUseVariableTransformer

        method = frog_parser.parse_method(
            """
            BitString<lambda> f(BitString<lambda> k) {
                BitString<2 * lambda> result = G.evaluate(k);
                BitString<lambda> a = result[0 : lambda];
                BitString<lambda> b = result[lambda : 2 * lambda];
                return a + G.evaluate(b);
            }
            """
        )
        expected = frog_parser.parse_method(
            """
            BitString<lambda> f(BitString<lambda> k) {
                BitString<2 * lambda> result = G.evaluate(k);
                return result[0 : lambda] + G.evaluate(result[lambda : 2 * lambda]);
            }
            """
        )
        result = InlineSingleUseVariableTransformer().transform(method)
        # 'a' and 'b' are single-use → inlined
        # 'result' is used twice → NOT inlined
        assert result == expected
