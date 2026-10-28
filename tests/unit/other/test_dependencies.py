import pytest
from proof_frog import frog_ast
from proof_frog import frog_parser
from proof_frog import dependencies
from proof_frog import proof_engine


@pytest.mark.parametrize(
    "method_code,expected_dependencies",
    [
        # Simple statements
        (
            """
            Void f() {
                Int x = 0;
                Int y = x;
                Int z = 0;
                Int w = 5;
                Int a = x + y + z + w;
            }""",
            [[], [0], [], [], [0, 1, 2, 3]],
        ),
        # If statement
        (
            """
            Int f() {
                Int x = 0;
                if (True) {
                    x = 1;
                }
                return x;
            }
            """,
            [[], [0], [1]],
        ),
        # If/Else
        (
            """
            Int f() {
                Int x = 0;
                Int y = 0;
                if (True) {
                    x = 1;
                } else {
                    y = 1;
                }
                return x + y;
            }
            """,
            [[], [], [0, 1], [2]],
        ),
        # Dependent return
        (
            """
            Int f() {
                if (True) {
                    return 1;
                }
                return 2;
            }
            """,
            [[], [0]],
        ),
        # Read after write
        (
            """
            Void f() {
                Int x = 1;
                return x;
            }
            """,
            [[], [0]],
        ),
        # Write after Read: below every earlier mention of x, nearest first
        (
            """
            Void f() {
                Int x = 1;
                Int y = x;
                x = 2;
            }
            """,
            [[], [0], [1, 0]],
        ),
        # Write after write
        (
            """
            Void f() {
                Int x = 1;
                x = 2;
            }
            """,
            [[], [0]],
        ),
        # A shadowing bare declaration depends on every earlier reader of
        # the outer binding, not only the nearest one. So does the write
        # below it, which also depends on the declaration. The return reads
        # x, so it depends on the nearest writer, which chains back to the
        # declaration.
        (
            """
            Int f() {
                Int a = x;
                Int b = x;
                Int x;
                x = 5;
                return a + b + x;
            }
            """,
            [[], [], [1, 0], [2, 1, 0], [0, 1, 3]],
        ),
    ],
)
def test_dependencies(method_code: str, expected_dependencies: list[list[int]]) -> None:
    method = frog_parser.parse_method(method_code)

    result = dependencies.generate_dependency_graph(method.block, [], {})

    nodes = [dependencies.Node(statement) for statement in method.block.statements]
    for to_add_index, dependency_list in enumerate(expected_dependencies):
        for index in dependency_list:
            nodes[to_add_index].add_neighbour(nodes[index])

    desired_graph = dependencies.DependencyGraph(nodes)
    print("Expected:")
    print(desired_graph)
    print("Received:")
    print(result)
    assert result == desired_graph


# --------------------------------------------------------------------------
# F-354: a write depends on EVERY earlier mention of the name it writes.
#
# The graph used to stop at the nearest earlier mention. Two earlier readers
# carry no edge between them, so the farther one could be sorted below the
# write and read the new value.
# --------------------------------------------------------------------------


def _edges(
    method_code: str,
    fields: tuple[str, ...] = (),
    namespace: dict | None = None,
) -> list[list[int]]:
    """The graph of a method body as, per statement, the indices of the
    statements it depends on, in edge order."""
    method = frog_parser.parse_method(method_code)
    statements = method.block.statements
    graph = dependencies.generate_dependency_graph(
        method.block,
        [frog_ast.Field(frog_ast.IntType(), name, None) for name in fields],
        namespace or {},
    )
    index_of = {id(statement): index for index, statement in enumerate(statements)}
    return [
        [index_of[id(neighbour.statement)] for neighbour in node.in_neighbours]
        for node in graph.nodes
    ]


@pytest.mark.parametrize(
    "write",
    [
        # plain assignment
        "x = 5;",
        # sample, sample from a set difference
        "x <- BitString<8>;",
        "x <- BitString<8> \\ {y};",
        # unique sample into x
        "x <-uniq[T] BitString<8>;",
        # element write (map entry, array or tuple slot), nested element write
        "x[k] = 5;",
        "x[0] = 5;",
        "x[k] <- BitString<8>;",
        "x[0][1] = 5;",
        # typed declarations: with an initializer, sampled
        "Int x = 5;",
        "BitString<8> x <- BitString<8>;",
        "BitString<8> x <-uniq[T] BitString<8>;",
        # bare declaration
        "Int x;",
        # a write inside a branch, an else branch, a loop
        "if (c) { x = 5; }",
        "if (c) { y = 1; } else { x = 5; }",
        "for (Int i = 0 to 3) { x = 5; }",
        "for (Int i in S) { if (c) { x[i] = 5; } }",
        # a unique sample inserts into its exclusion set
        "BitString<8> z <-uniq[x] BitString<8>;",
        "BitString<8> z <-uniq[x.seen] BitString<8>;",
        "if (c) { BitString<8> z <-uniq[x] BitString<8>; }",
    ],
)
def test_f354_write_depends_on_every_earlier_reader(write: str) -> None:
    """Two readers of x, then some form of write to x."""
    edges = _edges(f"""
        Int f() {{
            Int a = x + 1;
            Int b = x;
            {write}
            return a + b;
        }}
        """)
    assert edges[2][:2] == [1, 0]


@pytest.mark.parametrize("outer", ["field", "parameter"])
def test_f354_write_to_outer_binding_depends_on_every_earlier_reader(
    outer: str,
) -> None:
    """The written name is a field or a method parameter, and the farther
    reader is the one a chain delays."""
    signature = "Int f(Int x)" if outer == "parameter" else "Int f()"
    edges = _edges(
        f"""
        {signature} {{
            Int c = 1;
            Int d = c + 1;
            Int a = x + d;
            Int b = x;
            x = 5;
            return a + b;
        }}
        """,
        fields=("x",) if outer == "field" else (),
    )
    assert edges[4] == [3, 2]


def test_f354_typed_shadowing_declaration_depends_on_every_earlier_reader() -> None:
    """``Int x = 5;`` shadowing a field: both earlier readers saw the field."""
    edges = _edges(
        """
        Int f() {
            Int a = x + 1;
            Int b = x;
            Int x = 5;
            return a + b + x;
        }
        """,
        fields=("x",),
    )
    assert edges[2] == [1, 0]
    # ... and the use below reads the local.
    assert 2 in edges[3]


def test_f354_write_depends_on_every_earlier_write_and_read() -> None:
    """Write after write after read after write."""
    edges = _edges("""
        Void f() {
            Int x = 1;
            Int a = x;
            x = 2;
            x = 3;
        }
        """)
    assert edges == [[], [0], [1, 0], [2, 1, 0]]


def test_f354_writer_of_two_names_depends_on_all_readers_of_both() -> None:
    edges = _edges("""
        Void f() {
            Int a = x;
            Int b = y;
            Int c = x + y;
            x = y;
            y = 0;
        }
        """)
    # `x = y;` writes x (below both readers of x) and only reads y.
    assert edges[3] == [2, 0]
    # `y = 0;` is below every mention of y, `x = y;` included.
    assert edges[4] == [3, 2, 1]


def test_f354_equal_statements_are_distinct_readers() -> None:
    """Two textually identical readers are two nodes; the write is below
    both (neighbours are compared by identity, not structure)."""
    edges = _edges("""
        Void f() {
            S.Touch(x);
            S.Touch(x);
            x = 5;
        }
        """)
    assert edges[2] == [1, 0]


def test_f354_name_shared_with_proof_namespace_is_still_ordered() -> None:
    """A field or local that shares its name with a proof-level definition
    used to get no edges at all."""
    code = """
        Int f() {
            Int b = x;
            x = 5;
            return b + x;
        }
        """
    assert _edges(code, namespace={"x": None}) == _edges(code) == [[], [0], [0, 1]]


def test_read_depends_on_nearest_writer_only() -> None:
    """Read-after-write stays sparse: the nearest writer is itself below every
    earlier one, so the reader needs no edge to them."""
    edges = _edges("""
        Int f() {
            Int x = 1;
            x = 2;
            x = 3;
            Int a = x;
            return a;
        }
        """)
    assert edges == [[], [0], [1, 0], [2], [3]]


def test_set_difference_sample_only_reads_its_exclusion_set() -> None:
    """``z <- T \\ x`` is pure: unlike ``<-uniq[x]`` it inserts nothing into
    x, so it is not ordered against another reader of x."""
    edges = _edges("""
        Int f() {
            Int a = |x|;
            BitString<8> z <- BitString<8> \\ x;
            return a;
        }
        """)
    assert edges[1] == []


def test_independent_statements_stay_free() -> None:
    """The denser graph adds no edge between statements that do not conflict:
    readers of the same name, and statements over disjoint names."""
    edges = _edges(
        """
        Int f() {
            Int a = x + 1;
            Int b = x + 2;
            Int c = S.Draw();
            Int d = y;
            y = 5;
            Int e = x + c;
            return a + b + d + e;
        }
        """,
        fields=("x", "y"),
    )
    assert edges[0] == []
    assert edges[1] == []
    assert edges[2] == []
    assert edges[3] == []
    # The write to y is below the one reader of y -- and nothing else.
    assert edges[4] == [3]
    # A reader of x below the write to y does not depend on it.
    assert edges[5] == [2]


def test_bare_declaration_binds_later_uses() -> None:
    """Every bare declaration is a binder, whether or not it shadows an outer
    name: a use below it must stay below it, and reaches it from the return
    so the declaration is not pruned."""
    code = """
        Int f() {
            Int a = x;
            Int x;
            x = 5;
            Int b = x;
            return a + b;
        }
        """
    for fields in ((), ("x",)):
        edges = _edges(code, fields=fields)
        assert edges[1] == [0]
        assert edges[2] == [1, 0]
        # The reader depends on the nearest writer, which depends on the
        # declaration.
        assert edges[3] == [2]


def test_f354_sort_keeps_delayed_reader_above_write() -> None:
    """End of the line: the topological sort no longer moves ``a`` below the
    write."""
    game = frog_parser.parse_game("""
        Game G() {
            Int f;
            Int O() {
                Int c = 1;
                Int d = c + 1;
                Int e = d + 1;
                Int a = f + e;
                Int b = f;
                f = 5;
                return a + b;
            }
        }
        """)
    engine = proof_engine.ProofEngine()
    statements = [str(s) for s in engine.sort_game(game).methods[0].block.statements]
    write = statements.index("f = 5;")
    assert statements.index("Int a = f + e;") < write
    assert statements.index("Int b = f;") < write


def test_f354_bubble_sort_keeps_both_readers_above_write() -> None:
    """``BubbleSortFieldAssignment`` swaps adjacent field assignments that the
    graph leaves unordered. ``z = f;`` used to be unordered against ``f = 1;``
    and ended up below it."""
    game = frog_parser.parse_game("""
        Game G() {
            Int f;
            Int y;
            Int z;
            Void O() {
                z = f;
                y = f;
                f = 1;
            }
        }
        """)
    result = dependencies.BubbleSortFieldAssignment().transform_game(game)
    statements = [str(s) for s in result.methods[0].block.statements]
    # The two independent readers are still put in name order.
    assert statements == ["y = f;", "z = f;", "f = 1;"]


def test_bubble_sort_still_sorts_independent_field_assignments() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Int f;
            Int y;
            Int z;
            Void O(Int p) {
                z = p;
                y = p + 1;
                f = 1;
            }
        }
        """)
    result = dependencies.BubbleSortFieldAssignment().transform_game(game)
    statements = [str(s) for s in result.methods[0].block.statements]
    assert statements == ["f = 1;", "y = p + 1;", "z = p;"]


# ---------------------------------------------------------------------------
# Draws that may not complete (F-303, F-305, F-318, F-327)
# ---------------------------------------------------------------------------


def _first_statement(statement: str) -> frog_ast.Statement:
    method = frog_parser.parse_method(f"Void f() {{ {statement} }}")
    return method.block.statements[0]


@pytest.mark.parametrize(
    "statement, expected",
    [
        # T minus a runtime set: empty when the set covers T.
        ("BitString<1> x <- BitString<1> \\ E;", True),
        ("BitString<n> x <-uniq[E] BitString<n>;", True),
        # A set literal with at least as many elements as T may have.
        ("BitString<1> x <- BitString<1> \\ {0b0, 0b1};", True),
        ("Bool x <- Bool \\ {true, false};", True),
        ("ModInt<q> x <- ModInt<q> \\ {0};", True),
        ("ModInt<1> x <- ModInt<1> \\ {0};", True),
        # Fewer excluded elements than T certainly has: never empty. Every
        # length is at least 1, so BitString<n> has at least two elements.
        ("BitString<n> x <- BitString<n> \\ {s};", False),
        ("BitString<2> x <- BitString<2> \\ {0b00, 0b01, 0b10};", False),
        ("Bool x <- Bool \\ {true};", False),
        ("ModInt<5> x <- ModInt<5> \\ {0, 1};", False),
        ("BitString<n> x <- BitString<n> \\ {};", False),
        # Draws from types are never empty.
        ("BitString<n> x <- BitString<n>;", False),
        ("ModInt<q> x <- ModInt<q>;", False),
        ("Key k <- Key;", False),
        ("K.Key k <- K.Key;", False),
        ("Function<D, R> H <- Function<D, R>;", False),
        # A runtime set value as the domain may be empty.
        ("Set<BitString<n>> x <- S;", True),
        # Not a draw.
        ("BitString<n> x = y;", False),
    ],
)
def test_is_possibly_empty_draw(statement: str, expected: bool) -> None:
    node = _first_statement(statement)
    assert dependencies.is_possibly_empty_draw(node, {"S", "E"}) is expected


def test_possibly_empty_draw_depends_on_value_names() -> None:
    """A domain is a runtime value only if its name is bound to one; any
    other name is a type."""
    draw = _first_statement("Set<BitString<n>> x <- S;")
    assert dependencies.is_possibly_empty_draw(draw, {"S"})
    assert not dependencies.is_possibly_empty_draw(draw, set())
    keys = frog_ast.Sample(
        None,
        frog_ast.Variable("x"),
        frog_ast.FieldAccess(frog_ast.Variable("M"), "keys"),
    )
    assert dependencies.is_possibly_empty_draw(keys, {"M"})
    assert not dependencies.is_possibly_empty_draw(keys, set())
    # The pre-UniqueSample shape: a Sample whose domain is `T \ E`.
    minus = frog_ast.Sample(
        None,
        frog_ast.Variable("x"),
        frog_ast.BinaryOperation(
            frog_ast.BinaryOperators.SETMINUS,
            frog_ast.BitStringType(frog_ast.Integer(1)),
            frog_ast.Variable("E"),
        ),
    )
    assert dependencies.is_possibly_empty_draw(minus, set())


def test_may_not_complete_looks_inside_nested_blocks() -> None:
    nested = _first_statement(
        "if (c) { for (Int i = 0 to 2) { BitString<1> x <- BitString<1> \\ E; } }"
    )
    assert dependencies.may_not_complete(nested, {"E"})
    assert len(dependencies.possibly_empty_draws(nested, {"E"})) == 1
    plain = _first_statement("if (c) { BitString<1> x <- BitString<1>; }")
    assert not dependencies.may_not_complete(plain, {"E"})
    assert not dependencies.possibly_empty_draws(plain, {"E"})


def test_game_value_names() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Set<Int> F;
            Int O(Int p, Set<Int> S) {
                Int a = p;
                Bool b;
                for (Int i = 0 to 2) { a = a + i; }
                for (Int e in S) { a = a + e; }
                return a;
            }
        }
        """)
    assert dependencies.game_value_names(game) == {"F", "p", "S", "a", "b", "i", "e"}


def test_graph_pins_possibly_empty_draw_below_and_above_returns() -> None:
    """A draw whose domain may be empty stays below an earlier statement
    containing a return, and a later return stays below it (F-303, F-327)."""
    code = """
        Int f(Bool c) {
            if (c) { return 1; }
            BitString<1> x <- BitString<1> \\ E;
            return 0;
        }
        """
    edges = _edges(code, fields=("E",))
    assert 0 in edges[1]
    assert 1 in edges[2]


def test_graph_leaves_type_draw_free_of_returns() -> None:
    code = """
        Int f(Bool c) {
            if (c) { return 1; }
            BitString<1> x <- BitString<1>;
            return 0;
        }
        """
    edges = _edges(code)
    assert edges[1] == []
    assert edges[2] == [0]


def test_graph_value_names_override() -> None:
    """A draw from a name the caller says is a value is pinned; the same
    draw from a type name is not."""
    method = frog_parser.parse_method("""
        Int f() {
            Set<Int> x <- S;
            return 0;
        }
        """)
    as_value = dependencies.generate_dependency_graph(method.block, [], {}, {"S"})
    as_type = dependencies.generate_dependency_graph(method.block, [], {}, set())
    assert as_value.nodes[1].in_neighbours == [as_value.nodes[0]]
    assert not as_type.nodes[1].in_neighbours


def _sorted_statements(game_code: str) -> list[str]:
    game = frog_parser.parse_game(game_code)
    engine = proof_engine.ProofEngine()
    return [str(s) for s in engine.sort_game(game).methods[0].block.statements]


def test_sort_keeps_return_below_possibly_empty_draw() -> None:
    """F-303: the return is not hoisted above the draw, so the draw is not
    pruned."""
    statements = _sorted_statements("""
        Game G() {
            Set<BitString<1>> E;
            Int Draw() {
                BitString<1> junk <- BitString<1> \\ E;
                return 0;
            }
        }
        """)
    assert statements == ["BitString<1> junk <- BitString<1> \\ E;", "return 0;"]


def test_sort_keeps_possibly_empty_draw_over_local_set() -> None:
    """F-305: a draw over a local exclusion set, with no return after it and
    no field reference, is kept with the writes it depends on, and reported."""
    game = frog_parser.parse_game("""
        Game G() {
            Void Probe() {
                Set<BitString<1>> E;
                E = E union {0b0};
                BitString<1> junk <- BitString<1> \\ E;
                BitString<1> dead <- BitString<1>;
            }
        }
        """)
    kept: list = []
    result = proof_engine.ProofEngine().sort_game(game, kept)
    statements = [str(s) for s in result.methods[0].block.statements]
    assert statements == [
        "Set<BitString<1>> E;",
        "E = E union {0b0};",
        "BitString<1> junk <- BitString<1> \\ E;",
    ]
    assert [(name, str(draw)) for name, draw in kept] == [
        ("Probe", "BitString<1> junk <- BitString<1> \\ E;")
    ]


def test_sort_still_prunes_dead_type_draw() -> None:
    statements = _sorted_statements("""
        Game G() {
            Int Draw() {
                BitString<1> junk <- BitString<1>;
                BitString<1> other <- BitString<1> \\ {0b0};
                return 0;
            }
        }
        """)
    assert statements == ["return 0;"]


def test_remove_unnecessary_fields_keeps_possibly_empty_draw() -> None:
    """F-318: the dead draw is kept, so its oracle and the field it reads
    survive; a dead draw from a type is still removed."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<BitString<1>> E;
            Void Add(BitString<1> x) {
                E = E union {x};
            }
            Void Probe() {
                BitString<1> junk <- BitString<1> \\ E;
                BitString<1> dead <- BitString<1>;
            }
        }
        """)
    kept: list = []
    result = dependencies.remove_unnecessary_fields(game, kept)
    assert [field.name for field in result.fields] == ["E"]
    probe = result.get_method("Probe")
    assert [str(s) for s in probe.block.statements] == [
        "BitString<1> junk <- BitString<1> \\ E;"
    ]
    assert [str(s) for s in result.get_method("Add").block.statements] == [
        "E = E union {x};"
    ]
    assert [(name, str(draw)) for name, draw in kept] == [
        ("Probe", "BitString<1> junk <- BitString<1> \\ E;")
    ]


def test_remove_unnecessary_fields_drops_dead_type_draw_and_oracle() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Set<BitString<1>> E;
            Void Add(BitString<1> x) {
                E = E union {x};
            }
            Void Probe() {
                BitString<1> junk <- BitString<1>;
            }
        }
        """)
    kept: list = []
    result = dependencies.remove_unnecessary_fields(game, kept)
    assert not result.fields
    assert [m.signature.name for m in result.methods] == []
    assert not kept


def test_remove_unnecessary_statements_reports_only_dead_draws() -> None:
    """A possibly-empty draw whose result is used is live anyway and is not
    reported as kept for its domain."""
    method = frog_parser.parse_method("""
        BitString<1> f() {
            BitString<1> r <- BitString<1> \\ E;
            return r;
        }
        """)
    kept: list = []
    block = dependencies.remove_unnecessary_statements(
        ["E"], method.block, value_names={"E"}, kept_draws=kept
    )
    assert len(block.statements) == 2
    assert not kept
