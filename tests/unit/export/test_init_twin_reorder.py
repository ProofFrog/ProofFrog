"""Unit tests for the CFRG init functional-twin reorder synthesizer helpers.

The end-to-end proof is validated by the EC tripwires
``ec_templates/cg_ng_init_reorder.ec`` (the middle-leg reorder tactic),
``cg_ng_init_twin_blueprint.ec`` (the full 3-leg twin transitivity), and
``sim_field_rename.ec`` (the outer-leg ``proc; inline*; sim``). These unit tests
pin the AST-driven pieces of the tactic *generator*.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _init_group_backbone,
    _init_prefix_len,
    _init_reorder_group_swaps,
)


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
