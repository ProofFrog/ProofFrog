"""Unit tests for the field-cardinality survivor peel's applicability gate.

The peel emits one ``call``/``rnd`` step per backbone entry with nothing
between them, so it consumes one instruction per step from the end of both
programs. EasyCrypt's ``call`` requires the last instruction of each program to
be a procedure call, which makes the peel applicable exactly when every
executable statement from the first abstract call onward is itself a call or a
sample. A deterministic assignment sitting BETWEEN two calls makes the next
``call`` fail with "invalid last instruction" -- a tactic that runs but cannot
close -- so the gate declines instead.
"""

from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _coupled_field_renaming,
    _oracle_step_tactic,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
EMT = {"E": "E_c.Scheme"}
FLAT = [ec_ast.ModuleParam("E", "E_c.Scheme")]


def _var(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _game(name: str, extra_field: bool, interleaved: bool) -> frog_ast.Game:
    """A two-oracle game whose ``Challenge`` ends in two abstract calls.

    ``extra_field`` adds a second field so two such games differ in glob
    cardinality (the survivor-peel branch's trigger). ``interleaved`` puts a
    deterministic assignment between the two calls.
    """
    fields = [frog_ast.Field(BS, "k", None)] + (
        [frog_ast.Field(BS, "j", None)] if extra_field else []
    )
    init_stmts: list[frog_ast.Statement] = [
        frog_ast.Assignment(None, _var("k"), _call("E", "KeyGen"))
    ]
    if extra_field:
        init_stmts.append(frog_ast.Assignment(None, _var("j"), _call("E", "KeyGen")))
    init_stmts.append(frog_ast.ReturnStatement(_var("k")))
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block(init_stmts),
    )
    chal_stmts: list[frog_ast.Statement] = [
        frog_ast.Assignment(BS, _var("a"), _call("E", "Enc", _var("m")))
    ]
    mix_arg: frog_ast.Expression = _var("a")
    if interleaved:
        chal_stmts.append(frog_ast.Assignment(BS, _var("x"), _var("m")))
        mix_arg = _var("x")
    chal_stmts.append(frog_ast.Assignment(BS, _var("c"), _call("E", "Mix", mix_arg)))
    chal_stmts.append(frog_ast.ReturnStatement(_var("c")))
    chal = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", BS, [frog_ast.Parameter(BS, "m")]),
        frog_ast.Block(chal_stmts),
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


def _dispatch(interleaved: bool):
    return _oracle_step_tactic(
        _game("CB", False, interleaved),
        _game("CA", True, interleaved),
        "challenge",
        False,
        EMT,
        {},
        modules=mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory()),
        flat_params=FLAT,
        det_methods={},
        micro_pre_text="={m} /\\ ={glob E} /\\ CB.k{1} = CA.k{2}",
        left_ref="CB(E)",
        right_ref="CA(E)",
    )


def test_peel_fires_on_a_pure_call_tail() -> None:
    step = _dispatch(interleaved=False)
    assert step is not None
    tac, _reqs, rung = step
    assert tac == ["proc.", "call (_: true).", "call (_: true).", "auto."]
    assert rung == "synth-param"


def test_peel_declines_when_a_deterministic_assignment_splits_the_calls() -> None:
    # ``x <- m`` between ``E.Enc`` and ``E.Mix``: the second ``call`` would hit
    # an assignment, so the leg declines rather than emit a failing tactic.
    assert _dispatch(interleaved=True) is None


def test_coupling_classes_merge_same_side_survivor_equations() -> None:
    # The validated field-removal shape states the redundant-copy identity on
    # ONE side (``dk0 = challenger_dk0``) and pairs the surviving field across
    # sides. Both kinds of equation have to merge, or the body comparison sees
    # ``K.decaps(challenger_dk0, ct)`` against ``K.decaps(dk0, ct)`` as a real
    # difference and the peel declines on the very shape it was validated on.
    pre = (
        "={ct} /\\ S5.challenger_dk0{1} = S4.challenger_dk0{2} /\\ "
        "S4.dk0{2} = S4.challenger_dk0{2}"
    )
    classes = _coupled_field_renaming(pre, "S5", "S4")
    assert classes["dk0"] == classes["challenger_dk0"]


def test_coupling_classes_ignore_other_modules() -> None:
    # A conjunct naming a module that is not one of this lemma's two endpoints
    # says nothing about these two programs and must not merge their fields.
    pre = "Other.a{1} = Other.b{2}"
    assert _coupled_field_renaming(pre, "S5", "S4") == {}
