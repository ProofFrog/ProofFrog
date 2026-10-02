"""Unit tests for the definite-assignment analysis (``_definedness``).

The tests query the analysis the way a statement-level pass would: find a
statement in a method, take the scope just before it, and ask which
variables its expression reads that may be unassigned.
"""

from typing import Optional

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms._definedness import (
    GameDefinedness,
    MethodDefinedness,
    bare_declared_names,
    initialize_assigned_fields,
    initialized_binder,
    method_binder_counts,
)
from proof_frog.visitors import NameTypeMap


def _ctx(let_names: tuple[str, ...] = ()) -> PipelineContext:
    let_types = NameTypeMap()
    for name in let_names:
        let_types.set(name, frog_ast.IntType())
    return PipelineContext(
        variables={},
        proof_let_types=let_types,
        proof_namespace={},
        subsets_pairs=[],
    )


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    return next(m for m in game.methods if m.signature.name == name)


def _find(block: frog_ast.Block, text: str) -> Optional[frog_ast.Statement]:
    """The first statement, at any depth, whose source starts with *text*."""
    for statement in block.statements:
        if str(statement).startswith(text):
            return statement
        nested: list[frog_ast.Block] = []
        if isinstance(statement, frog_ast.IfStatement):
            nested = list(statement.blocks)
        elif isinstance(statement, (frog_ast.NumericFor, frog_ast.GenericFor)):
            nested = [statement.block]
        for inner in nested:
            found = _find(inner, text)
            if found is not None:
                return found
    return None


def _reads_at(
    source: str,
    statement_text: str,
    method_name: str = "Query",
    let_names: tuple[str, ...] = (),
) -> list[tuple[str, str]]:
    """Unassigned reads of the value of the statement starting with
    *statement_text* in *method_name*, as a statement-level pass asks."""
    game = frog_parser.parse_game(source)
    method = _method(game, method_name)
    statement = _find(method.block, statement_text)
    assert statement is not None, statement_text
    scope = GameDefinedness(game, _ctx(let_names)).at_statement(method, statement)
    assert scope is not None
    if isinstance(statement, frog_ast.ReturnStatement):
        return scope.unassigned_reads(statement.expression)
    assert isinstance(statement, frog_ast.Assignment)
    return scope.unassigned_reads(statement.value)


def _names(reads: list[tuple[str, str]]) -> list[str]:
    return [name for name, _ in reads]


# ---------------------------------------------------------------------------
# Accept rules
# ---------------------------------------------------------------------------

_ACCEPTS = {
    "method_parameter": (
        "Game G() { Int Query(Int x) { Int y = x; return 0; } }",
        "Int y",
    ),
    "game_parameter": (
        "Game G(Int q) { Int Query(Int x) { Int y = q + x; return 0; } }",
        "Int y",
    ),
    "initialized_local": (
        "Game G() { Int Query(Int x) { Int a = x; Int y = a; return 0; } }",
        "Int y",
    ),
    "sampled_local": (
        "Game G() { Int Query(Int x) { Bool a <- Bool; Bool y = a; return 0; } }",
        "Bool y",
    ),
    "unique_sampled_local": (
        "Game G() { Int Query(Set<Bool> S) {"
        " Bool a <-uniq[S] Bool; Bool y = a; return 0; } }",
        "Bool y",
    ),
    "local_from_enclosing_block": (
        "Game G() { Int Query(Int x, Bool c) {"
        " Int a = x; if (c) { Int y = a; } return 0; } }",
        "Int y",
    ),
    "numeric_loop_binder": (
        "Game G() { Int Query(Int x) {"
        " for (Int i = 0 to 3) { Int y = i; } return 0; } }",
        "Int y",
    ),
    "generic_loop_binder": (
        "Game G() { Int Query(Set<Int> S) {"
        " for (Int e in S) { Int y = e; } return 0; } }",
        "Int y",
    ),
    "field_assigned_in_initialize": (
        "Game G() { Bool f; Void Initialize() { f = false; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
    ),
    "field_sampled_in_initialize": (
        "Game G() { Bool f; Void Initialize() { f <- Bool; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
    ),
    "field_assigned_before_the_return": (
        "Game G() { Bool f; Bool Initialize() { f = false; Bool c <- Bool;"
        " if (c) { return true; } return false; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
    ),
    "field_with_initializer": (
        "Game G() { Bool f = false; Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
    ),
}


@pytest.mark.parametrize("name", sorted(_ACCEPTS))
def test_definitely_assigned_reads(name: str) -> None:
    source, statement = _ACCEPTS[name]
    assert _reads_at(source, statement) == []


def test_let_name_is_assigned() -> None:
    source = "Game G() { Int Query(Int x) { Int y = lambda + E.order; return 0; } }"
    game = frog_parser.parse_game(source)
    method = _method(game, "Query")
    statement = _find(method.block, "Int y")
    assert isinstance(statement, frog_ast.Assignment)
    ctx = _ctx(("lambda",))
    ctx.proof_namespace["E"] = None
    scope = GameDefinedness(game, ctx).at_statement(method, statement)
    assert scope is not None
    assert scope.unassigned_reads(statement.value) == []
    # Without a context no let name resolves.
    bare = GameDefinedness(game).at_statement(method, statement)
    assert bare is not None
    assert sorted(_names(bare.unassigned_reads(statement.value))) == ["E", "lambda"]


# ---------------------------------------------------------------------------
# Decline rules
# ---------------------------------------------------------------------------

# name -> (game, statement, method, variable, reason fragment)
_DECLINES = {
    "field_assigned_only_by_another_oracle": (
        "Game G() { Bool f; Void Store(Bool v) { f = v; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "Initialize does not assign",
    ),
    "field_assigned_after_possible_return": (
        "Game G() { Bool f; Bool Initialize() { Bool c <- Bool;"
        " if (c) { return true; } f = false; return false; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "before any return",
    ),
    "field_assigned_under_if": (
        "Game G() { Bool f; Void Initialize() { Bool c <- Bool;"
        " if (c) { f = false; } }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "Initialize does not assign",
    ),
    "field_assigned_in_loop": (
        "Game G(Int n) { Bool f; Void Initialize() {"
        " for (Int i = 0 to n) { f = false; } }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "Initialize does not assign",
    ),
    "field_element_write_only": (
        "Game G() { Map<Int, Bool> M; Void Initialize() { M[0] = true; }"
        " Int Query(Int x) { Map<Int, Bool> y = M; return 0; } }",
        "Map<Int, Bool> y",
        "Query",
        "M",
        "Initialize does not assign",
    ),
    "initialize_assigns_shadowing_local": (
        "Game G() { Bool f; Void Initialize() { Bool f = true; f = false; }"
        " Int Query(Int x) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "Initialize does not assign",
    ),
    "field_read_inside_initialize": (
        "Game G() { Bool f; Bool g; Void Initialize() { f = false; g = f; }"
        " Int Query(Int x) { return 0; } }",
        "g = f",
        "Initialize",
        "f",
        "field read inside Initialize",
    ),
    "bare_declared_local": (
        "Game G() { Int Query(Int x, Bool c) {"
        " Bool a; if (c) { a = true; } Bool y = a; return 0; } }",
        "Bool y",
        "Query",
        "a",
        "declared without a value",
    ),
    "bare_declared_local_assigned_on_every_path": (
        "Game G() { Int Query(Int x) { Bool a; a = true; Bool y = a; return 0; } }",
        "Bool y",
        "Query",
        "a",
        "declared without a value",
    ),
    "name_bound_more_than_once": (
        "Game G() { Int Query(Int x, Bool c) {"
        " if (c) { Bool a = true; Bool y = a; } else { Bool a = false; }"
        " return 0; } }",
        "Bool y",
        "Query",
        "a",
        "binds that name more than once",
    ),
    "name_is_field_and_local": (
        "Game G() { Bool f; Int Query(Int x) {"
        " Bool f = true; Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "both a local and a game field",
    ),
    "name_is_field_and_method_parameter": (
        "Game G() { Bool f; Int Query(Bool f) { Bool y = f; return 0; } }",
        "Bool y",
        "Query",
        "f",
        "both a local and a game field",
    ),
    "name_is_game_parameter_and_local": (
        "Game G(Int q) { Int Query(Int x) { Int q = x; Int y = q; return 0; } }",
        "Int y",
        "Query",
        "q",
        "both a local and a game field or parameter",
    ),
    "name_is_field_and_game_parameter": (
        "Game G(Int q) { Int q; Int Query(Int x) { Int y = q; return 0; } }",
        "Int y",
        "Query",
        "q",
        "both a game field and a game parameter",
    ),
    "local_bound_in_sibling_branch": (
        "Game G() { Int Query(Int x, Bool c) {"
        " if (c) { Bool a = true; } Bool y = a; return 0; } }",
        "Bool y",
        "Query",
        "a",
        "not in scope",
    ),
    "local_declared_after_the_read": (
        "Game G() { Int Query(Int x) { Bool y = a; Bool a = true; return 0; } }",
        "Bool y",
        "Query",
        "a",
        "not in scope",
    ),
    "local_read_in_its_own_declaration": (
        "Game G() { Int Query(Int x) { Bool y = y; return 0; } }",
        "Bool y",
        "Query",
        "y",
        "not in scope",
    ),
    "loop_binder_after_its_loop": (
        "Game G() { Int Query(Int x) {"
        " for (Int i = 0 to 3) { x = x + i; } Int y = i; return 0; } }",
        "Int y",
        "Query",
        "i",
        "not in scope",
    ),
    "loop_binder_shadowing_field": (
        "Game G() { Int f; Int Query(Int x) {"
        " for (Int f = 0 to 3) { x = x + f; } Int y = f; return 0; } }",
        "Int y",
        "Query",
        "f",
        "both a local and a game field",
    ),
    "unknown_name": (
        "Game G() { Int Query(Int x) { Int y = z; return 0; } }",
        "Int y",
        "Query",
        "z",
        "not a parameter, local, field or let name",
    ),
}


@pytest.mark.parametrize("name", sorted(_DECLINES))
def test_possibly_unassigned_reads(name: str) -> None:
    source, statement, method, variable, fragment = _DECLINES[name]
    reads = _reads_at(source, statement, method)
    assert _names(reads) == [variable]
    assert fragment in reads[0][1]


def test_let_name_shadowed_by_unassigned_field() -> None:
    reads = _reads_at(
        "Game G() { Int lambda; Int Query(Int x) { Int y = lambda; return 0; } }",
        "Int y",
        let_names=("lambda",),
    )
    assert _names(reads) == ["lambda"]


def test_every_offending_occurrence_is_reported() -> None:
    """Nested expressions are searched, and assigned reads are left out."""
    reads = _reads_at(
        "Game G() { Bool f; Bool g; Void Store(Bool v) { f = v; g = v; }"
        " Bool Query(Int x) { return [[x, {f}], !g] == None; } }",
        "return",
    )
    assert sorted(_names(reads)) == ["f", "g"]


def test_read_outside_a_method() -> None:
    game = frog_parser.parse_game("Game G(Int q) { Int Query(Int x) { return x; } }")
    scope = GameDefinedness(game, _ctx()).for_method(None)
    assert scope.method_name is None
    reads = scope.unassigned_reads(frog_parser.parse_expression("q + 1"))
    assert reads == [("q", "it is read outside a method")]


def test_method_without_a_game() -> None:
    """Parameters and locals still resolve; nothing is a field."""
    method = frog_parser.parse_method("""
        Int f(Int a) {
            Int b = a;
            return a + b + c;
        }
        """)
    statement = method.block.statements[1]
    assert isinstance(statement, frog_ast.ReturnStatement)
    scope = GameDefinedness(None).at_statement(method, statement)
    assert scope is not None
    assert _names(scope.unassigned_reads(statement.expression)) == ["c"]


# ---------------------------------------------------------------------------
# Scope tracking
# ---------------------------------------------------------------------------


def test_at_statement_returns_none_for_a_foreign_statement() -> None:
    game = frog_parser.parse_game("Game G() { Int Query(Int x) { return x; } }")
    other = frog_parser.parse_method("Int f(Int a) { return a; }")
    method = _method(game, "Query")
    foreign = other.block.statements[0]
    assert GameDefinedness(game).at_statement(method, foreign) is None


def test_at_statement_scope_excludes_the_statement_itself() -> None:
    """The scope is the one before the statement runs; declare() adds it."""
    game = frog_parser.parse_game(
        "Game G() { Int Query(Int x) { Int a = x; return a; } }"
    )
    method = _method(game, "Query")
    declaration = method.block.statements[0]
    scope = GameDefinedness(game).at_statement(method, declaration)
    assert scope is not None
    assert scope.unassigned_reason("a") == "its declaration is not in scope"
    scope.declare(declaration)
    assert scope.unassigned_reason("a") is None


def test_manual_walk_matches_at_statement() -> None:
    """A caller walking the method itself keeps the scope with enter/exit
    and declare, and sees the same answers as at_statement."""
    game = frog_parser.parse_game("""
        Game G() {
            Int Query(Int x, Bool c) {
                Int a = x;
                if (c) {
                    Int b = a;
                    x = b;
                }
                for (Int i = 0 to 3) {
                    x = x + i;
                }
                return x;
            }
        }
        """)
    method = _method(game, "Query")
    facts = GameDefinedness(game)
    scope = facts.for_method(method)
    seen: dict[str, list[Optional[str]]] = {}

    def walk(block: frog_ast.Block, scope: MethodDefinedness) -> None:
        scope.enter_block()
        for statement in block.statements:
            seen[str(statement).split("\n", maxsplit=1)[0]] = [
                scope.unassigned_reason(name) for name in ("a", "b", "i")
            ]
            if isinstance(statement, frog_ast.IfStatement):
                for inner in statement.blocks:
                    walk(inner, scope)
            elif isinstance(statement, frog_ast.NumericFor):
                scope.enter_loop(statement)
                walk(statement.block, scope)
                scope.exit_loop()
            scope.declare(statement)
        scope.exit_block()

    walk(method.block, scope)
    out = "its declaration is not in scope"
    assert seen["Int a = x;"] == [out, out, out]
    assert seen["Int b = a;"] == [None, out, out]
    assert seen["x = b;"] == [None, None, out]
    assert seen["x = x + i;"] == [None, out, None]
    assert seen["return x;"] == [None, out, out]

    for text, expected in seen.items():
        statement = _find(method.block, text)
        assert statement is not None
        at = facts.at_statement(method, statement)
        assert at is not None
        assert [at.unassigned_reason(n) for n in ("a", "b", "i")] == expected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_initialize_assigned_fields() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Bool a;
            Bool b;
            Bool c = true;
            Bool d;
            Map<Int, Bool> M;
            Bool Initialize() {
                a = false;
                M[0] = true;
                Bool d = true;
                d = false;
                Bool r <- Bool;
                if (r) { return true; }
                b = false;
                return false;
            }
        }
        """)
    assert initialize_assigned_fields(game) == {"a", "c"}
    assert GameDefinedness(game).initialize_assigned == {"a", "c"}


def test_method_binders() -> None:
    method = frog_parser.parse_method("""
        Int f(Int a, Bool c) {
            Int b = a;
            Bool d;
            if (c) {
                Int e <- Int;
            } else {
                Int e = 1;
            }
            for (Int i = 0 to 3) {
                b = b + i;
            }
            return b;
        }
        """)
    assert method_binder_counts(method) == {
        "a": 1,
        "c": 1,
        "b": 1,
        "d": 1,
        "e": 2,
        "i": 1,
    }
    assert bare_declared_names(method) == ["d"]
    assert initialized_binder(method.block.statements[0]) == "b"
    assert initialized_binder(method.block.statements[1]) is None
    assert initialized_binder(method.block.statements[-1]) is None
