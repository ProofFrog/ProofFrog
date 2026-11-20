"""Unit tests for the exact swap check behind the reorder entries.

The ``rendered-swap-sim`` and ``perm-swap-sim`` entries close a pure-reorder
micro-lemma (``Topological Sorting`` and the other reorder transforms) with
``proc. swap{1} ... sim.``. ``sim`` does not reorder anything, so the swaps
must leave the two bodies equal up to a renaming of locals, or the entry must
decline.

The masked check (``_swaps_realign``) compares statements with every
identifier replaced by a placeholder, so two independent assignments of the
same shape in swapped order look aligned already. The coarse sort then emits
one swap where the step needs two, and EasyCrypt rejects the zero-admit file
(measured on ``CK_seedbased_Correctness``: ``micro_0_left_18`` emitted
``swap{1} 6 -1. sim.``). The shape below is that micro's, cut down.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _ec_indep,
    _ec_perm_swaps,
    _exact_rendered_swaps,
    _straight_line_indep,
    _swaps_realign,
    _swaps_realign_exactly,
)

_T = ec_ast.EcType("t")


def _mod(locals_: list[str], body: list[ec_ast.EcStmt]) -> ec_ast.Module:
    return ec_ast.Module(
        name="Step",
        procs=[
            ec_ast.Proc(
                name="compute",
                params=[],
                return_type=_T,
                body=[ec_ast.VarDecl(n, _T) for n in locals_] + body,
            )
        ],
    )


_LOCALS = ["s", "dk0", "pk0", "dk1", "c0", "c1", "e0", "e1"]


def _before() -> ec_ast.Module:
    """``pk0 <- dk0.`1`` before ``T.derive``, and ``e1`` assigned before ``e0``."""
    return _mod(
        _LOCALS,
        [
            ec_ast.Sample("s", "dseed"),
            ec_ast.Call("dk0", "P.derive", "s"),
            ec_ast.Assign("pk0", "dk0.`1"),
            ec_ast.Call("dk1", "T.derive", "s"),
            ec_ast.Call("c0", "P.encaps", "pk0"),
            ec_ast.Call("c1", "T.encaps", "dk1.`1"),
            ec_ast.Assign("e1", "c1.`2"),
            ec_ast.Assign("e0", "c0.`2"),
            ec_ast.Return("(e0, e1)"),
        ],
    )


def _after(names: dict[str, str] | None = None) -> ec_ast.Module:
    """The same statements in topological order, locals renamed by ``names``."""
    n = {x: x for x in _LOCALS} | (names or {})
    return _mod(
        [n[x] for x in _LOCALS],
        [
            ec_ast.Sample(n["s"], "dseed"),
            ec_ast.Call(n["dk0"], "P.derive", n["s"]),
            ec_ast.Call(n["dk1"], "T.derive", n["s"]),
            ec_ast.Assign(n["pk0"], f"{n['dk0']}.`1"),
            ec_ast.Call(n["c0"], "P.encaps", n["pk0"]),
            ec_ast.Call(n["c1"], "T.encaps", f"{n['dk1']}.`1"),
            ec_ast.Assign(n["e0"], f"{n['c0']}.`2"),
            ec_ast.Assign(n["e1"], f"{n['c1']}.`2"),
            ec_ast.Return(f"({n['e0']}, {n['e1']})"),
        ],
    )


def _exec(mod: ec_ast.Module) -> list[ec_ast.EcStmt]:
    return [s for s in mod.procs[0].body if not isinstance(s, ec_ast.VarDecl)]


def test_the_masked_check_passes_one_swap_where_two_are_needed() -> None:
    """The defect: the coarse sort moves ``T.derive`` only, and the masked
    check calls the still-swapped ``e1``/``e0`` assignments aligned."""
    before, after = _before(), _after()
    coarse = _ec_perm_swaps(before.procs[0].body, after.procs[0].body)
    assert coarse == ["swap{1} 4 -1"]
    assert _swaps_realign(coarse, _exec(before), _exec(after))
    assert not _swaps_realign_exactly(coarse, before, after)


def test_every_swap_the_step_needs_is_emitted() -> None:
    assert _exact_rendered_swaps(_before(), _after()) == [
        "swap{1} 4 -1",
        "swap{1} 8 -1",
    ]


def test_a_consistent_renaming_of_locals_still_aligns() -> None:
    """``sim`` relates locals that differ only by name, so a renamed
    right-hand state (the hoister's ``_rN`` temporaries) is still aligned."""
    renamed = _after({"dk1": "_r0", "e0": "_r1", "e1": "_r2"})
    assert _swaps_realign_exactly(["swap{1} 4 -1", "swap{1} 8 -1"], _before(), renamed)


def test_a_renaming_onto_a_local_of_another_type_declines() -> None:
    after = _after()
    after.procs[0].body[6] = ec_ast.VarDecl("e0", ec_ast.EcType("u"))
    assert not _swaps_realign_exactly(
        ["swap{1} 4 -1", "swap{1} 8 -1"], _before(), after
    )


def test_a_reorder_across_a_dependency_declines() -> None:
    """``y <- x`` cannot move above ``x <- m``: no sequence is valid."""
    left = _mod(
        ["x", "y"],
        [ec_ast.Assign("x", "m"), ec_ast.Assign("y", "x"), ec_ast.Return("y")],
    )
    right = _mod(
        ["x", "y"],
        [ec_ast.Assign("y", "x"), ec_ast.Assign("x", "m"), ec_ast.Return("y")],
    )
    assert _exact_rendered_swaps(left, right) is None


def test_a_move_past_a_branch_declines() -> None:
    """The dependency check cannot see inside an ``if``, so a move across one
    is refused, even where it would be valid."""
    branch = ec_ast.If("b", [ec_ast.Assign("y", "m")])
    left = _mod(
        ["x", "y"],
        [ec_ast.Sample("x", "d"), branch, ec_ast.Return("(x, y)")],
    )
    right = _mod(
        ["x", "y"],
        [branch, ec_ast.Sample("x", "d"), ec_ast.Return("(x, y)")],
    )
    assert _exact_rendered_swaps(left, right) is None


def test_a_sample_reading_a_written_local_is_dependent() -> None:
    """``_ec_indep`` reads nothing from a sample's distribution."""
    smp = ec_ast.Sample("x", "duniform y")
    asg = ec_ast.Assign("y", "m")
    assert _ec_indep(smp, asg, {"x", "y"})
    assert not _straight_line_indep(smp, asg, {"x", "y"})
    assert not _straight_line_indep(asg, smp, {"x", "y"})


def test_independent_straight_line_statements_stay_independent() -> None:
    assert _straight_line_indep(
        ec_ast.Assign("pk0", "dk0.`1"),
        ec_ast.Call("dk1", "T.derive", "s"),
        {"pk0", "dk0", "dk1", "s"},
    )
