"""Tests for the shared write/rebind-detection helper ``reassigns_or_rebinds``.

It backs the RC1 interference checks in many structural-substitution passes, so
its node-kind coverage must match its "node-kind-complete" docstring."""

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import reassigns_or_rebinds


def _block(body: str):
    return frog_parser.parse_method(body).block


def test_f196_bare_declaration_counts_as_rebind() -> None:
    """F-196: a no-initializer local re-declaration ``T x;`` shadows the name and
    must be reported as a rebind -- otherwise a scope-blind structural
    substitution could capture the inner binding."""
    block = _block(
        """
        Int O(Int y) {
            Int x;
            return y;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is True


def test_f196_unrelated_declaration_is_not_a_rebind() -> None:
    """Control: a declaration of a different name does not count."""
    block = _block(
        """
        Int O(Int y) {
            Int w;
            return y;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is False


def test_typed_initializer_declaration_still_counts() -> None:
    """A typed ``T x = e;`` is an Assignment and was already caught via the
    l-value path; confirm the F-196 change does not disturb that."""
    block = _block(
        """
        Int O(Int y) {
            Int x = y + 1;
            return x;
        }
        """
    )
    assert reassigns_or_rebinds({"x"}, block) is True


_DESTRUCTURING_GAME = """
Game G() {
    Bool f;
    Bool g;
    Void Initialize() {
        f = true;
        g = true;
    }
    Bool Flip() {
        f = false;
        [Bool, Bool] [f, g] = [true, true];
        return f;
    }
}

Game H() {
    Bool f;
    Void Initialize() {
        f = true;
    }
    Bool Flip() {
        return f;
    }
}

export as P;
"""


def _flip_statements() -> list:
    game = frog_parser.parse_game_file(_DESTRUCTURING_GAME, desugar=False).games[0]
    flip = next(m for m in game.methods if m.signature.name == "Flip")
    return list(flip.block.statements)


def test_f370c_destructuring_binding_counts_as_write() -> None:
    """F-370(c): a ``DestructuringBinding`` (kept by a ``desugar=False``
    parse) writes each name it lists, so a pass that forwards a value up to
    the first write must stop there."""
    binding = _flip_statements()[1]
    assert isinstance(binding, frog_ast.DestructuringBinding)
    assert reassigns_or_rebinds({"f"}, binding) is True
    assert reassigns_or_rebinds({"g"}, binding) is True


def test_f370c_destructuring_binding_of_other_names_is_not_a_write() -> None:
    """Control: a binding that lists neither name does not count."""
    binding = _flip_statements()[1]
    assert reassigns_or_rebinds({"h"}, binding) is False


def test_f370c_tuple_literal_lvalue_counts_as_write() -> None:
    """F-370(c): a write whose l-value is a tuple literal (``[f, g] = e;``,
    built by hand; no front end produces it) writes each element."""
    write = frog_ast.Assignment(
        None,
        frog_ast.Tuple([frog_ast.Variable("f"), frog_ast.Variable("g")]),
        frog_ast.Tuple([frog_ast.Boolean(True), frog_ast.Boolean(True)]),
    )
    assert reassigns_or_rebinds({"g"}, write) is True
    assert reassigns_or_rebinds({"h"}, write) is False
