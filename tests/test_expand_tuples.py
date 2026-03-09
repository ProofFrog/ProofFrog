import pytest
from proof_frog import visitors, frog_parser, frog_ast


@pytest.mark.parametrize(
    "game,expected",
    [
        (
            """
            Game G() {
                Int * Int * Int * Int myTuple;
                Void Initialize() {
                    myTuple = [1, 2, 3, 4];
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Int myTuple2;
                Int myTuple3;
                Void Initialize() {
                    myTuple0 = 1;
                    myTuple1 = 2;
                    myTuple2 = 3;
                    myTuple3 = 4;
                }
            }
            """,
        ),
        # We cannot expand because we do not know all tuple values.
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 100;
                    myTuple[1] = 200;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 100;
                    myTuple[1] = 200;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = [100, 200];
                }
                Void f() {
                    challenger.g(myTuple);
                    challenger.h(myTuple[0], myTuple[1]);
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
                Void f() {
                    challenger.g([myTuple0, myTuple1]);
                    challenger.h(myTuple0, myTuple1);
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple = [100, 200];
                }
                Void swap() {
                    Int a = myTuple[0];
                    myTuple[0] = myTuple[1];
                    myTuple[1] = a;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 100;
                    myTuple1 = 200;
                }
                Void swap() {
                    Int a = myTuple0;
                    myTuple0 = myTuple1;
                    myTuple1 = a;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int firstTuple;
                Int * Int secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    Int * Int a = firstTuple;
                    firstTuple = secondTuple;
                    secondTuple = a;
                }
            }
            """,
            """
            Game G() {
                Int * Int firstTuple;
                Int * Int secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    Int * Int a = firstTuple;
                    firstTuple = secondTuple;
                    secondTuple = a;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int f() {
                    Int * Int tuple = [100, 200];
                    return tuple[1];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int tuple0 = 100;
                    Int tuple1 = 200;
                    return tuple1;
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int f() {
                    Int * Int tuple = [100, 200];
                    tuple = f();
                    return tuple[1];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int * Int tuple = [100, 200];
                    tuple = f();
                    return tuple[1];
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int f() {
                    Int * Int tuple = [100, 200];
                    Int a = 1;
                    return tuple[a];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int * Int tuple = [100, 200];
                    Int a = 1;
                    return tuple[a];
                }
            }
            """,
        ),
        (
            """
            Game G() {
                Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 0;
                    myTuple[1] = 1;
                }
                Int f() {
                    Int * Int tuple = [100, 200];
                    return tuple[1];
                }
                Int g() {
                    Int tuple = 2;
                    return tuple + myTuple[0];
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Void Initialize() {
                    myTuple0 = 0;
                    myTuple1 = 1;
                }
                Int f() {
                    Int tuple0 = 100;
                    Int tuple1 = 200;
                    return tuple1;
                }
                Int g() {
                    Int tuple = 2;
                    return tuple + myTuple0;
                }
            }
            """,
        ),
    ],
)
def test_expand_tuples(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    replace_map = frog_ast.ASTMap(identity=False)
    for i in range(0, 4):
        for prefix in ["tuple", "myTuple"]:
            replace_map.set(
                frog_ast.Variable(f"{prefix}{i}"), frog_ast.Variable(f"{prefix}@{i}")
            )
            replace_map.set(
                frog_ast.Field(frog_ast.IntType(), f"{prefix}{i}", None),
                frog_ast.Field(frog_ast.IntType(), f"{prefix}@{i}", None),
            )

    expected_ast = visitors.SubstitutionTransformer(replace_map).transform(expected_ast)

    print("EXPECTED: ", expected_ast)
    transformed_ast = visitors.ExpandTupleTransformer().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast


# ---------------------------------------------------------------------------
# split_tuple_type_top unit tests
# ---------------------------------------------------------------------------


def test_split_tuple_type_top_simple() -> None:
    """(Int * Int) split at top level gives [Int, Int]."""
    product = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), frog_ast.IntType()
    )
    result = frog_ast.split_tuple_type_top(product)
    assert result == [frog_ast.IntType(), frog_ast.IntType()]


def test_split_tuple_type_top_nested() -> None:
    """(Int * Int) * Int split at top level gives [Int * Int, Int]."""
    inner = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), frog_ast.IntType()
    )
    outer = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, inner, frog_ast.IntType()
    )
    result = frog_ast.split_tuple_type_top(outer)
    assert len(result) == 2
    assert result[0] == inner
    assert result[1] == frog_ast.IntType()


def test_split_tuple_type_top_right_nested() -> None:
    """Int * (Int * Int) split at top level gives [Int, Int * Int]."""
    inner = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), frog_ast.IntType()
    )
    outer = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), inner
    )
    result = frog_ast.split_tuple_type_top(outer)
    assert len(result) == 2
    assert result[0] == frog_ast.IntType()
    assert result[1] == inner


# ---------------------------------------------------------------------------
# ExpandTupleTransformer with nested product types
# ---------------------------------------------------------------------------


def test_nested_product_field_with_initializer() -> None:
    """Field with nested product type and initializer falls back to top-level split.

    Int * Int * Int is parsed right-associatively as Int * (Int * Int).
    expand_tuple_type gives [Int, Int, Int] (3 types) but the value [1, 2]
    has only 2 elements, so the transformer falls back to split_tuple_type_top:
    [Int, Int * Int].
    """
    game = """
    Game G() {
        Int * Int * Int myTuple = [1, [2, 3]];
        Void Initialize() {
        }
    }
    """
    game_ast = frog_parser.parse_game(game)
    transformed = visitors.ExpandTupleTransformer().transform(game_ast)

    assert len(transformed.fields) == 2
    assert transformed.fields[0].name == "myTuple@0"
    assert transformed.fields[0].type == frog_ast.IntType()
    assert transformed.fields[0].value == frog_ast.Integer(1)

    int_int = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), frog_ast.IntType()
    )
    assert transformed.fields[1].name == "myTuple@1"
    assert transformed.fields[1].type == int_int
    assert transformed.fields[1].value == frog_ast.Tuple(
        [frog_ast.Integer(2), frog_ast.Integer(3)]
    )


@pytest.mark.parametrize(
    "game,expected",
    [
        # Nested product type local variable: fallback in transform_block.
        # The value [100, [200, 300]] has 2 elements but the type
        # Int * Int * Int (= Int * (Int * Int)) flattens to 3 types,
        # so the transformer falls back to top-level split.
        (
            """
            Game G() {
                Int f() {
                    Int * Int * Int tuple = [100, [200, 300]];
                    return tuple[0];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    Int tuple0 = 100;
                    Int * Int tuple1 = [200, 300];
                    return tuple0;
                }
            }
            """,
        ),
        # Field with nested product type but no initial value — fully expands
        # (no fallback) since the arity check requires a value to be present.
        (
            """
            Game G() {
                Int * Int * Int myTuple;
                Void Initialize() {
                    myTuple[0] = 1;
                    myTuple[1] = 2;
                    myTuple[2] = 3;
                }
            }
            """,
            """
            Game G() {
                Int myTuple0;
                Int myTuple1;
                Int myTuple2;
                Void Initialize() {
                    myTuple0 = 1;
                    myTuple1 = 2;
                    myTuple2 = 3;
                }
            }
            """,
        ),
    ],
)
def test_expand_nested_product_tuples(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    int_int = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY, frog_ast.IntType(), frog_ast.IntType()
    )

    # Build replace map with both Int and Int*Int field types so that
    # the substitution matches whichever type appears in the expected output.
    replace_map = frog_ast.ASTMap(identity=False)
    for i in range(3):
        for prefix in ["tuple", "myTuple"]:
            replace_map.set(
                frog_ast.Variable(f"{prefix}{i}"),
                frog_ast.Variable(f"{prefix}@{i}"),
            )
            for the_type in [frog_ast.IntType(), int_int]:
                replace_map.set(
                    frog_ast.Field(the_type, f"{prefix}{i}", None),
                    frog_ast.Field(the_type, f"{prefix}@{i}", None),
                )

    expected_ast = visitors.SubstitutionTransformer(replace_map).transform(expected_ast)

    transformed_ast = visitors.ExpandTupleTransformer().transform(game_ast)
    assert expected_ast == transformed_ast
