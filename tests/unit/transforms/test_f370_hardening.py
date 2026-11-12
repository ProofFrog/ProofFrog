"""Hardening of the algebra passes (F-370 parts (e), (f), (h) and (k)).

Each case was reproduced at pass level only: no parsed, well-typed proof is
known to reach it. The tests apply one pass (or helper) to a hand-written
game and check that it declines, next to a control on which it still fires.
"""

import copy

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._algebra import Normalizer
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import BlockedLocalAbsorption, ModIntCancellation
from proof_frog.transforms.control_flow import GuardConditionSimplification
from proof_frog.visitors import NameTypeMap


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


# --- (k) coercing stores: an Int stored into a ModInt is not the Int ----------

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
