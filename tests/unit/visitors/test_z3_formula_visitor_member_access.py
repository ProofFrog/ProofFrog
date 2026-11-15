"""Tests for Z3FormulaVisitor's handling of member accesses.

``FieldAccess``, ``GroupGenerator`` and ``GroupOrder`` had no handler, so the
receiver's item stood for the whole access. ``G.generator == G.identity``
encoded as ``G == G``, and ``M.keys == M.values`` as ``M == M``; Z3 proved
both. A member access now encodes as one opaque atom per member, or as None
when the receiver doesn't translate.
"""

import pytest
import z3

from proof_frog import frog_ast, frog_parser, visitors


def _type_map() -> visitors.NameTypeMap:
    type_map = visitors.NameTypeMap()
    type_map.set("G", frog_ast.GroupType())
    type_map.set("S", frog_ast.Variable("P"))
    type_map.set("M", frog_ast.MapType(frog_ast.IntType(), frog_ast.IntType()))
    type_map.set("H", frog_ast.FunctionType(frog_ast.IntType(), frog_ast.IntType()))
    type_map.set("x", frog_ast.IntType())
    return type_map


def _encode(
    expr: str | frog_ast.Expression,
    fallback: bool = False,
    versions: dict[str, int] | None = None,
) -> z3.AstRef | None:
    if isinstance(expr, str):
        expr = frog_parser.parse_expression(expr)
    return visitors.Z3FormulaVisitor(
        _type_map(),
        variable_version_map={} if versions is None else versions,
        opaque_func_call_fallback=fallback,
    ).visit(expr)


def _valid(formula: z3.AstRef) -> bool:
    solver = z3.Solver()
    solver.add(z3.Not(formula))
    return solver.check() == z3.unsat


def _eq(
    left: frog_ast.Expression, right: frog_ast.Expression
) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(frog_ast.BinaryOperators.EQUALS, left, right)


_G = frog_ast.Variable("G")

# ---------------------------------------------------------------------------
# Soundness: two members of one receiver are not the receiver twice
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "src",
    [
        "G.generator == G.identity",
        "G.order == G.generator",
        "S.n == S.m",
        "M.keys == M.values",
    ],
)
@pytest.mark.parametrize("fallback", [False, True])
def test_distinct_members_are_not_equal(src: str, fallback: bool) -> None:
    formula = _encode(src, fallback)
    assert formula is not None
    assert not _valid(formula)


@pytest.mark.parametrize("fallback", [False, True])
def test_group_generator_node_is_not_identity(fallback: bool) -> None:
    expr = _eq(frog_ast.GroupGenerator(_G), frog_ast.FieldAccess(_G, "identity"))
    formula = _encode(expr, fallback)
    assert formula is not None
    assert not _valid(formula)


@pytest.mark.parametrize("fallback", [False, True])
def test_group_order_node_is_not_generator(fallback: bool) -> None:
    expr = _eq(frog_ast.GroupOrder(_G), frog_ast.GroupGenerator(_G))
    formula = _encode(expr, fallback)
    assert formula is not None
    assert not _valid(formula)


def test_member_is_not_its_receiver() -> None:
    # The receiver's own constant used to stand for the access.
    formula = _encode("G.generator")
    assert formula is not None
    assert not formula.eq(z3.Const("G", formula.sort()))


def test_member_read_after_a_write_is_a_new_atom() -> None:
    # `M.keys` before and after a write to `M` may differ.
    before = _encode("M.keys", versions={"M": 0})
    after = _encode("M.keys", versions={"M": 1})
    assert before is not None and after is not None
    assert not _valid(before == after)


def test_call_receiver_refuses() -> None:
    assert _encode("F.f(x).keys == F.f(x).values") is None


# ---------------------------------------------------------------------------
# Completeness: the same member read twice is one atom
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "src",
    [
        "G.generator == G.generator",
        "G.order == G.order",
        "S.n == S.n",
        "M.keys == M.keys",
        "H.domain == H.domain",
        "(G.generator == G.identity) == (G.identity == G.generator)",
    ],
)
@pytest.mark.parametrize("fallback", [False, True])
def test_same_member_is_equal(src: str, fallback: bool) -> None:
    formula = _encode(src, fallback)
    assert formula is not None
    assert _valid(formula)


def test_same_member_same_versions_is_equal() -> None:
    formula = _encode("M.keys == M.keys", versions={"M": 2})
    assert formula is not None
    assert _valid(formula)


def test_group_generator_node_matches_field_access() -> None:
    # `GroupGenerator(G)` and `G.generator` denote the same element.
    expr = _eq(frog_ast.GroupGenerator(_G), frog_ast.FieldAccess(_G, "generator"))
    formula = _encode(expr)
    assert formula is not None
    assert _valid(formula)


def test_two_visitors_share_member_atoms() -> None:
    # The residual check encodes each game with its own visitor.
    first = _encode("G.generator")
    second = _encode("G.generator")
    other = _encode("G.identity")
    assert first is not None and second is not None and other is not None
    assert _valid(first == second)
    assert not _valid(first == other)


def test_deterministic_call_on_member_still_translates() -> None:
    # A call's `func` is a member access; it must stay one stack item.
    formula = _encode("F.f(G.generator) == F.f(G.generator)", fallback=True)
    assert formula is not None
    assert _valid(formula)
    differs = _encode("F.f(G.generator) == F.f(G.identity)", fallback=True)
    assert differs is not None
    assert not _valid(differs)
