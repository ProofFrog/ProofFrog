"""Unit tests for EC parametric tactic synthesizers."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt import parametric_tactics
from proof_frog.transforms._base import TransformApplication


def _game_one_method(method: frog_ast.Method) -> frog_ast.Game:
    return frog_ast.Game(("G", [], [], [method]))


def _eavesdrop(body: list[frog_ast.Statement]) -> frog_ast.Method:
    sig = frog_ast.MethodSignature(
        "enc",
        frog_ast.ModIntType(frog_ast.Variable("q")),
        [frog_ast.Parameter(frog_ast.ModIntType(frog_ast.Variable("q")), "m")],
    )
    return frog_ast.Method(sig, frog_ast.Block(body))


def _sample_k() -> frog_ast.Sample:
    mod = frog_ast.ModIntType(frog_ast.Variable("q"))
    return frog_ast.Sample(mod, frog_ast.Variable("k"), mod)


def _app(before_ret: frog_ast.Expression) -> TransformApplication:
    before = _game_one_method(
        _eavesdrop([_sample_k(), frog_ast.ReturnStatement(before_ret)])
    )
    after = _game_one_method(
        _eavesdrop([_sample_k(), frog_ast.ReturnStatement(frog_ast.Variable("k"))])
    )
    return TransformApplication(
        iteration=1,
        transform_name="Uniform ModInt Simplification",
        game_before=before,
        game_after=after,
    )


def test_modint_tactic_add_left() -> None:
    """``k + m -> k`` synthesizes an rnd over add_q/sub_q (add first)."""
    add = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.ADD,
        frog_ast.Variable("k"),
        frog_ast.Variable("m"),
    )
    tac = parametric_tactics.uniform_modint_tactic(_app(add))
    assert tac is not None
    body = "\n".join(tac)
    assert "rnd (fun z => add_q z m{2}) (fun z => sub_q z m{2})." in body
    assert "smt(add_q_sub sub_q_add add_q_comm dmodint_q_fu dmodint_q_full)." in body


def test_modint_tactic_sub_left() -> None:
    """``k - m -> k`` synthesizes an rnd with sub first, add as inverse."""
    sub = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.SUBTRACT,
        frog_ast.Variable("k"),
        frog_ast.Variable("m"),
    )
    tac = parametric_tactics.uniform_modint_tactic(_app(sub))
    assert tac is not None
    assert "rnd (fun z => sub_q z m{2}) (fun z => add_q z m{2})." in "\n".join(tac)


def test_modint_tactic_minus_uniform_bails() -> None:
    """``m - k -> k`` is not closeable from the preamble axioms; bail."""
    sub = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.SUBTRACT,
        frog_ast.Variable("m"),
        frog_ast.Variable("k"),
    )
    assert parametric_tactics.uniform_modint_tactic(_app(sub)) is None


def test_modint_tactic_non_additive_bails() -> None:
    """A non-additive change is not a ModInt simplification; bail."""
    mul = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.MULTIPLY,
        frog_ast.Variable("k"),
        frog_ast.Variable("m"),
    )
    assert parametric_tactics.uniform_modint_tactic(_app(mul)) is None
