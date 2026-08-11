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


# ---------------------------------------------------------------------------
# Issue #255: bare product-typed local declarations
# ---------------------------------------------------------------------------


def test_bare_decl_whole_assignment_expands() -> None:
    """Issue #255: a bare product-typed local declaration followed by a
    whole-variable tuple-literal assignment splits into per-component
    declarations and assignments, exactly like the decl-with-initializer
    spelling."""
    method = frog_parser.parse_method("""
        Int Oracle() {
            [Int, Int] v;
            v = [1, 2];
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int]" not in out  # declaration split
    assert "v@0 = 1;" in out
    assert "v@1 = 2;" in out
    assert "return v@1;" in out


def test_bare_decl_element_writes_expand() -> None:
    """Issue #255 sibling: a bare product-typed local written element-wise
    also splits into components."""
    method = frog_parser.parse_method("""
        Int Oracle() {
            [Int, Int] v;
            v[0] = 1;
            v[1] = 2;
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int]" not in out
    assert "v@0 = 1;" in out
    assert "v@1 = 2;" in out
    assert "return v@1;" in out


def test_bare_decl_dead_declaration_left_alone() -> None:
    """A bare product-typed local that is never referenced afterwards is dead
    code: splitting it is pointless (and the use site may be in an enclosing
    scope), so the declaration is left intact for DCE."""
    method = frog_parser.parse_method("""
        Int Oracle() {
            [Int, Int] v;
            return 0;
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int] v;" in out


def test_bare_decl_non_constant_index_declines() -> None:
    """A non-constant index access blocks splitting a bare declaration (the
    component variable cannot be named at transform time). If the split fired
    anyway, ``v[i]`` would dangle."""
    method = frog_parser.parse_method("""
        Int Oracle(Int i) {
            [Int, Int] v;
            v = [1, 2];
            return v[i];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int] v;" in out  # left intact
    assert "v@0" not in out


def test_f324_bare_decl_declines_when_local_escapes_block() -> None:
    """F-324 guard on the bare-declaration path: a bare product local declared
    in an inner block but read in an enclosing block (an out-of-scope AST the
    typechecker rejects) must not be split -- the outer ``v[k]`` access would
    dangle."""
    method = frog_parser.parse_method("""
        Int Oracle(Bool c) {
            Int acc = 0;
            if (c) {
                [Int, Int] v;
                v = [1, 2];
                acc = acc + v[0];
            }
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int] v;" in out  # declaration left intact
    assert "v@1" not in out  # no dangling component reference


# ---------------------------------------------------------------------------
# F-321: whole-variable reassignment reading the tuple in its own RHS
# ---------------------------------------------------------------------------


def test_f321_swap_reassignment_declines_decl_with_init() -> None:
    """F-321: a swap ``v = [v[1], v[0]];`` must NOT be split into sequential
    component assignments ``v@0 = v@1; v@1 = v@0;`` -- after them BOTH
    components hold the old ``v[1]``, whereas the swap leaves ``v[1]`` holding
    the old ``v[0]``. Distinguisher (pre-fix): a game returning ``v[1]`` after
    the swap was canonicalized to return the wrong component, and the engine
    accepted an equivalence any instantiation with distinguishable components
    refutes with advantage 1."""
    method = frog_parser.parse_method("""
        Int Oracle() {
            [Int, Int] v = [1, 2];
            v = [v[1], v[0]];
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int] v = [1, 2];" in out  # left intact
    assert "v@0" not in out


def test_f321_swap_reassignment_declines_bare_decl() -> None:
    """F-321 on the bare-declaration path (issue #255): the same swap after a
    bare declaration must equally decline."""
    method = frog_parser.parse_method("""
        Int Oracle() {
            [Int, Int] v;
            v = [1, 2];
            v = [v[1], v[0]];
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "[Int, Int] v;" in out
    assert "v@0" not in out


def test_f321_swap_reassignment_declines_field() -> None:
    """F-321 on the field path: a product-typed game field whose oracle swaps
    it in place must not be expanded either -- the same sequentialization bug
    would corrupt the field across oracle calls."""
    game = frog_parser.parse_game("""
        Game G() {
            [Int, Int] pair;
            Void Initialize() {
                pair = [1, 2];
            }
            Int Swap() {
                pair = [pair[1], pair[0]];
                return pair[1];
            }
        }
        """)
    out = str(ExpandTupleTransformer().transform(game))
    assert "[Int, Int] pair;" in out  # field left intact
    assert "pair@0" not in out


def test_f321_control_plain_reassignment_still_expands() -> None:
    """Control for F-321: a whole-variable reassignment whose RHS does NOT
    read the variable still expands component-wise."""
    method = frog_parser.parse_method("""
        Int Oracle(Int x) {
            [Int, Int] v = [1, 2];
            v = [x, 3];
            return v[1];
        }
        """)
    out = str(ExpandTupleTransformer().transform(method))
    assert "v@0" in out  # expanded
    assert "return v@1;" in out


# ---------------------------------------------------------------------------
# SplitBareTupleDeclarations (bare_locals_only mode)
# ---------------------------------------------------------------------------


def test_bare_mode_splits_only_bare_local_declarations() -> None:
    """The early ``Split Bare Tuple Declarations`` pass must split bare local
    declarations but leave fields and decl-with-initializer locals to the full
    ``Expand Tuples`` pass, so their canonical routes are unchanged."""
    game = frog_parser.parse_game("""
        Game G() {
            [Int, Int] fieldPair;
            Void Initialize() {
                fieldPair = [1, 2];
            }
            Int WithInit() {
                [Int, Int] a = [3, 4];
                return a[0];
            }
            Int Bare() {
                [Int, Int] b;
                b = [5, 6];
                return b[0];
            }
        }
        """)
    out = str(
        ExpandTupleTransformer(bare_locals_only=True).transform(game)
    )
    assert "[Int, Int] fieldPair;" in out  # field untouched
    assert "[Int, Int] a = [3, 4];" in out  # decl-with-init untouched
    assert "b@0 = 5;" in out  # bare local split
    assert "return b@0;" in out
