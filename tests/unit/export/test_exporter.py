"""Unit tests for pure helpers in the EasyCrypt exporter top level."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt import exporter


def _concrete_step(game: str, side: str, reduction: str | None) -> frog_ast.Step:
    challenger = frog_ast.ConcreteGame(
        frog_ast.ParameterizedGame(game, [frog_ast.Variable("K")]), side
    )
    red = (
        frog_ast.ParameterizedGame(reduction, [frog_ast.Variable("K")])
        if reduction is not None
        else None
    )
    return frog_ast.Step(
        challenger=challenger,
        reduction=red,
        adversary=frog_ast.ParameterizedGame("Outer", [frog_ast.Variable("KF")]),
    )


def _intermediate_step(game: str) -> frog_ast.Step:
    return frog_ast.Step(
        challenger=frog_ast.ParameterizedGame(
            game, [frog_ast.Variable("K"), frog_ast.Variable("F")]
        ),
        reduction=None,
        adversary=frog_ast.ParameterizedGame("Outer", [frog_ast.Variable("KF")]),
    )


def test_wrapper_game_file_plain_step_uses_own_game_file() -> None:
    step = _concrete_step("KEM_INDCPA_MultiChal", "Real", reduction=None)
    assert exporter._wrapper_game_file_for(step, "Outer") == "KEM_INDCPA_MultiChal"


def test_wrapper_game_file_composed_step_uses_outer() -> None:
    step = _concrete_step("KEM_INDCPA_MultiChal", "Random", reduction="R_KEM")
    assert exporter._wrapper_game_file_for(step, "Outer") == "Outer"


def test_wrapper_game_file_intermediate_game_uses_outer() -> None:
    step = _intermediate_step("G_RandKey")
    assert exporter._wrapper_game_file_for(step, "Outer") == "Outer"


def test_safe_ec_op_ident_escapes_reserved_keyword() -> None:
    # ``in`` is an EasyCrypt keyword; a let named ``in`` must not emit
    # ``op in : int.`` (a parse error).
    assert exporter._safe_ec_op_ident("in") == "in_"
    assert exporter._safe_ec_op_ident("var") == "var_"


def test_safe_ec_op_ident_passes_through_non_keywords() -> None:
    assert exporter._safe_ec_op_ident("lambda") == "lambda"
    assert exporter._safe_ec_op_ident("out") == "out"
    assert exporter._safe_ec_op_ident("n") == "n"
