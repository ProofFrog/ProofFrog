"""Unit tests for the EasyCrypt ExpressionTranslator."""

from __future__ import annotations

from proof_frog import frog_ast
from proof_frog.export.easycrypt.expr_translator import ExpressionTranslator
from proof_frog.export.easycrypt.type_collector import TypeCollector


def _make(
    local_types: dict[str, frog_ast.Type] | None = None,
    known_abstract: set[str] | None = None,
) -> ExpressionTranslator:
    types = TypeCollector(known_abstract_types=known_abstract)
    local = local_types or {}

    def type_of(e: frog_ast.Expression) -> frog_ast.Type:
        if isinstance(e, frog_ast.Variable) and e.name in local:
            return local[e.name]
        raise KeyError(e)

    return ExpressionTranslator(types, type_of)


def test_translate_tuple_literal() -> None:
    tr = _make()
    t = frog_ast.Tuple([frog_ast.Variable("a"), frog_ast.Variable("b")])
    assert tr.translate(t) == "(a, b)"


def test_translate_indexed_tuple_access() -> None:
    tr = _make()
    access = frog_ast.ArrayAccess(frog_ast.Variable("t"), frog_ast.Integer(0))
    assert tr.translate(access) == "t.`1"
    access2 = frog_ast.ArrayAccess(frog_ast.Variable("t"), frog_ast.Integer(1))
    assert tr.translate(access2) == "t.`2"


def test_translate_variable() -> None:
    tr = _make()
    assert tr.translate(frog_ast.Variable("x")) == "x"
