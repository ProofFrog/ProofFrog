import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import HoistFieldPureAliasTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = HoistFieldPureAliasTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # Variable hoisting: field = v where v appears in earlier statement's expression
        (
            """
            Game Test() {
                Int field2;
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = v4 + 1;
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field2;
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                    field2 = field7 + 1;
                }
            }
            """,
        ),
        # Variable not used in earlier statement — no hoisting
        (
            """
            Game Test() {
                Int field7;
                Int field2;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = 42;
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field7;
                Int field2;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field2 = 42;
                    field7 = v4;
                }
            }
            """,
        ),
        # Variable only used in its own definition — no hoisting
        (
            """
            Game Test() {
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                }
            }
            """,
            """
            Game Test() {
                Int field7;
                Void Initialize() {
                    [Int, Int] pair = K.evaluate(1);
                    Int v4 = pair[0];
                    field7 = v4;
                }
            }
            """,
        ),
    ],
)
def test_hoist_field_pure_alias(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


def test_field_to_field_copy_not_hoisted() -> None:
    """field = other_field should NOT be hoisted (only field = local_var)."""
    source = """
    Game Test() {
        Int field1;
        Int field2;
        Int field3;
        Void Initialize() {
            field1 = 42;
            field3 = field1 + 1;
            field2 = field1;
        }
    }
    """
    _transform_and_compare(source, source)


def test_no_hoist_when_free_variable_reassigned_between_j_and_i() -> None:
    """Soundness: if a free variable of the hoisted expression is reassigned
    between the target position j and the original position i, hoisting would
    change the value of the expression. The transform must not fire."""
    source = """
    Game Test() {
        Int field7;
        Void Initialize() {
            Int v4 = 10;
            Int x = v4 + 1;
            v4 = 99;
            field7 = v4;
        }
    }
    """
    # field7 = v4 should NOT be hoisted before x = v4 + 1 because v4 is
    # reassigned at position 2 (v4 = 99) between j=1 and i=3.
    _transform_and_compare(source, source)


def test_no_hoist_when_match_is_in_assignment_target() -> None:
    """Soundness: the search should not match the expression in the LHS
    (assignment target) of an earlier statement, only in use positions."""
    source = """
    Game Test() {
        Int field7;
        Void Initialize() {
            Int v4 = 10;
            v4 = 100;
            field7 = v4;
        }
    }
    """
    # field7 = v4 should NOT be hoisted: at j=1 (v4 = 100), v4 appears
    # only as the assignment target. v4 is also reassigned there.
    _transform_and_compare(source, source)


def test_no_hoist_when_field_free_var_modified_between_j_and_i() -> None:
    """Soundness: if the expression references a field that is modified
    between the match position j and the field assignment position i,
    hoisting would evaluate the expression at an earlier state of the field.

    Example: field5 = field_arr[0] where field_arr[0] is modified in between.
    The stability check must not skip field-type free variables."""
    from proof_frog import frog_ast

    # Build: field_arr is a field, field5 is a field.
    # Initialize:
    #   Int x = field_arr[0] + 1;    // j=0: uses field_arr[0]
    #   field_arr[0] = 99;            // modifies field_arr
    #   field5 = field_arr[0];        // i=2: field assignment to hoist
    game = frog_ast.Game(
        (
            "Test",
            [],
            [
                frog_ast.Field(
                    frog_ast.Variable("Array"),  # simplified type
                    "field_arr",
                    None,
                ),
                frog_ast.Field(frog_ast.Variable("Int"), "field5", None),
            ],
            [
                frog_ast.Method(
                    frog_ast.MethodSignature(
                        "Initialize", frog_ast.Variable("Void"), []
                    ),
                    frog_ast.Block(
                        [
                            # Int x = field_arr[0] + 1;
                            frog_ast.Assignment(
                                frog_ast.Variable("Int"),
                                frog_ast.Variable("x"),
                                frog_ast.BinaryOperation(
                                    frog_ast.BinaryOperators.ADD,
                                    frog_ast.ArrayAccess(
                                        frog_ast.Variable("field_arr"),
                                        frog_ast.Integer(0),
                                    ),
                                    frog_ast.Integer(1),
                                ),
                            ),
                            # field_arr[0] = 99;
                            frog_ast.Assignment(
                                None,
                                frog_ast.ArrayAccess(
                                    frog_ast.Variable("field_arr"),
                                    frog_ast.Integer(0),
                                ),
                                frog_ast.Integer(99),
                            ),
                            # field5 = field_arr[0];
                            frog_ast.Assignment(
                                None,
                                frog_ast.Variable("field5"),
                                frog_ast.ArrayAccess(
                                    frog_ast.Variable("field_arr"),
                                    frog_ast.Integer(0),
                                ),
                            ),
                        ]
                    ),
                ),
            ],
            [],  # phases
        )
    )

    result = HoistFieldPureAliasTransformer().transform(game)

    # field5 = field_arr[0] must NOT be hoisted before the modification
    init_method = result.get_method("Initialize")
    stmts = init_method.block.statements
    # If hoisted, the field5 assignment would be at index 0.
    # It should still be at the end (index 2).
    last_stmt = stmts[-1]
    assert isinstance(
        last_stmt, frog_ast.Assignment
    ), "Last statement should still be the field5 assignment"
    assert (
        isinstance(last_stmt.var, frog_ast.Variable) and last_stmt.var.name == "field5"
    ), (
        "field5 = field_arr[0] should NOT be hoisted when field_arr is "
        "modified between the match position and the assignment position"
    )


def test_no_hoist_when_array_element_modified_between_j_and_i() -> None:
    """Soundness: if the expression is an ArrayAccess (e.g., v1[0]) and the
    array element is modified between j and i via v1[0] = expr, the hoisted
    expression would evaluate to the old value. The transform must not fire."""
    source = """
    Game Test() {
        Int field5;
        Void Initialize() {
            Array<Int, 2> v1 = A.make();
            Int x = v1[0] + 1;
            v1[0] = 99;
            field5 = v1[0];
        }
    }
    """
    # field5 = v1[0] should NOT be hoisted before x = v1[0] + 1 because
    # v1[0] is modified at position 2.
    _transform_and_compare(source, source)
