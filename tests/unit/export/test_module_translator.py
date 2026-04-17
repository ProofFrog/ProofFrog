"""Unit tests for the EasyCrypt module translator."""

from __future__ import annotations

from typing import Callable

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt import module_translator as mt
from proof_frog.export.easycrypt import type_collector as tc


def _render_stmt_for_test(stmt: ec_ast.EcStmt) -> str:
    # pylint: disable=protected-access
    return ec_ast._render_stmt(stmt)


@pytest.fixture
def reduction_r1() -> frog_ast.Reduction:
    proof = frog_parser.parse_proof_file(
        "examples/joy/Proofs/Ch2/OTPSecureLR.proof"
    )
    helpers = [h for h in proof.helpers if isinstance(h, frog_ast.Reduction)]
    return helpers[0]


@pytest.fixture
def otp_lr_proof_setup() -> dict[str, object]:
    """Parse OTPSecureLR and return handles commonly needed by Phase 4a tests."""
    proof_path = "examples/joy/Proofs/Ch2/OTPSecureLR.proof"
    proof = frog_parser.parse_proof_file(proof_path)
    game_files: list[frog_ast.GameFile] = []
    for imp in proof.imports:
        resolved = frog_parser.resolve_import_path(imp.filename, proof_path)
        root = frog_parser.parse_file(resolved)
        if isinstance(root, frog_ast.GameFile):
            game_files.append(root)
    otsr_lr_game_file = next(g for g in game_files if g.name == "OneTimeSecrecyLR")
    ots_game_file = next(g for g in game_files if g.name == "OneTimeSecrecy")
    reductions = [h for h in proof.helpers if isinstance(h, frog_ast.Reduction)]
    return {
        "translator": _make_translator(
            _otpsecurelr_aliases(), _otpsecurelr_return_types()
        ),
        "proof": proof,
        "otsr_lr_game_file": otsr_lr_game_file,
        "ots_game_file": ots_game_file,
        "reduction_R1": reductions[0],
        "reduction_R2": reductions[1],
    }


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


def test_translate_adversary_module_type(
    otp_lr_proof_setup: dict[str, object],
) -> None:
    """Each game file gets an adversary module type parameterized over its oracle."""
    translator = otp_lr_proof_setup["translator"]
    assert isinstance(translator, mt.ModuleTranslator)
    game_file = otp_lr_proof_setup["otsr_lr_game_file"]
    assert isinstance(game_file, frog_ast.GameFile)
    adv = translator.translate_adversary_type(
        game_file, oracle_type_name="OneTimeSecrecyLR_Oracle"
    )
    assert adv.name == "OneTimeSecrecyLR_Adv"
    assert len(adv.params) == 1
    assert adv.params[0].name == "O"
    assert adv.params[0].module_type == "OneTimeSecrecyLR_Oracle"
    assert len(adv.procs) == 1
    assert adv.procs[0].name == "distinguish"
    assert adv.procs[0].return_type.text == "bool"


def test_translate_reduction_adversary(otp_lr_proof_setup: dict[str, object]) -> None:
    translator = otp_lr_proof_setup["translator"]
    assert isinstance(translator, mt.ModuleTranslator)
    r1 = otp_lr_proof_setup["reduction_R1"]
    assert isinstance(r1, frog_ast.Reduction)
    adv = translator.translate_reduction_adversary(
        reduction=r1,
        outer_adversary_type_name="OneTimeSecrecyLR_Adv",
        inner_oracle_type_name="OneTimeSecrecy_Oracle",
        scheme_module_expr="OTP",
    )
    assert adv.name == "R1_Adv"
    assert len(adv.params) == 2
    assert adv.params[0].name == "A"
    assert adv.params[0].module_type == "OneTimeSecrecyLR_Adv"
    assert adv.params[1].name == "C"
    assert adv.params[1].module_type == "OneTimeSecrecy_Oracle"
    proc = adv.procs[0]
    assert proc.name == "distinguish"
    body_str = "\n".join(_render_stmt_for_test(s) for s in proc.body)
    assert "b <@ A(R1(OTP, C)).distinguish()" in body_str


def test_translate_game_wrapper(otp_lr_proof_setup: dict[str, object]) -> None:
    translator = otp_lr_proof_setup["translator"]
    assert isinstance(translator, mt.ModuleTranslator)
    wrapper = translator.translate_game_wrapper(
        wrapper_name="Game_step_0",
        adversary_type_name="OneTimeSecrecyLR_Adv",
        oracle_module_expr="OneTimeSecrecyLR_Left(OTP)",
    )
    assert wrapper.name == "Game_step_0"
    assert len(wrapper.params) == 1
    assert wrapper.params[0].name == "A"
    assert wrapper.params[0].module_type == "OneTimeSecrecyLR_Adv"
    assert len(wrapper.procs) == 1
    proc = wrapper.procs[0]
    assert proc.name == "main"
    assert proc.return_type.text == "bool"
    body_str = "\n".join(_render_stmt_for_test(s) for s in proc.body)
    assert "var b : bool" in body_str
    assert "b <@ A(OneTimeSecrecyLR_Left(OTP)).distinguish()" in body_str
    assert "return b" in body_str
