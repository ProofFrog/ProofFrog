"""Unit tests for the EasyCrypt module translator."""

from __future__ import annotations

from typing import Callable

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc


@pytest.fixture
def reduction_r1() -> frog_ast.Reduction:
    proof = frog_parser.parse_proof_file(
        "examples/joy/Proofs/Ch2/OTPSecureLR.proof"
    )
    helpers = [h for h in proof.helpers if isinstance(h, frog_ast.Reduction)]
    return helpers[0]


def _make_translator(
    aliases: dict[str, frog_ast.Type],
    return_types: dict[tuple[str, str], frog_ast.Type] | None = None,
) -> mt.ModuleTranslator:
    rt = return_types or {}
    types = tc.TypeCollector(aliases=aliases)

    def type_of_factory(
        local: dict[str, frog_ast.Type],
        module_param_types: dict[str, str],
    ) -> Callable[[frog_ast.Expression], frog_ast.Type]:
        def type_of(e: frog_ast.Expression) -> frog_ast.Type:
            if isinstance(e, frog_ast.Variable) and e.name in local:
                return local[e.name]
            if isinstance(e, frog_ast.FuncCall) and isinstance(
                e.func, frog_ast.FieldAccess
            ):
                obj = e.func.the_object
                if (
                    isinstance(obj, frog_ast.Variable)
                    and obj.name in module_param_types
                ):
                    key = (module_param_types[obj.name], e.func.name)
                    if key in rt:
                        return rt[key]
            raise KeyError(e)

        return type_of

    return mt.ModuleTranslator(types, type_of_factory)


def _otpsecurelr_aliases() -> dict[str, frog_ast.Type]:
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    return {"Key": bs, "Message": bs, "Ciphertext": bs}


def _otpsecurelr_return_types() -> dict[tuple[str, str], frog_ast.Type]:
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    return {("OneTimeSecrecy_Oracle", "ENC"): bs}


def test_translate_reduction_has_two_curried_params(
    reduction_r1: frog_ast.Reduction,
) -> None:
    tx = _make_translator(_otpsecurelr_aliases(), _otpsecurelr_return_types())
    mod = tx.translate_reduction(
        reduction_r1,
        primitive_name="SymEnc",
        oracle_type_name="OneTimeSecrecy_Oracle",
    )
    assert mod.name == "R1"
    assert [p.name for p in mod.params] == ["E", "Challenger"]
    assert [p.module_type for p in mod.params] == [
        "SymEnc",
        "OneTimeSecrecy_Oracle",
    ]


def test_reduction_return_call_is_lifted(
    reduction_r1: frog_ast.Reduction,
) -> None:
    tx = _make_translator(_otpsecurelr_aliases(), _otpsecurelr_return_types())
    mod = tx.translate_reduction(
        reduction_r1,
        primitive_name="SymEnc",
        oracle_type_name="OneTimeSecrecy_Oracle",
    )
    proc = mod.procs[0]
    kinds = [type(s).__name__ for s in proc.body]
    assert "Call" in kinds
    assert kinds[-1] == "Return"
