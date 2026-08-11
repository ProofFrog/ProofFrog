"""An evidence-only lemma whose whole-glob precondition does not TYPECHECK.

`_micro_pre_well_typed` is what makes evidence-only emission strictly
additive: a chain the oracle never takes can carry a coupling EasyCrypt
rejects, and one such lemma rejects the whole file. Its whole-glob branch
compares the signature EasyCrypt actually compares, and two things about that
signature were measured the hard way:

* ``glob F(A, B)`` contains ``glob A`` only when ``F``'s body actually CALLS
  ``A`` -- EasyCrypt drops unused functor arguments -- so two flat states
  whose ``initialize`` differs in which parameters it calls have DIFFERENT
  glob types even with identical field lists. Isolated standalone in
  ``.ec-tmp/diag/param_glob_probe.ec``: two functors over one abstract
  module, one calling it and one not, rejected at the ``=`` with *no matching
  operator, named `='* and no parameter types listed at all; the same pair
  with matching usage compiles.
* the comparison must be made on the WHOLE flat state, not on this oracle's
  projection, because ``initialize`` is where the difference lives and the
  projection to ``challenge`` drops it.

Measured as the single cause of all four proofs evidence-only emission was
breaking (`CG_seedbased` LEAK_BIND_K_PK / K_CT_DIFFKEY / K_CT_SAMEKEY and
`CK_seedbased` LEAK_BIND_K_CT_SAMEKEY), each goal read separately rather than
inferred from the first.
"""

from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _glob_signature,
    _micro_pre_well_typed,
    _render_flat_state,
)

BS = frog_ast.BitStringType(parameterization=frog_ast.Variable("lam"))
EMT = {"K": "K_c.Scheme", "N": "N_c.Scheme"}
FLAT = [ec_ast.ModuleParam("K", "K_c.Scheme"), ec_ast.ModuleParam("N", "N_c.Scheme")]


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _state(name: str, init_calls: bool) -> frog_ast.Game:
    """A two-oracle flat state. ``init_calls`` decides whether ``Initialize``
    calls the functor parameter ``K`` -- the only difference, and one the
    ``Challenge`` projection cannot see."""
    fields = [frog_ast.Field(BS, "dk0", None)]
    init_body: list[frog_ast.Statement] = []
    if init_calls:
        init_body.append(
            frog_ast.Assignment(
                BS,
                _var("s"),
                frog_ast.FuncCall(
                    frog_ast.FieldAccess(_var("K"), "Decaps"), [_var("dk0")]
                ),
            )
        )
        init_body.append(frog_ast.ReturnStatement(_var("s")))
    else:
        init_body.append(frog_ast.ReturnStatement(_var("dk0")))
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []), frog_ast.Block(init_body)
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge", frog_ast.BoolType(), [frog_ast.Parameter(BS, "ct0")]
        ),
        frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Boolean(False))]),
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


def _well_typed(left: frog_ast.Game, right: frog_ast.Game) -> bool:
    lref, rref = "S_left(K, N)", "S_right(K, N)"
    pre = f"={{ct0}} /\\ (glob {lref}){{1}} = (glob {rref}){{2}}"
    modules = mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())
    return _micro_pre_well_typed(
        (left, right, lref, rref, pre), "challenge", modules, EMT, {}, FLAT
    )


def test_the_pair_differs_ONLY_in_parameter_usage() -> None:
    """Guard against the target test passing for the older reason. The two
    states must have identical FIELD lists, so the only thing that can make
    the statement ill-typed is which parameters the bodies call."""
    modules = mt.ModuleTranslator(tc.TypeCollector(aliases={}), _factory())
    sigs = [
        _glob_signature(
            _render_flat_state(
                modules,
                "S",
                _state("S", calls),
                EMT,
                {},
                FLAT,
                emit_state_vars=True,
            ),
            [p.name for p in FLAT],
        )
        for calls in (True, False)
    ]
    assert sigs[0][0] == sigs[1][0], "fields must agree for this to be the right test"
    assert sigs[0][1] != sigs[1][1], "used parameters must be what differs"


def test_drops_the_lemma_when_only_initialize_calls_the_parameter() -> None:
    assert not _well_typed(_state("S_left", True), _state("S_right", False))


def test_keeps_the_lemma_when_both_states_call_the_parameter() -> None:
    """The control the filter must not over-reach on: matching usage is a
    well-typed statement, and dropping it would silently lose evidence."""
    assert _well_typed(_state("S_left", True), _state("S_right", True))


def test_keeps_the_lemma_when_neither_state_calls_the_parameter() -> None:
    assert _well_typed(_state("S_left", False), _state("S_right", False))
