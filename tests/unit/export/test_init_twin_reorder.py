"""Unit tests for the CFRG init functional-twin reorder synthesizer helpers.

The end-to-end proof is validated by the EC tripwires
``ec_templates/cg_ng_init_reorder.ec`` (the middle-leg reorder tactic),
``cg_ng_init_twin_blueprint.ec`` (the full 3-leg twin transitivity), and
``sim_field_rename.ec`` (the outer-leg ``proc; inline*; sim``). These unit tests
pin the AST-driven pieces of the tactic *generator*.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _init_functionalize_side,
    _init_group_backbone,
    _init_legmid_tactic,
    _init_legmid_inv,
    _init_prefix_len,
    _init_reorder_group_swaps,
)

_NG_DET = {("NG", "randomscalar"), ("NG", "generator"), ("NG", "exp")}


def _ng_det(module: str, method: str) -> bool:
    return (module, method) in _NG_DET


def _cg_game_body() -> list[ec_ast.EcStmt]:
    """The CG_expanded game init flat body (2 interleaved NG-group keygens),
    exactly as ``_flat_state_module`` renders ``FG_calls`` -- keygen, two
    projections, seed sample, randomscalar/generator/exp, pack, ek/dk writes,
    repeated for the second index."""
    body: list[ec_ast.EcStmt] = []

    def _index(n: str) -> None:
        body.append(ec_ast.Call(f"tup{n}", "KEM_PQ.keygen", ""))
        body.append(ec_ast.Assign(f"ek_PQ{n}", f"tup{n}.`1"))
        body.append(ec_ast.Assign(f"dk_PQ{n}", f"tup{n}.`2"))
        body.append(ec_ast.Sample(f"seed_T{n}", "dbs_ng_nseed"))
        body.append(ec_ast.Call(f"dk_T{n}", "NG.randomscalar", f"seed_T{n}"))
        body.append(ec_ast.Call(f"r{n}", "NG.generator", ""))
        body.append(ec_ast.Call(f"ek_T{n}", "NG.exp", f"r{n}, dk_T{n}"))
        body.append(
            ec_ast.Assign(
                f"tp{n}", f"((ek_PQ{n}, ek_T{n}), (dk_PQ{n}, dk_T{n}, ek_T{n}))"
            )
        )
        body.append(ec_ast.Assign(f"ek{n}", f"tp{n}.`1"))
        body.append(ec_ast.Assign(f"dk{n}", f"tp{n}.`2"))

    _index("0")
    _index("1")
    body.append(ec_ast.Return("(ek0, dk0, ek1, dk1)"))
    return body


def test_group_swaps_matches_validated_tactic() -> None:
    # The validated real-export tactic groups the interleaved game backbone with
    # exactly swap{1} 11 -7 (2nd keygen up past index-0's NG block + sample) then
    # swap{1} 14 -8 (2nd seed up past index-0's NG block). See
    # ec_templates/cg_ng_init_reorder.ec.
    swaps = _init_reorder_group_swaps(_cg_game_body(), "KEM_PQ.keygen")
    assert swaps == ["swap{1} 11 -7.", "swap{1} 14 -8."]


def test_group_swaps_empty_when_already_grouped() -> None:
    # A grouped body (all keygens, then all samples, then the NG calls) needs no
    # swaps -- the reduction side is already in this shape.
    body: list[ec_ast.EcStmt] = [
        ec_ast.Call("tup0", "KEM_PQ.keygen", ""),
        ec_ast.Assign("ek_PQ0", "tup0.`1"),
        ec_ast.Assign("dk_PQ0", "tup0.`2"),
        ec_ast.Call("tup1", "KEM_PQ.keygen", ""),
        ec_ast.Assign("ek_PQ1", "tup1.`1"),
        ec_ast.Assign("dk_PQ1", "tup1.`2"),
        ec_ast.Sample("seed_T0", "dbs_ng_nseed"),
        ec_ast.Sample("seed_T1", "dbs_ng_nseed"),
        ec_ast.Call("dk_T0", "NG.randomscalar", "seed_T0"),
        ec_ast.Call("dk_T1", "NG.randomscalar", "seed_T1"),
    ]
    assert _init_reorder_group_swaps(body, "KEM_PQ.keygen") == []


def _cg_reduction_prefix() -> list[ec_ast.EcStmt]:
    """The FR_calls (reduction twin) grouped prefix through the two seed samples,
    as ``_flat_state_module`` renders it: two challenger keygens (+ their field
    writes), the packed-tuple destructure into dk_PQ_i fields, then the two
    seeds. The last sample sits at executable position 13 -> seq split 13."""
    return [
        ec_ast.Call("t0", "KEM_PQ.keygen", ""),  # 1
        ec_ast.Assign("ek00", "t0.`1"),  # 2
        ec_ast.Assign("challenger_dk0", "t0.`2"),  # 3
        ec_ast.Call("t1", "KEM_PQ.keygen", ""),  # 4
        ec_ast.Assign("ek10", "t1.`1"),  # 5
        ec_ast.Assign("challenger_dk1", "t1.`2"),  # 6
        ec_ast.Assign("tup", "(ek00, challenger_dk0, ek10, challenger_dk1)"),  # 7
        ec_ast.Assign("ek_PQ_0", "tup.`1"),  # 8
        ec_ast.Assign("dk_PQ_0", "tup.`2"),  # 9
        ec_ast.Assign("ek_PQ_1", "tup.`3"),  # 10
        ec_ast.Assign("dk_PQ_1", "tup.`4"),  # 11
        ec_ast.Sample("seed_T_0", "dbs_ng_nseed"),  # 12
        ec_ast.Sample("seed_T_1", "dbs_ng_nseed"),  # 13
    ]


def test_seq_split_lengths_match_validated_tactic() -> None:
    # The validated real-export tactic splits `seq 6 13`: the game prefix (after
    # grouping) ends at its 2nd seed (pos 6); the reduction prefix ends at its
    # 2nd seed (pos 13).
    _swaps, grouped_game = _init_group_backbone(_cg_game_body(), "KEM_PQ.keygen")
    assert _init_prefix_len(grouped_game) == 6
    assert _init_prefix_len(_cg_reduction_prefix()) == 13


def _cg_reduction_ng_suffix() -> list[ec_ast.EcStmt]:
    """The FR_calls NG suffix (grouped): randomscalar x2, then generator/exp per
    index, then the four packing assignments."""
    return [
        ec_ast.Call("dk_T_0", "NG.randomscalar", "seed_T_0"),
        ec_ast.Call("dk_T_1", "NG.randomscalar", "seed_T_1"),
        ec_ast.Call("_r0", "NG.generator", ""),
        ec_ast.Call("ek_T_0", "NG.exp", "_r0, dk_T_0"),
        ec_ast.Call("_r1", "NG.generator", ""),
        ec_ast.Call("ek_T_1", "NG.exp", "_r1, dk_T_1"),
        ec_ast.Assign("ek0", "(ek_PQ_0, ek_T_0)"),
        ec_ast.Assign("dk0", "(dk_PQ_0, dk_T_0, ek_T_0)"),
        ec_ast.Assign("ek1", "(ek_PQ_1, ek_T_1)"),
        ec_ast.Assign("dk1", "(dk_PQ_1, dk_T_1, ek_T_1)"),
    ]


def test_functionalize_reduction_suffix() -> None:
    lines = _init_functionalize_side(
        _cg_reduction_ng_suffix(),
        side=2,
        clone_alias="NG_c",
        det_pred=_ng_det,
        seed_binders={"seed_T_0": "es0", "seed_T_1": "es1"},
        glob_binder="g",
        skip_leading_wp=False,
    )
    assert lines == [
        "wp.",
        "call{2} (NG_exp_det g NG_c.ev_generator (NG_c.ev_randomscalar (es1))).",
        "call{2} (NG_generator_det g).",
        "call{2} (NG_exp_det g NG_c.ev_generator (NG_c.ev_randomscalar (es0))).",
        "call{2} (NG_generator_det g).",
        "call{2} (NG_randomscalar_det g es1).",
        "call{2} (NG_randomscalar_det g es0).",
    ]


def test_functionalize_game_suffix_two_blocks() -> None:
    # The game suffix (after grouping + the seq-6 split) has TWO NG blocks
    # separated by index-0's packing; with skip_leading_wp the first block emits
    # no leading wp (the reduction side's wp already cleared both tails) and the
    # second block gets a wp -- matching VALIDATED_hop0_tactic.txt's {1} peel.
    _swaps, grouped = _init_group_backbone(_cg_game_body(), "KEM_PQ.keygen")
    suffix = grouped[6:]  # drop the 6-stmt probabilistic prefix
    lines = _init_functionalize_side(
        suffix,
        side=1,
        clone_alias="NG_c",
        det_pred=_ng_det,
        seed_binders={"seed_T0": "fs0", "seed_T1": "fs1"},
        glob_binder="g",
        skip_leading_wp=True,
    )
    assert lines == [
        "call{1} (NG_exp_det g NG_c.ev_generator (NG_c.ev_randomscalar (fs1))).",
        "call{1} (NG_generator_det g).",
        "call{1} (NG_randomscalar_det g fs1).",
        "wp.",
        "call{1} (NG_exp_det g NG_c.ev_generator (NG_c.ev_randomscalar (fs0))).",
        "call{1} (NG_generator_det g).",
        "call{1} (NG_randomscalar_det g fs0).",
    ]


def _cg_game_prefix() -> list[ec_ast.EcStmt]:
    """FG_calls grouped prefix (kg0 + its projections, kg1, both seeds), with the
    exact _flat_state_module twin var names."""
    return [
        ec_ast.Call("v_Hybrid_KeyGen__tup0", "KEM_PQ.keygen", ""),
        ec_ast.Assign("v_Hybrid_KeyGen_ek_PQ0", "v_Hybrid_KeyGen__tup0.`1"),
        ec_ast.Assign("v_Hybrid_KeyGen_dk_PQ0", "v_Hybrid_KeyGen__tup0.`2"),
        ec_ast.Call("v_Hybrid_KeyGen__tup9", "KEM_PQ.keygen", ""),
        ec_ast.Sample("v_Hybrid_KeyGen_seed_T0", "dbs_ng_nseed"),
        ec_ast.Sample("v_Hybrid_KeyGen_seed_T9", "dbs_ng_nseed"),
    ]


def _cg_red_prefix_full() -> list[ec_ast.EcStmt]:
    """FR_calls prefix through both seeds, exact twin names (see FR_calls dump)."""
    return [
        ec_ast.Call("challenger_Initialize__tup0", "KEM_PQ.keygen", ""),
        ec_ast.Assign("challenger_Initialize_ek00", "challenger_Initialize__tup0.`1"),
        ec_ast.Assign("challenger_dk0", "challenger_Initialize__tup0.`2"),
        ec_ast.Call("challenger_Initialize__tup_00", "KEM_PQ.keygen", ""),
        ec_ast.Assign("challenger_Initialize_ek10", "challenger_Initialize__tup_00.`1"),
        ec_ast.Assign("challenger_dk1", "challenger_Initialize__tup_00.`2"),
        ec_ast.Assign(
            "_tup",
            "(challenger_Initialize_ek00, challenger_dk0, "
            "challenger_Initialize_ek10, challenger_dk1)",
        ),
        ec_ast.Assign("ek_PQ_0", "_tup.`1"),
        ec_ast.Assign("dk_PQ_0", "_tup.`2"),
        ec_ast.Assign("ek_PQ_1", "_tup.`3"),
        ec_ast.Assign("dk_PQ_1", "_tup.`4"),
        ec_ast.Sample("seed_T_0", "dbs_ng_nseed"),
        ec_ast.Sample("seed_T_1", "dbs_ng_nseed"),
    ]


def test_legmid_inv_matches_validated() -> None:
    red_fields = {
        "challenger_dk0",
        "challenger_dk1",
        "dk_PQ_0",
        "dk_PQ_1",
        "dk_T_0",
        "dk_T_1",
        "ek_T_0",
        "ek_T_1",
    }
    inv = _init_legmid_inv(
        _cg_game_prefix(),
        _cg_red_prefix_full(),
        keygen_callee="KEM_PQ.keygen",
        glob_names=["KEM_PQ", "NG", "G", "H", "L"],
        red_mod="FR_calls",
        red_fields=red_fields,
    )
    expected = " /\\ ".join(
        [
            "(glob KEM_PQ){1} = (glob KEM_PQ){2}",
            "(glob NG){1} = (glob NG){2}",
            "(glob G){1} = (glob G){2}",
            "(glob H){1} = (glob H){2}",
            "(glob L){1} = (glob L){2}",
            "v_Hybrid_KeyGen_ek_PQ0{1} = ek_PQ_0{2}",
            "v_Hybrid_KeyGen_dk_PQ0{1} = FR_calls.dk_PQ_0{2}",
            "FR_calls.dk_PQ_0{2} = FR_calls.challenger_dk0{2}",
            "v_Hybrid_KeyGen__tup9{1}.`1 = ek_PQ_1{2}",
            "v_Hybrid_KeyGen__tup9{1}.`2 = FR_calls.dk_PQ_1{2}",
            "FR_calls.dk_PQ_1{2} = FR_calls.challenger_dk1{2}",
            "v_Hybrid_KeyGen_seed_T0{1} = seed_T_0{2}",
            "v_Hybrid_KeyGen_seed_T9{1} = seed_T_1{2}",
        ]
    )
    assert inv == expected


def test_legmid_tactic_assembles() -> None:
    red_body = _cg_red_prefix_full() + _cg_reduction_ng_suffix()
    red_fields = {
        "challenger_dk0",
        "challenger_dk1",
        "dk_PQ_0",
        "dk_PQ_1",
        "dk_T_0",
        "dk_T_1",
        "ek_T_0",
        "ek_T_1",
    }
    tac = _init_legmid_tactic(
        _cg_game_body(),
        red_body,
        keygen_callee="KEM_PQ.keygen",
        glob_names=["KEM_PQ", "NG", "G", "H", "L"],
        red_mod="FR_calls",
        red_fields=red_fields,
        clone_alias="NG_c",
        det_pred=_ng_det,
    )
    assert tac is not None
    assert tac[:4] == ["proc.", "swap{1} 11 -7.", "swap{1} 14 -8.", tac[3]]
    assert tac[3].startswith("seq 6 13 : (")
    assert tac[-4:] == ["sp.", "skip.", "move => * /=.", "smt()."]
    # prefix peel: 2 rnd, 2 (wp;call), auto
    assert tac[4:11] == [
        "rnd.",
        "rnd.",
        "wp.",
        "call (_: true).",
        "wp.",
        "call (_: true).",
        "auto.",
    ]
    # one exists* per side + 6 NG calls each (2 exp, 2 gen, 2 rs)
    assert sum(1 for t in tac if t.startswith("call{2} (NG_")) == 6
    assert sum(1 for t in tac if t.startswith("call{1} (NG_")) == 6
    assert sum(1 for t in tac if t.startswith("exists* (glob NG)")) == 2
