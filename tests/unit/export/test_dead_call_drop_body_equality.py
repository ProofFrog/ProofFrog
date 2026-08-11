"""Unit tests for the one-sided call drop's EQUAL-BACKBONE body check.

When the two flat states have the same call backbone, `_dead_call_drop_step`
closes the leg with `proc; sim.`. That is only licensed when the two bodies are
the SAME PROGRAM apart from the names holding dead call results -- names `sim`
is free to ignore. The branch always documented that condition; for a long time
it only CHECKED that the calls were dead, and never that the bodies agreed
elsewhere. A body difference then slipped through, `sim` ran without closing,
and the enclosing `qed.` failed with "cannot save an incomplete proof" -- the
failure mode admit-counting cannot see, because no `admit` marks it.

`_blank_dead_result_names` is the normalization the check runs first: blanking
each call's result variable turns "equal modulo dead names" into plain equality,
so anything else that differs survives and is caught. The tests below pin the
two shapes that were actually measured in the corpus.
"""

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _blank_dead_result_names,
    _strip_decls,
)


def _norm(body: list[ec_ast.EcStmt]) -> list[ec_ast.EcStmt]:
    return _strip_decls(_blank_dead_result_names(body))


def test_a_pure_dead_name_rename_stays_equal() -> None:
    """The shape the branch exists for: same program, different name holding a
    dead result. This must keep comparing equal or the route stops firing."""
    left = [
        ec_ast.Call("ss3", "F.evaluate", "k3, c3"),
        ec_ast.Sample("ss", "dbs"),
        ec_ast.Return("(pk, ss)"),
    ]
    right = [
        ec_ast.Call("_r0", "F.evaluate", "k3, c3"),
        ec_ast.Sample("ss", "dbs"),
        ec_ast.Return("(pk, ss)"),
    ]
    assert _norm(left) == _norm(right)


def test_a_commuted_equality_inside_a_loop_is_a_real_difference() -> None:
    """The measured wall: `CG_expanded_INDCCA_T`'s `micro_8_hash_left_12`.

    Both sides' calls are dead and the backbones match, so the liveness-only
    gate fired -- but the lazy-random-oracle `while` bodies differ by the
    operand order of an equality, which `sim` does not absorb. Blanking the
    dead names leaves that difference standing, so the gate now declines.
    """
    def body(eq: str) -> list[ec_ast.EcStmt]:
        return [
            ec_ast.Call("_r6", "L.get", "i"),
            ec_ast.While(
                "i < n",
                [
                    ec_ast.If(eq, [ec_ast.Assign("found", "true")], []),
                    ec_ast.Assign("i", "i + 1"),
                ],
            ),
            ec_ast.Return("found"),
        ]

    assert _norm(body("_r6 = slice_0_128(m)")) != _norm(
        body("slice_0_128(m) = _r6")
    )


def test_a_dead_name_difference_inside_a_loop_still_matches() -> None:
    """The mirror of the previous test: blanking reaches INTO the loop, so a
    nested call whose result name differs is still recognized as the same
    program. Without the recursive descent the route would decline every
    loop-bearing leg it used to close."""
    def body(name: str) -> list[ec_ast.EcStmt]:
        return [
            ec_ast.While(
                "i < n",
                [
                    ec_ast.Call(name, "L.get", "i"),
                    ec_ast.Assign("i", "i + 1"),
                ],
            ),
            ec_ast.Return("i"),
        ]

    assert _norm(body("_r6")) == _norm(body("ss3"))


def test_an_extra_live_statement_is_a_real_difference() -> None:
    """A dropped redundant copy is a genuine body change to this check, even
    though `sim` happens to close it (measured on
    `GeneralDoubleSymEnc_INDCPA$_MultiChal`'s `micro_2_ctxt_left_1`). Declining
    it costs an evidence leg in an already-rejected proof and is the safe side
    of decline-don't-guess: recovering it needs copy propagation, not a `sim`
    guess. Pinned so the decline is a recorded choice rather than an accident.
    """
    left = [
        ec_ast.Call("__a0__", "D.enc", "dKey, m"),
        ec_ast.Sample("__a1__", "dC_2"),
        ec_ast.Assign("__a2__", "__a1__"),
        ec_ast.Return("__a2__"),
    ]
    right = [
        ec_ast.Call("__a0__", "D.enc", "dKey, m"),
        ec_ast.Sample("__a1__", "dC_2"),
        ec_ast.Return("__a1__"),
    ]
    assert _norm(left) != _norm(right)
