import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.standardization import (
    _StabilizeIndependentStatementsTransformer,
)


@pytest.mark.parametrize(
    "source,expected",
    [
        # Basic swap: second assignment sorts before first → swapped
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = B();
                    Int v2 = A();
                    return v1 + v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v2 = A();
                    Int v1 = B();
                    return v1 + v2;
                }
            }
            """,
        ),
        # Already sorted — no change
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = A();
                    Int v2 = B();
                    return v1 + v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v1 = A();
                    Int v2 = B();
                    return v1 + v2;
                }
            }
            """,
        ),
        # Dependent statements — no change (v2 depends on v1)
        (
            """
            Game Test() {
                Int f() {
                    Int v1 = 42;
                    Int v2 = v1 + 1;
                    return v2;
                }
            }
            """,
            """
            Game Test() {
                Int f() {
                    Int v1 = 42;
                    Int v2 = v1 + 1;
                    return v2;
                }
            }
            """,
        ),
        # Independent field assignments sorted by canonical field name
        (
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field2 = 1;
                    field1 = 2;
                    return field1 + field2;
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = 2;
                    field2 = 1;
                    return field1 + field2;
                }
            }
            """,
        ),
        # Field sample interleaved with local samples — canonical order
        # regardless of source order (fields sort before locals with same RHS)
        (
            """
            Game Test() {
                Set T;
                T field1;
                T field2;
                Void f() {
                    field1 <- T;
                    T v1 <- T;
                    field2 <- T;
                }
            }
            """,
            """
            Game Test() {
                Set T;
                T field1;
                T field2;
                Void f() {
                    field1 <- T;
                    field2 <- T;
                    T v1 <- T;
                }
            }
            """,
        ),
        # Reverse source order produces same canonical form
        (
            """
            Game Test() {
                Set T;
                T field1;
                T field2;
                Void f() {
                    T v1 <- T;
                    field2 <- T;
                    field1 <- T;
                }
            }
            """,
            """
            Game Test() {
                Set T;
                T field1;
                T field2;
                Void f() {
                    field1 <- T;
                    field2 <- T;
                    T v1 <- T;
                }
            }
            """,
        ),
        # Dependent field assignment not reordered past its dependency
        (
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = 1;
                    field2 = field1 + 1;
                    return field2;
                }
            }
            """,
            """
            Game Test() {
                Int field1;
                Int field2;
                Int f() {
                    field1 = 1;
                    field2 = field1 + 1;
                    return field2;
                }
            }
            """,
        ),
    ],
)
def test_stabilize_independent(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


def test_non_sortable_stmt_between_sortables_is_barrier() -> None:
    """Regression: a non-sortable stmt (e.g. `if`) between two sortable
    stmts is a dependency barrier. Reordering must not move a sortable
    stmt past a non-sortable stmt that uses its defined variable.

    Before the fix, this transform would swap the `BitString<16> v1 = m[...]`
    assignment (whose value-key sorts later) with the `BitString<8> v2 <- ...`
    sample (whose value-key sorts earlier), ignoring the fact that the `if`
    between them uses `v1`. Result: after the swap, the `if` references
    `v1` before `v1` is defined.
    """
    source = """
        Game Test() {
            BitString<8> f(BitString<16> m) {
                BitString<16> v1 = m[0 : 16];
                if (v1 == 0^16) {
                    BitString<8> r <- BitString<8>;
                    return r;
                }
                BitString<8> v2 <- BitString<8>;
                return v2;
            }
        }
    """
    game = frog_parser.parse_game(source)
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    stmts = result.methods[0].block.statements
    # Minimal check: stmts[0] is the `v1 = m[0:16]` assignment, not the
    # `v2 <- BitString<8>` sample. Swapping them would put `v1` after the
    # `if` that uses it.
    assert isinstance(stmts[0], frog_ast.Assignment), (
        f"expected stmts[0] to still be `v1 = m[0:16]`, got {stmts[0]!r}"
    )


def test_if_with_return_in_body_is_a_barrier() -> None:
    """A non-sortable ``if`` whose body contains a ``return`` still acts
    as a dependency barrier for the sortable stmts on either side. The
    early-return path means the second sortable (``v2``) is only observed
    on the ``!cond`` branch, but the barrier behavior of the ``if``
    itself does not depend on whether its body returns -- the ``if``
    references ``v1``, so any swap that puts ``v1`` after ``v2`` would
    print ``v1`` before its definition. Mirrors the a78a070 / 2ab448f
    return-in-if pattern for the other reordering passes.
    """
    source = """
        Game Test() {
            BitString<8> f(BitString<16> m, Bool cond) {
                BitString<16> v1 = m[0 : 16];
                if (v1 == 0^16) {
                    BitString<8> r <- BitString<8>;
                    return r;
                }
                BitString<8> v2 <- BitString<8>;
                return v2;
            }
        }
    """
    game = frog_parser.parse_game(source)
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    stmts = result.methods[0].block.statements
    assert isinstance(stmts[0], frog_ast.Assignment), (
        f"expected stmts[0] to still be `v1 = m[0:16]`, got {stmts[0]!r}"
    )
    # The if-with-return still sits between v1 and v2 (positions 0/1/2).
    assert isinstance(stmts[1], frog_ast.IfStatement)
    assert isinstance(stmts[2], frog_ast.Sample)


def _stabilized_statements(source: str) -> list[str]:
    game = frog_parser.parse_game(source)
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    return [str(stmt) for stmt in result.methods[0].block.statements]


def test_f354_reader_not_moved_below_conditional_write() -> None:
    """Two readers of field ``f`` above an ``if`` that writes ``f``. The
    dependency graph used to tie the ``if`` to the nearest reader (``a``)
    only, so ``b`` -- last in return order -- traded places with ``c`` and
    landed below the write."""
    statements = _stabilized_statements("""
        Game Test() {
            Int f;
            [Int, Int, Int] O(Int p) {
                Int b = f + 2;
                Int a = f + 1;
                if (p == 0) {
                    f = 5;
                }
                Int c = p + 0;
                return [c, a, b];
            }
        }
        """)
    barrier = next(i for i, text in enumerate(statements) if text.startswith("if"))
    assert statements.index("Int a = f + 1;") < barrier
    assert statements.index("Int b = f + 2;") < barrier
    assert statements.index("Int c = p + 0;") > barrier


def test_f354_independent_readers_above_write_still_reorder() -> None:
    """Sound twin: the two readers are independent of each other, so they are
    still put in return order above the write."""
    statements = _stabilized_statements("""
        Game Test() {
            Int f;
            [Int, Int] O(Int p) {
                Int b = f + 2;
                Int a = f + 1;
                if (p == 0) {
                    f = 5;
                }
                return [a, b];
            }
        }
        """)
    assert statements[:2] == ["Int a = f + 1;", "Int b = f + 2;"]


def test_write_not_moved_above_shadowing_declaration() -> None:
    """``f = p;`` below ``Int f;`` writes the local. The pass sorts field
    assignments first, and used to lift it above the declaration, where it
    writes the field."""
    statements = _stabilized_statements("""
        Game Test() {
            Int f;
            Int O(Int p) {
                Int z = p + 9;
                Int f;
                f = p;
                Int a = f + 1;
                return a + z;
            }
        }
        """)
    declaration = statements.index("Int f;")
    assert statements.index("f = p;") > declaration
    assert statements.index("Int a = f + 1;") > declaration
