"""F-356: an Int stored into a ModInt is reduced, so it must not be forwarded.

FrogLang accepts an ``Int`` wherever a ``ModInt<q>`` is expected, and the
stored value is the ``Int`` reduced modulo ``q``: after ``ModInt<q> x = b;``
the variable ``x`` holds ``b mod q``. A pass that reads ``x`` as ``b`` (or
replaces ``b`` by ``x``) changes the game, e.g. ``x == z`` (a comparison of
``ModInt`` values) becomes the integer comparison ``b == z``.

These tests cover the shared check (:mod:`proof_frog.transforms._coercion`),
each pass that forwards a stored value (it declines on a converting store,
with a near miss, and still fires on a store that keeps its value), and the
inliner, which binds a ``ModInt`` parameter or return value to a typed
variable instead of substituting the expression.
"""

from __future__ import annotations

import pytest

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext, TransformPass
from proof_frog.transforms._coercion import coercing_store_names, store_keeps_value
from proof_frog.transforms.algebraic import InjectiveEqualitySimplify
from proof_frog.transforms.control_flow import (
    FoldEquivalentReturnBranchTransformer,
    IfConditionAliasSubstitution,
)
from proof_frog.transforms.inlining import (
    CrossMethodFieldAlias,
    ForwardExpressionAlias,
    HoistFieldPureAlias,
    IfSplitBranchAssignment,
    InlineLocalTupleLiteral,
    InlineMultiUsePureExpression,
    InlineSingleUseField,
    InlineSingleUseVariable,
    RedundantCopy,
    RedundantFieldCopy,
    _build_local_stable_alias_map,
)
from proof_frog.transforms.random_functions import _build_local_assignments
from proof_frog.visitors import InlineTransformer, NameTypeMap


def _ctx(
    namespace: frog_ast.Namespace | None = None,
    lets: dict[str, frog_ast.Type] | None = None,
) -> PipelineContext:
    let_types = NameTypeMap()
    for name, the_type in (lets or {}).items():
        let_types.set(name, the_type)
    return PipelineContext(
        variables={},
        proof_let_types=let_types,
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


def _namespace(primitive_src: str) -> frog_ast.Namespace:
    primitive = frog_parser.parse_primitive_file(primitive_src)
    return {"P": primitive}


_INT_PRIMITIVE = """
Primitive P(Int q) {
    deterministic injective Int f(Int x);
}
"""


# ---------------------------------------------------------------------------
# The shared check
# ---------------------------------------------------------------------------


def _type(src: str) -> frog_ast.Type:
    game = frog_parser.parse_game(f"Game T() {{ {src} slot; Void Initialize() {{ }} }}")
    return game.fields[0].type


def _types(**names: str) -> NameTypeMap:
    type_map = NameTypeMap()
    for name, src in names.items():
        type_map.set(name, _type(src))
    return type_map


_MAP = _types(b="Int", c="Int", a="ModInt<q>", u="ModInt<5>", s="Set<Int>")


@pytest.mark.parametrize(
    "target, value, keeps",
    [
        ("ModInt<q>", "b", False),
        ("ModInt<q>", "b + c", False),
        ("ModInt<q>", "|s|", False),
        ("ModInt<q>", "a", True),
        ("ModInt<q>", "a + a", True),
        ("ModInt<q>", "0", True),
        ("ModInt<q>", "1", False),
        ("ModInt<5>", "3", True),
        ("ModInt<5>", "5", False),
        ("ModInt<q>", "unknown", False),
        ("ModInt<q>?", "None", True),
        ("Int", "b", True),
        ("BitString<8>", "unknown", True),
        ("[ModInt<q>, Int]", "[b, c]", False),
        ("[ModInt<q>, Int]", "[a, c]", True),
        ("Set<ModInt<q>>", "{b}", False),
        ("Set<ModInt<q>>", "{a}", True),
    ],
)
def test_f356_store_keeps_value(target: str, value: str, keeps: bool) -> None:
    expr = frog_parser.parse_expression(value)
    assert store_keeps_value(_type(target), expr, _MAP) is keeps


def test_f356_coercing_store_names_covers_every_store_form() -> None:
    game = frog_parser.parse_game("""
        Game T(Int q) {
            ModInt<q> f;
            ModInt<q> g;
            Map<Int, ModInt<q>> M;
            Void Initialize() {
                f = q;
            }
            Bool O(Int b, ModInt<q> a) {
                ModInt<q> x = b;
                ModInt<q> y = a;
                ModInt<q> w = 0;
                w = b;
                [ModInt<q>, Int] t = [b, b];
                M[b] = b;
                g = a;
                return x == y;
            }
        }
        """)
    names = coercing_store_names(
        game, _ctx(lets={"q": frog_ast.IntType()}).proof_let_types
    )
    assert names == {"f", "x", "w", "t", "M"}


def test_f356_no_modint_no_coercing_store() -> None:
    game = frog_parser.parse_game("""
        Game T() {
            Bool O(Int b) {
                Int x = b;
                return x == b;
            }
        }
        """)
    assert not coercing_store_names(game)


# ---------------------------------------------------------------------------
# The forwarding passes
# ---------------------------------------------------------------------------


def _near_miss_names(ctx: PipelineContext, transform: str) -> set[str | None]:
    return {
        nm.variable
        for nm in ctx.near_misses
        if nm.transform_name == transform and "ModInt" in nm.reason
    }


# (pass, near-miss transform name, game, name kept, name forwarded)
_PASS_CASES = [
    (
        RedundantCopy(),
        "Remove Redundant Copies",
        """
        Game T(Int q) {
            Bool O(Int b, ModInt<q> a) {
                ModInt<q> x = b;
                ModInt<q> y = a;
                return x == y;
            }
        }
        """,
        "x",
        "y",
    ),
    (
        InlineSingleUseVariable(),
        "Inline Single-Use Variable",
        """
        Game T(Int q) {
            Bool O(Int b, ModInt<q> a) {
                ModInt<q> x = b + 1;
                ModInt<q> y = a + a;
                return x == y;
            }
        }
        """,
        "x",
        "y",
    ),
    (
        InlineMultiUsePureExpression(),
        "Inline Multi-Use Pure Expressions",
        """
        Game T(Int q) {
            Bool O(Int b, ModInt<q> a) {
                ModInt<q> x = b + 1;
                ModInt<q> y = a + a;
                return x == y && y == x;
            }
        }
        """,
        "x",
        "y",
    ),
    (
        InlineLocalTupleLiteral(),
        "Inline Local Tuple Literal",
        """
        Game T(Int q) {
            Bool O(Int b, ModInt<q> a) {
                [ModInt<q>, Int] x = [b, b];
                [ModInt<q>, Int] y = [a, b];
                return x[0] == y[0];
            }
        }
        """,
        "x",
        "y",
    ),
    (
        ForwardExpressionAlias(),
        "Forward Expression Alias",
        """
        Game T(Int q) {
            Int O(Int b) {
                ModInt<q> x = b + 1;
                Int y = b + 2;
                Int r = b + 1;
                Int s = b + 2;
                return r + s;
            }
        }
        """,
        "x",
        None,
    ),
]


@pytest.mark.parametrize(
    "the_pass, transform_name, source, kept, forwarded",
    _PASS_CASES,
    ids=[case[1] for case in _PASS_CASES],
)
def test_f356_pass_keeps_converting_store(
    the_pass: TransformPass,
    transform_name: str,
    source: str,
    kept: str,
    forwarded: str | None,
) -> None:
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    result = the_pass.apply(game, ctx)
    text = str(result)
    assert f"ModInt<q> {kept} = " in text or f"{kept} = [" in text, text
    if forwarded is not None:
        assert f" {forwarded} = " not in text, text
    assert kept in _near_miss_names(ctx, transform_name)


def test_f356_forward_expression_alias_still_aliases_exact_store() -> None:
    game = frog_parser.parse_game("""
        Game T(Int q) {
            Int O(Int b) {
                Int y = b + 2;
                Int s = b + 2;
                return s;
            }
        }
        """)
    result = ForwardExpressionAlias().apply(game, _ctx())
    assert "Int s = y;" in str(result)


def test_f356_forward_expression_alias_converting_store_not_aliased() -> None:
    game = frog_parser.parse_game("""
        Game T(Int q) {
            Int O(Int b) {
                ModInt<q> x = b + 1;
                Int r = b + 1;
                return r;
            }
        }
        """)
    ctx = _ctx()
    result = ForwardExpressionAlias().apply(game, ctx)
    assert "Int r = b + 1;" in str(result)
    assert "x" in _near_miss_names(ctx, "Forward Expression Alias")


def test_f356_if_split_branch_assignment() -> None:
    converting = frog_parser.parse_game("""
        Game T(Int q) {
            Bool O(Bool c, Int b, ModInt<q> a) {
                ModInt<q> x;
                if (c) {
                    x = b;
                } else {
                    x = a;
                }
                return x == a;
            }
        }
        """)
    ctx = _ctx()
    assert IfSplitBranchAssignment().apply(converting, ctx) == converting
    assert "x" in _near_miss_names(ctx, "If-Split Branch Assignment")

    exact = frog_parser.parse_game("""
        Game T(Int q) {
            Bool O(Bool c, ModInt<q> d, ModInt<q> a) {
                ModInt<q> x;
                if (c) {
                    x = d;
                } else {
                    x = a;
                }
                return x == a;
            }
        }
        """)
    assert IfSplitBranchAssignment().apply(exact, _ctx()) != exact


def test_f356_hoist_field_pure_alias() -> None:
    def game(field_type: str) -> frog_ast.Game:
        return frog_parser.parse_game(f"""
            Game T(Int q) {{
                Int g;
                {field_type} f;
                Void O(Int k) {{
                    Int v = k;
                    g = v + 1;
                    f = v;
                }}
            }}
            """)

    ctx = _ctx()
    converting = game("ModInt<q>")
    assert HoistFieldPureAlias().apply(converting, ctx) == converting
    assert "f" in _near_miss_names(ctx, "Hoist Field Pure Alias")

    assert "g = f + 1;" in str(HoistFieldPureAlias().apply(game("Int"), _ctx()))


def test_f356_redundant_field_copy() -> None:
    other_type = frog_parser.parse_game("""
        Game T(Int q) {
            ModInt<q>? f;
            Void O(Int b) {
                ModInt<q> v = b;
                f = v;
            }
        }
        """)
    ctx = _ctx()
    assert "ModInt<q> v = b;" in str(RedundantFieldCopy().apply(other_type, ctx))
    assert "v" in _near_miss_names(ctx, "Remove redundant variables for fields")

    # The field converts `b` the same way, so the copy is still redundant.
    same_type = frog_parser.parse_game("""
        Game T(Int q) {
            ModInt<q> f;
            Void O(Int b) {
                ModInt<q> v = b;
                f = v;
            }
        }
        """)
    assert "f = b;" in str(RedundantFieldCopy().apply(same_type, _ctx()))


def test_f356_inline_single_use_field() -> None:
    game = frog_parser.parse_game("""
        Game T(Int q) {
            ModInt<q> s;
            ModInt<q> f;
            ModInt<q> g;
            Void Initialize() {
                s <- ModInt<q>;
                f = q;
                g = s + s;
            }
            Bool Test() {
                return f == g;
            }
        }
        """)
    ctx = _ctx(lets={"q": frog_ast.IntType()})
    result = str(InlineSingleUseField().apply(game, ctx))
    assert "f = q;" in result
    assert "g = " not in result
    assert "f" in _near_miss_names(ctx, "Inline Single-Use Field")


def test_f356_if_condition_alias_substitution() -> None:
    def game(field_type: str) -> frog_ast.Game:
        return frog_parser.parse_game(f"""
            Game T(Int q) {{
                {field_type} g;
                ModInt<q> f;
                Void Initialize() {{
                    g = 5;
                    f = g;
                }}
                Bool O({field_type} x, ModInt<q> z) {{
                    if (x == g) {{
                        return f == z;
                    }}
                    return false;
                }}
            }}
            """)

    ctx = _ctx()
    converting = game("Int")
    result = IfConditionAliasSubstitution().apply(converting, ctx)
    assert "return f == z;" in str(result)
    assert "f" in _near_miss_names(ctx, "If Condition Alias Substitution")

    exact = game("ModInt<q>")
    assert "return x == z;" in str(IfConditionAliasSubstitution().apply(exact, _ctx()))


def test_f356_cross_method_field_alias() -> None:
    def game(field_type: str) -> frog_ast.Game:
        return frog_parser.parse_game(f"""
            Game T(Int q) {{
                Int k;
                {field_type} h;
                Void Initialize() {{
                    k = 3;
                    h = P.f(k);
                }}
                Int O() {{
                    Int r = P.f(k);
                    return r;
                }}
            }}
            """)

    ctx = _ctx(_namespace(_INT_PRIMITIVE))
    converting = game("ModInt<q>")
    assert "Int r = P.f(k);" in str(CrossMethodFieldAlias().apply(converting, ctx))
    assert "h" in _near_miss_names(ctx, "Cross-Method Field Alias")

    exact = game("Int")
    result = CrossMethodFieldAlias().apply(exact, _ctx(_namespace(_INT_PRIMITIVE)))
    assert "Int r = h;" in str(result)


def test_f356_injective_equality_simplify() -> None:
    def game(local_type: str) -> frog_ast.Game:
        return frog_parser.parse_game(f"""
            Game T(Int q) {{
                Bool O(Int b, Int c) {{
                    {local_type} v = P.f(b);
                    {local_type} w = P.f(c);
                    return v == w;
                }}
            }}
            """)

    ctx = _ctx(_namespace(_INT_PRIMITIVE))
    result = InjectiveEqualitySimplify().apply(game("ModInt<q>"), ctx)
    assert "return v == w;" in str(result)
    assert {"v", "w"} <= _near_miss_names(ctx, "Injective Equality Simplify")

    result = InjectiveEqualitySimplify().apply(
        game("Int"), _ctx(_namespace(_INT_PRIMITIVE))
    )
    assert "return b == c;" in str(result)


def test_f356_fold_equivalent_return_branch_skips_converting_field() -> None:
    def game(field_type: str) -> frog_ast.Game:
        return frog_parser.parse_game(f"""
            Game T(Int q) {{
                Int k;
                {field_type} F;
                Void Initialize() {{
                    k = 3;
                    F = P.f(k);
                }}
                Bool O() {{
                    return true;
                }}
            }}
            """)

    ctx = _ctx(_namespace(_INT_PRIMITIVE))
    converting = game("ModInt<q>")
    transformer = FoldEquivalentReturnBranchTransformer(ctx, converting)
    assert transformer._init_field_rhs == []  # pylint: disable=protected-access
    assert "F" in _near_miss_names(ctx, "Fold Equivalent Return Branch")

    exact = game("Int")
    transformer = FoldEquivalentReturnBranchTransformer(
        _ctx(_namespace(_INT_PRIMITIVE)), exact
    )
    recorded = [
        str(v) for v, _ in transformer._init_field_rhs
    ]  # pylint: disable=protected-access
    assert recorded == ["F"]


def test_f356_alias_maps_leave_out_converting_locals() -> None:
    method = frog_parser.parse_game("""
        Game T(Int q) {
            Int k;
            Int O() {
                ModInt<q> x = k;
                Int y = k;
                return y;
            }
        }
        """).methods[0]
    stable = _build_local_stable_alias_map(
        method, {"k"}, set(), {}, None, None, frozenset({"x"})
    )
    assert "x" not in stable and "y" in stable
    assigned = _build_local_assignments(method.block, frozenset({"x"}))
    assert "x" not in assigned and "y" in assigned


# ---------------------------------------------------------------------------
# The inliner
# ---------------------------------------------------------------------------


def _inline_once(scheme_src: str, caller_src: str) -> str:
    scheme = frog_parser.parse_scheme_file(scheme_src)
    lookup = {("S", m.signature.name): m for m in scheme.methods}
    game = frog_parser.parse_game(caller_src)
    for _ in range(10):
        new_game = InlineTransformer(lookup).transform(game)
        if new_game == game:
            break
        game = new_game
    return str(game)


_SCHEME = """
Scheme S(Int q) extends P {
    Bool IsZero(ModInt<q> x) {
        ModInt<q> z = 0;
        return x == z;
    }

    ModInt<q> Reduce(Int b) {
        return b;
    }

    Int Echo(Int b) {
        return b;
    }
}
"""


def test_f356_inliner_binds_modint_parameter() -> None:
    text = _inline_once(
        _SCHEME,
        "Game T(Int q) { Bool O(Int b) { return S.IsZero(b); } }",
    )
    assert "ModInt<q> S.IsZero@x0 = b;" in text
    assert "S.IsZero@x0 == " in text


def test_f356_inliner_binds_modint_return_value() -> None:
    text = _inline_once(
        _SCHEME,
        "Game T(Int q) { ModInt<q> O(Int b) { ModInt<q> r = S.Reduce(b); return r; } }",
    )
    assert "ModInt<q> S.Reduce@return0_0 = b;" in text
    assert "ModInt<q> r = S.Reduce@return0_0;" in text


def test_f356_inliner_substitutes_other_parameters_and_returns() -> None:
    text = _inline_once(
        _SCHEME,
        "Game T(Int q) { Int O(Int b) { Int r = S.Echo(b); return r; } }",
    )
    assert "Int r = b;" in text
    assert "@" not in text
