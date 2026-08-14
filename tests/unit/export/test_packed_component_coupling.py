"""Unit tests for the PACKED-value/COMPONENTS coupling conjunct and the guard
descent that consumes it.

A canonicalization step that splits a tuple-valued state field into one field
per component leaves the two adjacent states with no field in common for it, so
neither the same-name nor the same-role pairing relates it -- and a ``decaps``
testing ``ct = ctStar`` against ``ct = (ctStar_0, ctStar_1)`` then cannot be
shown to take the same branch. The conjunct is DERIVED from the two states'
``initialize`` sources; these tests pin the derivation, every case it refuses,
and the expansion the guard test reads back out of the emitted text.

The tactic the descent then emits is EasyCrypt-checked in
``.ec-tmp/packedguard_probe.ec``, whose negative control
(``packedguard_negctl.ec``) drops the packed conjunct and gets *cannot prove
goal (strict)* at the guard-equivalence goal.
"""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt.chain_emitter import (
    _coupled_field_renaming,
    _coupled_packed_expansion,
    _init_packed_components,
    _init_source_map,
    _rename_tokens,
)


def _ty(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _assign(name: str, value: frog_ast.Expression) -> frog_ast.Assignment:
    return frog_ast.Assignment(None, frog_ast.Variable(name), value)


def _game(
    fields: list[str], statements: list[frog_ast.Statement]
) -> frog_ast.Game:
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _ty("Out"), []),
        frog_ast.Block(statements),
    )
    return frog_ast.Game(
        ("S", [], [frog_ast.Field(_ty("T"), f, None) for f in fields], [init])
    )


PACKED_STATE = _game(
    ["dk", "ctStar"],
    [
        _assign("dk", frog_ast.Variable("__a0__")),
        _assign(
            "ctStar",
            frog_ast.Tuple([frog_ast.Variable("__a10__"), frog_ast.Variable("__a15__")]),
        ),
    ],
)

SPLIT_STATE = _game(
    ["dk", "ctStar_0", "ctStar_1"],
    [
        _assign("dk", frog_ast.Variable("__a0__")),
        _assign("ctStar_0", frog_ast.Variable("__a10__")),
        _assign("ctStar_1", frog_ast.Variable("__a15__")),
    ],
)


def test_reads_the_components_of_a_tuple_valued_field() -> None:
    assert _init_packed_components(PACKED_STATE) == {
        "ctStar": ["__a10__", "__a15__"]
    }


def test_a_non_tuple_source_names_no_components() -> None:
    assert _init_packed_components(SPLIT_STATE) == {}


def test_a_one_element_tuple_is_not_a_packing() -> None:
    state = _game(
        ["ctStar"],
        [_assign("ctStar", frog_ast.Tuple([frog_ast.Variable("__a10__")]))],
    )
    assert _init_packed_components(state) == {}


def test_a_later_non_tuple_write_drops_the_entry() -> None:
    # Last write wins, matching ``_init_source_map``: a field reassigned from a
    # non-tuple no longer holds the pair the first write named.
    state = _game(
        ["ctStar"],
        [
            _assign(
                "ctStar",
                frog_ast.Tuple(
                    [frog_ast.Variable("__a10__"), frog_ast.Variable("__a15__")]
                ),
            ),
            _assign("ctStar", frog_ast.Variable("__a20__")),
        ],
    )
    assert _init_packed_components(state) == {}


def test_the_components_are_the_split_states_own_sources() -> None:
    # The relation is derivable exactly because each component's source is the
    # source of one field on the other side.
    components = _init_packed_components(PACKED_STATE)["ctStar"]
    sources = _init_source_map(SPLIT_STATE)
    owners = [
        [f for f, s in sources.items() if s == component] for component in components
    ]
    assert owners == [["ctStar_0"], ["ctStar_1"]]


PRE = (
    "={ct} /\\ ={glob K} /\\ S1.dk{1} = S2.dk{2}"
    " /\\ S1.ctStar{1} = (S2.ctStar_0, S2.ctStar_1){2}"
)


def test_expansion_is_read_back_out_of_the_emitted_conjunct() -> None:
    renaming = _coupled_field_renaming(PRE, "S1", "S2")
    assert _coupled_packed_expansion(PRE, "S1", "S2", renaming) == {
        "ctStar": "(ctStar_0, ctStar_1)"
    }


def test_the_two_guards_normalize_to_the_same_text() -> None:
    renaming = _coupled_field_renaming(PRE, "S1", "S2")
    merged = {**renaming, **_coupled_packed_expansion(PRE, "S1", "S2", renaming)}
    fields = {"dk", "ctStar", "ctStar_0", "ctStar_1"}
    assert _rename_tokens("ct = ctStar", fields, merged) == _rename_tokens(
        "ct = (ctStar_0, ctStar_1)", fields, merged
    )


def test_a_plain_field_equality_yields_no_expansion() -> None:
    plain = "={ct} /\\ S1.dk{1} = S2.dk{2}"
    renaming = _coupled_field_renaming(plain, "S1", "S2")
    assert _coupled_packed_expansion(plain, "S1", "S2", renaming) == {}


def test_a_conjunct_naming_another_module_is_ignored() -> None:
    # The two sides of a leg are the only modules whose fields the tactic may
    # substitute; a conjunct reaching outside them says nothing about them.
    other = "S1.ctStar{1} = (Chal.ctStar_0, Chal.ctStar_1){2}"
    assert _coupled_packed_expansion(other, "S1", "S2", {}) == {}


def test_a_packed_name_also_related_plainly_is_left_alone() -> None:
    # A plain equality on the same name says the name denotes a field on BOTH
    # sides, so expanding it would rewrite the wrong side's read too -- and it
    # says some other route already related the two.
    both = PRE + " /\\ S1.ctStar{1} = S2.ctStar{2}"
    renaming = _coupled_field_renaming(both, "S1", "S2")
    assert "ctStar" not in _coupled_packed_expansion(both, "S1", "S2", renaming)


def test_components_are_spelled_through_the_renaming_in_force() -> None:
    pre = PRE + " /\\ S2.ctStar_0{2} = S2.alias{2}"
    renaming = _coupled_field_renaming(pre, "S1", "S2")
    expansion = _coupled_packed_expansion(pre, "S1", "S2", renaming)
    assert expansion == {"ctStar": "(alias, ctStar_1)"}
