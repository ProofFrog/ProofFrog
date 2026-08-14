"""Unit tests for what one level of the coupled-guard descent inherits.

Two defects lived here and they are one change, not two:

* ``_decl_types`` reads ``VarDecl``s, and only the whole procedure body has
  them -- EasyCrypt lifts an arm's declarations to the procedure top, so an arm
  carries none. Re-deriving them one level down returned ``{}`` and made every
  common local below depth 0 look type-mismatched, so the split path always
  declined there.
* ``seq n m : (I)`` DISCARDS the prefix except for ``I``. An inner level that
  restated only the leg's coupling threw away an enclosing run's locals, which
  are still in scope and may still be read.

Fixing the first without the second is what made the route emit tactics
EasyCrypt rejects, which is why they land together.

The tactic shape is EasyCrypt-checked in ``.ec-tmp/nestedrun_probe.ec`` (a
case split nested inside an arm that also has work before it, with the inner
invariant accumulating the enclosing one -- ACCEPTED). Its negative control
``.ec-tmp/nestedrun_negctl.ec`` drops one enclosing local from the inner
invariant and EasyCrypt answers *cannot prove goal (strict)*, printing the
missing ``a{1} = a{2}``.
"""

from __future__ import annotations

from proof_frog.export.easycrypt import ec_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _decl_types,
    _guard_descent_lines,
    _invariant_covers_reads,
    _split_invariant,
)


def _ty(name: str) -> ec_ast.EcType:
    return ec_ast.EcType(name)


def _decl(name: str, ty: str) -> ec_ast.VarDecl:
    return ec_ast.VarDecl(name=name, type=_ty(ty))


def _assign(var: str, rhs: str) -> ec_ast.Assign:
    return ec_ast.Assign(var=var, rhs=rhs)


def _call(var: str, callee: str, args: str) -> ec_ast.Call:
    return ec_ast.Call(var=var, callee=callee, args=args)


def _if(guard: str, then_body, else_body) -> ec_ast.If:
    return ec_ast.If(guard=guard, then_body=then_body, else_body=else_body)


PRE = "={ct} /\\ ={glob K} /\\ S1.dk{1} = S2.dk{2}"


def _body(guard_inner: str, alt_field: str) -> list[ec_ast.EcStmt]:
    """``a <- f ct; if (ct = star) {..} else { b <- g a; if (..) {..} else {..} }``.

    The inner else-arm reads ``a``, which the OUTER run binds -- the shape whose
    invariant must accumulate.
    """
    return [
        _decl("a", "bs"),
        _decl("b", "bs"),
        _decl("r0", "bs"),
        _assign("a", "f ct"),
        _if(
            f"ct = {alt_field}",
            [_assign("r0", "witness")],
            [
                _assign("b", "g a"),
                _if(
                    guard_inner,
                    [_call("r0", "K.decaps", "dk, ct")],
                    [_call("r0", "K.decaps", "dk, a")],
                ),
            ],
        ),
        ec_ast.Return(expr="r0"),
    ]


def test_an_arm_carries_no_declarations() -> None:
    # The mechanism of the trap, pinned so a future reader sees why the types
    # must be threaded rather than re-derived.
    body = _body("b = alt", "star")
    arm = body[4]
    assert isinstance(arm, ec_ast.If)
    assert sorted(_decl_types(body)) == ["a", "b", "r0"]
    assert _decl_types(arm.else_body) == {}


def test_the_inner_split_inherits_the_types_and_accumulates_the_invariant() -> None:
    lines = _guard_descent_lines(
        _body("b = alt", "star"),
        _body("b = alt", "star"),
        {"dk", "star", "alt"},
        {},
        PRE,
        False,
    )
    assert lines is not None
    seqs = [ln for ln in lines if ln.strip().lstrip("+ ").startswith("seq ")]
    # Two levels split, and the inner one carries BOTH runs' locals plus the
    # leg's own coupling. Without the inherited declarations there would be no
    # inner ``seq`` at all; without accumulation it would not mention ``a``.
    assert len(seqs) == 2
    inner = seqs[1]
    assert "={b}" in inner and "={a}" in inner and "S1.dk{1} = S2.dk{2}" in inner


def test_a_type_mismatched_common_local_still_declines() -> None:
    # The pre-existing refusal must survive the threading: a canonicalization
    # that expands a tuple leaves one side holding a pair where the other holds
    # a component, and ``={x}`` would not typecheck.
    left = _body("b = alt", "star")
    right = _body("b = alt", "star")
    right[1] = _decl("b", "bs * bs")
    assert (
        _guard_descent_lines(
            left, right, {"dk", "star", "alt"}, {}, PRE, False
        )
        is None
    )


def test_coverage_gate_sees_an_enclosing_run_s_local() -> None:
    # The inner branch reads ``a``; an invariant that does not carry it leaves
    # the closer a goal it cannot discharge, and that is what the gate must
    # catch even though ``a`` is bound one level up.
    branch = _if("b = alt", [_call("r0", "K.decaps", "dk, ct")], [_call("r0", "K.decaps", "dk, a")])
    assert not _invariant_covers_reads("={b} /\\ " + PRE, {"a", "b"}, branch)
    assert _invariant_covers_reads("={b} /\\ ={a} /\\ " + PRE, {"a", "b"}, branch)


def test_split_invariant_prefixes_the_enclosing_text() -> None:
    run1 = [_assign("b", "g a")]
    run2 = [_assign("b", "g a")]
    enclosing = "={a} /\\ " + PRE
    assert _split_invariant(run1, run2, enclosing, {"b": "bs"}, {"b": "bs"}) == (
        "={b} /\\ ={a} /\\ " + PRE
    )


def test_split_invariant_skips_a_local_only_one_run_binds() -> None:
    run1 = [_assign("b", "g a"), _assign("c", "h a")]
    run2 = [_assign("b", "g a")]
    assert _split_invariant(run1, run2, PRE, {"b": "bs", "c": "bs"}, {"b": "bs"}) == (
        "={b} /\\ " + PRE
    )


def test_nested_run_descent_matches_the_ec_validated_template() -> None:
    """Lockstep: the template's proof body IS the synthesizer's output.

    The template (``ec_templates/plumbing_peel_nested_run_descent.ec``) is
    EasyCrypt-accepted, so this keeps the route and the checked shape from
    drifting apart.
    """
    import textwrap
    from pathlib import Path

    from proof_frog.export.easycrypt.chain_emitter import (
        _coupled_field_renaming,
        _coupled_guard_descent,
    )

    def state(star: str, inner_guard: str) -> list[ec_ast.EcStmt]:
        return [
            _decl("a", "bs"),
            _decl("b", "bs"),
            _decl("r0", "bs"),
            _decl("out", "bs"),
            _assign("a", "f ct.`1"),
            _if(
                f"ct = {star}",
                [_assign("out", "witness")],
                [
                    _assign("b", "g a"),
                    _if(
                        inner_guard,
                        [_call("r0", "K.decaps", "dk0, ct.`2"), _assign("out", "r0")],
                        [_call("r0", "K.decaps", "dk0, a"), _assign("out", "r0")],
                    ),
                ],
            ),
            ec_ast.Return(expr="out"),
        ]

    pre = (
        "={ct} /\\ ={glob K} /\\ S_L.dk0{1} = S_R.dk0{2}"
        " /\\ S_L.ctStar_0{1} = S_R.field2{2} /\\ S_L.ctStar_1{1} = S_R.field4{2}"
        " /\\ S_L.alt{1} = S_R.field6{2}"
    )
    fields = {"dk0", "ctStar_0", "ctStar_1", "alt", "field2", "field4", "field6"}
    got = _coupled_guard_descent(
        state("(ctStar_0, ctStar_1)", "b = alt"),
        state("(field2, field4)", "b = field6"),
        fields,
        _coupled_field_renaming(pre, "S_L", "S_R"),
        pre,
        False,
    )
    assert got is not None
    template = (
        Path(__file__).parents[2]
        / "integration"
        / "ec_templates"
        / "plumbing_peel_nested_run_descent.ec"
    ).read_text()
    block = template.split("lemma nested_run_descent :", 1)[1]
    proof_body = block.split("proof.\n", 1)[1].split("qed.", 1)[0]
    assert got[0] == textwrap.dedent(proof_body).strip().splitlines()
