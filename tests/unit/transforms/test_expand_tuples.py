import pytest
from proof_frog import visitors, frog_parser, frog_ast
from proof_frog.transforms.tuples import ExpandTupleTransformer


@pytest.mark.parametrize(
    "game,expected",
    [
        (
            """
            Game G() {
                [Int, Int, Int, Int] myTuple;
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
                [Int, Int] myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
            """
            Game G() {
                [Int, Int] myTuple;
                Void Initialize() {
                    myTuple = challenger.f();
                }
            }
            """,
        ),
        (
            """
            Game G() {
                [Int, Int] myTuple;
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
                [Int, Int] myTuple;
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
                [Int, Int] myTuple;
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
                [Int, Int] myTuple;
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
                [Int, Int] firstTuple;
                [Int, Int] secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    [Int, Int] a = firstTuple;
                    firstTuple = secondTuple;
                    secondTuple = a;
                }
            }
            """,
            """
            Game G() {
                [Int, Int] firstTuple;
                [Int, Int] secondTuple;
                Void Initialize() {
                    firstTuple = [100, 200];
                    secondTuple = [300, 400];
                }
                Void swap() {
                    [Int, Int] a = firstTuple;
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
                    [Int, Int] tuple = [100, 200];
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
                    [Int, Int] tuple = [100, 200];
                    tuple = f();
                    return tuple[1];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    [Int, Int] tuple = [100, 200];
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
                    [Int, Int] tuple = [100, 200];
                    Int a = 1;
                    return tuple[a];
                }
            }
            """,
            """
            Game G() {
                Int f() {
                    [Int, Int] tuple = [100, 200];
                    Int a = 1;
                    return tuple[a];
                }
            }
            """,
        ),
        (
            """
            Game G() {
                [Int, Int] myTuple;
                Void Initialize() {
                    myTuple[0] = 0;
                    myTuple[1] = 1;
                }
                Int f() {
                    [Int, Int] tuple = [100, 200];
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
    transformed_ast = ExpandTupleTransformer().transform(game_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast


# ---------------------------------------------------------------------------
# ExpandTupleTransformer with 3-element product types
# ---------------------------------------------------------------------------


def test_three_element_product_field_with_initializer() -> None:
    """Field with 3-element product type and initializer expands fully."""
    game = """
    Game G() {
        [Int, Int, Int] myTuple = [1, 2, 3];
        Void Initialize() {
        }
    }
    """
    game_ast = frog_parser.parse_game(game)
    transformed = ExpandTupleTransformer().transform(game_ast)

    assert len(transformed.fields) == 3
    assert transformed.fields[0].name == "myTuple@0"
    assert transformed.fields[0].type == frog_ast.IntType()
    assert transformed.fields[0].value == frog_ast.Integer(1)

    assert transformed.fields[1].name == "myTuple@1"
    assert transformed.fields[1].type == frog_ast.IntType()
    assert transformed.fields[1].value == frog_ast.Integer(2)

    assert transformed.fields[2].name == "myTuple@2"
    assert transformed.fields[2].type == frog_ast.IntType()
    assert transformed.fields[2].value == frog_ast.Integer(3)


@pytest.mark.parametrize(
    "game,expected",
    [
        # Field with 3-element product type but no initial value — fully expands.
        (
            """
            Game G() {
                [Int, Int, Int] myTuple;
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
def test_expand_three_element_product_tuples(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)

    replace_map = frog_ast.ASTMap(identity=False)
    for i in range(3):
        for prefix in ["tuple", "myTuple"]:
            replace_map.set(
                frog_ast.Variable(f"{prefix}{i}"),
                frog_ast.Variable(f"{prefix}@{i}"),
            )
            replace_map.set(
                frog_ast.Field(frog_ast.IntType(), f"{prefix}{i}", None),
                frog_ast.Field(frog_ast.IntType(), f"{prefix}@{i}", None),
            )

    expected_ast = visitors.SubstitutionTransformer(replace_map).transform(expected_ast)

    transformed_ast = ExpandTupleTransformer().transform(game_ast)
    assert expected_ast == transformed_ast


def _bs(n: int) -> frog_ast.BitStringType:
    return frog_ast.BitStringType(frog_ast.Integer(n))


def test_f322_all_constant_declines_whole_var_product_sample() -> None:
    """F-322: a whole-variable product-type sample ``v <- [T0, T1]`` must make
    the AllConstantFieldAccesses gate decline -- ExpandTuple cannot split an
    atomic aggregate draw into per-component draws. (Built as an AST because the
    typechecker rejects product-type sample domains at the surface.)"""
    prod = frog_ast.ProductType([_bs(4), _bs(4)])
    block = frog_ast.Block(
        [
            frog_ast.Sample(prod, frog_ast.Variable("v"), prod),
            frog_ast.ReturnStatement(
                frog_ast.ArrayAccess(frog_ast.Variable("v"), frog_ast.Integer(0))
            ),
        ]
    )
    assert visitors.AllConstantFieldAccesses("v").visit(block) is False


def test_f322_element_sample_still_splittable() -> None:
    """Control: an element sample at a constant index ``v[0] <- T`` keeps its
    ArrayAccess lvalue and does NOT block expansion."""
    block = frog_ast.Block(
        [
            frog_ast.Sample(
                _bs(4),
                frog_ast.ArrayAccess(frog_ast.Variable("v"), frog_ast.Integer(0)),
                _bs(4),
            ),
            frog_ast.ReturnStatement(
                frog_ast.ArrayAccess(frog_ast.Variable("v"), frog_ast.Integer(1))
            ),
        ]
    )
    assert visitors.AllConstantFieldAccesses("v").visit(block) is True


def test_f322_whole_var_unique_sample_declines() -> None:
    """A whole-variable ``v <-uniq[S] [T0, T1]`` is equally unsplittable."""
    prod = frog_ast.ProductType([_bs(4), _bs(4)])
    block = frog_ast.Block(
        [
            frog_ast.UniqueSample(
                prod, frog_ast.Variable("v"), frog_ast.Variable("S"), prod, "uniq"
            ),
            frog_ast.ReturnStatement(
                frog_ast.ArrayAccess(frog_ast.Variable("v"), frog_ast.Integer(0))
            ),
        ]
    )
    assert visitors.AllConstantFieldAccesses("v").visit(block) is False


def test_f324_declines_when_local_escapes_block() -> None:
    """F-324: a block-local product declaration whose variable is also read in
    an enclosing block (an out-of-scope AST the typechecker rejects) must not be
    expanded -- splitting it here would leave the outer ``v[k]`` access dangling.
    (Compare the control below, which expands when every use is in-block.)"""
    method = frog_parser.parse_method("""
        Int Oracle(Bool c) {
            Int acc = 0;
            if (c) {
                [Int, Int] v = [1, 2];
                acc = acc + v[0];
            }
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[1, 2]" in out  # tuple left intact
    assert "v@1" not in out  # no dangling component reference


def test_f324_control_expands_when_all_uses_in_block() -> None:
    """Control for F-324: with every use inside the declaring block the local
    still expands."""
    method = frog_parser.parse_method("""
        Int Oracle(Bool c) {
            Int acc = 0;
            if (c) {
                [Int, Int] v = [1, 2];
                acc = acc + v[0] + v[1];
            }
            return acc;
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[1, 2]" not in out  # expanded into components
