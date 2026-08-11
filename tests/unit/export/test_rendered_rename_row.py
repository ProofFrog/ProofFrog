"""Unit tests for the rendered-identity row's alpha-rename variant.

`_rendered_rename_step` closes a leg with `proc; sim.` when the two adjacent
flat states render to the same EC module up to a renaming of LOCAL variables.
It exists because the two existing rows each miss this shape from a different
side: `_rename_equal_projection` (Move 1) decides on the FrogLang ASTs, which
can differ by material the renderer normalizes away, and the plain
rendered-identity row requires the names to match. Measured on
`CG_expanded_INDCCA_T`, every declining `Alpha Rename` leg passes all of Move
1's cheap checks and then fails its final equality.

`_modules_alpha_equal` is the whole decision. The risk it carries is that a
too-permissive notion of "same up to renaming" would equate modules `sim`
cannot relate -- masking every identifier, which is how the class was first
measured, equates a field rename and two different callees. So the tests
below spend most of their effort on what must still DECLINE.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import _modules_alpha_equal


def _mod(
    locals_: list[tuple[str, str]],
    body: list[ec_ast.EcStmt],
    state: tuple[str, str] = ("f00", "int"),
) -> ec_ast.Module:
    return ec_ast.Module(
        name="Step_id",
        procs=[
            ec_ast.Proc(
                name="g",
                params=[ec_ast.ProcParam(name="m", type=ec_ast.EcType(text="int"))],
                return_type=ec_ast.EcType(text="int"),
                body=[
                    ec_ast.VarDecl(name=n, type=ec_ast.EcType(text=t))
                    for n, t in locals_
                ]
                + body,
            )
        ],
        module_vars=[ec_ast.VarDecl(name=state[0], type=ec_ast.EcType(text=state[1]))],
    )


def test_a_pure_local_rename_is_alpha_equal() -> None:
    """The measured shape: same program, locals named differently."""
    left = _mod(
        [("ct_T", "int")],
        [ec_ast.Assign("ct_T", "f00 + m"), ec_ast.Return("ct_T")],
    )
    right = _mod(
        [("__a0__", "int")],
        [ec_ast.Assign("__a0__", "f00 + m"), ec_ast.Return("__a0__")],
    )
    assert left != right
    assert _modules_alpha_equal(left, right)


def test_a_swap_of_two_local_names_is_alpha_equal() -> None:
    """The substitution is a single pass, so a genuine swap must not be
    mangled into an accidental collision."""
    left = _mod(
        [("x", "int"), ("y", "int")],
        [ec_ast.Assign("x", "m"), ec_ast.Assign("y", "x"), ec_ast.Return("y")],
    )
    right = _mod(
        [("y", "int"), ("x", "int")],
        [ec_ast.Assign("y", "m"), ec_ast.Assign("x", "y"), ec_ast.Return("x")],
    )
    assert _modules_alpha_equal(left, right)


def test_a_state_field_rename_declines() -> None:
    """A field rename changes `glob`, and masking identifiers would have
    called these equal. This is the main thing the text comparison buys."""
    left = _mod([("x", "int")], [ec_ast.Return("f00")])
    right = _mod([("y", "int")], [ec_ast.Return("f01")], state=("f01", "int"))
    assert not _modules_alpha_equal(left, right)


def test_a_different_callee_declines() -> None:
    """Two calls to DIFFERENT procedures are not a renaming."""
    left = _mod([("x", "int")], [ec_ast.Call("x", "E.enc", "m"), ec_ast.Return("x")])
    right = _mod([("y", "int")], [ec_ast.Call("y", "E.dec", "m"), ec_ast.Return("y")])
    assert not _modules_alpha_equal(left, right)


def test_a_local_retyped_declines() -> None:
    left = _mod([("x", "int")], [ec_ast.Return("m")])
    right = _mod([("y", "bool")], [ec_ast.Return("m")])
    assert not _modules_alpha_equal(left, right)


def test_a_non_injective_renaming_declines() -> None:
    """Two distinct locals may not collapse onto one name -- that merges two
    variables and is not a renaming."""
    left = _mod(
        [("x", "int"), ("y", "int")],
        [ec_ast.Assign("x", "m"), ec_ast.Assign("y", "m"), ec_ast.Return("x")],
    )
    right = _mod(
        [("z", "int"), ("z", "int")],
        [ec_ast.Assign("z", "m"), ec_ast.Assign("z", "m"), ec_ast.Return("z")],
    )
    assert not _modules_alpha_equal(left, right)


def test_a_local_colliding_with_a_state_field_declines() -> None:
    """Renaming a local onto a state var's name would capture it."""
    left = _mod([("x", "int")], [ec_ast.Assign("x", "m"), ec_ast.Return("x")])
    right = _mod([("f00", "int")], [ec_ast.Assign("f00", "m"), ec_ast.Return("f00")])
    assert not _modules_alpha_equal(left, right)


def test_a_body_difference_declines() -> None:
    """The row must never absorb a real program change."""
    left = _mod([("x", "int")], [ec_ast.Assign("x", "f00 + m"), ec_ast.Return("x")])
    right = _mod([("y", "int")], [ec_ast.Assign("y", "f00 - m"), ec_ast.Return("y")])
    assert not _modules_alpha_equal(left, right)


def test_a_differing_local_count_declines() -> None:
    left = _mod([("x", "int")], [ec_ast.Return("m")])
    right = _mod([("y", "int"), ("z", "int")], [ec_ast.Return("m")])
    assert not _modules_alpha_equal(left, right)


def test_identical_modules_with_no_locals_decline_here() -> None:
    """With no locals there is no renaming to make, and the plain
    rendered-identity row already owns that case; this row must not claim it
    a second time."""
    left = _mod([], [ec_ast.Return("f00")])
    right = _mod([], [ec_ast.Return("f00")])
    assert not _modules_alpha_equal(left, right)


def _two_proc_mod(
    first: list[tuple[str, str]], second: list[tuple[str, str]]
) -> ec_ast.Module:
    """A module with two procs, each declaring one local, so the two procs'
    scopes can be exercised independently."""

    def proc(name: str, locals_: list[tuple[str, str]]) -> ec_ast.Proc:
        var = locals_[0][0]
        return ec_ast.Proc(
            name=name,
            params=[ec_ast.ProcParam(name="m", type=ec_ast.EcType(text="int"))],
            return_type=ec_ast.EcType(text="int"),
            body=[
                ec_ast.VarDecl(name=n, type=ec_ast.EcType(text=t)) for n, t in locals_
            ]
            + [ec_ast.Assign(var, "f00 + m"), ec_ast.Return(var)],
        )

    return ec_ast.Module(
        name="Step_id",
        procs=[proc("g", first), proc("h", second)],
        module_vars=[ec_ast.VarDecl(name="f00", type=ec_ast.EcType(text="int"))],
    )


def test_the_same_local_name_may_map_differently_in_two_procs() -> None:
    """EC procedure scopes are independent, so `ct_PQ` in `g` and `ct_PQ` in
    `h` are different variables and may correspond to different names.

    A single module-wide rename map calls that a conflict and declines. Four
    legs of `CG_expanded_INDCCA_T` were lost to exactly this before the map
    was made per-proc -- found by re-running the guard instrument after the
    row landed, not by review.
    """
    left = _two_proc_mod([("ct_PQ", "int")], [("ct_PQ", "int")])
    right = _two_proc_mod([("__a6__", "int")], [("__a7__", "int")])
    assert _modules_alpha_equal(left, right)


def test_a_per_proc_map_still_declines_a_body_change_in_the_second_proc() -> None:
    """Per-proc comparison must not stop at the first proc that matches."""
    left = _two_proc_mod([("x", "int")], [("y", "int")])
    right = _two_proc_mod([("a", "int")], [("b", "int")])
    right.procs[1].body[-1] = ec_ast.Return("f00")
    assert not _modules_alpha_equal(left, right)
