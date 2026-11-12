"""Tests for UniformModIntRepeatedMask and ExpressAfterUpdate."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.algebraic import (
    ExpressAfterUpdate,
    UniformModIntRepeatedMask,
)
from proof_frog.visitors import NameTypeMap, SearchVisitor


def _ctx() -> PipelineContext:
    lets = NameTypeMap()
    lets.set("G", frog_ast.GroupType())
    return PipelineContext(
        variables={}, proof_let_types=lets, proof_namespace={}, subsets_pairs=[]
    )


def _game(fields: str, body: str) -> frog_ast.Game:
    return frog_parser.parse_game(
        f"""
        Game T(Group G) {{
            {fields}
            [GroupElem<G>, ModInt<G.order>, ModInt<G.order>] f(ModInt<G.order> d, ModInt<G.order> e) {{
                {body}
            }}
        }}
        """
    )


# --- UniformModIntRepeatedMask ---------------------------------------------


def test_mask_repeated_same_combination() -> None:
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "return [G.generator ^ (s + u), s + u];",
    )
    result = UniformModIntRepeatedMask().apply(game, _ctx())
    assert str(result.methods[0].block.statements[-1]) == (
        "return [G.generator ^ u, u];"
    )


def test_mask_no_fire_on_different_combinations() -> None:
    # s + u and e + u are correlated through u: not two independent uniforms.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "return [G.generator ^ (s + u), e + u];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_mask_no_fire_on_bare_use() -> None:
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "return [G.generator ^ (s + u), u];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_mask_no_fire_across_statements() -> None:
    # s changes between the two occurrences, so the two sums differ by d.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "ModInt<G.order> a = s + u;\n"
        "s = s + d;\n"
        "return [G.generator ^ a, s + u];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


# --- ExpressAfterUpdate ----------------------------------------------------


def test_express_after_update() -> None:
    game = _game(
        "ModInt<G.order> s;",
        "GroupElem<G> pk = G.generator ^ (s + d);\n"
        "s = s + d;\n"
        "return [pk, s];",
    )
    result = ExpressAfterUpdate().apply(game, _ctx())
    statements = [str(s) for s in result.methods[0].block.statements]
    assert statements[0] == "s = s + d;"
    assert statements[1] == "GroupElem<G> pk = G.generator ^ s;"


def test_express_after_update_has_no_int_literal_next_to_a_modint() -> None:
    # In terms of the new s, v is s + s + e: rebuilt without the Int literal
    # of 2 * s, which FrogLang refuses next to a ModInt operand and which the
    # engine's type helpers read by its literal, as an Int.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> v = ((s + d) + (s + d)) + e;\n"
        "s = s + d;\n"
        "return [G.generator ^ v, v, e];",
    )
    result = ExpressAfterUpdate().apply(game, _ctx())
    statements = [str(s) for s in result.methods[0].block.statements]
    assert statements[:2] == ["s = s + d;", "ModInt<G.order> v = s + s + e;"]
    integers = SearchVisitor(lambda n: isinstance(n, frog_ast.Integer)).visit(result)
    assert integers is None


def test_express_after_update_no_fire_on_old_value() -> None:
    # pk is the OLD public key: in terms of the new s it is g^(s - d),
    # which is not smaller, so it stays before the update.
    game = _game(
        "ModInt<G.order> s;",
        "GroupElem<G> pk = G.generator ^ s;\n"
        "s = s + d;\n"
        "return [pk, s];",
    )
    assert ExpressAfterUpdate().apply(game, _ctx()) == game


def test_express_after_update_no_fire_when_used_before() -> None:
    game = _game(
        "ModInt<G.order> s;\nModInt<G.order> t;",
        "ModInt<G.order> x = s + d;\n"
        "t = x;\n"
        "s = s + d;\n"
        "return [G.generator ^ x, s];",
    )
    assert ExpressAfterUpdate().apply(game, _ctx()) == game


def test_express_after_update_no_fire_on_unsimplified_old_value() -> None:
    # pk = g^(s - t) * g^t is the OLD key g^s, merely not yet simplified. In
    # terms of the new s it is g^(s + t - (t + d)), smaller than the spelling
    # above but not than pk's normal form g^s, so nothing cancels and the
    # read stays before the update.
    game = _game(
        "ModInt<G.order> s;\nModInt<G.order> t;",
        "GroupElem<G> pk = G.generator ^ (s - t) * G.generator ^ t;\n"
        "s = s + d;\n"
        "return [pk, s, t];",
    )
    assert ExpressAfterUpdate().apply(game, _ctx()) == game


def test_express_after_update_no_fire_when_delta_reads_the_field() -> None:
    # delta = H(g^(s*e)) depends on s: after the update it reads the NEW s,
    # so g^(s - delta) after the update is not the old g^(s + delta - delta').
    game = frog_parser.parse_game(
        """
        Game T(Group G) {
            ModInt<G.order> s;
            GroupElem<G> f(Function<GroupElem<G>, ModInt<G.order>> H, ModInt<G.order> e) {
                GroupElem<G> pk = G.generator ^ (s + H(G.generator ^ (s * e)));
                s = s + H(G.generator ^ (s * e));
                return pk;
            }
        }
        """
    )
    assert ExpressAfterUpdate().apply(game, _ctx()) == game


def test_mask_no_fire_with_a_third_use_elsewhere() -> None:
    # Regression: u appears twice as s + u and once on its own (in g^u).
    # Replacing the two sums by u would make the first component g^u while
    # the others become u, breaking g^(second) == first. A use counter
    # capped at 2 once let this through.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "return [G.generator ^ u, s + u, s + u];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_mask_no_fire_on_nondeterministic_partner() -> None:
    # F.Sample() is evaluated once per copy: F.Sample() + u twice is two
    # different values, not u twice.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "return [G.generator ^ (F.Sample() + u), F.Sample() + u, d];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_mask_no_fire_across_branches_of_one_statement() -> None:
    # s changes between the copy in the condition and the one returned.
    game = frog_parser.parse_game(
        """
        Game T(Group G) {
            ModInt<G.order> s;
            ModInt<G.order> f(ModInt<G.order> d) {
                ModInt<G.order> u <- ModInt<G.order>;
                if (s + u == d) {
                    s = s + d;
                    return s + u;
                }
                return d;
            }
        }
        """
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_f370_mask_no_fire_past_a_bare_redeclaration() -> None:
    # F-370(a), case RM1: after the bare re-declaration ModInt<G.order> u;,
    # the u the return reads is not the draw, so s + u is not uniform.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> u <- ModInt<G.order>;\n"
        "ModInt<G.order> u;\n"
        "return [G.generator ^ (s + u), s + u, e];",
    )
    assert UniformModIntRepeatedMask().apply(game, _ctx()) == game


def test_f370_express_after_update_no_fire_past_a_bare_redeclaration() -> None:
    # F-370(a), case E3: the bare re-declaration ModInt<G.order> v; between
    # the value and the update was not seen as a use of v; moving the value
    # below it would make the return read the moved value.
    game = _game(
        "ModInt<G.order> s;",
        "ModInt<G.order> v = s + d;\n"
        "ModInt<G.order> v;\n"
        "s = s + d;\n"
        "return [G.generator ^ v, v, e];",
    )
    assert ExpressAfterUpdate().apply(game, _ctx()) == game
