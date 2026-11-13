"""Tests for ModIntCancellation: ModInt arithmetic whose terms cancel."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import ModIntCancellation
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    group = frog_ast.Variable("G")
    lets.set("G", frog_ast.GroupType())
    lets.set(
        "H",
        frog_ast.FunctionType(
            frog_ast.GroupElemType(group),
            frog_ast.ModIntType(frog_ast.FieldAccess(group, "order")),
        ),
    )
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _return_of(game: frog_ast.Game) -> frog_ast.Expression:
    statement = game.methods[0].block.statements[-1]
    assert isinstance(statement, frog_ast.ReturnStatement)
    return statement.expression


def _apply(body: str) -> tuple[frog_ast.Game, frog_ast.Game]:
    game = frog_parser.parse_game(
        f"""
        Game T(Group G) {{
            ModInt<G.order> sk;
            ModInt<G.order> f(ModInt<G.order> d, ModInt<G.order> u, ModInt<G.order> a, ModInt<G.order> b) {{
                {body}
            }}
        }}
        """
    )
    return game, ModIntCancellation().apply(game, _ctx())


def test_hash_term_cancels() -> None:
    _, result = _apply(
        "return sk + ((d + H(G.generator ^ (sk * u))) - H(G.generator ^ (sk * u)));"
    )
    out = _return_of(result)
    assert "H(" not in str(out)
    assert str(out) in ("sk + d", "d + sk")


def test_cancellation_inside_larger_statement() -> None:
    _, result = _apply(
        "ModInt<G.order> x = a * (b + 1) - a;\nreturn x;"
    )
    first = result.methods[0].block.statements[0]
    assert isinstance(first, frog_ast.Assignment)
    assert str(first.value) in ("a * b", "b * a")


def test_no_fire_without_cancellation() -> None:
    game, result = _apply("return a * (b + d);")
    assert result == game


def test_no_fire_on_nondeterministic_call() -> None:
    # Two draws of a non-deterministic primitive method are different
    # values: (d + F.Sample()) - F.Sample() is not d.
    game, result = _apply("return (d + F.Sample()) - F.Sample();")
    assert result == game


def test_f370_sibling_declarations_are_not_typed_by_the_last_one() -> None:
    # F-370(a), case N2: the method's type map is last-write-wins, so the
    # if-block's ModInt locals a and d read as the group elements declared
    # after the if, and (a / (d * d)) * d ^ 2 cancelled to a as if in a
    # group. In ModInt<q> it is not a when d = 0. A term that reads neither
    # name still cancels.
    game = frog_parser.parse_game(
        """
        Game Left(Int q, Group G) {
            ModInt<q> Probe(Bool c, ModInt<q> a0, ModInt<q> d0, ModInt<q> b, ModInt<q> e, GroupElem<G> h) {
                if (c) {
                    ModInt<q> a = a0 * a0 * a0;
                    ModInt<q> d = d0 * d0 * d0;
                    return b * ((a / (d * d)) * (d ^ 2)) + ((e + b) - b);
                }
                GroupElem<G> a = h * h;
                GroupElem<G> d = h * h * h;
                return b + b;
            }
        }
        """
    )
    lets = NameTypeMap()
    lets.set("q", frog_ast.IntType())
    lets.set("G", frog_ast.GroupType())
    ctx = PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )
    result = ModIntCancellation().apply(game, ctx)
    branch = result.methods[0].block.statements[0]
    assert isinstance(branch, frog_ast.IfStatement)
    assert str(branch.blocks[0].statements[-1]).strip() == (
        "return b * (a / (d * d) * d ^ 2) + e;"
    )


# F-378: a ModInt zero is rebuilt as the Int literal 0 only where an Int
# operand does not change the operation around it.


def test_f378_zero_power_base_is_kept() -> None:
    # (a - a) ^ 0 is 1 mod q; with the Int 0 as its base it would be the Int
    # power 0 ^ 0. The comparison's b - b still cancels.
    _, result = _apply("return (a - a) ^ 0 + (a - a) ^ 0 == b - b;")
    assert _return_of(result) == frog_parser.parse_expression(
        "(a - a) ^ 0 + (a - a) ^ 0 == 0"
    )


def test_f378_zero_division_operands_are_kept() -> None:
    # 0 / 0 would be an Int division.
    game, result = _apply("return (a - a) / (b - b);")
    assert result == game


def test_f378_zero_under_negation_in_power_base_is_kept() -> None:
    # -e has the type of e: -0 would make the power an Int one.
    game, result = _apply("return (-(a - a)) ^ 0;")
    assert result == game


def test_f378_zero_next_to_int_literal_is_kept() -> None:
    # (a - a) + 1 is 1 mod q, kept whole (F-357); its zero operand is not
    # rewritten either, since 0 + 1 would be the Int 1.
    game, result = _apply("return (a - a) + 1;")
    assert result == game


def test_f378_kept_zero_stays_whole() -> None:
    # The parts of a kept zero are not rewritten one by one: the base does
    # not become b - b.
    game, result = _apply("return ((a + b) - a - b) ^ 2;")
    assert result == game


def test_f378_zero_elsewhere_still_cancels() -> None:
    _, result = _apply("return (a - a) * b + d;")
    assert _return_of(result) == frog_parser.parse_expression("d")
    _, result = _apply("return a - a;")
    assert _return_of(result) == frog_ast.Integer(0)
    _, result = _apply("return (a - a) == b;")
    assert _return_of(result) == frog_parser.parse_expression("0 == b")
