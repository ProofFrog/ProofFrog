"""The plain deterministic-plumbing peel (last row of the leg dispatch).

`_isuv_align_step` fires only when the leg also carries a call REORDER, on
the reasoning that "the calls already line up, so the canned ``sim`` route
closes it". For a plumbing leg that reasoning is false: the call sequence
lines up but the two bodies differ in their deterministic assignments -- a
repeated projection extracted to a ``__cse_*`` local, a redundant copy
removed, an operand order commuted -- and ``sim`` compares programs
syntactically, so it aligns the extra assignment against a call and gives up.
Those legs reached no route at all.

`wp` absorbs the deterministic runs and ``/#`` equates the substituted
expressions, so the ordinary backbone peel closes them. Tactic shape pinned
against the synthesizer-generated template
``tests/integration/ec_templates/plain_plumbing_peel.ec``, which EasyCrypt
compiles and whose falsified sibling it refuses.
"""

from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _plain_plumbing_peel_step,
    _project_to_method,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lam"))
EMT = {"K": "K_c.Scheme"}
FLAT = [ec_ast.ModuleParam("K", "K_c.Scheme")]


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _game(
    name: str,
    *,
    extracted: bool = False,
    swap_fields: bool = False,
    branch_call: bool = False,
    drop_call: bool = False,
    cross_args: bool = False,
    extra_sample: bool = False,
) -> frog_ast.Game:
    """``extracted``: the repeated ``ct0`` use is bound to a local first --
    the plumbing difference. ``swap_fields``: the two fields change roles,
    which the coupling cannot support. ``branch_call``: a call inside an
    ``if``, which a top-level peel cannot reach. ``drop_call``: one call
    fewer, which is a different route's business. ``cross_args``: the two
    ``K.Ess`` calls run in the opposite order. ``extra_sample``: a ``<$``
    that only one side has."""
    fields = [frog_ast.Field(BS, "dk0", None), frog_ast.Field(BS, "dk1", None)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var("dk0"))]),
    )
    first, second = ("dk1", "dk0") if swap_fields else ("dk0", "dk1")
    arg: frog_ast.Expression = _var("cse") if extracted else _var("ct0")
    stmts: list[frog_ast.Statement] = []
    if extracted:
        stmts.append(frog_ast.Assignment(BS, _var("cse"), _var("ct0")))
    if extra_sample:
        stmts.append(frog_ast.Sample(BS, _var("z"), BS))
    if cross_args:
        # Two calls on ONE callee whose crossed arguments are LOCALS, not
        # fields, so this pair is declined by the crossing gate alone and not
        # incidentally by the field-order gate -- the two must be told apart
        # or the test passes for the wrong reason.
        stmts.append(frog_ast.Assignment(BS, _var("p"), _var("ct0")))
        stmts.append(frog_ast.Assignment(BS, _var("q"), _var("ct1")))
        if extracted:
            stmts.append(frog_ast.Assignment(BS, _var("r"), _var("p")))
        lo, hi = (_var("q"), _var("p")) if extracted else (_var("p"), _var("q"))
        stmts.append(
            frog_ast.Assignment(BS, _var("s"), _call("K", "Ess", _var("dk0"), lo))
        )
        stmts.append(
            frog_ast.Assignment(BS, _var("u"), _call("K", "Ess", _var("dk0"), hi))
        )
    else:
        stmts.append(
            frog_ast.Assignment(BS, _var("s"), _call("K", "Decaps", _var(first), arg))
        )
        if not drop_call:
            stmts.append(
                frog_ast.Assignment(BS, _var("u"), _call("K", "Ess", _var(second), arg))
            )
    if branch_call:
        stmts.append(
            frog_ast.IfStatement(
                [
                    frog_ast.BinaryOperation(
                        frog_ast.BinaryOperators.EQUALS, _var("s"), _var("s")
                    )
                ],
                [
                    frog_ast.Block(
                        [
                            frog_ast.Assignment(
                                None, _var("s"), _call("K", "Ess", _var(first), arg)
                            )
                        ]
                    )
                ],
            )
        )
    ret = _var("s") if drop_call else _var("u")
    stmts.append(
        frog_ast.ReturnStatement(
            frog_ast.BinaryOperation(frog_ast.BinaryOperators.EQUALS, ret, _var("s"))
        )
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge",
            frog_ast.BoolType(),
            [frog_ast.Parameter(BS, "ct0"), frog_ast.Parameter(BS, "ct1")],
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


def _row(gb: frog_ast.Game, ga: frog_ast.Game):
    modules = mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())
    pb = _project_to_method(gb, "challenge")
    pa = _project_to_method(ga, "challenge")
    assert pb is not None and pa is not None
    return _plain_plumbing_peel_step(pb, pa, EMT, {}, modules, FLAT)


def _template_proof_body() -> list[str]:
    text = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plain_plumbing_peel.ec"
    ).read_text()
    proof_body = text.split("proof.\n", 1)[1].split("qed.", 1)[0]
    return [ln.strip() for ln in proof_body.strip().splitlines()]


def test_fires_and_locksteps_with_template() -> None:
    step = _row(_game("PP_L"), _game("PP_R", extracted=True))
    assert step is not None
    tac, reqs, rung = step
    assert rung == "synth-param"
    assert reqs == type(reqs)()  # call (_: true) needs no axiom
    assert tac == _template_proof_body()


def test_closer_is_auto_not_skip() -> None:
    """``_backbone_peel`` leaves the body's LEADING deterministic run to its
    caller, and a micro body starts with the flat state's field projections,
    so ``skip`` fails with "left instruction list is not empty"."""
    step = _row(_game("PP_L"), _game("PP_R", extracted=True))
    assert step is not None
    assert step[0][0] == "proc."
    assert step[0][-1] == "auto => /#."
    assert not any(t.startswith("swap") for t in step[0])


def test_declines_equal_bodies() -> None:
    """An equal pair is the rendered-identity row's, above this one."""
    assert _row(_game("PP_L"), _game("PP_R")) is None


def test_declines_a_field_permutation() -> None:
    """The micro precondition couples the two globs by NAME, so a leg that
    swaps two fields' roles is not provable from it however the plumbing
    lines up -- measured as a FALSE subgoal on
    ``CG_expanded_LEAK_BIND_K_PK`` before this gate existed."""
    assert _row(_game("PP_L"), _game("PP_R", extracted=True, swap_fields=True)) is None


def test_declines_a_branch_local_call() -> None:
    """A call under an ``if`` is invisible to a top-level peel and
    unreachable by its ``wp``: EasyCrypt answers *invalid last instruction*."""
    assert (
        _row(
            _game("PP_L", branch_call=True),
            _game("PP_R", extracted=True, branch_call=True),
        )
        is None
    )


def test_declines_a_differing_callee_sequence() -> None:
    """A dropped or reordered call is a deduplication or a reorder, which the
    swap and functional-twin routes own."""
    assert _row(_game("PP_L"), _game("PP_R", extracted=True, drop_call=True)) is None


def test_declines_a_same_callee_argument_crossing() -> None:
    """An identical callee sequence is exactly the shape a crossing hides in:
    the peel pairs the i-th call of each side, so two calls on one callee with
    swapped arguments make that pairing wrong. Measured on eleven binding
    cells whose two ciphertext branches run in opposite orders -- the goal
    demanded that the oracle's two input ciphertexts be equal."""
    left = _game("PP_L", cross_args=True)
    right = _game("PP_R", cross_args=True, extracted=True)
    assert _row(left, right) is None


def test_declines_a_one_sided_sample() -> None:
    """The peel is generated from one side's backbone and must fit the other:
    comparing only the CALLEES is not enough. Measured on `7_13_Forward`,
    whose leg adds a `<$` on one side only -- *invalid last instruction*."""
    assert _row(_game("PP_L"), _game("PP_R", extracted=True, extra_sample=True)) is None
