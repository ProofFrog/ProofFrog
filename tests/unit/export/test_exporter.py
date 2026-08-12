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


def test_concrete_function_value_types_keeps_concrete_lets() -> None:
    """A sampled random oracle declared in the proof's ``let`` block is keyed
    under both its raw and its EC-mangled name.

    Without it the exporter's ``type_of`` cannot type the bare application an
    inlined ``G.evaluate(x)`` reduces to, and the whole oracle body falls back
    to the ``return witness;`` stub -- which then makes the step's micro-lemma
    relate one stub to another and count as evidence for nothing.
    """
    fn = frog_ast.FunctionType(
        frog_ast.BitStringType(frog_ast.Variable("lambda")),
        frog_ast.BitStringType(frog_ast.Variable("n")),
    )
    lets = [frog_ast.Field(fn, "G_RO", None)]
    got = exporter._concrete_function_value_types(lets)
    assert got["G_RO"] is fn
    # The mangled spelling is present too (uppercase-initial names are
    # lowered for EC), and every key maps to the same type object.
    assert all(v is fn for v in got.values())
    assert len(got) >= 1


def test_concrete_function_value_types_skips_abstract_and_non_function() -> None:
    """A ``Function`` over the game's own formal type parameters is skipped.

    The theorem game declares the oracle as ``Function<D, R>`` over abstract
    ``Set D, Set R``. Keying that by the oracle's name would let the abstract
    range displace the concrete one from the proof's ``let``, trading one
    untranslatable body for another. Non-Function lets are skipped outright.
    """
    abstract = frog_ast.FunctionType(
        frog_ast.Variable("D"), frog_ast.Variable("R")
    )
    half_abstract = frog_ast.FunctionType(
        frog_ast.BitStringType(frog_ast.Variable("lambda")), frog_ast.Variable("R")
    )
    lets = [
        frog_ast.Field(abstract, "G_RO", None),
        frog_ast.Field(half_abstract, "H_RO", None),
        frog_ast.Field(frog_ast.BoolType(), "flag", None),
    ]
    assert exporter._concrete_function_value_types(lets) == {}
