"""Regression tests for per-method type-map scoping.

The flat game-wide ``build_game_type_map`` was last-write-wins and scope-blind:
a parameter or local named ``x`` in one method silently overwrote a same-named
binding of a *different* type in a sibling method. Type-directed algebraic
transforms then read a sibling method's type for a bare name, laundering a
wrong type onto an operand and performing an unsound rewrite (audit
F-256/F-261/F-263/F-270/F-308) -- or corrupting a true equivalence
(F-255/F-269/F-287).

``build_method_type_map`` + ``MethodScopedTypeMapMixin`` scope the map to a
single method (fields + only that method's params/locals). These tests pin the
attack shapes (poisoning must NOT fire) alongside positive controls (the
transform still fires where legitimately sound).
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.visitors import (
    build_game_type_map,
    build_method_type_map,
    NameTypeMap,
)
from proof_frog.transforms.algebraic import (
    XorCancellationTransformer,
    TupleEqualityDecomposeTransformer,
    GroupElemCancellationTransformer,
)
from proof_frog.transforms._base import PipelineContext


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    for m in game.methods:
        if m.signature.name == name:
            return m
    raise KeyError(name)


# ---------------------------------------------------------------------------
# build_method_type_map itself
# ---------------------------------------------------------------------------


def test_build_method_type_map_scopes_params_to_method() -> None:
    game = frog_parser.parse_game("""
        Game G(Int q, Int n) {
            ModInt<q> f(ModInt<q> x, ModInt<q> m) { return x + m; }
            BitString<n> g(BitString<n> x) { return x; }
        }
        """)
    f_map = build_method_type_map(game, _method(game, "f"))
    g_map = build_method_type_map(game, _method(game, "g"))
    # ``x`` resolves to each method's OWN parameter type, not the sibling's.
    assert isinstance(f_map.get("x"), frog_ast.ModIntType)
    assert isinstance(g_map.get("x"), frog_ast.BitStringType)
    # The flat map, by contrast, is last-write-wins: g's BitString x clobbers
    # f's ModInt x (this is the defect the scoped map removes).
    flat = build_game_type_map(game)
    assert isinstance(flat.get("x"), frog_ast.BitStringType)


def test_build_method_type_map_local_shadows_field() -> None:
    game = frog_parser.parse_game("""
        Game G(Int n) {
            BitString<n> x;
            Bool f() { ModInt<n> x = 0; return x == 0; }
        }
        """)
    f_map = build_method_type_map(game, _method(game, "f"))
    # The method-local ``x`` (ModInt) shadows the field ``x`` (BitString).
    assert isinstance(f_map.get("x"), frog_ast.ModIntType)


# ---------------------------------------------------------------------------
# F-261 / F-263 -- XorCancellation must not cancel a ModInt chain because a
# sibling method has a BitString parameter of the same name.
# ---------------------------------------------------------------------------

_XOR_POISON = """
    Game G(Int q, Int n) {
        ModInt<q> f(ModInt<q> x, ModInt<q> m) { return x + x + m; }
        BitString<n> g(BitString<n> x) { return x; }
    }
"""

_XOR_POSITIVE = """
    Game G(Int n) {
        BitString<n> f(BitString<n> x, BitString<n> m) { return x + x + m; }
        BitString<n> g(BitString<n> x) { return x; }
    }
"""


def test_f261_xor_cancellation_not_cross_method_poisoned() -> None:
    game = frog_parser.parse_game(_XOR_POISON)
    out = (
        XorCancellationTransformer(build_game_type_map(game), _ctx())
        .scope_to_game(game, None)
        .transform(game)
    )
    # f's ModInt chain x + x + m must survive: NOT cancelled to m.
    assert _method(out, "f") == _method(game, "f")


def test_f261_xor_cancellation_still_fires_on_genuine_bitstring() -> None:
    game = frog_parser.parse_game(_XOR_POSITIVE)
    out = (
        XorCancellationTransformer(build_game_type_map(game), _ctx())
        .scope_to_game(game, None)
        .transform(game)
    )
    # f's genuine BitString chain x + x + m DOES cancel to m.
    body = _method(out, "f").block.statements
    assert len(body) == 1
    ret = body[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    assert ret.expression == frog_ast.Variable("m")


def test_f263_xor_all_cancel_zero_uses_own_method_width() -> None:
    # f returns x + x on a BitString<n> x; a sibling g has a BitString<n + n>
    # parameter also named x. The flat map minted a wrong-width 0^(n + n);
    # per-method scoping mints 0^n (this method's width).
    game = frog_parser.parse_game(
        """
        Game G(Int n) {
            BitString<n> f(BitString<n> x) { return x + x; }
            BitString<n + n> g(BitString<n + n> x) { return x; }
        }
        """
    )
    out = (
        XorCancellationTransformer(build_game_type_map(game), _ctx())
        .scope_to_game(game, None)
        .transform(game)
    )
    ret = _method(out, "f").block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    zero = ret.expression
    assert isinstance(zero, frog_ast.BitStringLiteral)
    # width is n, not n + n
    assert zero.length == frog_ast.Variable("n")


# ---------------------------------------------------------------------------
# F-256 -- TupleEqualityDecompose must use this method's tuple arity, not a
# sibling method's smaller-arity same-named parameter.
# ---------------------------------------------------------------------------


def test_f256_tuple_decompose_uses_own_method_arity() -> None:
    game = frog_parser.parse_game("""
        Game G() {
            Bool O1([Int, Int, Int] x, [Int, Int, Int] y) { return x != y; }
            Bool O2([Int, Int] x, [Int, Int] y) { return x != y; }
        }
        """)
    out = (
        TupleEqualityDecomposeTransformer(_ctx(), build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    # O1 decomposes into THREE component comparisons (its own arity), not two.
    ret = _method(out, "O1").block.statements[0]
    assert isinstance(ret, frog_ast.ReturnStatement)
    # Count the leaf ArrayAccess disequalities in the OR chain.
    leaves: list[frog_ast.Expression] = []
    stack = [ret.expression]
    while stack:
        e = stack.pop()
        if (
            isinstance(e, frog_ast.BinaryOperation)
            and e.operator == frog_ast.BinaryOperators.OR
        ):
            stack.append(e.left_expression)
            stack.append(e.right_expression)
        else:
            leaves.append(e)
    assert len(leaves) == 3


# ---------------------------------------------------------------------------
# F-270 -- GroupElemCancellation must not cancel an Int chain (m / x) * x
# because a sibling method's same-named params are GroupElem.
# ---------------------------------------------------------------------------


def test_f270_groupelem_cancellation_not_cross_method_poisoned() -> None:
    game = frog_parser.parse_game("""
        Game G(Group H) {
            Int Compute(Int m, Int x) { return (m / x) * x; }
            GroupElem<H> ZOracle(GroupElem<H> m, GroupElem<H> x) { return m; }
        }
        """)
    out = (
        GroupElemCancellationTransformer(build_game_type_map(game))
        .scope_to_game(game, None)
        .transform(game)
    )
    # Compute's Int chain (m / x) * x must survive: NOT cancelled to m
    # (truncating Int division makes the cancellation unsound).
    assert _method(out, "Compute") == _method(game, "Compute")
