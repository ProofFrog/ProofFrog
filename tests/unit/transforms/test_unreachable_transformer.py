import pytest
from proof_frog import frog_parser
from proof_frog.transforms.control_flow import RemoveUnreachableTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Statements after an unconditional top-level return are unreachable
        # and must be dropped (regression coverage for the flattened
        # `return a; return b;` shape the topological sort can emit).
        (
            """
            Int f(Int x) {
                Int y = x + 1;
                return y;
                return x;
            }
            """,
            """
            Int f(Int x) {
                Int y = x + 1;
                return y;
            }
            """,
        ),
        (
            """
            BitString<8> f() {
                BitString<8> a <- BitString<8>;
                return a;
                BitString<8> b <- BitString<8>;
                return b;
            }
            """,
            """
            BitString<8> f() {
                BitString<8> a <- BitString<8>;
                return a;
            }
            """,
        ),
        (
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                } else {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                } else {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b) {
                if (b) {
                    return 1;
                }
                if (!b) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                } else if (x <= 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                } else if (x <= 0) {
                    return 2;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x == 0) {
                    return 2;
                }
                if (x < 0) {
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x == 0) {
                    return 2;
                }
                if (x < 0) {
                    return 3;
                }
            }
            """,
        ),
        (
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x < 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x > 0) {
                    return 1;
                }
                if (x < 0) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Bool b, Bool c) {
                if (b) {
                    return 1;
                }
                b = c;
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool b, Bool c) {
                if (b) {
                    return 1;
                }
                b = c;
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Bool a, Bool b) {
                if (a) {
                    x = 1;
                } else if (b) {
                    return 1;
                }
                if (!a && !b) {
                    return 2;
                }
                if (a && !b) {
                    return 3;
                }
                if (a && b) {
                    return 4;
                }
                return 5;
            }
            """,
            """
            Int f(Int x, Bool a, Bool b) {
                if (a) {
                    x = 1;
                } else if (b) {
                    return 1;
                }
                if (!a && !b) {
                    return 2;
                }
                if (a && !b) {
                    return 3;
                }
                if (a && b) {
                    return 4;
                }
            }
            """,
        ),
        (
            """
            Int f(Bool a, Bool b) {
                if (b) {
                    return 1;
                }
                if (a) {
                    b = !b;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Bool a, Bool b) {
                if (b) {
                    return 1;
                }
                if (a) {
                    b = !b;
                }
                if (!b) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                if (!(x in S)) {
                    return 2;
                }
            }
            """,
        ),
        (
            # `challenger.g()` is a method call, which is non-deterministic
            # by default: two evaluations may differ, so `g() in S` and
            # `!(g() in S)` are NOT complementary and `return 3` is
            # reachable. The condition is untranslatable to a Z3 formula, so
            # the transform conservatively keeps every branch.
            """
            Int f(Int x, Set<Int> s) {
                if (challenger.g() in S) {
                    return 1;
                }
                if (!(challenger.g() in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (challenger.g() in S) {
                    return 1;
                }
                if (!(challenger.g() in S)) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                x = 2;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s) {
                if (x in S) {
                    return 1;
                }
                x = 2;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in S) {
                    return 1;
                }
                s = t;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in S) {
                    return 1;
                }
                s = t;
                if (!(x in S)) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        (
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in s && x in t) {
                    return 1;
                }
                if (!(x in s) && x in t) {
                    return 2;
                }
                if (x in s && !(x in t)) {
                    return 3;
                }
                if (!(x in s) && !(x in t)) {
                    return 4;
                }
                return 5;
            }
            """,
            """
            Int f(Int x, Set<Int> s, Set<Int> t) {
                if (x in s && x in t) {
                    return 1;
                }
                if (!(x in s) && x in t) {
                    return 2;
                }
                if (x in s && !(x in t)) {
                    return 3;
                }
                if (!(x in s) && !(x in t)) {
                    return 4;
                }
            }
            """,
        ),
        # Duplicate if-condition with return: second check is dead code
        (
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                if (x == 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                return 3;
            }
            """,
        ),
        # Duplicate if-condition with intervening statement
        (
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                Int y = x + 1;
                if (x == 0) {
                    return 2;
                }
                return y;
            }
            """,
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                Int y = x + 1;
                return y;
            }
            """,
        ),
        # Should NOT eliminate: variable reassigned between checks
        (
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                x = x + 1;
                if (x == 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x == 0) {
                    return 1;
                }
                x = x + 1;
                if (x == 0) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        # Should NOT eliminate: first if doesn't return
        (
            """
            Int f(Int x) {
                if (x == 0) {
                    x = 5;
                }
                if (x == 0) {
                    return 2;
                }
                return 3;
            }
            """,
            """
            Int f(Int x) {
                if (x == 0) {
                    x = 5;
                }
                if (x == 0) {
                    return 2;
                }
                return 3;
            }
            """,
        ),
        # Should NOT eliminate: no tuple guard present
        (
            """
            Int f([Int, Int] c, Int a, Int b) {
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    if (x == a) {
                        return 2;
                    }
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f([Int, Int] c, Int a, Int b) {
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    if (x == a) {
                        return 2;
                    }
                    return 3;
                }
                return 4;
            }
            """,
        ),
        # Should NOT eliminate: guard checks different tuple
        (
            """
            Int f([Int, Int] c, [Int, Int] d, Int a, Int b) {
                if (d == [a, b]) {
                    return 1;
                }
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    if (x == a) {
                        return 2;
                    }
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f([Int, Int] c, [Int, Int] d, Int a, Int b) {
                if (d == [a, b]) {
                    return 1;
                }
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    if (x == a) {
                        return 2;
                    }
                    return 3;
                }
                return 4;
            }
            """,
        ),
        # Tuple equality guard: nested branch on component is dead
        (
            """
            Int f([Int, Int] c, Int a, Int b) {
                if (c == [a, b]) {
                    return 1;
                }
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    if (x == a) {
                        return 2;
                    }
                    return 3;
                }
                return 4;
            }
            """,
            """
            Int f([Int, Int] c, Int a, Int b) {
                if (c == [a, b]) {
                    return 1;
                }
                Int x = c[0];
                Int y = c[1];
                if (y == b) {
                    return 3;
                }
                return 4;
            }
            """,
        ),
    ],
)
def test_unreachable_transformer(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    print("EXPECTED: ", expected_ast)
    transformed_ast = RemoveUnreachableTransformer(method_ast).transform(method_ast)
    print("TRANSFORMED: ", transformed_ast)
    assert expected_ast == transformed_ast


def _count_ifs(node) -> int:
    from proof_frog import frog_ast

    count = 0
    stack = [node]
    seen: set[int] = set()
    while stack:
        n = stack.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        if isinstance(n, frog_ast.IfStatement):
            count += 1
        if isinstance(n, frog_ast.ASTNode):
            for attr in vars(n).values():
                if isinstance(attr, frog_ast.ASTNode):
                    stack.append(attr)
                elif isinstance(attr, (list, tuple)):
                    stack.extend(a for a in attr if isinstance(a, frog_ast.ASTNode))
    return count


def test_remove_unreachable_nested_element_write_bumps_version() -> None:
    """RC1 / F-104: a nested element write `M[0][0] = 0` mutates `M[0][0]`,
    so the second `if (M[0][0] == 0)` is a fresh test, not a dead duplicate
    of the first.  A depth-1-only write scan left `M` looking unmodified and
    Case-B dedup wrongly deleted the reachable second if."""
    method = frog_parser.parse_method("""
        Int O(Map<Int, Map<Int, Int>> M) {
            if (M[0][0] == 0) { return 1; }
            M[0][0] = 0;
            if (M[0][0] == 0) { return 2; }
            return 3;
        }
        """)
    transformed = RemoveUnreachableTransformer(method).transform(method)
    assert (
        _count_ifs(transformed) == 2
    ), f"second if wrongly deleted after nested element write:\n{transformed}"


def test_remove_unreachable_unique_sample_bumps_version() -> None:
    """RC1: a `<-uniq` re-sample of a condition variable mutates it, so a
    later structurally identical condition is not a dead duplicate.  The
    write scan must recognise `UniqueSample.var` as a write."""
    method = frog_parser.parse_method("""
        Int O() {
            BitString<2> x <- BitString<2>;
            if (x == 0b00) { return 1; }
            x <-uniq[{x}] BitString<2>;
            if (x == 0b00) { return 2; }
            return 3;
        }
        """)
    transformed = RemoveUnreachableTransformer(method).transform(method)
    assert (
        _count_ifs(transformed) == 2
    ), f"second if wrongly deleted after <-uniq re-sample:\n{transformed}"


def test_remove_unreachable_modint_wraparound_not_deleted() -> None:
    """RC7 / F-106: Case C must NOT delete a live branch whose reachability
    depends on ModInt wraparound.  Here ``y <- ModInt<2>`` and ``x = y + 1``,
    so at ``y == 1`` we get ``x == 0`` (mod 2) and the branch fires (w.p. 1/2).
    Modelling ModInt as unbounded z3.Int made ``x == y + 1`` imply ``x != 0``
    when ``y == 1`` (2 != 0 over the integers), falsely proving the branch
    unsat.  Modelling ModInt as an opaque const blocks the arithmetic, so the
    branch survives."""
    method = frog_parser.parse_method("""
        Int O() {
            ModInt<2> y <- ModInt<2>;
            ModInt<2> x = y + 1;
            if (x == 0 && y == 1) { return 0; }
            return 1;
        }
        """)
    transformed = RemoveUnreachableTransformer(method).transform(method)
    assert (
        _count_ifs(transformed) == 1
    ), f"live ModInt wraparound branch wrongly deleted:\n{transformed}"


def test_remove_unreachable_still_dedups_genuine_duplicate() -> None:
    """Positive control: with NO intervening write, two identical
    conditions are genuinely redundant and the second must still be
    removed (the version-tracking fix must not over-preserve)."""
    method = frog_parser.parse_method("""
        Int O(Int x) {
            if (x == 0) { return 1; }
            if (x == 0) { return 2; }
            return 3;
        }
        """)
    transformed = RemoveUnreachableTransformer(method).transform(method)
    assert (
        _count_ifs(transformed) == 1
    ), f"genuinely dead duplicate if was not removed:\n{transformed}"


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-107): Case B dedups structurally-equal
# return-conditions; a non-deterministic condition re-evaluates independently,
# so a later structurally-identical one is NOT subsumed and must survive.
# ---------------------------------------------------------------------------

from proof_frog.transforms.control_flow import RemoveUnreachable
from proof_frog.transforms._base import PipelineContext as _PipelineContext
from proof_frog.visitors import NameTypeMap as _NameTypeMap


def _ru_ctx(**namespace):
    return _PipelineContext(
        variables={},
        proof_let_types=_NameTypeMap(),
        proof_namespace=dict(namespace),
        subsets_pairs=[],
    )


def _ru_nondet_prim():
    return frog_parser.parse_primitive_file("Primitive P(Int n) { Bool f(Int x); }")


def _ru_det_prim():
    return frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic Bool f(Int x); }"
    )


def test_ru_keeps_nondeterministic_duplicate_condition() -> None:
    """Two ``if (F.f(x)) { return ...; }`` with a non-deterministic condition:
    the second is an independent re-evaluation, so it must NOT be deduped."""
    game = frog_parser.parse_game("""
        Game G(P F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                if (F.f(x)) {
                    return 2;
                }
                return 3;
            }
        }
        """)
    ctx = _ru_ctx(P=_ru_nondet_prim(), F=_ru_nondet_prim())
    result = RemoveUnreachable().apply(game, ctx)
    assert result == game  # second if survives
    assert any(
        nm.transform_name == "Remove unreachable blocks of code"
        for nm in ctx.near_misses
    )


def test_ru_dedups_deterministic_duplicate_condition() -> None:
    """Control: with a deterministic condition ``D.f(x)`` the second
    structurally-identical if is dead (subsumed by the first) and is
    removed."""
    game = frog_parser.parse_game("""
        Game G(D F, Int n) {
            Int O(Int x) {
                if (F.f(x)) {
                    return 1;
                }
                if (F.f(x)) {
                    return 2;
                }
                return 3;
            }
        }
        """)
    ctx = _ru_ctx(D=_ru_det_prim(), F=_ru_det_prim())
    result = RemoveUnreachable().apply(game, ctx)
    assert result != game  # the dead duplicate if was removed
