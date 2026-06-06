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


def _render_module_for_test(module: ec_ast.Module) -> list[str]:
    # pylint: disable=protected-access
    return ec_ast._render_module(module)


@pytest.fixture
def reduction_r1() -> frog_ast.Reduction:
    proof = frog_parser.parse_proof_file("examples/joy/Proofs/Ch2/OTPSecureLR.proof")
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
    abstract_types: dict[str, str] | None = None,
) -> mt.ModuleTranslator:
    rt = return_types or {}
    types = tc.TypeCollector(aliases=aliases, abstract_types=abstract_types)

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


@pytest.fixture
def stateful_reduction() -> frog_ast.Reduction:
    """A reduction carrying module-level field state (``dk0``, ``dk1``)."""
    proof = frog_parser.parse_proof_file(
        "examples/applications/cfrg-hybrid-kems/proofs/Generic/"
        "LEAK_implies_HON_BIND_K_CT.proof"
    )
    return next(h for h in proof.helpers if isinstance(h, frog_ast.Reduction))


def test_stateful_reduction_emits_module_vars(
    stateful_reduction: frog_ast.Reduction,
) -> None:
    """A reduction's field declarations become module-level ``var`` decls."""
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    tx = _make_translator(
        {
            "DecapsKey": bs,
            "EncapsKey": bs,
            "SharedSecret": bs,
            "Ciphertext": bs,
        }
    )
    mod = tx.translate_reduction(
        stateful_reduction,
        primitive_name="KEM",
        oracle_type_name="LEAK_BIND_K_CT_Oracle",
    )
    assert [v.name for v in mod.module_vars] == ["dk0", "dk1"]
    # The rendered module declares the state vars before the procs.
    rendered = "\n".join(_render_module_for_test(mod))
    assert "var dk0 :" in rendered
    assert rendered.index("var dk0 :") < rendered.index("proc ")


def test_stateful_reduction_field_writes_are_assignments(
    stateful_reduction: frog_ast.Reduction,
) -> None:
    """Field writes (no type annotation) update state via ``<-``, not a fresh local.

    The state vars must not be re-declared as locals inside the procs, and
    field reads must resolve to the module var.
    """
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    tx = _make_translator(
        {
            "DecapsKey": bs,
            "EncapsKey": bs,
            "SharedSecret": bs,
            "Ciphertext": bs,
        }
    )
    mod = tx.translate_reduction(
        stateful_reduction,
        primitive_name="KEM",
        oracle_type_name="LEAK_BIND_K_CT_Oracle",
    )
    init = next(p for p in mod.procs if p.name == "initialize")
    # dk0/dk1 are assigned (Assign / `<-`), never re-declared as locals.
    assert any(isinstance(s, ec_ast.Assign) and s.var == "dk0" for s in init.body)
    assert not any(
        isinstance(s, ec_ast.VarDecl) and s.name in {"dk0", "dk1"} for s in init.body
    )
    # A reading proc references the module var as a plain identifier.
    decaps0 = next(p for p in mod.procs if p.name == "decaps0")
    assert any(isinstance(s, ec_ast.Call) and "dk0" in s.args for s in decaps0.body)


def _kem_multichal_real_game() -> frog_ast.Game:
    """The Real side of the multi-oracle KEM INDCPA_MultiChal game (fields pk/sk)."""
    gf = frog_parser.parse_file("examples/Games/KEM/INDCPA_MultiChal.game")
    return gf.games[0]


def test_translate_game_emits_state_vars_for_multi_oracle_game() -> None:
    """A stateful multi-oracle game (``Initialize`` sets ``pk``/``sk`` read by
    ``Challenge``) must declare those fields as module-level ``var``s, else EC
    rejects the cross-proc reference with ``unknown module-level variable``."""
    abstract = {
        "PublicKey": "publickey",
        "SecretKey": "secretkey",
        "SharedSecret": "sharedsecret",
        "Ciphertext": "ciphertext",
    }
    tx = _make_translator({}, abstract_types=abstract)
    mod = tx.translate_game(
        _kem_multichal_real_game(),
        "KEM_INDCPA_MultiChal_Real",
        "KEM",
        implements="KEM_INDCPA_MultiChal_Oracle",
        emit_state_vars=True,
    )
    assert [v.name for v in mod.module_vars] == ["pk", "sk"]
    rendered = "\n".join(_render_module_for_test(mod))
    assert "var pk :" in rendered
    assert rendered.index("var pk :") < rendered.index("proc ")


def test_translate_game_no_state_vars_by_default() -> None:
    """Single-oracle games (the legacy path) emit no state-var block, so their
    output stays byte-identical."""
    abstract = {
        "PublicKey": "publickey",
        "SecretKey": "secretkey",
        "SharedSecret": "sharedsecret",
        "Ciphertext": "ciphertext",
    }
    tx = _make_translator({}, abstract_types=abstract)
    mod = tx.translate_game(
        _kem_multichal_real_game(),
        "KEM_INDCPA_MultiChal_Real",
        "KEM",
        implements="KEM_INDCPA_MultiChal_Oracle",
    )
    assert mod.module_vars == []


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


# --- Multi-oracle (Initialize-lifted) emission, P2 -----------------------


def _multi_oracle_game_file() -> frog_ast.GameFile:
    """A synthetic two-side multi-oracle game file (Initialize + Eval + Chk).

    Mirrors the validated EC template shape: an ``Initialize`` oracle plus two
    post-init oracles. Initialize returns a bitstring (so the lifted-init param
    type is concrete); Eval/Chk are the adversary-facing oracles.
    """
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))

    def side(name: str) -> frog_ast.Game:
        param = frog_ast.Parameter(frog_ast.Variable("PRF"), "E")
        init = frog_ast.Method(
            frog_ast.MethodSignature("Initialize", bs, []), frog_ast.Block([])
        )
        eval_m = frog_ast.Method(
            frog_ast.MethodSignature("Eval", bs, [frog_ast.Parameter(bs, "x")]),
            frog_ast.Block([]),
        )
        chk = frog_ast.Method(
            frog_ast.MethodSignature("Chk", bs, [frog_ast.Parameter(bs, "x")]),
            frog_ast.Block([]),
        )
        return frog_ast.Game((name, [param], [], [init, eval_m, chk]))

    return frog_ast.GameFile([], (side("Left"), side("Right")), "PRFGame")


def _multi_oracle_translator() -> mt.ModuleTranslator:
    return _make_translator({})


def test_multi_oracle_spec_built_for_multi_oracle_game() -> None:
    tx = _multi_oracle_translator()
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    assert spec is not None
    assert spec.init_name == "initialize"
    assert spec.init_return_type.text == "bs_lambda"
    assert spec.post_init_names == ["eval", "chk"]
    assert spec.oracle_restriction("O") == ["O.eval", "O.chk"]


def test_multi_oracle_spec_none_for_single_oracle() -> None:
    tx = _multi_oracle_translator()
    # OTPSecureLR's OneTimeSecrecyLR game has no Initialize -> single-oracle.
    proof_path = "examples/joy/Proofs/Ch2/OTPSecureLR.proof"
    gf = next(
        g
        for g in (
            frog_parser.parse_file(
                frog_parser.resolve_import_path(imp.filename, proof_path)
            )
            for imp in frog_parser.parse_proof_file(proof_path).imports
        )
        if isinstance(g, frog_ast.GameFile) and g.name == "OneTimeSecrecyLR"
    )
    assert tx.multi_oracle_spec(gf) is None


def test_multi_oracle_adversary_type_restricts_to_post_init() -> None:
    tx = _multi_oracle_translator()
    gf = _multi_oracle_game_file()
    spec = tx.multi_oracle_spec(gf)
    adv = tx.translate_adversary_type(
        gf, oracle_type_name="PRFGame_Oracle", multi_oracle=spec
    )
    assert len(adv.procs) == 1
    distinguish = adv.procs[0]
    assert distinguish.name == "distinguish"
    # distinguish gains the lifted-init result parameter ...
    assert [p.name for p in distinguish.params] == ["pk"]
    assert distinguish.params[0].type.text == "bs_lambda"
    # ... and is restricted to the post-init oracles only.
    assert distinguish.oracle_restriction == ["O.eval", "O.chk"]
    # The rendered module type carries the restriction clause.
    rendered = "\n".join(ec_ast._render_decl(adv))  # pylint: disable=protected-access
    assert "proc distinguish(pk : bs_lambda) : bool {O.eval, O.chk}" in rendered


def test_multi_oracle_game_wrapper_lifts_initialize() -> None:
    tx = _multi_oracle_translator()
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    wrapper = tx.translate_game_wrapper(
        wrapper_name="Game_step_0",
        adversary_type_name="PRFGame_Adv",
        oracle_module_expr="PRFGame_Left(E)",
        multi_oracle=spec,
    )
    body_str = "\n".join(_render_stmt_for_test(s) for s in wrapper.procs[0].body)
    assert "var pk : bs_lambda;" in body_str
    assert "pk <@ PRFGame_Left(E).initialize();" in body_str
    assert "b <@ A(PRFGame_Left(E)).distinguish(pk);" in body_str
    assert "return b;" in body_str


def test_multi_oracle_theory_game_wrapper_lifts_initialize() -> None:
    tx = _multi_oracle_translator()
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    wrapper = tx.translate_theory_game_wrapper(
        wrapper_name="Game_PRFGame_Left",
        scheme_param_name="Em",
        scheme_type_name="Scheme",
        adversary_type_name="PRFGame_Adv",
        side_module_name="PRFGame_Left",
        multi_oracle=spec,
    )
    body_str = "\n".join(_render_stmt_for_test(s) for s in wrapper.procs[0].body)
    assert "pk <@ PRFGame_Left(Em).initialize();" in body_str
    assert "b <@ A(PRFGame_Left(Em)).distinguish(pk);" in body_str


def test_multi_oracle_reduction_adversary_threads_init(
    otp_lr_proof_setup: dict[str, object],
) -> None:
    tx = _multi_oracle_translator()
    r1 = otp_lr_proof_setup["reduction_R1"]
    assert isinstance(r1, frog_ast.Reduction)
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    adv = tx.translate_reduction_adversary(
        reduction=r1,
        outer_adversary_type_name="PRFGame_Adv",
        inner_oracle_type_name="PRFGame_Oracle",
        scheme_module_expr="OTP",
        inner_multi_oracle=spec,
        outer_multi_oracle=spec,
    )
    distinguish = adv.procs[0]
    # distinguish takes the inner-init result; the body re-runs Initialize
    # through the reduction to produce the outer-init result it forwards to A.
    assert [p.name for p in distinguish.params] == ["pk"]
    body_str = "\n".join(_render_stmt_for_test(s) for s in distinguish.body)
    assert "var pk0 : bs_lambda;" in body_str
    assert "pk0 <@ R1(OTP, C).initialize();" in body_str
    assert "b <@ A(R1(OTP, C)).distinguish(pk0);" in body_str


def _pure_forward_reduction() -> frog_ast.Reduction:
    """A reduction whose ``Initialize`` forwards ``challenger.Initialize()``.

    Mirrors KEMPRF's ``R_KEM``: ``Initialize() { return challenger.Initialize(); }``
    plus a post-init ``Challenge`` that delegates to the challenger.
    """
    bs = frog_ast.BitStringType(parameterization=frog_ast.Variable("lambda"))
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", bs, []),
        frog_ast.Block(
            [
                frog_ast.ReturnStatement(
                    frog_ast.FuncCall(
                        frog_ast.FieldAccess(
                            frog_ast.Variable("challenger"), "Initialize"
                        ),
                        [],
                    )
                )
            ]
        ),
    )
    challenge = frog_ast.Method(
        frog_ast.MethodSignature("Challenge", bs, []), frog_ast.Block([])
    )
    game = frog_ast.ParameterizedGame("KEM_INDCPA_MultiChal", [frog_ast.Variable("K")])
    return frog_ast.Reduction(
        (
            "R_KEM",
            [frog_ast.Parameter(frog_ast.Variable("KEM"), "K")],
            [],
            [init, challenge],
        ),
        game,
        game,
    )


def test_multi_oracle_reduction_adversary_forwards_pk_for_pure_forward_init() -> None:
    """Blocker B: a pure-forward-Initialize reduction against a multi-oracle inner
    game forwards the received ``pk`` instead of re-running ``Initialize`` (which
    would re-call ``C.initialize`` and break the restricted adversary interface).
    """
    tx = _multi_oracle_translator()
    reduction = _pure_forward_reduction()
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    adv = tx.translate_reduction_adversary(
        reduction=reduction,
        outer_adversary_type_name="KEM_Adv",
        inner_oracle_type_name="KEM_Oracle",
        scheme_module_expr="K",
        inner_multi_oracle=spec,
        outer_multi_oracle=spec,
    )
    distinguish = adv.procs[0]
    assert [p.name for p in distinguish.params] == ["pk"]
    body_str = "\n".join(_render_stmt_for_test(s) for s in distinguish.body)
    # The received pk is forwarded directly; no re-init local, no R.initialize call.
    assert "b <@ A(R_KEM(K, C)).distinguish(pk);" in body_str
    assert "initialize()" not in body_str
    assert "pk0" not in body_str


def test_multi_oracle_reduction_adversary_reinit_for_single_oracle_inner() -> None:
    """When the inner game is single-oracle (no Initialize lifted), ``distinguish``
    takes NO parameter (matching the inner single-oracle adversary type) and the
    reduction re-runs its own Initialize to produce the outer-init result.
    ``inner_multi_oracle=None`` is the trigger.
    """
    tx = _multi_oracle_translator()
    reduction = _pure_forward_reduction()
    spec = tx.multi_oracle_spec(_multi_oracle_game_file())
    adv = tx.translate_reduction_adversary(
        reduction=reduction,
        outer_adversary_type_name="KEM_Adv",
        inner_oracle_type_name="PRF_Oracle",
        scheme_module_expr="K",
        inner_multi_oracle=None,
        outer_multi_oracle=spec,
    )
    distinguish = adv.procs[0]
    # Single-oracle inner type -> distinguish() takes no parameter.
    assert distinguish.params == []
    body_str = "\n".join(_render_stmt_for_test(s) for s in distinguish.body)
    assert "pk0 <@ R_KEM(K, C).initialize();" in body_str
    assert "b <@ A(R_KEM(K, C)).distinguish(pk0);" in body_str


def test_single_oracle_emitters_unchanged_when_spec_none() -> None:
    """multi_oracle=None reproduces the legacy single-oracle shapes exactly."""
    tx = _multi_oracle_translator()
    gf = _multi_oracle_game_file()
    adv = tx.translate_adversary_type(gf, oracle_type_name="PRFGame_Oracle")
    assert adv.procs[0].params == []
    assert adv.procs[0].oracle_restriction is None
    wrapper = tx.translate_game_wrapper(
        wrapper_name="Game_step_0",
        adversary_type_name="PRFGame_Adv",
        oracle_module_expr="PRFGame_Left(E)",
    )
    body_str = "\n".join(_render_stmt_for_test(s) for s in wrapper.procs[0].body)
    assert "b <@ A(PRFGame_Left(E)).distinguish();" in body_str
    assert "initialize" not in body_str
