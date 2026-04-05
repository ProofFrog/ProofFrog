import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.control_flow import IfConditionAliasSubstitutionTransformer
from proof_frog.visitors import SearchVisitor


def _transform_game(source: str) -> str:
    game = frog_parser.parse_game(source)
    result = IfConditionAliasSubstitutionTransformer().transform(game)
    return str(result)


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = IfConditionAliasSubstitutionTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # Basic: if (v == field1) { return field1; } else { return v; }
        # → replaces field1 with v in if-branch
        (
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v == field1) {
                        return field1;
                    } else {
                        return v;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v == field1) {
                        return v;
                    } else {
                        return v;
                    }
                }
            }
            """,
        ),
        # With function calls: F(field1) → F(v) in if-branch
        (
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v == field1) {
                        return field1 + 1;
                    } else {
                        return v + 1;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v == field1) {
                        return v + 1;
                    } else {
                        return v + 1;
                    }
                }
            }
            """,
        ),
        # Field on left side: if (field1 == v) { return field1; }
        (
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (field1 == v) {
                        return field1;
                    } else {
                        return v;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (field1 == v) {
                        return v;
                    } else {
                        return v;
                    }
                }
            }
            """,
        ),
        # No substitution when both sides are locals
        (
            """
            Game Test() {
                Int f(Int a, Int b) {
                    if (a == b) {
                        return b;
                    } else {
                        return a;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int f(Int a, Int b) {
                    if (a == b) {
                        return b;
                    } else {
                        return a;
                    }
                }
            }
            """,
        ),
        # No substitution when both sides are fields
        (
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 == field2) {
                        return field2;
                    } else {
                        return field1;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    if (field1 == field2) {
                        return field2;
                    } else {
                        return field1;
                    }
                }
            }
            """,
        ),
        # Local variable (not just parameter) qualifies
        (
            """
            Game Test() {
                Int field1;
                Int f() {
                    Int v = 42;
                    if (v == field1) {
                        return field1;
                    } else {
                        return v;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f() {
                    Int v = 42;
                    if (v == field1) {
                        return v;
                    } else {
                        return v;
                    }
                }
            }
            """,
        ),
        # No substitution for != conditions
        (
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v != field1) {
                        return field1;
                    } else {
                        return v;
                    }
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int f(Int v) {
                    if (v != field1) {
                        return field1;
                    } else {
                        return v;
                    }
                }
            }
            """,
        ),
        # No inlining when a field in the definition is reassigned
        (
            """
            Game Test() {
                Int field_ct;
                Int field_stored;
                Int f(Int x) {
                    if (x == field_ct) {
                        return field_stored;
                    }
                    return 0;
                }
                Int g() {
                    field_ct = 5;
                    field_stored = field_ct + 1;
                    field_ct = 7;
                    return 0;
                }
            }
            """,
            """
            Game Test() {
                Int field_ct;
                Int field_stored;
                Int f(Int x) {
                    if (x == field_ct) {
                        return field_stored;
                    }
                    return 0;
                }
                Int g() {
                    field_ct = 5;
                    field_stored = field_ct + 1;
                    field_ct = 7;
                    return 0;
                }
            }
            """,
        ),
    ],
)
def test_if_condition_alias_substitution(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


def test_no_phase1_inline_when_field_assigned_in_nested_block() -> None:
    """If the field is assigned inside an if-branch in another method,
    _collect_field_definitions must count it. The shallow scan only sees
    top-level statements, so it misclassifies the field as single-assignment."""
    source = """
    Game Test() {
        Int field1;
        Int field2;
        Void Initialize() {
            field1 = 0;
            field2 = field1 + 1;
        }
        Int f(Int v) {
            if (v == field1) {
                return field2;
            }
            return 0;
        }
        Void g(Int x) {
            if (x == 0) {
                field2 = 99;
            }
        }
    }
    """
    game = frog_parser.parse_game(source)
    result = IfConditionAliasSubstitutionTransformer().transform(game)
    # field2 is assigned in Initialize AND inside an if-branch in g().
    # It should NOT be treated as single-assignment, so Phase 1
    # should not inline field2's definition into the if-branch of f().
    # If Phase 1 fired, field2 would be replaced with (field1 + 1),
    # then Phase 2 would substitute field1 -> v, producing (v + 1).
    # This is wrong because field2 could have been changed by g().
    f_method = result.get_method("f")
    if_stmt = f_method.block.statements[0]
    assert isinstance(if_stmt, frog_ast.IfStatement)
    # The return should still reference field2, not an inlined expression
    ret_stmt = if_stmt.blocks[0].statements[0]
    assert isinstance(ret_stmt, frog_ast.ReturnStatement)
    assert isinstance(ret_stmt.expression, frog_ast.Variable)
    assert ret_stmt.expression.name == "field2", (
        "field2 should not be inlined when it has nested assignments in other methods"
    )


def test_no_phase1_inline_when_field_def_has_nondeterministic_call() -> None:
    """If a field definition contains a non-deterministic function call,
    Phase 1 must NOT inline it — inlining would create a fresh call that
    may return a different value than the stored one.

    Setup: field4 = F.eval(field1) in Initialize, and another method
    has if (v == field1) { return field4; }.  Without the guard, Phase 1
    would replace field4 with F.eval(field1), producing a fresh
    non-deterministic evaluation.
    """
    # Build the game AST manually since we need a FuncCall
    func_call = frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable("F"), "eval"),
        [frog_ast.Variable("field1")],
    )
    game = frog_ast.Game((
        "Test",
        [frog_ast.Parameter(frog_ast.Variable("SomePrimitive"), "F")],
        [
            frog_ast.Field(frog_ast.Variable("Int"), "field1", None),
            frog_ast.Field(frog_ast.Variable("Int"), "field4", None),
        ],
        [
            frog_ast.Method(
                frog_ast.MethodSignature("Initialize", frog_ast.Variable("Void"), []),
                frog_ast.Block([
                    frog_ast.Assignment(
                        None,
                        frog_ast.Variable("field1"),
                        frog_ast.Integer(5),
                    ),
                    frog_ast.Assignment(
                        None,
                        frog_ast.Variable("field4"),
                        func_call,
                    ),
                ]),
            ),
            frog_ast.Method(
                frog_ast.MethodSignature(
                    "f",
                    frog_ast.Variable("Int"),
                    [frog_ast.Parameter(frog_ast.Variable("Int"), "v")],
                ),
                frog_ast.Block([
                    frog_ast.IfStatement(
                        [
                            frog_ast.BinaryOperation(
                                frog_ast.BinaryOperators.EQUALS,
                                frog_ast.Variable("v"),
                                frog_ast.Variable("field1"),
                            )
                        ],
                        [
                            frog_ast.Block([
                                frog_ast.ReturnStatement(frog_ast.Variable("field4")),
                            ]),
                        ],
                    ),
                    frog_ast.ReturnStatement(frog_ast.Integer(0)),
                ]),
            ),
        ],
        [],  # phases
    ))

    # F is a primitive with a non-deterministic eval method
    f_primitive = frog_ast.Primitive(
        "SomePrimitive",
        [],
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

    result = IfConditionAliasSubstitutionTransformer(
        proof_namespace=proof_namespace
    ).transform(game)

    # field4 should NOT have been replaced with F.eval(...)
    f_method = result.get_method("f")
    if_stmt = f_method.block.statements[0]
    assert isinstance(if_stmt, frog_ast.IfStatement)
    ret_in_branch = if_stmt.blocks[0].statements[0]
    assert isinstance(ret_in_branch, frog_ast.ReturnStatement)

    def is_func_call(node: frog_ast.ASTNode) -> bool:
        return isinstance(node, frog_ast.FuncCall)

    assert SearchVisitor(is_func_call).visit(ret_in_branch) is None, (
        "Phase 1 should not inline field definitions containing "
        "non-deterministic function calls"
    )


def test_no_substitution_after_field_reassignment_in_branch() -> None:
    """If the field is reassigned within the if-branch, substitution must
    stop at the reassignment point.  After `field1 = 99;`, references to
    field1 should remain as field1, not be replaced by v."""
    source = """
    Game Test() {
        Int field1;
        Int f(Int v) {
            if (v == field1) {
                field1 = 99;
                return field1;
            }
            return 0;
        }
    }
    """
    game = frog_parser.parse_game(source)
    result = IfConditionAliasSubstitutionTransformer().transform(game)
    # After substitution, field1=99 should still be field1=99 (not v=99),
    # and `return field1` should remain (not become `return v`).
    assert result == game, (
        "Field references after field reassignment in branch should not be substituted"
    )
