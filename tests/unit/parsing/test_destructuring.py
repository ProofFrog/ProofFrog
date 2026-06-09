"""Tests for tuple-destructuring bindings, e.g. ``[T1, T2] [a, b] = expr;``.

These are parse-time sugar: the parser desugars each binding into a temporary
binding plus one assignment per element, choosing a typed declaration for a new
local and a plain assignment for a name already in scope (field/param/outer
local). No later stage ever sees a ``DestructuringBinding`` node.
"""

import tempfile

import pytest

from proof_frog import frog_ast, frog_parser


def _stmts(method_src: str) -> list[frog_ast.Statement]:
    method = frog_parser.parse_method(method_src)
    return list(method.block.statements)


def test_all_new_locals_desugar_to_temp_plus_typed_reads() -> None:
    stmts = _stmts("""
        [Int, Int] Foo() {
            [Int, Int] [a, b] = pair();
            return [a, b];
        }
        """)
    # temp decl + two typed reads + return
    assert isinstance(stmts[0], frog_ast.Assignment)
    assert isinstance(stmts[0].the_type, frog_ast.ProductType)
    assert isinstance(stmts[0].var, frog_ast.Variable)
    temp = stmts[0].var.name
    a, b = stmts[1], stmts[2]
    assert isinstance(a, frog_ast.Assignment) and isinstance(a.the_type, frog_ast.Type)
    assert isinstance(b, frog_ast.Assignment) and isinstance(b.the_type, frog_ast.Type)
    assert a.var == frog_ast.Variable("a")
    assert a.value == frog_ast.ArrayAccess(frog_ast.Variable(temp), frog_ast.Integer(0))
    assert b.value == frog_ast.ArrayAccess(frog_ast.Variable(temp), frog_ast.Integer(1))


def test_field_targets_become_assignments_not_declarations() -> None:
    # `sk` is a field, `pk` is new: pk should be declared, sk merely assigned.
    src = """
import 'x';
Game G() {
    Int sk;
    [Int, Int] Init() {
        [Int, Int] [pk, sk] = kg();
        return [pk, sk];
    }
}
Game H() {
    Int sk;
    [Int, Int] Init() {
        [Int, Int] [pk, sk] = kg();
        return [pk, sk];
    }
}
export as T;
"""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".game", delete=False, encoding="ascii"
    ) as f:
        f.write(src)
        path = f.name
    gf = frog_parser.parse_game_file(path)
    stmts = list(gf.games[0].methods[0].block.statements)
    temp = stmts[0].var.name  # type: ignore[attr-defined]
    pk_stmt, sk_stmt = stmts[1], stmts[2]
    assert isinstance(pk_stmt, frog_ast.Assignment)
    assert isinstance(sk_stmt, frog_ast.Assignment)
    # pk is a new local -> typed declaration
    assert pk_stmt.the_type is not None
    # sk is an existing field -> plain assignment (no type)
    assert sk_stmt.the_type is None
    assert sk_stmt.value == frog_ast.ArrayAccess(
        frog_ast.Variable(temp), frog_ast.Integer(1)
    )


def test_new_syntax_matches_hand_written_expansion() -> None:
    sugar = _stmts("""
        [Int, Int] Foo() {
            [Int, Int] [a, b] = pair();
            return [a, b];
        }
        """)
    expanded = _stmts("""
        [Int, Int] Foo() {
            [Int, Int] _tup = pair();
            Int a = _tup[0];
            Int b = _tup[1];
            return [a, b];
        }
        """)
    assert sugar == expanded


def test_plain_variable_rhs_skips_the_temp() -> None:
    stmts = _stmts("""
        [Int, Int] Foo([Int, Int] pair) {
            [Int, Int] [a, b] = pair;
            return [a, b];
        }
        """)
    # No temp binding: first statement is the read of element 0 directly off pair.
    a, b = stmts[0], stmts[1]
    assert isinstance(a, frog_ast.Assignment)
    assert a.value == frog_ast.ArrayAccess(
        frog_ast.Variable("pair"), frog_ast.Integer(0)
    )
    assert isinstance(b, frog_ast.Assignment)
    assert b.value == frog_ast.ArrayAccess(
        frog_ast.Variable("pair"), frog_ast.Integer(1)
    )


def test_sample_form_desugars_to_sample_temp() -> None:
    stmts = _stmts("""
        [Int, Int] Foo() {
            [Int, Int] [a, b] <- dist();
            return [a, b];
        }
        """)
    assert isinstance(stmts[0], frog_ast.Sample)
    assert isinstance(stmts[0].the_type, frog_ast.ProductType)
    assert isinstance(stmts[1], frog_ast.Assignment)


def test_sample_minus_form_desugars_to_unique_sample_temp() -> None:
    stmts = _stmts("""
        [Int, Int] Foo(Set<[Int, Int]> used) {
            [Int, Int] [a, b] <- [Int, Int] \\ used;
            return [a, b];
        }
        """)
    assert isinstance(stmts[0], frog_ast.UniqueSample)
    assert isinstance(stmts[0].the_type, frog_ast.ProductType)
    assert isinstance(stmts[0].sampled_from, frog_ast.ProductType)
    assert isinstance(stmts[1], frog_ast.Assignment)


def test_temp_name_avoids_collision() -> None:
    stmts = _stmts("""
        [Int, Int] Foo() {
            Int _tup = 0;
            [Int, Int] [a, b] = pair();
            return [a, b];
        }
        """)
    # The pre-existing `_tup` forces the generated temp to a fresh name.
    gen = stmts[1]
    assert isinstance(gen, frog_ast.Assignment) and isinstance(
        gen.var, frog_ast.Variable
    )
    assert gen.var.name != "_tup"


def test_two_destructurings_use_distinct_temps() -> None:
    stmts = _stmts("""
        [Int, Int] Foo() {
            [Int, Int] [a, b] = p();
            [Int, Int] [c, d] = q();
            return [a, b];
        }
        """)
    temp1 = stmts[0].var.name  # type: ignore[attr-defined]
    temp2 = stmts[3].var.name  # type: ignore[attr-defined]
    assert temp1 != temp2


def test_destructuring_inside_nested_block() -> None:
    # A destructuring inside an if-block desugars there, and a target naming an
    # outer field becomes an assignment (scope threads into nested blocks).
    src = """
import 'x';
Game G() {
    Int sk;
    Int Init(Bool b) {
        if (b) {
            [Int, Int] [pk, sk] = kg();
            return pk;
        }
        return 0;
    }
}
Game H() {
    Int Init(Bool b) {
        return 0;
    }
}
export as T;
"""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".game", delete=False, encoding="ascii"
    ) as f:
        f.write(src)
        path = f.name
    gf = frog_parser.parse_game_file(path)
    if_stmt = gf.games[0].methods[0].block.statements[0]
    assert isinstance(if_stmt, frog_ast.IfStatement)
    inner = list(if_stmt.blocks[0].statements)
    # temp decl + pk(new, typed) + sk(field, untyped) + return
    pk_stmt, sk_stmt = inner[1], inner[2]
    assert isinstance(pk_stmt, frog_ast.Assignment) and pk_stmt.the_type is not None
    assert isinstance(sk_stmt, frog_ast.Assignment) and sk_stmt.the_type is None


def test_arity_mismatch_is_a_parse_error() -> None:
    with pytest.raises(frog_parser.ParseError, match="2 names"):
        frog_parser.parse_method("""
            [Int, Int] Foo() {
                [Int, Int, Int] [a, b] = p();
                return [a, b];
            }
            """)


def test_non_product_leading_type_is_a_parse_error() -> None:
    with pytest.raises(frog_parser.ParseError, match="tuple type"):
        frog_parser.parse_method("""
            [Int, Int] Foo() {
                Int [a, b] = p();
                return [a, b];
            }
            """)
