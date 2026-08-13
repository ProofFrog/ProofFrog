"""Unit tests for the derived-from-``Initialize`` coupling conjuncts.

The exporter may state that two endpoints' fields are equal only when it has
DERIVED that from how each ``Initialize`` produces the value: both fields must
expand, through their own body's locals, to the same expression over module
calls. These tests pin the derivation and, more importantly, every case it
REFUSES -- a wrong conjunct here would be a false precondition, and for an
already-admitted hop nothing downstream would catch it.

The shape being derived is EasyCrypt-checked in
``.ec-tmp/kemprf_probe.ec``: with ``G_RandKey.ctStar{1} = R_MultiPRF.ctStar{2}``
added, ``KEMPRF_INDCCA``'s hop-3 ``initialize`` and ``decaps`` lemmas both
close; the negative control drops that one conjunct and EasyCrypt answers
*cannot prove goal (strict)* at the guard-equivalence goal
``c{1} = ctStar{1} <=> c{2} = ctStar{2}``.
"""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt.exporter import (
    _init_source_texts,
    _shared_source_field_pairs,
)


def _ty(name: str) -> frog_ast.Variable:
    return frog_ast.Variable(name)


def _call(module: str, method: str, *args: frog_ast.Expression) -> frog_ast.FuncCall:
    return frog_ast.FuncCall(
        frog_ast.FieldAccess(frog_ast.Variable(module), method), list(args)
    )


def _assign(name: str, value: frog_ast.Expression) -> frog_ast.Assignment:
    return frog_ast.Assignment(None, frog_ast.Variable(name), value)


def _index(name: str, i: int) -> frog_ast.ArrayAccess:
    return frog_ast.ArrayAccess(frog_ast.Variable(name), frog_ast.Integer(i))


def _game(
    name: str, fields: list[str], statements: list[frog_ast.Statement]
) -> frog_ast.Game:
    init = frog_ast.Method(
        frog_ast.MethodSignature("Initialize", _ty("Out"), []),
        frog_ast.Block(statements),
    )
    return frog_ast.Game(
        (
            name,
            [],
            [frog_ast.Field(_ty("T"), f, None) for f in fields],
            [init],
        )
    )


def _keygen_encaps_body() -> list[frog_ast.Statement]:
    """``KEMPRF``'s shared init prefix: a keygen destructure then an encaps."""
    return [
        _assign("_tup", _call("K", "KeyGen")),
        _assign("pk", _index("_tup", 0)),
        _assign("sk", _index("_tup", 1)),
        _assign("rsp", _call("K", "Encaps", frog_ast.Variable("pk"))),
        _assign("ctStar", _index("rsp", 1)),
    ]


def test_expands_through_locals_to_module_calls() -> None:
    texts = _init_source_texts(_game("G", ["sk", "ctStar"], _keygen_encaps_body()))
    assert texts == {
        "sk": "K.KeyGen()[1]",
        "ctStar": "K.Encaps(K.KeyGen()[0])[1]",
    }


def test_tuple_literal_index_folds_and_drops_the_other_component() -> None:
    # The packed shape the theorem game repacks into: the component the field
    # takes must not drag the OTHER component's call into the text, or the two
    # endpoints holding the same ciphertext would not look alike.
    body = [
        _assign("_tup", _call("K", "KeyGen")),
        _assign("pk", _index("_tup", 0)),
        _assign("x", _call("K", "Encaps", frog_ast.Variable("pk"))),
        _assign("k", _index("x", 0)),
        _assign("c", _index("x", 1)),
        _assign("ss", _call("F", "evaluate", frog_ast.Variable("k"),
                            frog_ast.Variable("c"))),
        _assign("packed", frog_ast.Tuple([frog_ast.Variable("ss"),
                                          frog_ast.Variable("c")])),
        _assign("ctStar", _index("packed", 1)),
    ]
    texts = _init_source_texts(_game("G", ["ctStar"], body))
    assert texts == {"ctStar": "K.Encaps(K.KeyGen()[0])[1]"}


def test_refuses_a_field_whose_calls_are_not_a_backbone_prefix() -> None:
    # A sample happens BEFORE the keygen this field comes from. Only an initial
    # segment of the backbone is coupled pairwise by the init leg's peel, so the
    # equality is not derivable and the field gets no text.
    body = [
        frog_ast.Sample(None, frog_ast.Variable("seed"), _ty("D")),
        _assign("_tup", _call("K", "KeyGen")),
        _assign("sk", _index("_tup", 1)),
    ]
    assert _init_source_texts(_game("G", ["sk"], body)) == {}


def test_refuses_a_sampled_field() -> None:
    body = [frog_ast.Sample(None, frog_ast.Variable("key"), _ty("D"))]
    assert _init_source_texts(_game("G", ["key"], body)) == {}


def test_refuses_a_field_written_twice() -> None:
    body = [
        _assign("_tup", _call("K", "KeyGen")),
        _assign("ctStar", _index("_tup", 0)),
        _assign("ctStar", _index("_tup", 1)),
    ]
    assert _init_source_texts(_game("G", ["ctStar"], body)) == {}


def test_refuses_a_local_the_body_does_not_define() -> None:
    # ``arg`` is a parameter, not a local: two bodies' unresolved names need not
    # denote the same thing.
    body = [_assign("ctStar", _call("K", "Encaps", frog_ast.Variable("arg")))]
    assert _init_source_texts(_game("G", ["ctStar"], body)) == {}


def test_pairs_the_two_endpoints_fields_by_their_source() -> None:
    left = _game("G", ["sk", "ctStar"], _keygen_encaps_body())
    right = _game("R", ["sk", "ctStar"], _keygen_encaps_body())
    pairs = _shared_source_field_pairs(
        left, right, {"sk", "ctStar"}, {"sk", "ctStar"}
    )
    assert sorted(pairs) == [("ctStar", "ctStar"), ("sk", "sk")]


def test_refuses_when_one_side_has_two_fields_of_the_same_source() -> None:
    # A state and a copy of it: choosing a partner would be a guess, so the
    # source is dropped from BOTH sides.
    left = _game("G", ["ctStar"], _keygen_encaps_body())
    right_body = _keygen_encaps_body() + [_assign("copy", _index("rsp", 1))]
    right = _game("R", ["ctStar", "copy"], right_body)
    assert (
        _shared_source_field_pairs(
            left, right, {"ctStar"}, {"ctStar", "copy"}
        )
        == []
    )


def test_restricts_each_side_to_the_fields_its_own_module_declares() -> None:
    # A field absorbed from a composed challenger lives in another EC module
    # under another name, so it may not be named through this base.
    left = _game("G", ["sk"], _keygen_encaps_body())
    right = _game("R", ["challenger@sk"], [
        _assign("_tup", _call("K", "KeyGen")),
        _assign("challenger@sk", _index("_tup", 1)),
    ])
    assert _shared_source_field_pairs(left, right, {"sk"}, set()) == []
    assert _shared_source_field_pairs(
        left, right, {"sk"}, {"challenger@sk"}
    ) == [("sk", "challenger@sk")]
