"""Regression tests for variable name collisions during InlineTransformer.

The InlineTransformer renames local variables introduced in inlined method
bodies to avoid collisions with variables in the calling scope.  Prior to
the fix, UniqueSample statements were not covered by this renaming, so a
game method with a local ``r`` could collide with an inlined method that
also declared ``r`` via a ``<-uniq`` sampling statement.
"""

import copy

from proof_frog import frog_ast, visitors


def _make_method_with_unique_sample() -> frog_ast.Method:
    """Build a method: BitString<128> Samp(Set<BitString<128>> S) {
        BitString<128> r <-uniq[S] BitString<128>;
        return r;
    }"""
    bs128 = frog_ast.BitStringType(frog_ast.Integer(128))
    return frog_ast.Method(
        frog_ast.MethodSignature(
            "Samp",
            bs128,
            [frog_ast.Parameter(frog_ast.SetType(copy.deepcopy(bs128)), "S")],
        ),
        frog_ast.Block(
            [
                frog_ast.UniqueSample(
                    copy.deepcopy(bs128),
                    frog_ast.Variable("r"),
                    frog_ast.Variable("S"),
                    copy.deepcopy(bs128),
                ),
                frog_ast.ReturnStatement(frog_ast.Variable("r")),
            ]
        ),
    )


def _make_method_with_sample() -> frog_ast.Method:
    """Build a method: BitString<128> Samp() {
        BitString<128> r <- BitString<128>;
        return r;
    }"""
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


def _collect_variable_names(node: frog_ast.ASTNode) -> set[str]:
    """Collect all Variable names that appear in an AST."""
    collector = visitors.VariableCollectionVisitor()
    collector.visit(node)
    return {v.name for v in collector.result()}


class TestUniqueSampleRenaming:
    """UniqueSample variables must be renamed during inlining."""

    def test_unique_sample_var_renamed(self) -> None:
        """A UniqueSample variable 'r' inlined into a scope that also has 'r'
        should be renamed to avoid collision."""
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))

        # Caller method has its own local variable 'r' and calls obj.Samp(S)
        caller = frog_ast.Method(
            frog_ast.MethodSignature("Challenge", bs128, []),
            frog_ast.Block(
                [
                    # BitString<128> r <- BitString<128>;
                    frog_ast.Sample(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("r"),
                        copy.deepcopy(bs128),
                    ),
                    # BitString<128> result = obj.Samp(S);
                    frog_ast.Assignment(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Samp"),
                            [frog_ast.Variable("r")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        samp_method = _make_method_with_unique_sample()
        lookup = {("obj", "Samp"): samp_method}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # After inlining, the caller's 'r' and the inlined method's 'r'
        # must have different names.  The inlined one should be prefixed.
        var_names = _collect_variable_names(result)

        # The original 'r' should still be present (caller's variable)
        assert "r" in var_names

        # There should be a renamed variable like 'obj.Samp@r1'
        renamed = [n for n in var_names if n.startswith("obj.Samp@r")]
        assert len(renamed) == 1, (
            f"Expected one renamed variable matching 'obj.Samp@r*', "
            f"got {renamed}. All names: {var_names}"
        )

    def test_sample_var_still_renamed(self) -> None:
        """Sanity check: Sample (non-unique) variables are renamed too."""
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))

        caller = frog_ast.Method(
            frog_ast.MethodSignature("Challenge", bs128, []),
            frog_ast.Block(
                [
                    frog_ast.Sample(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("r"),
                        copy.deepcopy(bs128),
                    ),
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

        samp_method = _make_method_with_sample()
        lookup = {("obj", "Samp"): samp_method}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        var_names = _collect_variable_names(result)
        assert "r" in var_names
        renamed = [n for n in var_names if n.startswith("obj.Samp@r")]
        assert len(renamed) == 1, (
            f"Expected one renamed variable matching 'obj.Samp@r*', "
            f"got {renamed}. All names: {var_names}"
        )

    def test_no_collision_between_caller_and_inlined(self) -> None:
        """After inlining, the UniqueSample variable from the inlined method
        must not share a name with the caller's variable."""
        bs128 = frog_ast.BitStringType(frog_ast.Integer(128))

        caller = frog_ast.Method(
            frog_ast.MethodSignature("Challenge", bs128, []),
            frog_ast.Block(
                [
                    frog_ast.Sample(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("r"),
                        copy.deepcopy(bs128),
                    ),
                    frog_ast.Assignment(
                        copy.deepcopy(bs128),
                        frog_ast.Variable("result"),
                        frog_ast.FuncCall(
                            frog_ast.FieldAccess(frog_ast.Variable("obj"), "Samp"),
                            [frog_ast.Variable("r")],
                        ),
                    ),
                    frog_ast.ReturnStatement(frog_ast.Variable("result")),
                ]
            ),
        )

        samp_method = _make_method_with_unique_sample()
        lookup = {("obj", "Samp"): samp_method}

        result = visitors.InlineTransformer(lookup).transform(copy.deepcopy(caller))

        # Find all statements that declare a variable named exactly 'r'
        raw_r_decls = [
            s
            for s in result.block.statements
            if isinstance(
                s, (frog_ast.Sample, frog_ast.UniqueSample, frog_ast.Assignment)
            )
            and s.the_type is not None
            and isinstance(s.var, frog_ast.Variable)
            and s.var.name == "r"
        ]
        # Only the caller's 'r' should remain with that exact name
        assert (
            len(raw_r_decls) == 1
        ), f"Expected exactly 1 declaration of bare 'r', got {len(raw_r_decls)}"
