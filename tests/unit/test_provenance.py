import copy
import dataclasses

import pytest

from proof_frog.frog_ast import SourceOrigin, Variable


def test_source_origin_is_immutable():
    origin = SourceOrigin(
        file="test.game",
        line=5,
        col=8,
        original_text="return x;",
        transform_chain=(),
    )
    assert origin.file == "test.game"
    assert origin.transform_chain == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        origin.line = 10  # type: ignore[misc]


def test_source_origin_extend_chain():
    origin = SourceOrigin(
        file="test.game",
        line=5,
        col=8,
        original_text="return x;",
        transform_chain=(),
    )
    extended = dataclasses.replace(
        origin, transform_chain=origin.transform_chain + ("XorCancellation",)
    )
    assert extended.transform_chain == ("XorCancellation",)
    assert origin.transform_chain == ()


def test_ast_node_origin_defaults_to_none():
    var = Variable("x")
    assert var.origin is None


def test_ast_node_origin_excluded_from_equality():
    v1 = Variable("x")
    v2 = Variable("x")
    v2.origin = SourceOrigin(
        file="test.game",
        line=1,
        col=0,
        original_text="x",
        transform_chain=(),
    )
    assert v1 == v2


def test_ast_node_origin_preserved_on_copy():
    origin = SourceOrigin(
        file="test.game",
        line=5,
        col=8,
        original_text="return x;",
        transform_chain=(),
    )
    var = Variable("x")
    var.origin = origin
    var_copy = copy.copy(var)
    assert var_copy.origin is origin


def test_transformer_propagates_origin_to_copy():
    """When Transformer's COW path copies a parent node, origin is preserved."""
    from proof_frog.frog_ast import BinaryOperation, BinaryOperators
    from proof_frog.visitors import ReplaceTransformer

    origin = SourceOrigin(
        file="test.game",
        line=10,
        col=4,
        original_text="x + y",
        transform_chain=(),
    )
    expr = BinaryOperation(BinaryOperators.ADD, Variable("x"), Variable("y"))
    expr.origin = origin

    result = ReplaceTransformer(expr.right_expression, Variable("z")).transform(expr)

    assert result is not expr
    assert result.origin is not None
    assert result.origin.file == "test.game"
    assert result.origin.line == 10


def test_parser_populates_origin():
    """The parser should set origin on AST nodes it creates."""
    from proof_frog import frog_parser

    method = frog_parser.parse_method(
        "BitString<n> f(BitString<n> m) { return m; }"
    )
    assert method.origin is not None
    assert method.origin.file == "<unknown>"
    assert method.origin.line >= 1
    assert method.origin.transform_chain == ()


def test_parser_populates_origin_on_expressions():
    """Origin should be set on expression nodes too."""
    from proof_frog import frog_parser

    method = frog_parser.parse_method(
        "BitString<n> f(BitString<n> m) { return m; }"
    )
    # The return statement's expression should have origin
    ret = method.block.statements[0]
    assert ret.origin is not None
    assert ret.origin.transform_chain == ()


def test_transformer_does_not_invent_origin():
    """Nodes without origin should not gain one through transformation."""
    from proof_frog.frog_ast import BinaryOperation, BinaryOperators
    from proof_frog.visitors import ReplaceTransformer

    expr = BinaryOperation(BinaryOperators.ADD, Variable("x"), Variable("y"))
    assert expr.origin is None

    result = ReplaceTransformer(expr.right_expression, Variable("z")).transform(expr)

    assert result is not expr
    assert result.origin is None
