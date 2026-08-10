"""Unit tests for Move 5's rendered-identity row.

The row (``_rendered_identity_step``) fires when two adjacent flat states
render to the SAME EasyCrypt module -- the transform's whole effect was
absorbed by the renderer's own normalization. Measured class: ``Symbolic
Computation`` rewriting a bitstring width ANNOTATION, which the type
collector canonicalizes to one EC type. That class caused 173 of the 179
chain deaths in the 2026-08-09 route-retirement shadow run.

Reachability on the REAL corpus is measured, not assumed: with the
whole-oracle routes declined, ``CG_expanded_LEAK_BIND_K_PK`` hop 0
``challenge`` pair 1 renders identically and this row fires (the deaths
move to pair 2). See the plan's shadow report.
"""

from pathlib import Path
from typing import Callable

from proof_frog import frog_ast
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc
from proof_frog.export.easycrypt.chain_emitter import (
    _project_to_method,
    _rendered_identity_step,
)

OPS = frog_ast.BinaryOperators
EMT = {"K": "K_c.Scheme"}
FLAT = [ec_ast.ModuleParam("K", "K_c.Scheme")]


def _var(n: str) -> frog_ast.Variable:
    return frog_ast.Variable(n)


def _sum(*names: object) -> frog_ast.Expression:
    terms = [(_var(n) if isinstance(n, str) else n) for n in names]
    out = terms[0]
    for t in terms[1:]:
        out = frog_ast.BinaryOperation(OPS.ADD, out, t)
    return out


def _mul(k: int, name: str) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(OPS.MULTIPLY, frog_ast.Integer(k), _var(name))


# The measured class: na + nb + nb  vs  na + 2 * nb.
W_LONG = frog_ast.BitStringType(parameterization=_sum("na", "nb", "nb"))
W_SHORT = frog_ast.BitStringType(parameterization=_sum("na", _mul(2, "nb")))
W_OTHER = frog_ast.BitStringType(parameterization=_sum("na", "nb", "nb", "nb"))
BS = frog_ast.BitStringType(parameterization=_var("na"))


def _call(mod: str, meth: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(frog_ast.FieldAccess(_var(mod), meth), list(args))


def _game(
    name: str,
    width: frog_ast.Type,
    field_name: str = "dk0",
    second_arg: str = "ct0",
) -> frog_ast.Game:
    fields = [frog_ast.Field(BS, field_name, None)]
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", BS, []),
        frog_ast.Block([frog_ast.ReturnStatement(_var(field_name))]),
    )
    chal = frog_ast.Method(
        frog_ast.MethodSignature(
            "Challenge", frog_ast.BoolType(), [frog_ast.Parameter(BS, "ct0")]
        ),
        frog_ast.Block(
            [
                frog_ast.Assignment(
                    width, _var("w0"), _call("K", "Widen", _var(field_name))
                ),
                frog_ast.Assignment(
                    width, _var("w1"), _call("K", "Widen", _var(second_arg))
                ),
                frog_ast.ReturnStatement(
                    frog_ast.BinaryOperation(OPS.EQUALS, _var("w0"), _var("w1"))
                ),
            ]
        ),
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
    return _rendered_identity_step(pb, pa, EMT, {}, modules, FLAT)


def test_fires_on_width_annotation_pair() -> None:
    step = _row(_game("SB", W_LONG), _game("SA", W_SHORT))
    assert step is not None
    tac, reqs, rung = step
    assert tac == ["proc; sim."]
    assert rung == "synth-static"
    assert reqs == type(reqs)()  # no axiom requests: sim needs no facts


def test_declines_on_genuinely_different_body() -> None:
    """A real statement difference must decline -- the row's gate is
    module equality, never 'looks similar'."""
    assert _row(_game("SB", W_LONG), _game("SA", W_SHORT, second_arg="dk0")) is None


def test_declines_on_different_width_class() -> None:
    """Widths that canonicalize to DIFFERENT EC types render different
    modules -> decline (this is the soundness-relevant case: the row must
    not equate two genuinely different bitstring types)."""
    assert _row(_game("SB", W_LONG), _game("SA", W_OTHER)) is None


def test_declines_on_field_rename() -> None:
    """The comparison covers the module's state-variable block, so a field
    rename declines even when the statements match up to that name."""
    assert _row(_game("SB", W_LONG), _game("SA", W_SHORT, field_name="dk1")) is None


def test_template_lockstep() -> None:
    """The frozen EC-validated template's tactic must equal the row's
    current output (ec_templates/rendered_identity.ec)."""
    step = _row(_game("SB", W_LONG), _game("SA", W_SHORT))
    assert step is not None
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "rendered_identity.ec"
    ).read_text()
    proof_body = template.split("proof.\n", 1)[1].split("qed.", 1)[0]
    frozen = [ln.strip() for ln in proof_body.strip().splitlines()]
    assert step[0] == frozen


def test_template_modules_are_identical_modulo_name() -> None:
    """The template's two modules must be the same program modulo their
    name -- the row's entire claim, pinned so the template cannot drift."""
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "rendered_identity.ec"
    ).read_text()
    left = template.split("module ID_L", 1)[1].split("}.", 1)[0]
    right = template.split("module ID_R", 1)[1].split("}.", 1)[0]
    assert left.replace("ID_L", "ID_R") == right
