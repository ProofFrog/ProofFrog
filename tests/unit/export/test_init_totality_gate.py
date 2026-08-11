"""Unit tests for the Initialize-leg totality gate.

An init leg's precondition is ``true`` -- there is no incoming state to
relate -- while its postcondition asserts the state coupling. That is
provable exactly when the two ``Initialize`` bodies DETERMINE the coupled
state between them, so every field has to be written. A field ``Initialize``
never writes (the lazy random-oracle table) holds an arbitrary value that
nothing relates across the two memories, and EasyCrypt answers *cannot save
an incomplete proof* -- measured on `CG_expanded_INDCCA_T`
`micro_8_initialize_left_0`.
"""

from __future__ import annotations

from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _init_determines_whole_state,
    _oracle_step_tactic,
    _project_to_method,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _game(name: str, write_all: bool) -> frog_ast.Game:
    """``write_all``: Initialize writes both fields; otherwise it leaves the
    second one (think: a lazily-filled random-oracle table) untouched."""
    fields = [frog_ast.Field(BS, "k", None), frog_ast.Field(BS, "tbl", None)]
    stmts: list[frog_ast.Statement] = [
        frog_ast.Sample(BS, _var("k"), frog_ast.Variable("dbs")),
    ]
    if write_all:
        stmts.append(frog_ast.Sample(BS, _var("tbl"), frog_ast.Variable("dbs")))
    stmts.append(frog_ast.ReturnStatement(_var("k")))
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []), frog_ast.Block(stmts)
    )
    return frog_ast.Game((name, [], fields, [init]))


def _factory() -> Callable[..., Callable[[frog_ast.Expression], frog_ast.Type]]:
    def factory(_local, _mpt):  # type: ignore[no-untyped-def]
        def type_of(_e: frog_ast.Expression) -> frog_ast.Type:
            return BS

        return type_of

    return factory


def _modules() -> mt.ModuleTranslator:
    return mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())


def test_total_initialize_passes_the_gate() -> None:
    proj = _project_to_method(_game("G", write_all=True), "initialize")
    assert proj is not None
    assert _init_determines_whole_state(proj, _modules(), {}, {}, [], False)


def test_initialize_leaving_a_field_unwritten_fails_the_gate() -> None:
    proj = _project_to_method(_game("G", write_all=False), "initialize")
    assert proj is not None
    assert not _init_determines_whole_state(proj, _modules(), {}, {}, [], False)


def test_dispatch_declines_an_init_leg_that_cannot_determine_the_state() -> None:
    """The gate is on the DISPATCH, so no route gets the chance to emit a
    tactic for a leg whose coupling is underivable."""
    assert (
        _oracle_step_tactic(
            _game("GB", write_all=False),
            _game("GA", write_all=False),
            "initialize",
            False,
            {},
            {},
            modules=_modules(),
            flat_params=[],
            det_methods={},
            micro_pre_text="true",
            is_init=True,
        )
        is None
    )


def test_a_non_init_leg_is_not_subject_to_the_gate() -> None:
    """The gate is keyed on ``is_init``, NOT on the precondition alone: a
    non-init leg can also carry a ``true`` precondition, and it has incoming
    state, so the reasoning does not apply to it. (An earlier version keyed
    on the precondition and wrongly declined such a leg -- caught by an
    existing multi-oracle test.)"""
    gb = _game("GB", write_all=False)
    ga = _game("GA", write_all=False)
    step = _oracle_step_tactic(
        gb,
        ga,
        "initialize",
        False,
        {},
        {},
        modules=_modules(),
        flat_params=[],
        det_methods={},
        micro_pre_text="true",
        is_init=False,
    )
    # Identical bodies under a real precondition: the equal-body route closes
    # it, so the gate did not swallow a leg it should not have.
    assert step is not None and step[0] == ["proc; sim."]
