"""F-405: every variable an inlined body brings in has a fresh name.

The method inliner renamed only the typed locals a callee declares at the
top of its body, to ``obj.method@<name><index of the call's statement>``,
before it put the arguments in for the parameters. A local declared in a
nested block, a bare declaration ``T x;`` and a ``for`` binder kept their
names, so one named like a variable an argument reads captured it:
``if (c) { Bool b = false; return v; }`` with ``v := b`` returned the local.

The names were not fresh either. A call in a block nested inside an earlier
inlined body (the leaves of its ``if``) can sit at the same statement index,
with the earlier body's variables in scope, and got the same names for its
locals and for its parameter and return bindings, overwriting the earlier
ones: ``S.G(a, d) + S.G(b, d)`` returned ``b + b``.

Every binder of the callee's body is now renamed by scope, and every new
name (locals, parameter bindings, return bindings) is made fresh against
the names the caller and the callee mention (``base@fresh<k>`` on a clash).
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.alpha_rename import rename_block_binders_by_name
from proof_frog.visitors import InlineTransformer, SearchVisitor, mentioned_names

_SCHEME = """
Scheme S(Int n) extends P {
    Bool Nested(Bool v, Bool c) {
        if (c) {
            Bool b = false;
            return v;
        }
        return v;
    }

    Int Sum(Int v, Int k) {
        Int s = 0;
        for (Int i = 0 to k) {
            s = s + v;
        }
        return s;
    }

    Int Count(Int v, Set<Int> E) {
        Int s = 0;
        for (Int e in E) {
            s = s + v;
        }
        return s;
    }

    Bool Keep(Bool v) {
        Bool b;
        b = false;
        return v;
    }

    Int Guard(Int x, Bool d) {
        Int y = x;
        if (d) {
            return y;
        }
        return 0;
    }

    Int Bump(Int x, Bool d) {
        x = x + 1;
        if (d) {
            return x;
        }
        return 0;
    }

    ModInt<7> Reduce(Int x, Bool d) {
        if (d) {
            return x;
        }
        return 0;
    }

    Int Outer(Int v) {
        Int t = k;
        Int k = 5;
        return t + k + v;
    }

    Int Twice(Bool c) {
        Int r = 0;
        if (c) {
            Int u = 1;
            r = u;
        } else {
            Int u = 2;
            r = u;
        }
        return r;
    }

    BitString<n> Draw() {
        BitString<n> r <- BitString<n>;
        return r;
    }
}
"""


def _inline(caller_src: str, steps: int = 20) -> frog_ast.Game:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    game = frog_parser.parse_game(caller_src)
    for _ in range(steps):
        new_game = InlineTransformer(lookup).transform(game)
        if new_game == game:
            break
        game = new_game
    return game


def _declared_names(node: frog_ast.ASTNode) -> list[str]:
    """The names every binder in *node* declares, in order, repeats kept."""
    names: list[str] = []

    def _collect(inner: frog_ast.ASTNode) -> bool:
        if isinstance(inner, frog_ast.VariableDeclaration):
            names.append(inner.name)
        elif isinstance(inner, frog_ast.NumericFor):
            names.append(inner.name)
        elif isinstance(inner, frog_ast.GenericFor):
            names.append(inner.var_name)
        elif (
            isinstance(
                inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
            )
            and inner.the_type is not None
            and isinstance(inner.var, frog_ast.Variable)
        ):
            names.append(inner.var.name)
        return False

    SearchVisitor(_collect).visit(node)
    return names


def _returns(node: frog_ast.ASTNode) -> list[str]:
    """The printed expression of every ``return`` in *node*, in order."""
    found: list[str] = []

    def _collect(inner: frog_ast.ASTNode) -> bool:
        if isinstance(inner, frog_ast.ReturnStatement):
            found.append(str(inner.expression))
        return False

    SearchVisitor(_collect).visit(node)
    return found


# ---------------------------------------------------------------------------
# Every binder of the callee's body is renamed
# ---------------------------------------------------------------------------


def test_f405_nested_local_does_not_capture_argument() -> None:
    """The attack's shape: a local in a branch named like the argument."""
    method = _inline(
        "Game T(Int n) { Bool O(Bool b, Bool c) { return S.Nested(b, c); } }"
    ).get_method("O")
    assert "b" not in _declared_names(method)
    assert _returns(method) == ["b", "b"]


def test_f405_numeric_for_binder_does_not_capture_argument() -> None:
    method = _inline(
        "Game T(Int n) { Int O(Int i, Int k) { return S.Sum(i, k); } }"
    ).get_method("O")
    loop = method.block.statements[1]
    assert isinstance(loop, frog_ast.NumericFor)
    assert loop.name != "i"
    assert str(loop.block.statements[0]) == "S.Sum@s0 = S.Sum@s0 + i;"


def test_f405_generic_for_binder_does_not_capture_argument() -> None:
    method = _inline(
        "Game T(Int n) { Int O(Int e, Set<Int> E) { return S.Count(e, E); } }"
    ).get_method("O")
    loop = method.block.statements[1]
    assert isinstance(loop, frog_ast.GenericFor)
    assert loop.var_name != "e"
    assert str(loop.block.statements[0]) == "S.Count@s0 = S.Count@s0 + e;"


def test_f405_bare_declaration_does_not_capture_argument() -> None:
    """A bare declaration was not renamed even at the top of the body."""
    method = _inline(
        "Game T(Int n) { Bool O(Bool b) { return S.Keep(b); } }"
    ).get_method("O")
    assert _declared_names(method) == ["S.Keep@b0"]
    assert _returns(method) == ["b"]


def test_f405_read_before_same_named_local_keeps_outer_name() -> None:
    """Renaming follows scope: a read of `k` before the local `k` is
    declared reads the outer `k`, and keeps reading it."""
    method = _inline(
        "Game T(Int n) { Int O(Int v) { return S.Outer(v); } }"
    ).get_method("O")
    assert [str(s) for s in method.block.statements] == [
        "Int S.Outer@t0 = k;",
        "Int S.Outer@k0 = 5;",
        "return S.Outer@t0 + S.Outer@k0 + v;",
    ]


def test_f405_two_declarations_of_one_name_get_two_names() -> None:
    method = _inline(
        "Game T(Int n) { Int O(Bool c) { return S.Twice(c); } }"
    ).get_method("O")
    assert _declared_names(method) == [
        "S.Twice@r0",
        "S.Twice@u0",
        "S.Twice@u0@fresh1",
    ]
    branches = method.block.statements[1]
    assert isinstance(branches, frog_ast.IfStatement)
    assert str(branches.blocks[0].statements[1]) == "S.Twice@r0 = S.Twice@u0;"
    assert str(branches.blocks[1].statements[1]) == "S.Twice@r0 = S.Twice@u0@fresh1;"


def test_f405_unclashing_names_are_unchanged() -> None:
    """Without a clash a local keeps the name `obj.method@<name><index>`."""
    method = _inline(
        "Game T(Int n) { BitString<n> O() { return S.Draw(); } }"
    ).get_method("O")
    assert _declared_names(method) == ["S.Draw@r0"]


# ---------------------------------------------------------------------------
# New names are fresh against the caller: a call in a block nested in an
# earlier inlined body sits at the same statement index
# ---------------------------------------------------------------------------


def test_f405_nested_call_at_same_index_gets_fresh_local() -> None:
    method = _inline(
        "Game T(Int n) { Int O(Int a, Int b, Bool d) "
        "{ return S.Guard(a, d) + S.Guard(b, d); } }"
    ).get_method("O")
    declared = _declared_names(method)
    assert len(declared) == len(set(declared)), declared
    assert "return S.Guard@y0 + S.Guard@y0@fresh1;" in str(method)


def test_f405_nested_call_at_same_index_gets_fresh_parameter_binding() -> None:
    """`Bump` writes its parameter, so the inliner binds it."""
    method = _inline(
        "Game T(Int n) { Int O(Int a, Int b, Bool d) "
        "{ return S.Bump(a, d) + S.Bump(b, d); } }"
    ).get_method("O")
    declared = _declared_names(method)
    assert len(declared) == len(set(declared)), declared
    assert "Int S.Bump@x0 = a;" in str(method)
    assert "Int S.Bump@x0@fresh1 = b;" in str(method)
    assert "return S.Bump@x0 + S.Bump@x0@fresh1;" in str(method)


def test_f405_nested_call_at_same_index_gets_fresh_return_binding() -> None:
    """`Reduce` returns a ModInt, so the inliner binds each returned value."""
    method = _inline(
        "Game T(Int n) { ModInt<7> O(Int a, Int b, Bool d) "
        "{ Bool e = d; return S.Reduce(a, e) + S.Reduce(b, e); } }"
    ).get_method("O")
    declared = _declared_names(method)
    assert len(declared) == len(set(declared)), declared
    assert "return S.Reduce@return1_0 + S.Reduce@return1_0@fresh1;" in str(method)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_mentioned_names_covers_references_and_every_kind_of_binder() -> None:
    game = frog_parser.parse_game("""
        Game T(Int n) {
            Int f;
            Int O(Int p, Set<Int> E) {
                Int t;
                Int s = q;
                for (Int i = 0 to n) {
                    s = s + i;
                }
                for (Int e in E) {
                    t = e;
                }
                return s + t;
            }
        }
        """)
    assert mentioned_names(game) == {
        "n", "f", "p", "E", "t", "s", "q", "i", "e",
    }  # fmt: skip


def test_rename_block_binders_by_name_passes_each_binders_name() -> None:
    block = frog_parser.parse_method("""
        Int O(Int v) {
            Int x = y;
            if (v == 0) {
                Int x = 1;
                Int y = x;
                return y;
            }
            for (Int i = 0 to v) {
                x = x + i;
            }
            return x;
        }
        """).block
    asked: list[str] = []

    def fresh(name: str) -> str:
        asked.append(name)
        return f"{name}'{len(asked)}"

    renamed = rename_block_binders_by_name(block, fresh)
    assert asked == ["x", "x", "y", "i"]
    assert [str(s) for s in renamed.statements[:1]] == ["Int x'1 = y;"]
    inner = renamed.statements[1]
    assert isinstance(inner, frog_ast.IfStatement)
    assert [str(s) for s in inner.blocks[0].statements] == [
        "Int x'2 = 1;",
        "Int y'3 = x'2;",
        "return y'3;",
    ]
    assert str(renamed.statements[3]) == "return x'1;"
