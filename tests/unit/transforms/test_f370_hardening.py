"""Hardening of the algebra and state-relation passes (F-370 parts (d) to (k)).

Each case was reproduced at pass level only: no parsed, well-typed proof is
known to reach it. The tests apply one pass (or helper) to a hand-written
game and check that it declines, next to a control on which it still fires.
"""

import copy

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms import state_relations
from proof_frog.transforms._algebra import Normalizer
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import BlockedLocalAbsorption, ModIntCancellation
from proof_frog.transforms.control_flow import GuardConditionSimplification
from proof_frog.transforms.state_relations import (
    FieldInvariantElimination,
    ForwardLiteralFieldWrite,
    GeneratorPowerFieldToExponent,
    OffsetFusion,
)
from proof_frog.visitors import NameTypeMap

# pylint: disable=protected-access


def _ctx(**lets: frog_ast.Type) -> PipelineContext:
    types = NameTypeMap()
    for name, the_type in lets.items():
        types.set(name, the_type)
    return PipelineContext(
        variables={}, proof_let_types=types, proof_namespace={}, subsets_pairs=[]
    )


def _group_ctx() -> PipelineContext:
    return _ctx(G=frog_ast.GroupType(), q=frog_ast.IntType(), n=frog_ast.IntType())


def _method(game: frog_ast.Game, name: str) -> frog_ast.Method:
    return next(m for m in game.methods if m.signature.name == name)


def _field_names(game: frog_ast.Game) -> list[str]:
    return [field.name for field in game.fields]


def _reasons(ctx: PipelineContext, transform: str) -> list[str]:
    return [nm.reason for nm in ctx.near_misses if nm.transform_name == transform]


# --- (d) Field Invariant Elimination's verdict cache --------------------------

_CACHE_GAME = """
Game G(Int n) {
    BitString<n> a;
    BitString<n> b;
    Void Initialize() {
        a = 0^n;
        b = 0^n;
    }
    Void Upd(BitString<n> x, BitString<n> y) {
        a = (x || y)[0 : n];
        b = (x || y)[0 : n];
    }
    BitString<n> GetA() { return a; }
}
"""


def test_f370d_cache_tells_apart_games_that_print_alike() -> None:
    # G2 writes a = x || y[0 : n] (built by hand), which prints like G1's
    # (x || y)[0 : n]. A verdict for G1 must not answer for G2.
    g1 = frog_parser.parse_game(_CACHE_GAME)
    g2 = copy.deepcopy(g1)
    x, y, n = (frog_ast.Variable(name) for name in "xyn")
    _method(g2, "Upd").block.statements[0].value = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.OR, x, frog_ast.Slice(y, frog_ast.Integer(0), n)
    )
    assert str(g1) == str(g2) and g1 != g2
    ctx = _ctx(n=frog_ast.IntType())
    b = frog_ast.Variable("b")
    state_relations._proof_cache.clear()
    try:
        assert state_relations._cached_preserves(g1, "a", b, ctx)[0] is True
        assert state_relations._cached_preserves(g2, "a", b, ctx)[0] is False
    finally:
        state_relations._proof_cache.clear()


# --- (e) the normalizer's generator symbol ------------------------------------


def test_f370e_generators_of_groups_that_print_alike_stay_apart() -> None:
    # A Variable named "E.G" and the access E.G print alike; the generator
    # of the second must not be rebuilt as the first's.
    dotted = frog_ast.Variable("E.G")
    accessed = frog_ast.FieldAccess(frog_ast.Variable("E"), "G")
    q = frog_ast.Variable("q")
    types = NameTypeMap()
    types.set(
        "H1",
        frog_ast.FunctionType(frog_ast.GroupElemType(dotted), frog_ast.ModIntType(q)),
    )
    types.set(
        "H2",
        frog_ast.FunctionType(frog_ast.GroupElemType(accessed), frog_ast.ModIntType(q)),
    )
    first = frog_ast.FuncCall(
        frog_ast.Variable("H1"), [frog_ast.GroupGenerator(dotted)]
    )
    second = frog_ast.FuncCall(
        frog_ast.Variable("H2"),
        [
            frog_ast.BinaryOperation(
                frog_ast.BinaryOperators.EXPONENTIATE,
                frog_ast.GroupGenerator(accessed),
                frog_ast.Integer(1),
            )
        ],
    )
    out = Normalizer(types).canonical(
        frog_ast.BinaryOperation(frog_ast.BinaryOperators.ADD, first, second)
    )
    rebuilt = out.right_expression.args[0]
    assert rebuilt == frog_ast.FieldAccess(copy.deepcopy(accessed), "generator")


# --- (f) Guard Condition Simplification's implied facts -----------------------


def test_f370f_concatenation_guard_settles_no_bit_string() -> None:
    # `x || y` on bit strings is a concatenation (an AST no front end makes
    # a guard); its "parts" x and y are not flags.
    game = frog_parser.parse_game("""Game T() {
        BitString<8> Q(BitString<4> x, BitString<4> y) {
          if (x || y) { return 0^8; }
          return x || y; } }""")
    assert GuardConditionSimplification().apply(game, _ctx()) == game


def test_f370f_boolean_guard_still_settles_its_flags() -> None:
    game = frog_parser.parse_game("""Game T() {
        Bool revealed;
        Bool challenged;
        Int Q(Int x) {
          if (revealed || !challenged) { return 0; }
          if (revealed) { return 1; }
          return x; } }""")
    out = GuardConditionSimplification().apply(game, _ctx())
    second = _method(out, "Q").block.statements[1]
    assert second.conditions[0] == frog_ast.Boolean(False)


# --- (g) Field Invariant Elimination: a coercing store into a tuple -----------


def test_f370g_store_into_a_tuple_with_a_modint_part_coerces() -> None:
    q = frog_ast.Variable("q")
    target = frog_ast.ProductType([frog_ast.ModIntType(q), frog_ast.IntType()])
    ints = frog_ast.ProductType([frog_ast.IntType(), frog_ast.IntType()])
    assert state_relations._coerces(target, ints) is True
    assert state_relations._coerces(target, copy.deepcopy(target)) is False
    assert state_relations._coerces(ints, copy.deepcopy(ints)) is False


def test_f370g_executor_does_not_read_a_coerced_tuple_as_its_value() -> None:
    # [ModInt<q>, Int] t = [n, n]; holds n reduced mod q in its first part:
    # the executor must give t a fresh value, not the tuple of Ints.
    method = frog_parser.parse_method("""Void F(Int n) {
            [ModInt<q>, Int] t = [n, n];
        }""")
    types = NameTypeMap()
    types.set("n", frog_ast.IntType())
    types.set(
        "t",
        frog_ast.ProductType(
            [frog_ast.ModIntType(frog_ast.Variable("q")), frog_ast.IntType()]
        ),
    )
    import itertools  # pylint: disable=import-outside-toplevel

    executor = state_relations._SymbolicExecutor(
        types, _ctx(q=frog_ast.IntType()), itertools.count()
    )
    env = {"n": frog_ast.Variable("n")}
    paths = executor.run(list(method.block.statements), [state_relations._Path(env)])
    assert state_relations._is_symbol(paths[0].env["t"])


# --- (h) ModInt Cancellation emits no Int literal next to a ModInt ------------


def _mic_return(expr: str) -> frog_ast.Expression:
    game = frog_parser.parse_game(f"""Game T(Int q) {{
        ModInt<q> Probe(ModInt<q> s, ModInt<q> u) {{
            return {expr};
        }} }}""")
    out = ModIntCancellation().apply(game, _ctx(q=frog_ast.IntType()))
    return _method(out, "Probe").block.statements[0].expression


def test_f370h_coefficient_is_rebuilt_as_repeated_addition() -> None:
    # (u + s) + (u - s) is 2u; `2 * u` is an Int literal times a ModInt,
    # which the engine's type helpers read as an Int.
    assert str(_mic_return("(u + s) + (u - s)")) == "u + u"


def test_f370h_large_coefficient_is_kept_as_written() -> None:
    expr = "(u + u + u + u + u + s) - s"
    out = _mic_return(expr)
    assert not any(
        isinstance(node, frog_ast.Integer) for node in _nodes(out)
    ), f"rebuilt with an Int literal: {out}"


def _nodes(node: frog_ast.ASTNode) -> list[frog_ast.ASTNode]:
    found: list[frog_ast.ASTNode] = [node]
    for value in vars(node).values():
        children = value if isinstance(value, list) else [value]
        for child in children:
            if isinstance(child, frog_ast.ASTNode):
                found.extend(_nodes(child))
    return found


# --- (i) Offset Fusion: a bare block statement --------------------------------

_OFFSET_GAME = """
Game T(Group G) {
    GroupElem<G> P;
    ModInt<G.order> D;
    Void Initialize() {
        ModInt<G.order> e <- ModInt<G.order>;
        P = G.generator ^ e;
        D = 0;
    }
    GroupElem<G> Shift(ModInt<G.order> r) {
        if (true) { D = D + r; }
        return P * G.generator ^ D;
    }
}
"""


def test_f370i_offset_write_in_a_bare_block_is_tracked() -> None:
    game = frog_parser.parse_game(_OFFSET_GAME)
    shift = _method(game, "Shift")
    statements = list(shift.block.statements)
    statements[0] = frog_ast.Block(list(statements[0].blocks[0].statements))
    shift.block = frog_ast.Block(statements)
    fixed = next(f for f in game.fields if f.name == "P")
    offset = next(f for f in game.fields if f.name == "D")
    fused = state_relations._fuse(
        game, state_relations._initialize(game), fixed, offset, _group_ctx()
    )
    assert fused is not None
    block = _method(fused, "Shift").block.statements[0]
    assert isinstance(block, frog_ast.Block)
    assert any(
        isinstance(s, frog_ast.Assignment) and s.var == frog_ast.Variable("P@fused")
        for s in block.statements
    )


def test_f370i_return_in_a_bare_block_sets_the_fused_field() -> None:
    inner = frog_ast.Block([frog_ast.ReturnStatement(frog_ast.Integer(0))])
    out = state_relations._before_exits(
        frog_ast.Block([inner]), lambda: frog_ast.FuncCall(frog_ast.Variable("f"), [])
    )
    nested = out.statements[0]
    assert isinstance(nested, frog_ast.Block)
    assert isinstance(nested.statements[0], frog_ast.FuncCall)


# --- (j) the state-relation passes and names bound twice ----------------------

_FIE_REDECLARED = """
Game T(Int q) {{
    Int b;
    Int a;
    Void Initialize(Int n) {{
        b = n;
        a = n + 1;
    }}
    Void Inc(Bool c) {{
        if (c) {{ Int x = b + 1; b = x; a = x + 1; }}
        else {{ Int {second} = b + 2; b = {second}; a = {second} + 1; }}
    }}
    Int Get() {{
        return a;
    }}
}}
"""


def test_f370j_fie_declines_a_method_binding_a_name_twice() -> None:
    game = frog_parser.parse_game(_FIE_REDECLARED.format(second="x"))
    out = FieldInvariantElimination().apply(game, _ctx(q=frog_ast.IntType()))
    assert "a" in _field_names(out)


def test_f370j_fie_still_eliminates_with_distinct_names() -> None:
    game = frog_parser.parse_game(_FIE_REDECLARED.format(second="y"))
    out = FieldInvariantElimination().apply(game, _ctx(q=frog_ast.IntType()))
    assert "a" not in _field_names(out)


_GPFE_REDECLARED = """
Game T(Group G) {{
    GroupElem<G> h;
    Void Initialize() {{
        ModInt<G.order> e <- ModInt<G.order>;
        h = G.generator ^ e;
    }}
    GroupElem<G> Upd(Bool c, ModInt<G.order> r) {{
        if (c) {{ ModInt<G.order> d = r; h = h * G.generator ^ d; }}
        else {{ ModInt<G.order> {second} = r + r; h = h * G.generator ^ {second}; }}
        return h;
    }}
}}
"""


def test_f370j_gpfe_declines_an_exponent_naming_a_name_bound_twice() -> None:
    game = frog_parser.parse_game(_GPFE_REDECLARED.format(second="d"))
    ctx = _group_ctx()
    out = GeneratorPowerFieldToExponent().apply(game, ctx)
    assert "h" in _field_names(out)
    assert any("'d'" in r for r in _reasons(ctx, "Generator Power Field To Exponent"))


def test_f370j_gpfe_still_fires_with_distinct_names() -> None:
    game = frog_parser.parse_game(_GPFE_REDECLARED.format(second="d2"))
    out = GeneratorPowerFieldToExponent().apply(game, _group_ctx())
    assert "h" not in _field_names(out)


_OFFSET_REDECLARED = """
Game T(Group G) {{
    GroupElem<G> P;
    ModInt<G.order> D;
    Void Initialize(Bool c) {{
        ModInt<G.order> e <- ModInt<G.order>;
        P = G.generator ^ e;
        D = 0;
        if (c) {{ ModInt<G.order> {second} <- ModInt<G.order>; D = {second}; }}
    }}
    GroupElem<G> Shift(ModInt<G.order> r) {{
        D = D + r;
        return P * G.generator ^ D;
    }}
}}
"""


def test_f370j_offset_fusion_declines_an_exponent_naming_a_name_bound_twice() -> None:
    game = frog_parser.parse_game(_OFFSET_REDECLARED.format(second="e"))
    ctx = _group_ctx()
    fixed = next(f for f in game.fields if f.name == "P")
    offset = next(f for f in game.fields if f.name == "D")
    init = state_relations._initialize(game)
    assert state_relations._fuse(game, init, fixed, offset, ctx) is None
    assert any("'e'" in r for r in _reasons(ctx, "Offset Fusion"))


def test_f370j_offset_fusion_still_fuses_with_distinct_names() -> None:
    game = frog_parser.parse_game(_OFFSET_REDECLARED.format(second="e2"))
    fixed = next(f for f in game.fields if f.name == "P")
    offset = next(f for f in game.fields if f.name == "D")
    init = state_relations._initialize(game)
    assert state_relations._fuse(game, init, fixed, offset, _group_ctx()) is not None


# --- (k) coercing stores: an Int stored into a ModInt is not the Int ----------

_COERCED_INVARIANT = """
Game T(Int q, Group G) {{
    Int b;
    {a_type} a;
    Void Initialize(Int n) {{
        b = n;
        a = n + 1;
    }}
    Void Inc() {{
        b = b + 1;
        a = b + 1;
    }}
    GroupElem<G> Get() {{
        return G.generator ^ a;
    }}
}}
"""


def test_f370k_fie_keeps_a_field_holding_an_int_reduced_mod_q() -> None:
    game = frog_parser.parse_game(_COERCED_INVARIANT.format(a_type="ModInt<q>"))
    out = FieldInvariantElimination().apply(game, _group_ctx())
    assert "a" in _field_names(out)


def test_f370k_fie_removes_the_same_field_of_type_int() -> None:
    game = frog_parser.parse_game(_COERCED_INVARIANT.format(a_type="Int"))
    out = FieldInvariantElimination().apply(game, _group_ctx())
    assert "a" not in _field_names(out)


_COERCED_LITERAL = """
Game T(Int q) {{
    {f_type} f;
    {f_type} Get() {{
        f = 7;
        return f + f;
    }}
    {f_type} Read() {{
        return f;
    }}
}}
"""


def test_f370k_flfw_keeps_a_literal_stored_into_a_modint() -> None:
    game = frog_parser.parse_game(_COERCED_LITERAL.format(f_type="ModInt<q>"))
    out = ForwardLiteralFieldWrite().apply(game, _ctx(q=frog_ast.IntType()))
    assert str(_method(out, "Get").block.statements[1]) == "return f + f;"


def test_f370k_flfw_forwards_a_literal_into_an_int() -> None:
    game = frog_parser.parse_game(_COERCED_LITERAL.format(f_type="Int"))
    out = ForwardLiteralFieldWrite().apply(game, _ctx(q=frog_ast.IntType()))
    assert str(_method(out, "Get").block.statements[1]) == "return 7 + 7;"


_COERCED_ABSORPTION = """
Game T(Int q, Group G) {{
    Int b;
    GroupElem<G> Get() {{
        {x_type} x = b;
        b = b + 1;
        return G.generator ^ x;
    }}
}}
"""


def test_f370k_bla_keeps_a_local_holding_an_int_reduced_mod_q() -> None:
    game = frog_parser.parse_game(_COERCED_ABSORPTION.format(x_type="ModInt<q>"))
    out = BlockedLocalAbsorption().apply(game, _group_ctx())
    assert str(_method(out, "Get").block.statements[0]) == "ModInt<q> x = b;"


def test_f370k_bla_absorbs_the_same_local_of_type_int() -> None:
    game = frog_parser.parse_game(_COERCED_ABSORPTION.format(x_type="Int"))
    out = BlockedLocalAbsorption().apply(game, _group_ctx())
    assert str(_method(out, "Get").block.statements[0]) != "Int x = b;"
