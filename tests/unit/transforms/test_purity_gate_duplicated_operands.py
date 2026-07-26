"""Regression tests: purity gates on duplicated / deleted operands.

Per ruling 7.A.6, each invocation of an abstract-primitive (unannotated) call
is an independent i.i.d. draw. Passes that duplicate an operand (deep-copy it
into several positions) or delete one of two structurally-equal operands must
therefore decline when the operand carries a non-deterministic call -- else
they collapse independent draws or multiply one draw into several. Each test
pins the decline for a non-deterministic operand alongside a deterministic
positive (the transform still fires).

Findings: F-242, F-243 (BooleanAbsorption dedup), F-254 (ConcatEqualityDecompose
`other`), F-257 (TupleEqualityDecompose `project`).
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import build_game_type_map, NameTypeMap
from proof_frog.transforms.algebraic import (
    BooleanAbsorptionTransformer,
    ConcatEqualityDecomposeTransformer,
    TupleEqualityDecomposeTransformer,
)
from proof_frog.transforms._base import PipelineContext


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _expr(src: str) -> frog_ast.Expression:
    return frog_parser.parse_expression(src)


# ---------------------------------------------------------------------------
# F-242 / F-243 -- BooleanAbsorption duplicate-conjunct dedup
# ---------------------------------------------------------------------------


def test_f242_dedup_declines_nondeterministic_duplicate_conjuncts() -> None:
    # flip() && flip(): two structurally-equal conjuncts, but each flip() is
    # an independent draw -- dedup to flip() is unsound.
    expr = _expr("flip() && flip()")
    out = BooleanAbsorptionTransformer(_ctx()).transform(expr)
    assert out == expr  # unchanged


def test_f243_dedup_declines_nondet_multiset_collision() -> None:
    # (flip() || flip() || b) && (flip() || b || b): mutually-"subset"
    # disjunct sets {flip(), b} but each flip() is an independent draw.
    expr = _expr("(flip() || flip() || b) && (flip() || b || b)")
    out = BooleanAbsorptionTransformer(_ctx()).transform(expr)
    assert out == expr  # unchanged


def test_f242_dedup_still_fires_on_deterministic_duplicate() -> None:
    # a && a: deterministic variable, dedup to a is sound.
    expr = _expr("a && a")
    out = BooleanAbsorptionTransformer(_ctx()).transform(expr)
    assert out == frog_ast.Variable("a")


# ---------------------------------------------------------------------------
# F-254 -- ConcatEqualityDecompose slices `other` once per concat term
# ---------------------------------------------------------------------------


def _concat_decompose(method_src: str) -> frog_ast.Method:
    game = frog_parser.parse_game("Game G(Int n) {\n" + method_src + "\n}")
    out = (
        ConcatEqualityDecomposeTransformer(_ctx(), build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    for m in out.methods:
        return m
    raise AssertionError


def test_f254_concat_decompose_declines_nondeterministic_other() -> None:
    # gen() == a || b: `other` = gen() would be sliced twice -> two draws.
    method = _concat_decompose("""
        Bool f(BitString<n> a, BitString<n> b) {
            return gen() == (a || b);
        }
        """)
    ret = method.block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    # Unchanged: still a single top-level equality, not a slice conjunction.
    assert isinstance(ret.expression, frog_ast.BinaryOperation)
    assert ret.expression.operator == frog_ast.BinaryOperators.EQUALS


def test_f254_concat_decompose_still_fires_on_deterministic_other() -> None:
    # c == a || b with c a plain variable: decomposes into slice comparisons.
    method = _concat_decompose("""
        Bool f(BitString<n> c, BitString<n> a, BitString<n> b) {
            return c == (a || b);
        }
        """)
    ret = method.block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    # Fired: top-level AND of per-slice equalities.
    assert isinstance(ret.expression, frog_ast.BinaryOperation)
    assert ret.expression.operator == frog_ast.BinaryOperators.AND


# ---------------------------------------------------------------------------
# F-257 -- TupleEqualityDecompose projects a non-Tuple operand per component
# ---------------------------------------------------------------------------


def _tuple_decompose(method_src: str) -> frog_ast.Method:
    game = frog_parser.parse_game("Game G() {\n" + method_src + "\n}")
    out = (
        TupleEqualityDecomposeTransformer(_ctx(), build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    for m in out.methods:
        return m
    raise AssertionError


def test_f257_tuple_decompose_declines_nondeterministic_operand() -> None:
    # Coin() != t where Coin() returns a 2-tuple: projecting Coin()[0],
    # Coin()[1] would call Coin() twice -> two independent draws.
    method = _tuple_decompose("""
        Bool f([Int, Int] t) {
            return Coin() != t;
        }
        """)
    ret = method.block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    # Unchanged: still a single top-level NOTEQUALS, not an OR of projections.
    assert isinstance(ret.expression, frog_ast.BinaryOperation)
    assert ret.expression.operator == frog_ast.BinaryOperators.NOTEQUALS


def test_f257_tuple_decompose_still_fires_on_variable_operand() -> None:
    # s != t, both tuple-typed variables: decomposes (variable reads are
    # deterministic, so per-component projection is sound).
    method = _tuple_decompose("""
        Bool f([Int, Int] s, [Int, Int] t) {
            return s != t;
        }
        """)
    ret = method.block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert isinstance(ret.expression, frog_ast.BinaryOperation)
    assert ret.expression.operator == frog_ast.BinaryOperators.OR
