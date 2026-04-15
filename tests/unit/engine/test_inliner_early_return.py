"""Tests for InlineTransformer handling of methods with early returns.

The InlineTransformer must normalize early returns (``if (C) { return X; }
return Y;``) so that no bare ``ReturnStatement`` leaks into the enclosing
method.  After inlining, the call-site variable should be assigned in each
branch of an if-else tree produced by the normalization.
"""

import copy

from proof_frog import frog_ast, visitors


def _has_top_level_return(block: frog_ast.Block) -> bool:
    """True if any top-level statement in *block* is a ReturnStatement."""
    return any(
        isinstance(s, frog_ast.ReturnStatement) for s in block.statements
    )


def _make_simple_early_return_method() -> frog_ast.Method:
    """Build a method:
        Bool Check(Bool cond) {
            if (cond) { return false; }
            return true;
        }
    """
    return frog_ast.Method(
        frog_ast.MethodSignature(
            "Check",
            frog_ast.BoolType(),
            [frog_ast.Parameter(frog_ast.BoolType(), "cond")],
        ),
        frog_ast.Block(
            [
                frog_ast.IfStatement(
                    [frog_ast.Variable("cond")],
                    [
                        frog_ast.Block(
                            [frog_ast.ReturnStatement(frog_ast.Boolean(False))]
                        )
                    ],
                ),
                frog_ast.ReturnStatement(frog_ast.Boolean(True)),
            ]
        ),
    )


def _make_nested_early_return_method() -> frog_ast.Method:
    """Build a method:
        Bool Check(Bool a, Bool b) {
            if (a) {
                if (b) { return false; }
            }
            return true;
        }
    """
    inner_if = frog_ast.IfStatement(
        [frog_ast.Variable("b")],
        [frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Boolean(False))])],
    )
    outer_if = frog_ast.IfStatement(
        [frog_ast.Variable("a")],
        [frog_ast.Block([inner_if])],
    )
    return frog_ast.Method(
        frog_ast.MethodSignature(
            "Check",
            frog_ast.BoolType(),
            [
                frog_ast.Parameter(frog_ast.BoolType(), "a"),
                frog_ast.Parameter(frog_ast.BoolType(), "b"),
            ],
        ),
        frog_ast.Block([outer_if, frog_ast.ReturnStatement(frog_ast.Boolean(True))]),
    )


def _make_no_early_return_method() -> frog_ast.Method:
    """Build a method with no early returns (regression):
        BitString<128> Samp() {
            BitString<128> r <- BitString<128>;
            return r;
        }
    """
    bs128 = frog_ast.BitStringType(frog_ast.Integer(128))
    return frog_ast.Method(
        frog_ast.MethodSignature("Samp", bs128, []),
        frog_ast.Block(
            [
                frog_ast.Sample(
                    copy.deepcopy(bs128),
                    frog_ast.Variable("r"),
                    copy.deepcopy(bs128),
                ),
                frog_ast.ReturnStatement(frog_ast.Variable("r")),
            ]
        ),
    )


class TestSimpleEarlyReturn:
    """if (C) { return X; } return Y; inlined into a call site."""

    def test_no_leaked_return(self) -> None:
        """After inlining, no top-level ReturnStatement from the callee
        should appear in the caller's block (only the caller's own return)."""
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Outer", bs128, []),
            frog_ast.Block(
                [
                    # Bool result = obj.Check(flag);
                    frog_ast.Assignment(
                        frog_ast.BoolType(),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Check"),
                            [frog_ast.Variable("flag")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        callee = _make_simple_early_return_method()
        lookup = {("obj", "Check"): callee}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # The result block should not have any bare ReturnStatement from the
        # callee leaking at the top level (before the caller's own return).
        # Specifically, the inlined body should produce an IfStatement where
        # each branch assigns `result`, not a bare `return false;`.
        non_return_stmts = result.block.statements[:-1]
        for s in non_return_stmts:
            assert not isinstance(s, frog_ast.ReturnStatement), (
                f"Leaked ReturnStatement from callee: {s}"
            )

    def test_if_else_structure(self) -> None:
        """After inlining a simple early return, the result should contain
        an IfStatement with both branches assigning the call-site variable."""
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Outer", frog_ast.BoolType(), []),
            frog_ast.Block(
                [
                    frog_ast.Assignment(
                        frog_ast.BoolType(),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Check"),
                            [frog_ast.Variable("flag")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        callee = _make_simple_early_return_method()
        lookup = {("obj", "Check"): callee}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # Find the IfStatement produced by inlining
        if_stmts = [
            s for s in result.block.statements
            if isinstance(s, frog_ast.IfStatement)
        ]
        assert len(if_stmts) == 1, (
            f"Expected 1 IfStatement, got {len(if_stmts)}: "
            f"{[str(s) for s in result.block.statements]}"
        )
        if_stmt = if_stmts[0]
        # Should have an else block (2 blocks, 1 condition)
        assert if_stmt.has_else_block(), (
            "Expected if-else from early return normalization"
        )
        # Each branch should contain an assignment to 'result'
        for i, block in enumerate(if_stmt.blocks):
            assigns = [
                s for s in block.statements
                if isinstance(s, frog_ast.Assignment)
                and isinstance(s.var, frog_ast.Variable)
                and s.var.name == "result"
            ]
            assert len(assigns) >= 1, (
                f"Branch {i} should assign 'result', got: "
                f"{[str(s) for s in block.statements]}"
            )


class TestNestedEarlyReturn:
    """Nested if with early return: if (a) { if (b) { return X; } } return Y;"""

    def test_no_leaked_return(self) -> None:
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Outer", frog_ast.BoolType(), []),
            frog_ast.Block(
                [
                    frog_ast.Assignment(
                        frog_ast.BoolType(),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Check"),
                            [frog_ast.Variable("x"), frog_ast.Variable("y")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        callee = _make_nested_early_return_method()
        lookup = {("obj", "Check"): callee}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # No top-level return from callee should leak
        non_return_stmts = result.block.statements[:-1]
        for s in non_return_stmts:
            assert not isinstance(s, frog_ast.ReturnStatement), (
                f"Leaked ReturnStatement: {s}"
            )


class TestNoEarlyReturn:
    """Method without early returns — existing behavior preserved."""

    def test_existing_behavior_preserved(self) -> None:
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Outer", bs128, []),
            frog_ast.Block(
                [
                    frog_ast.Assignment(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Samp"),
                            [],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        callee = _make_no_early_return_method()
        lookup = {("obj", "Samp"): callee}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # Should have a sample statement and a return, no IfStatement
        has_sample = any(
            isinstance(s, frog_ast.Sample) for s in result.block.statements
        )
        assert has_sample, "Expected sample from inlined method"
        # No leaked returns
        assert not any(
            isinstance(s, frog_ast.ReturnStatement)
            and isinstance(s.expression, frog_ast.Boolean)
            for s in result.block.statements
        )


class TestC2PRIPattern:
    """C2PRI pattern: if (ct == ctStar) { return false; } return Decaps == kStar;
    inlined into a Bool call site."""

    def test_bool_early_return_no_leak(self) -> None:
        """When the early return is `return false` (not `return None`),
        the inliner must still produce correct branch assignments."""
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))

        # Callee: Bool Submit(BitString<128> ct) {
        #   if (ct == ctStar) { return false; }
        #   return (K.Decaps(sk, ct) == kStar);
        # }
        callee = frog_ast.Method(
            frog_ast.MethodSignature(
                "Submit",
                frog_ast.BoolType(),
                [frog_ast.Parameter(copy.deepcopy(bs128), "ct")],
            ),
            frog_ast.Block(
                [
                    frog_ast.IfStatement(
                        [
                            frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.EQUALS,
                                frog_ast.Variable("ct"),
                                frog_ast.Variable("ctStar"),
                            )
                        ],
                        [
                            frog_ast.Block(
                                [frog_ast.ReturnStatement(frog_ast.Boolean(False))]
                            )
                        ],
                    ),
                    frog_ast.ReturnStatement(
                        frog_ast.BinaryOperation(
                            frog_ast.BinaryOperators.EQUALS,
                            frog_ast.FuncCall(
                                frog_ast.FieldAccess(
                                    frog_ast.Variable("K"), "Decaps"
                                ),
                                [frog_ast.Variable("sk"), frog_ast.Variable("ct")],
                            ),
                            frog_ast.Variable("kStar"),
                        )
                    ),
                ]
            ),
        )

        # Caller: Bool check = challenger.Submit(ct1);
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Oracle", frog_ast.BoolType(), []),
            frog_ast.Block(
                [
                    frog_ast.Assignment(
                        frog_ast.BoolType(),
                        frog_ast.Variable("check"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(
                                frog_ast.Variable("challenger"), "Submit"
                            ),
                            [frog_ast.Variable("ct1")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("check")),
                ]
            ),
        )

        lookup = {("challenger", "Submit"): callee}
        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # No bare ReturnStatement(Boolean(false)) at top level
        for s in result.block.statements[:-1]:
            assert not isinstance(s, frog_ast.ReturnStatement), (
                f"Leaked return: {s}"
            )

        # Should have an IfStatement with branches assigning 'check'
        if_stmts = [
            s for s in result.block.statements
            if isinstance(s, frog_ast.IfStatement)
        ]
        assert len(if_stmts) == 1, (
            f"Expected 1 IfStatement, got {len(if_stmts)}"
        )
        assert if_stmts[0].has_else_block(), "Expected if-else structure"
