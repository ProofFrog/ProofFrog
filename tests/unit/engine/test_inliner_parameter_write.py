"""F-373: a callee's write to its own parameter does not write the caller's
variable.

Arguments are passed by value: a method gets its own copy of every argument,
Map and Set included, so a write to the parameter, or to an element of it,
never changes the caller's variable. The inliner used to substitute a
call-free argument for the parameter, which turned the callee's
``x = 0^n;`` into the caller's ``y = 0^n;``. A parameter the callee writes
(assigns, samples into, writes an element of, inserts into with ``<-uniq``)
is now bound to a variable of the parameter's type before the body.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import InlineTransformer, lvalue_base_name

_SCHEME = """
Scheme S(Int n) extends P {
    BitString<n> Zero(BitString<n> x) {
        x = 0^n;
        return x;
    }

    BitString<n> Redraw(BitString<n> x) {
        x <- BitString<n>;
        return x;
    }

    Bool ClearAt(Map<BitString<n>, BitString<n>> X, BitString<n> k) {
        X[k] = 0^n;
        return true;
    }

    Bool Pick(Set<BitString<n>> U) {
        BitString<n> u <-uniq[U] BitString<n>;
        return true;
    }

    BitString<n> ZeroFirst([BitString<n>, BitString<n>] t) {
        t[0] = 0^n;
        return t[0];
    }

    BitString<n> ZeroIf(BitString<n> x, Bool b) {
        if (b) {
            x = 0^n;
        }
        return x;
    }

    BitString<n> ZeroFirstOfTwo(BitString<n> x, BitString<n> z) {
        x = 0^n;
        return x + z;
    }

    BitString<n> Copy(BitString<n> x) {
        BitString<n> c = x;
        c = c + x;
        return c;
    }
}
"""

_CHALLENGER = """
Game C(Int n) {
    BitString<n> Query(BitString<n> m) {
        m = 0^n;
        return m;
    }
}
"""


def _lookup() -> dict[tuple[str, str], frog_ast.Method]:
    scheme = frog_parser.parse_scheme_file(_SCHEME)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    challenger = frog_parser.parse_game(_CHALLENGER)
    lookup.update({("challenger", m.signature.name): m for m in challenger.methods})
    return lookup


def _inline(caller_src: str, steps: int = 10) -> frog_ast.Game:
    lookup = _lookup()
    game = frog_parser.parse_game(caller_src)
    for _ in range(steps):
        new_game = InlineTransformer(lookup).transform(game)
        if new_game == game:
            break
        game = new_game
    return game


def _written_names(method: frog_ast.Method) -> set[str]:
    """Base names of every assignment or sample target in *method*'s body
    (top level and inside ``if`` blocks)."""
    names: set[str] = set()

    def _visit(inner: frog_ast.ASTNode) -> None:
        if isinstance(
            inner, (frog_ast.Assignment, frog_ast.Sample, frog_ast.UniqueSample)
        ):
            base = lvalue_base_name(inner.var)
            assert base is not None, f"write to a non-variable target: {inner}"
            names.add(base)
        if isinstance(inner, frog_ast.IfStatement):
            for block in inner.blocks:
                for statement in block.statements:
                    _visit(statement)

    for statement in method.block.statements:
        _visit(statement)
    return names


@pytest.mark.parametrize(
    "caller, bound, caller_var",
    [
        (
            "Game T(Int n) { BitString<n> O(BitString<n> y) "
            "{ BitString<n> z = S.Zero(y); return y; } }",
            "BitString<n> S.Zero@x0 = y;",
            "y",
        ),
        (
            "Game T(Int n) { BitString<n> O(BitString<n> y) "
            "{ BitString<n> z = S.Redraw(y); return y; } }",
            "BitString<n> S.Redraw@x0 = y;",
            "y",
        ),
        (
            "Game T(Int n) { Map<BitString<n>, BitString<n>> M; "
            "BitString<n> O(BitString<n> k) "
            "{ Bool b = S.ClearAt(M, k); return M[k]; } }",
            "Map<BitString<n>, BitString<n>> S.ClearAt@X0 = M;",
            "M",
        ),
        (
            "Game T(Int n) { BitString<n> O([BitString<n>, BitString<n>] a) "
            "{ BitString<n> z = S.ZeroFirst(a); return a[0]; } }",
            "[BitString<n>, BitString<n>] S.ZeroFirst@t0 = a;",
            "a",
        ),
        (
            "Game T(Int n) { BitString<n> O(BitString<n> y, Bool b) "
            "{ BitString<n> z = S.ZeroIf(y, b); return y; } }",
            "BitString<n> S.ZeroIf@x0 = y;",
            "y",
        ),
    ],
    ids=["assign", "sample", "map_element", "tuple_element", "nested_write"],
)
def test_f373_written_parameter_is_bound(
    caller: str, bound: str, caller_var: str
) -> None:
    game = _inline(caller)
    method = game.methods[-1]
    assert bound in str(game)
    assert caller_var not in _written_names(method)


def test_f373_uniq_insertion_into_parameter_set_is_bound() -> None:
    """``u <-uniq[U] T`` adds ``u`` to ``U``; with ``U`` the callee's own
    copy, the caller's set is unchanged."""
    game = _inline(
        "Game T(Int n) { Set<BitString<n>> W; "
        "Int O() { Bool b = S.Pick(W); return |W|; } }"
    )
    text = str(game)
    assert "Set<BitString<n>> S.Pick@U0 = W;" in text
    draws = [
        s
        for s in game.get_method("O").block.statements
        if isinstance(s, frog_ast.UniqueSample)
    ]
    assert len(draws) == 1
    assert draws[0].unique_set == frog_ast.Variable("S.Pick@U0")


def test_f373_challenger_writing_its_parameter_is_bound() -> None:
    """A reduction's variable passed to a challenger oracle that assigns its
    parameter keeps its value."""
    game = _inline(
        "Game R(Int n) { BitString<n> O(BitString<n> y) "
        "{ BitString<n> z = challenger.Query(y); return y; } }"
    )
    method = game.get_method("O")
    assert "BitString<n> challenger.Query@m0 = y;" in str(game)
    assert "y" not in _written_names(method)
    final = method.block.statements[-1]
    assert isinstance(final, frog_ast.ReturnStatement)
    assert final.expression == frog_ast.Variable("y")


def test_f373_expression_argument_to_written_parameter_is_bound() -> None:
    """An argument without calls that is not a variable was substituted into
    the callee's write, leaving ``y + w = 0^n;``; it is now bound."""
    game = _inline(
        "Game T(Int n) { BitString<n> O(BitString<n> y, BitString<n> w) "
        "{ return S.Zero(y + w); } }"
    )
    method = game.get_method("O")
    assert "BitString<n> S.Zero@x0 = y + w;" in str(game)
    assert _written_names(method) == {"S.Zero@x0"}


def test_f373_only_the_written_parameter_is_bound() -> None:
    game = _inline(
        "Game T(Int n) { BitString<n> O(BitString<n> y, BitString<n> w) "
        "{ return S.ZeroFirstOfTwo(y, w); } }"
    )
    text = str(game)
    assert "BitString<n> S.ZeroFirstOfTwo@x0 = y;" in text
    assert "S.ZeroFirstOfTwo@z0" not in text
    assert "S.ZeroFirstOfTwo@x0 + w" in text


def test_f373_parameter_read_but_not_written_is_substituted() -> None:
    """A callee that copies its parameter into a local and writes the local
    leaves the parameter substituted."""
    game = _inline(
        "Game T(Int n) { BitString<n> O(BitString<n> y) { return S.Copy(y); } }"
    )
    text = str(game)
    assert "S.Copy@x0" not in text
    assert "BitString<n> S.Copy@c0 = y;" in text
    assert "y" not in _written_names(game.get_method("O"))
