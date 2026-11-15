"""Unit tests for FoldLiteralConditions."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.control_flow import (
    BranchEliminiationTransformer,
    FoldLiteralConditions,
    FoldLiteralConditionsTransformer,
)
from proof_frog.visitors import NameTypeMap


def _fold(source: str) -> str:
    expr = frog_parser.parse_expression(source)
    return str(FoldLiteralConditionsTransformer().transform(expr))


@pytest.mark.parametrize(
    "source,expected",
    [
        # Negation of a boolean literal.
        ("!false", "true"),
        ("!true", "false"),
        ("!(!(false))", "false"),
        # Relational comparison of integer literals.
        ("0 >= 1", "false"),
        ("1 >= 1", "true"),
        ("0 > 1", "false"),
        ("2 > 1", "true"),
        ("0 < 1", "true"),
        ("3 <= 2", "false"),
        # Equal integer literals.
        ("1 == 1", "true"),
        ("1 != 1", "false"),
        # Boolean literal equality.
        ("true == false", "false"),
        ("true != false", "true"),
        ("false == false", "true"),
        # None against syntactically non-None literals, both orders.
        ("None == [1, true, None]", "false"),
        ("[1, true, None] == None", "false"),
        ("None != [[1, None], [true, 0b1]]", "true"),
        ("None == {1, 2}", "false"),
        ("None == 0", "false"),
        ("None == true", "false"),
        ("None == 0b101", "false"),
        ("None == 0^8", "false"),
        ("1^8 != None", "true"),
        # Folds nest so an enclosing connective sees the literal.
        ("!(false) && 0 >= 1", "true && false"),
    ],
)
def test_folds(source: str, expected: str) -> None:
    assert _fold(source) == str(frog_parser.parse_expression(expected))


@pytest.mark.parametrize(
    "source",
    [
        # Non-literal operands are left alone.
        "!x",
        "x >= 1",
        "0 >= y",
        "b == true",
        # Distinct integer literals may be equal mod q in a ModInt slot.
        "0 == 1",
        "0 != 1",
        # None against a variable, call, or expression needs types.
        "None == v",
        "v != None",
        "None == F.f(x)",
        "None == x + y",
        "None == M[k]",
        # A literal whose evaluation makes a call or indexes stays.
        "None == [F.f(x), 1]",
        "None == [M[k], 1]",
        "None == [s[0 : 2], 1]",
        # A variable read outside any method cannot be shown assigned.
        "None == [1, x]",
        "None != [[1, x], [a, b]]",
        # Division inside the literal is not dropped.
        "None == [1 / 0, 1]",
        # None == None is ReflexiveComparison's job.
        "None == None",
    ],
)
def test_does_not_fold(source: str) -> None:
    assert _fold(source) == str(frog_parser.parse_expression(source))


def test_fold_then_branch_elimination() -> None:
    method = frog_parser.parse_method("""
        Int f(Int a) {
            if (None == [1, a]) {
                return 0;
            }
            if (!(false)) {
                a = a + 1;
            } else {
                if (0 >= 1) {
                    a = 5;
                } else {
                    a = 6;
                }
            }
            return a;
        }
        """)
    expected = frog_parser.parse_method("""
        Int f(Int a) {
            a = a + 1;
            return a;
        }
        """)
    result = FoldLiteralConditionsTransformer().transform(method)
    # BranchElimination rewrites one if-statement per call.
    for _ in range(3):
        result = BranchEliminiationTransformer().transform(result)
    assert result == expected


# ---------------------------------------------------------------------------
# Definedness: ``None == L`` folds only if every variable L reads is
# definitely assigned. Dropping a read of an unassigned variable would hide
# an event the adversary observes.
# ---------------------------------------------------------------------------


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


def _apply(source: str, let_names: tuple[str, ...] = ()) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return FoldLiteralConditions().apply(game, _ctx(let_names))


# Each entry would be distinguishable from its folded form by an adversary
# that reaches the comparison while the named variable is unassigned, or is
# a shape whose binding the guard cannot resolve.
_DECLINES = {
    # Query before Store reads f unassigned.
    "field_assigned_only_in_another_oracle": """
        Game G() {
            Bool f;
            Void Store(Bool v) { f = v; }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # A game with no Initialize assigns no field.
    "field_never_assigned": """
        Game G() {
            Bool f;
            Bool Query(Int x) { return [x, f] != None; }
        }
        """,
    # Query(0, false) reads y unassigned.
    "bare_declared_local": """
        Game G() {
            Bool Query(Int x, Bool c) {
                Bool y;
                if (c) { y = true; }
                return None == [x, y];
            }
        }
        """,
    # Assigned on every path, but the guard does not track assignments to a
    # bare declaration: it declines.
    "bare_declared_local_assigned_later": """
        Game G() {
            Bool Query(Int x) {
                Bool y;
                y = true;
                return None == [x, y];
            }
        }
        """,
    # Initialize returns before f = false when c holds.
    "field_assigned_after_possible_return": """
        Game G() {
            Bool f;
            Bool Initialize() {
                Bool c <- Bool;
                if (c) { return true; }
                f = false;
                return false;
            }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # f stays unassigned when c is false.
    "field_assigned_under_if": """
        Game G() {
            Bool f;
            Void Initialize() {
                Bool c <- Bool;
                if (c) { f = false; }
            }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # The loop may run zero times.
    "field_assigned_in_loop": """
        Game G(Int n) {
            Bool f;
            Void Initialize() {
                for (Int i = 0 to n) { f = false; }
            }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # An element write does not assign the field.
    "field_element_write": """
        Game G() {
            Map<Int, Bool> M;
            Void Initialize() { M[0] = true; }
            Bool Query(Int x) { return None == [x, M]; }
        }
        """,
    # Initialize assigns a local named f, not the field.
    "initialize_assigns_shadowing_local": """
        Game G() {
            Bool f;
            Void Initialize() {
                Bool f = true;
                f = false;
            }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # A bare local named f in Initialize also takes the assignment.
    "initialize_assigns_bare_shadowing_local": """
        Game G() {
            Bool f;
            Void Initialize() {
                Bool f;
                f = false;
            }
            Bool Query(Int x) { return None == [x, f]; }
        }
        """,
    # A name that is both a field and a local is ambiguous.
    "name_is_field_and_local": """
        Game G() {
            Bool f;
            Bool Query(Int x) {
                Bool f = true;
                return None == [x, f];
            }
        }
        """,
    # A name that is both a field and a method parameter is ambiguous.
    "name_is_field_and_parameter": """
        Game G() {
            Bool f;
            Bool Query(Bool f) { return None == [1, f]; }
        }
        """,
    # y is bound only inside the first branch.
    "local_bound_in_sibling_branch": """
        Game G() {
            Bool Query(Int x, Bool c) {
                if (c) {
                    Bool y = true;
                }
                return None == [x, y];
            }
        }
        """,
    # y is declared after the read.
    "local_declared_after_use": """
        Game G() {
            Bool Query(Int x) {
                Bool r = None == [x, y];
                Bool y = true;
                return r;
            }
        }
        """,
    # The declaration's own value is evaluated before y is bound.
    "local_read_in_its_own_declaration": """
        Game G() {
            Bool Query(Int x) {
                Bool y = None == [x, y];
                return y;
            }
        }
        """,
    # Bound twice: once with a value, once bare.
    "local_bound_twice": """
        Game G() {
            Bool Query(Int x, Bool c) {
                if (c) {
                    Bool y = true;
                    return None == [x, y];
                }
                Bool y;
                return None == [x, y];
            }
        }
        """,
    # Bound with a value in two sibling branches: the guard does not pick.
    "local_bound_in_two_branches": """
        Game G() {
            Bool Query(Int x, Bool c) {
                if (c) {
                    Bool y = true;
                    return None == [x, y];
                } else {
                    Bool y = false;
                    return None == [x, y];
                }
            }
        }
        """,
    # The loop binder shadows the field only inside the loop.
    "loop_binder_shadows_field": """
        Game G() {
            Int f;
            Int Query(Int x) {
                for (Int f = 0 to 3) {
                    if (None == [x, f]) { x = 0; }
                }
                if (None == [x, f]) { x = 1; }
                return x;
            }
        }
        """,
    # A loop binder is out of scope after its loop.
    "loop_binder_after_loop": """
        Game G() {
            Int Query(Int x) {
                for (Int i = 0 to 3) {
                    x = x + i;
                }
                if (None == [x, i]) { return 0; }
                return x;
            }
        }
        """,
    # A loop binder is not in scope in its own bound.
    "loop_binder_in_its_own_bound": """
        Game G() {
            Int Query(Int x, Set<Bool> S) {
                for (Bool e in S union {None == [e]}) {
                    x = x + 1;
                }
                return x;
            }
        }
        """,
    # Inside Initialize the guard does not track statement order for fields.
    "field_read_inside_initialize": """
        Game G() {
            Bool f;
            Bool g;
            Void Initialize() {
                g = None == [1, f];
                f = false;
            }
            Bool Query(Int x) { return g; }
        }
        """,
    # Nested tuples and sets are searched too.
    "unassigned_field_in_nested_literal": """
        Game G() {
            Bool f;
            Void Store(Bool v) { f = v; }
            Bool Query(Int x) { return None == [[1, {f}], x]; }
        }
        """,
    "unassigned_field_under_operator": """
        Game G() {
            Bool f;
            Void Store(Bool v) { f = v; }
            Bool Query(Int x) { return None == [x, !f]; }
        }
        """,
    # A name nothing in scope binds.
    "unknown_name": """
        Game G() {
            Bool Query(Int x) { return None == [x, z]; }
        }
        """,
    # A field initializer is evaluated outside any method.
    "field_initializer_expression": """
        Game G() {
            Bool f;
            Bool g = None == [f];
            Bool Query(Int x) { return g; }
        }
        """,
}


@pytest.mark.parametrize("name", sorted(_DECLINES))
def test_none_fold_declines_on_possibly_unassigned_read(name: str) -> None:
    game = frog_parser.parse_game(_DECLINES[name])
    assert FoldLiteralConditions().apply(game, _ctx()) == game


# name -> (method, expected method, fields and other methods)
_FIRES = {
    "method_parameters": (
        "Bool Query(Int x, Bool b) { return None == [x, [b, x + 1]]; }",
        "Bool Query(Int x, Bool b) { return false; }",
        "",
    ),
    "initialized_local": (
        "Bool Query(Int x) { Int y = x; return [x, y] != None; }",
        "Bool Query(Int x) { Int y = x; return true; }",
        "",
    ),
    "sampled_local": (
        "Bool Query(Int x) { Bool y <- Bool; return None == {y}; }",
        "Bool Query(Int x) { Bool y <- Bool; return false; }",
        "",
    ),
    "unique_sampled_local": (
        "Bool Query(Set<Bool> S) { Bool y <-uniq[S] Bool; return None == [y]; }",
        "Bool Query(Set<Bool> S) { Bool y <-uniq[S] Bool; return false; }",
        "",
    ),
    "local_from_enclosing_block": (
        "Bool Query(Int x, Bool c) { Int y = x;"
        " if (c) { return None == [y]; } return c; }",
        "Bool Query(Int x, Bool c) { Int y = x; if (c) { return false; } return c; }",
        "",
    ),
    "numeric_loop_binder": (
        "Int Query(Int x) { for (Int i = 0 to 3) {"
        " if (None == [i, x]) { x = 0; } } return x; }",
        "Int Query(Int x) { for (Int i = 0 to 3) { if (false) { x = 0; } } return x; }",
        "",
    ),
    "generic_loop_binder": (
        "Int Query(Set<Int> S) { Int n = 0; for (Int e in S) {"
        " if ([e] != None) { n = n + e; } } return n; }",
        "Int Query(Set<Int> S) { Int n = 0; for (Int e in S) {"
        " if (true) { n = n + e; } } return n; }",
        "",
    ),
    "field_assigned_in_initialize": (
        "Bool Query(Int x) { return None == [x, f]; }",
        "Bool Query(Int x) { return false; }",
        "Bool f; Void Initialize() { f = false; } Void Store(Bool v) { f = v; }",
    ),
    "field_sampled_in_initialize": (
        "Bool Query(Int x) { return None == [x, f]; }",
        "Bool Query(Int x) { return false; }",
        "Bool f; Void Initialize() { f <- Bool; }",
    ),
    "field_assigned_before_the_return": (
        "Bool Query(Int x) { return None == [x, f]; }",
        "Bool Query(Int x) { return false; }",
        "Bool f; Bool Initialize() { f = false; Bool c <- Bool;"
        " if (c) { return true; } return false; }",
    ),
    "field_with_initializer": (
        "Bool Query(Int x) { return None == [x, f]; }",
        "Bool Query(Int x) { return false; }",
        "Bool f = false;",
    ),
    "game_parameter": (
        "Bool Query(Int x) { return None == [x, q]; }",
        "Bool Query(Int x) { return false; }",
        "",
    ),
}


@pytest.mark.parametrize("name", sorted(_FIRES))
def test_none_fold_fires_on_definitely_assigned_reads(name: str) -> None:
    method, expected, prefix = _FIRES[name]
    result = _apply(f"Game G(Int q) {{ {prefix} {method} }}")
    assert result == frog_parser.parse_game(
        f"Game G(Int q) {{ {prefix} {expected} }}"
    )


def test_none_fold_fires_on_let_names() -> None:
    """A proof ``let:`` name, and a field access on one, is always assigned."""
    game = frog_parser.parse_game("""
        Game G() {
            Bool Query(Int x) { return None == [x, lambda, E.order]; }
        }
        """)
    ctx = _ctx(("lambda",))
    ctx.proof_namespace["E"] = None
    expected = frog_parser.parse_game("""
        Game G() {
            Bool Query(Int x) { return false; }
        }
        """)
    assert FoldLiteralConditions().apply(game, ctx) == expected
    # Without the let names nothing binds them.
    assert FoldLiteralConditions().apply(game, _ctx()) == game


def test_none_fold_let_name_shadowed_by_unassigned_field() -> None:
    """A field hides a same-named let name, and the field is unassigned."""
    game = frog_parser.parse_game("""
        Game G() {
            Int lambda;
            Bool Query(Int x) { return None == [x, lambda]; }
        }
        """)
    assert FoldLiteralConditions().apply(game, _ctx(("lambda",))) == game


def test_other_folds_do_not_need_definedness() -> None:
    """The other folds have only literal operands: they fire next to an
    unassigned read and leave that read in place."""
    result = _apply("""
        Game G() {
            Bool f;
            Bool Query(Int x) {
                if (!false && 1 >= 1 && true == true && 2 == 2) { return f; }
                return None == [f];
            }
        }
        """)
    expected = frog_parser.parse_game("""
        Game G() {
            Bool f;
            Bool Query(Int x) {
                if (true && true && true && true) { return f; }
                return None == [f];
            }
        }
        """)
    assert result == expected
