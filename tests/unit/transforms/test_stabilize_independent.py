import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.proof_engine import ProofEngine
from proof_frog.transforms._base import PipelineContext, run_standardization
from proof_frog.transforms.algebraic import NormalizeCommutativeChains
from proof_frog.transforms.pipelines import STANDARDIZATION_PIPELINE
from proof_frog.transforms.standardization import (
    _StabilizeIndependentStatementsTransformer,
)
from proof_frog.visitors import NameTypeMap


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
    landed below the write. (``c`` reads only ``p``, so it may go on either
    side of the ``if``; since the ``if`` is sorted too, it goes after the
    declarations free at the same point.)"""
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


@pytest.mark.parametrize(
    "body, expected",
    [
        # F-381's shape: the write to b reads the a of the first doubling and
        # must stay above the second, equal doubling.
        (
            "a = a + a; b = b + a; a = a + a;",
            ["a = a + a;", "b = b + a;", "a = a + a;"],
        ),
        # Sound twin: an independent write to b still sorts below both.
        (
            "a = a + a; b = b + b; a = a + a;",
            ["a = a + a;", "a = a + a;", "b = b + b;"],
        ),
    ],
)
def test_f381_equal_statements_keep_their_own_edges(
    body: str, expected: list[str]
) -> None:
    statements = _stabilized_statements(f"""
        Game Test() {{
            Int a;
            Int b;
            Void O() {{
                {body}
            }}
        }}
        """)
    assert statements == expected


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


_DRAW_ACROSS_RETURN = """
    Game G() {{
        Set<BitString<1>> E;
        Bool guard;
        Int Draw(BitString<1> w) {{
            BitString<1> junk <- {domain};
            if (guard) {{
                return 1;
            }}
            BitString<1> other = w;
            return 0;
        }}
    }}
    """


def test_stabilize_keeps_possibly_empty_draw_above_early_return() -> None:
    """F-327: the draw may not complete (E may cover BitString<1>), so moving
    it below `if (guard) { return 1; }` would remove the traces on which it
    fails to complete. It stays above the if."""
    game = frog_parser.parse_game(
        _DRAW_ACROSS_RETURN.format(domain="BitString<1> \\ E")
    )
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game


def test_stabilize_still_moves_type_draw_across_early_return() -> None:
    """A draw from a type always completes and is independent of the guard,
    so the pass still orders it after the independent assignment."""
    game = frog_parser.parse_game(_DRAW_ACROSS_RETURN.format(domain="BitString<1>"))
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    statements = [str(s) for s in result.get_method("Draw").block.statements]
    assert statements[0] == "BitString<1> other = w;"
    assert statements[2] == "BitString<1> junk <- BitString<1>;"


# ---------------------------------------------------------------------------
# Independent if statements and bare declarations
# ---------------------------------------------------------------------------


def _method(body: str, fields: str = "", params: str = "Int p, Int q") -> str:
    return f"""
        Game Test() {{
            {fields}
            Bool f({params}) {{
                {body}
            }}
        }}
        """


def _stabilized(body: str, fields: str = "") -> frog_ast.Game:
    game = frog_parser.parse_game(_method(body, fields))
    return _StabilizeIndependentStatementsTransformer().transform_game(game)


def test_independent_ifs_are_sorted_and_declarations_follow() -> None:
    """Two independent ifs are ordered by their structure, and each bare
    declaration moves to just before the statement that first mentions it."""
    result = _stabilized(
        "Int? r; Int? s;"
        "if (q == 0) { s = 1; } else { s = None; }"
        "if (p == 0) { r = 1; } else { r = None; }"
        "return r == s;"
    )
    expected = frog_parser.parse_game(
        _method(
            "Int? r;"
            "if (p == 0) { r = 1; } else { r = None; }"
            "Int? s;"
            "if (q == 0) { s = 1; } else { s = None; }"
            "return r == s;"
        )
    )
    assert result == expected, f"\nGot:\n{result}"


def test_if_order_ignores_the_names_it_writes() -> None:
    """The names an if writes come from the order itself, so they do not
    decide it: `b = q` sorts before `a = r` although `a < b`."""
    result = _stabilized(
        "if (p == 0) { a = r; } if (p == 0) { b = q; } return a == b;"
    )
    expected = frog_parser.parse_game(
        _method("if (p == 0) { b = q; } if (p == 0) { a = r; } return a == b;")
    )
    assert result == expected, f"\nGot:\n{result}"


@pytest.mark.parametrize(
    "body, fields",
    [
        # Read after write: the second if reads the a the first writes.
        ("if (q == 0) { a = 1; } if (a == 0) { b = 1; } return b == 1;", ""),
        # Write after read: the second writes the a the first reads.
        ("if (q == 0) { b = a; } if (p == 0) { a = 1; } return a == b;", ""),
        # Write after write to a field.
        ("if (q == 0) { f = 1; } if (p == 0) { f = 2; } return true;", "Int f;"),
        # Element writes to one map.
        (
            "if (q == 0) { M[q] = 1; } if (p == 0) { M[p] = 2; } return true;",
            "Map<Int, Int> M;",
        ),
    ],
)
def test_dependent_ifs_keep_their_order(body: str, fields: str) -> None:
    """Swapping would change what one of them reads or what is left
    written: each pair conflicts on a name."""
    game = frog_parser.parse_game(_method(body, fields))
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game, f"\nGot:\n{result}"


def test_if_with_return_is_not_moved() -> None:
    """An if holding a return is not sorted: it stays ahead of the
    independent declarations after it."""
    game = frog_parser.parse_game(
        _method("if (q == 0) { return true; } Int b = p + 1; Int c = p + 2;"
                "return b == c;")
    )
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game, f"\nGot:\n{result}"


def test_loop_is_not_moved() -> None:
    game = frog_parser.parse_game(
        _method("Int a = 0; for (Int i = 0 to q) { a = a + i; } Int b = p + 1;"
                "return a == b;")
    )
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game, f"\nGot:\n{result}"


def test_declaration_of_a_name_declared_twice_is_not_moved() -> None:
    """Moving the first `Int? r;` below the second would swap which one
    binds the later uses."""
    game = frog_parser.parse_game(
        _method("Int? r; Int a = p + 1; Int? r; r = a; return r == None;")
    )
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game, f"\nGot:\n{result}"


def test_declaration_not_moved_past_a_write_to_its_type() -> None:
    """`BitString<n> v;` fixes its length where it runs; below `n = p;` the
    length would be the new n."""
    game = frog_parser.parse_game(
        _method("BitString<n> v; n = p; v = 0^n; return v == 0^n;",
                fields="Int n;")
    )
    result = _StabilizeIndependentStatementsTransformer().transform_game(game)
    assert result == game, f"\nGot:\n{result}"


_RESULT_A = "if (a == None) { r = None; } else { if (c) { r = a; } else { r = None; } }"
_RESULT_B = "if (b == None) { s = None; } else { if (d) { s = b; } else { s = None; } }"


def _two_results(first: str, second: str, decls: str, ret: str) -> frog_ast.Game:
    return frog_parser.parse_game(f"""
        Game G() {{
            Bool f(BitString<8>? a, BitString<8>? b, Bool c, Bool d) {{
                {decls}
                {first}
                {second}
                {ret}
            }}
        }}
        """)


def test_engine_identifies_independent_ifs_in_either_order() -> None:
    """The shape two inlined decapsulations leave: two independent ifs that
    each compute a result, compared at the end. The order of the ifs and
    the names of the results follow how the code arrived."""
    left = _two_results(
        _RESULT_A, _RESULT_B, "BitString<8>? r; BitString<8>? s;",
        "return r == s && r != None && s != None;",
    )
    right = _two_results(
        _RESULT_B, _RESULT_A, "BitString<8>? s; BitString<8>? r;",
        "return s == r && r != None && s != None;",
    )
    assert ProofEngine().check_equivalent(left, right).valid


def test_engine_keeps_dependent_ifs_apart() -> None:
    """Swapped, the second if reads r before the first writes it: with c
    and d true and a = 0^8, the left returns false and the right true."""
    first = "if (c) { r = a; } else { r = None; }"
    second = "if (d) { s = r; } else { s = b; }"
    decls = "BitString<8>? r; BitString<8>? s;"
    ret = "return s == None;"
    left = _two_results(first, second, decls, ret)
    right = _two_results(second, first, decls, ret)
    assert not ProofEngine().check_equivalent(left, right).valid


_TWO_DECAPSULATIONS = """
    Game G() {
        VerificationKeySpace vk1;
        SigningKeySpace sk1;
        PKEPublicKeySpace ek2;
        VerificationKeySpace vk2;
        PKESecretKeySpace dk2;
        PKEPublicKeySpace ek3;
        VerificationKeySpace vk3;
        PKESecretKeySpace dk3;
        Void Initialize() {
            [VerificationKeySpace, SigningKeySpace] kpS2 = S.KeyGen();
            [VerificationKeySpace, SigningKeySpace] kpS3 = S.KeyGen();
            vk2 = kpS2[0];
            vk3 = kpS3[0];
            [VerificationKeySpace, SigningKeySpace] kpS = S.KeyGen();
            [PKEPublicKeySpace, PKESecretKeySpace] kp2 = E.KeyGen();
            [PKEPublicKeySpace, PKESecretKeySpace] kp3 = E.KeyGen();
            vk1 = kpS[0];
            sk1 = kpS[1];
            ek2 = kp2[0];
            dk2 = kp2[1];
            ek3 = kp3[0];
            dk3 = kp3[1];
        }
        Bool Run() {
            KeySpace? r2;
            KeySpace? r3;
            KeySpace k <- KeySpace;
            KeySpace? m3 = E.Dec(dk3, E.Enc(ek3, k));
            SignatureSpace sigma = S.Sign(sk1, k);
            KeySpace? m2 = E.Dec(dk2, E.Enc(ek2, k));
            if (m3 == None) {
                r3 = None;
            } else {
                if (S.Verify(vk1, m3, sigma)) { r3 = m3; } else { r3 = None; }
            }
            if (m2 == None) {
                r2 = None;
            } else {
                if (S.Verify(vk1, m2, sigma)) { r2 = m2; } else { r2 = None; }
            }
            return r2 == r3 && (ek2 != ek3 || vk2 != vk3) && (r2 != None && r3 != None);
        }
    }
    """


def test_standardized_comparisons_are_normalized() -> None:
    """The last renumbering of locals, after the second sort, may leave
    `v6 == v5`; the standardization ends with the operands in order. (A
    decapsulation chain from the AKEM weak-scheme counterexample, where
    Field Lex-Min By RHS swaps the two receivers' field numbers.)"""
    ctx = PipelineContext(
        variables={}, proof_let_types=NameTypeMap(), proof_namespace={},
        subsets_pairs=[],
    )
    game = run_standardization(
        frog_parser.parse_game(_TWO_DECAPSULATIONS), STANDARDIZATION_PIPELINE, ctx
    )
    assert NormalizeCommutativeChains().apply(game, ctx) == game, f"\n{game}"


def test_if_order_follows_the_sorted_order_of_what_it_reads() -> None:
    """The ifs read `z` and `a`, whose names still reflect the input order;
    `z = p + 0` sorts first, so the if reading `z` goes first in this one
    run, although `a < z`."""
    result = _stabilized(
        "Int a = q + 0; Int z = p + 0;"
        "if (a == 0) { s = 1; } if (z == 0) { r = 1; } return r == s;"
    )
    expected = frog_parser.parse_game(
        _method(
            "Int z = p + 0; Int a = q + 0;"
            "if (z == 0) { r = 1; } if (a == 0) { s = 1; } return r == s;"
        )
    )
    assert result == expected, f"\nGot:\n{result}"


def test_declarations_left_between_ifs_do_not_pin_them() -> None:
    """Where an earlier run left `Int? r;` (just before the if writing r)
    does not keep that if below the other one."""
    result = _stabilized(
        "Int a = p + 0; Int b = q + 0;"
        "Int? s; if (b == 0) { s = 1; } else { s = None; }"
        "Int? r; if (a == 0) { r = 1; } else { r = None; }"
        "return r == s;"
    )
    expected = frog_parser.parse_game(
        _method(
            "Int a = p + 0; Int b = q + 0;"
            "Int? r; if (a == 0) { r = 1; } else { r = None; }"
            "Int? s; if (b == 0) { s = 1; } else { s = None; }"
            "return r == s;"
        )
    )
    assert result == expected, f"\nGot:\n{result}"
