"""Unit tests for Move 6's ISUV calls-alignment row.

The row (``_isuv_align_step``) fires when an inlining step (``Inline
Single-Use Variables`` / ``Extract Repeated Tuple Access``) left the two
sides differing in statement COUNT *and* freed two independent calls of
different declared modules to swap. Measured as the second blocker layer
of the route-retirement shadow run: 160 of the 179 remaining chain deaths
once the rendered-identity row cleared the width class.

Tactic shape is pinned by the probe (``.ec-tmp/move6/isuv_coupling_probe.ec``
-- the walker under a field-wise micro coupling, both controls proof-level)
and the synthesizer-generated template
(``tests/integration/ec_templates/isuv_align_walk.ec``).
"""

from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _isuv_align_step,
    _project_to_method,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lam"))
EMT = {"K": "K_c.Scheme", "N": "N_c.Scheme"}
FLAT = [ec_ast.ModuleParam("K", "K_c.Scheme"), ec_ast.ModuleParam("N", "N_c.Scheme")]


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _game(name: str, inlined: bool, ess_first: bool = False) -> frog_ast.Game:
    """``inlined``: the single-use projection local is gone (count differs).
    ``ess_first``: ``K.Ess`` sits BEFORE the two ``N`` calls -- the reorder
    the inlining exposed. The measured pair is
    ``before(inlined=False, ess_first=False)`` vs
    ``after(inlined=True, ess_first=True)``."""
    fields = [frog_ast.Field(BS, "dk0", None), frog_ast.Field(BS, "ek0", None)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("dk0"))]),
    )
    ret = frog_ast.ReturnStatement(
        frog_ast.BinaryOperation(frog_ast.BinaryOperators.EQUALS, _var("u"), _var("t"))
    )
    key: frog_ast.Expression = _var("dk0") if inlined else _var("d")
    decaps = frog_ast.Assignment(BS, _var("s"), _call("K", "Decaps", key, _var("ct0")))
    ess = frog_ast.Assignment(BS, _var("u"), _call("K", "Ess", _var("s")))
    exp = frog_ast.Assignment(BS, _var("x"), _call("N", "Exp", _var("e0"), key))
    ets = frog_ast.Assignment(BS, _var("t"), _call("N", "Ets", _var("x")))
    stmts: list[frog_ast.Statement] = []
    if not inlined:
        stmts.append(frog_ast.Assignment(BS, _var("d"), _var("dk0")))
    stmts += [decaps, ess, exp, ets] if ess_first else [decaps, exp, ets, ess]
    stmts.append(ret)
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge",
            frog_ast.BoolType(),
            [frog_ast.Parameter(BS, "ct0"), frog_ast.Parameter(BS, "e0")],
        ),
        frog_ast.Block(stmts),
    )
    return frog_ast.Game((name, [], fields, [init, chal]))


def _factory() -> Callable[..., Callable[[frog_ast.Expression], frog_ast.Type]]:
    def factory(
        _local: dict[str, frog_ast.Type], _mpt: dict[str, str]
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable):
                return BS
            raise KeyError(e)

        return type_of

    return factory


def _row(gb: frog_ast.Game, ga: frog_ast.Game, reversed_dir: bool = False):
    modules = mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())
    pb = _project_to_method(gb, "challenge")
    pa = _project_to_method(ga, "challenge")
    assert pb is not None and pa is not None
    return _isuv_align_step(pb, pa, reversed_dir, EMT, {}, modules, FLAT)


def _template_proof_body() -> list[str]:
    text = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "isuv_align_walk.ec"
    ).read_text()
    proof_body = text.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [ln.strip() for ln in proof_body.strip().splitlines()]


def test_fires_and_locksteps_with_template() -> None:
    step = _row(
        _game("IV_L", inlined=False), _game("IV_R", inlined=True, ess_first=True)
    )
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs == type(reqs)()  # call (_: true) needs no axiom
    assert tac == _template_proof_body()


def test_emits_swap_on_side_two_and_auto_closer() -> None:
    """The alignment must target side 2 (the emitted right module), and the
    closer must be ``auto => /#`` -- ``skip`` fails on a body whose leading
    deterministic run the peel leaves behind."""
    step = _row(
        _game("IV_L", inlined=False), _game("IV_R", inlined=True, ess_first=True)
    )
    assert step is not None
    tac = step[0]
    assert any(t.startswith("swap{2}") for t in tac)
    assert not any(t.startswith("swap{1}") for t in tac)
    assert tac[-1] == "auto => /#."


def test_reversed_direction_still_aligns_side_two() -> None:
    """In the reversed (right-chain) direction side 1 is the AFTER state, so
    the row must align the other body -- never emit a side-1 swap."""
    step = _row(
        _game("IV_L", inlined=False),
        _game("IV_R", inlined=True, ess_first=True),
        reversed_dir=True,
    )
    assert step is not None
    tac = step[0]
    assert any(t.startswith("swap{2}") for t in tac)
    assert not any(t.startswith("swap{1}") for t in tac)


def test_declines_when_calls_already_aligned() -> None:
    """No reorder to recover: an already-aligned pair belongs to another
    row, and firing here would mask it."""
    assert _row(_game("IV_L", inlined=False), _game("IV_R", inlined=True)) is None


def test_declines_when_callees_do_not_match() -> None:
    """A dropped call is not a permutation -- decline rather than guess."""
    ga = _game("IV_R", inlined=True, ess_first=True)
    del ga.methods[1].block.statements[1]  # drop the K.Ess call
    assert _row(_game("IV_L", inlined=False), ga) is None
