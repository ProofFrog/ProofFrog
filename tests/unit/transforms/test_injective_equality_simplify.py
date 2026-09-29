"""Tests for InjectiveEqualitySimplify.

Covers rewriting ``f(a1, ..., an) == f(b1, ..., bn)`` to the pairwise
conjunction of argument equalities (and ``!=`` to the disjunction of
argument disequalities) when ``f`` is a primitive method annotated
``deterministic injective``; plus negative / near-miss cases.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.algebraic import InjectiveEqualitySimplify
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ns(primitive_src: str) -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file(primitive_src)
    return {"T": prim}


def _ctx(namespace: frog_ast.Namespace | None = None) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


NS_DETERMINISTIC_INJECTIVE = """
Primitive T(Set SecretSet, Set InputSet, Set ImageSet) {
    deterministic injective ImageSet Eval(SecretSet sk, InputSet x);
}
"""

NS_DETERMINISTIC_ONLY = """
Primitive T(Set SecretSet, Set InputSet, Set ImageSet) {
    deterministic ImageSet Eval(SecretSet sk, InputSet x);
}
"""

NS_INJECTIVE_ONLY = """
Primitive T(Set SecretSet, Set InputSet, Set ImageSet) {
    injective ImageSet Eval(SecretSet sk, InputSet x);
}
"""


def _apply(source: str, namespace: frog_ast.Namespace) -> tuple[frog_ast.Game, PipelineContext]:
    game = frog_parser.parse_game(source)
    ctx = _ctx(namespace)
    return InjectiveEqualitySimplify().apply(game, ctx), ctx


# --------------------------------------------------------------------------
# Positive tests
# --------------------------------------------------------------------------


def test_two_arg_equality_rewrites_to_conjunction() -> None:
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Eval(sk, a) == T.Eval(sk, b);
        }
    }
    """
    expected = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return (sk == sk) && (a == b);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_DETERMINISTIC_INJECTIVE))
    assert result == frog_parser.parse_game(expected)


def test_two_arg_disequality_rewrites_to_disjunction() -> None:
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Eval(sk, a) != T.Eval(sk, b);
        }
    }
    """
    expected = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return (sk != sk) || (a != b);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_DETERMINISTIC_INJECTIVE))
    assert result == frog_parser.parse_game(expected)


# --------------------------------------------------------------------------
# Negative tests
# --------------------------------------------------------------------------


def test_deterministic_only_does_not_fire_and_emits_near_miss() -> None:
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Eval(sk, a) == T.Eval(sk, b);
        }
    }
    """
    result, ctx = _apply(source, _ns(NS_DETERMINISTIC_ONLY))
    assert result == frog_parser.parse_game(source)
    assert any(
        nm.transform_name == "Injective Equality Simplify" and nm.method == "Eval"
        for nm in ctx.near_misses
    )


def test_injective_only_does_not_fire() -> None:
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Eval(sk, a) == T.Eval(sk, b);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_INJECTIVE_ONLY))
    assert result == frog_parser.parse_game(source)


def test_different_callees_does_not_fire_no_near_miss() -> None:
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Eval(sk, a) == T.Other(sk, b);
        }
    }
    """
    ns_src = """
    Primitive T(Set SecretSet, Set InputSet, Set ImageSet) {
        deterministic injective ImageSet Eval(SecretSet sk, InputSet x);
        deterministic injective ImageSet Other(SecretSet sk, InputSet x);
    }
    """
    result, ctx = _apply(source, _ns(ns_src))
    assert result == frog_parser.parse_game(source)
    assert not ctx.near_misses


def test_sampled_function_call_does_not_fire() -> None:
    """Equality between calls to a sampled Function<D, R> must not simplify —
    random functions are not injective in general."""
    source = """
    Game G() {
        Function<BitString<8>, BitString<8>> F;
        BitString<8> a;
        BitString<8> b;
        Bool Query() {
            return F(a) == F(b);
        }
    }
    """
    result, ctx = _apply(source, {})
    assert result == frog_parser.parse_game(source)
    assert not ctx.near_misses


def test_reflexive_same_args_unchanged_by_this_pass() -> None:
    """When both sides are identical, InjectiveEqualitySimplify still rewrites
    to the pairwise conjunction (which ReflexiveComparison then collapses to
    true elsewhere in the pipeline).  Verify this pass does not double-reduce
    or crash on identical calls."""
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        Bool Query() {
            return T.Eval(sk, a) == T.Eval(sk, a);
        }
    }
    """
    expected = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        Bool Query() {
            return (sk == sk) && (a == a);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_DETERMINISTIC_INJECTIVE))
    assert result == frog_parser.parse_game(expected)


# --------------------------------------------------------------------------
# Soundness gap regression tests (Gap C: Sample-write detection;
# Gap D: free-variable stability)
# --------------------------------------------------------------------------


NS_INJECTIVE_PLUS_SAMPLABLE = """
Primitive T(Set SecretSet, Set InputSet, Set ImageSet) {
    deterministic injective ImageSet Eval(SecretSet sk, InputSet x);
}
"""


def test_gap_c_sample_rebinding_blocks_resolution() -> None:
    """Gap C distinguisher: a typed-local FuncCall binding that is later
    *sampled* (e.g. ``v <- ImageSet;``) must be dropped from the resolver
    map; otherwise the comparison would be rewritten using the original
    Eval call's args, but the actual value at the comparison is the sample."""
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet a;
        Bool Query(T.InputSet b) {
            T.ImageSet v = T.Eval(sk, a);
            v <- T.ImageSet;
            return v == T.Eval(sk, b);
        }
    }
    """
    # Post-fix: transform refuses to resolve `v`, leaves comparison unchanged.
    result, _ = _apply(source, _ns(NS_INJECTIVE_PLUS_SAMPLABLE))
    assert result == frog_parser.parse_game(source)


def test_gap_d_unstable_free_var_blocks_resolution() -> None:
    """Gap D: when the FuncCall binding's free variables include a field
    that is mutated between the binding site and the comparison site, the
    resolver must not substitute (the comparison would evaluate against a
    different environment)."""
    source = """
    Game G() {
        T.SecretSet sk;
        T.InputSet xfld;
        Bool Query(T.InputSet b) {
            T.ImageSet v = T.Eval(sk, xfld);
            xfld = b;
            return v == T.Eval(sk, b);
        }
    }
    """
    # Post-fix: the field `xfld` is written between binding and use, so the
    # transform refuses to resolve `v`.
    result, _ = _apply(source, _ns(NS_INJECTIVE_PLUS_SAMPLABLE))
    assert result == frog_parser.parse_game(source)


def test_single_arg_call_rewrites() -> None:
    source = """
    Game G() {
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return T.Encode(a) == T.Encode(b);
        }
    }
    """
    expected = """
    Game G() {
        T.InputSet a;
        T.InputSet b;
        Bool Query() {
            return a == b;
        }
    }
    """
    ns_src = """
    Primitive T(Set InputSet, Set ImageSet) {
        deterministic injective ImageSet Encode(InputSet x);
    }
    """
    result, _ = _apply(source, _ns(ns_src))
    assert result == frog_parser.parse_game(expected)


# --------------------------------------------------------------------------
# Value-stability of resolved bindings (audit F-247 / F-248)
# --------------------------------------------------------------------------

NS_INJ_ENC = """
Primitive T(Int n) {
    deterministic injective BitString<n> Enc1(BitString<n> x);
}
"""


def test_f247_nested_write_binding_not_resolved() -> None:
    """A local binding `w = T.Enc1(x)` whose arg `x` is reassigned inside an
    if-body is NOT write-once; resolving `w == T.Enc1(x)` to `x == x` would be
    unsound (the nested write is invisible to a top-level-only scan)."""
    source = """
    Game G(Int n) {
        Bool Test(Bool c) {
            BitString<n> x = 0^n;
            BitString<n> w = T.Enc1(x);
            if (c) {
                x = 1^n;
            }
            return w == T.Enc1(x);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_INJ_ENC))
    assert "w == T.Enc1(x)" in str(result)  # not collapsed to x == x


def test_f247_stable_arg_binding_still_resolves() -> None:
    """Positive control: no reassignment of `x`, so `w == T.Enc1(x)` resolves
    and the injective rewrite fires."""
    source = """
    Game G(Int n) {
        Bool Test(BitString<n> x) {
            BitString<n> w = T.Enc1(x);
            return w == T.Enc1(x);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_INJ_ENC))
    assert "x == x" in str(result)


def test_f248_mutated_field_rhs_not_resolved() -> None:
    """A field `F = T.Enc1(t)` frozen at Init must not be resolved to its RHS
    at a site where the free field `t` has since been mutated -- that would
    collapse `F == T.Enc1(t)` to `t == t` though F holds the stale value."""
    source = """
    Game G(Int n) {
        BitString<n> t;
        BitString<n> F;
        Void Initialize() {
            t = 0^n;
            F = T.Enc1(t);
        }
        Bool Test() {
            t = 1^n;
            return F == T.Enc1(t);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_INJ_ENC))
    assert "F == T.Enc1(t)" in str(result)  # not collapsed to t == t


def test_f248_immutable_field_rhs_still_resolves() -> None:
    """Positive control: `t` is never mutated after Init, so F resolves to its
    RHS and the injective comparison collapses."""
    source = """
    Game G(Int n) {
        BitString<n> t;
        BitString<n> F;
        Void Initialize() {
            t = 0^n;
            F = T.Enc1(t);
        }
        Bool Test() {
            return F == T.Enc1(t);
        }
    }
    """
    result, _ = _apply(source, _ns(NS_INJ_ENC))
    assert "t == t" in str(result)


# ---------------------------------------------------------------------------
# F-343 / F-344 / F-347: stability of the values a resolved image names
# ---------------------------------------------------------------------------

NS_MAP_IMAGE = """
Primitive T(Int n) {
    deterministic injective BitString<n> inj(Map<BitString<n>, BitString<n>> m);
    deterministic injective BitString<n> eval(BitString<n> x);
}
"""


def _simplify(source: str, method: str) -> str:
    game = frog_parser.parse_game(source)
    prim = frog_parser.parse_primitive_file(NS_MAP_IMAGE)
    result = InjectiveEqualitySimplify().apply(game, _ctx({"T": prim, "F": prim}))
    return str(result.get_method(method))


def test_f343_field_image_not_resolved_across_element_write() -> None:
    """F-343: ``Fd = F.inj(T)`` in Initialize; an oracle writes ``T[x]``, so
    ``Fd == F.inj(T)`` compares the old image with the new one."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            Map<BitString<n>, BitString<n>> M;
            BitString<n> Fd;
            Void Initialize() { Fd = F.inj(M); }
            Void Put(BitString<n> x, BitString<n> y) { M[x] = y; }
            Bool Test() { return Fd == F.inj(M); }
        }
        """,
        "Test",
    )
    assert "M == M" not in out, out


def test_f343_field_image_still_resolved_when_map_unwritten() -> None:
    """F-343 control: with no write to the map, the images are equal."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            Map<BitString<n>, BitString<n>> M;
            BitString<n> Fd;
            Void Initialize() { Fd = F.inj(M); }
            Bool Test() { return Fd == F.inj(M); }
        }
        """,
        "Test",
    )
    assert "M == M" in out, out


def test_f343_nested_rewrite_of_defined_field_blocks_resolution() -> None:
    """A nested second write of the defined field inside Initialize means its
    value need not be the top-level right-hand side."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            BitString<n> K;
            BitString<n> A;
            Void Initialize(Bool c) {
                K <- BitString<n>;
                A = F.eval(K);
                if (c) { A <- BitString<n>; }
            }
            Bool Test() { return A == F.eval(K); }
        }
        """,
        "Test",
    )
    assert "K == K" not in out, out


def test_f344_local_image_not_stable_across_element_write() -> None:
    """F-344: ``v = F.inj(M); M[a] = b;`` -- v is the image of the old map."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            Map<BitString<n>, BitString<n>> M;
            Bool Test(BitString<n> a, BitString<n> b) {
                BitString<n> v = F.inj(M);
                M[a] = b;
                return v == F.inj(M);
            }
        }
        """,
        "Test",
    )
    assert "M == M" not in out, out


def test_f347_field_image_not_resolved_into_shadowing_parameter() -> None:
    """F-347: the comparison's method has a parameter named like the field the
    image reads, so the resolved ``F.eval(K)`` would name the parameter."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            BitString<n> K;
            BitString<n> A;
            Void Initialize() { K <- BitString<n>; A = F.eval(K); }
            Bool Test(BitString<n> K) { return A == F.eval(K); }
        }
        """,
        "Test",
    )
    assert "K == K" not in out, out


def test_f349_field_image_not_resolved_past_earlier_initialize_return() -> None:
    """F-349: Initialize may return before ``A = F.eval(K)``, leaving ``A`` at
    its initial value, so ``A == F.eval(L)`` is not ``K == L``."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            BitString<n> K;
            BitString<n> L;
            BitString<n> A = 0^n;
            Bool Initialize() {
                K <- BitString<n>;
                L <- BitString<n>;
                Bool c <- Bool;
                if (c) { return true; }
                A = F.eval(K);
                return false;
            }
            Bool Test() { return A == F.eval(L); }
        }
        """,
        "Test",
    )
    assert "K == L" not in out, out


def test_f349_field_image_not_resolved_inside_initialize() -> None:
    """F-349: a comparison in Initialize may run before the definition."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            BitString<n> K;
            BitString<n> L;
            BitString<n> A = 0^n;
            Bool Initialize() {
                K <- BitString<n>;
                L <- BitString<n>;
                Bool c <- Bool;
                if (c) { return A == F.eval(L); }
                A = F.eval(K);
                return false;
            }
        }
        """,
        "Initialize",
    )
    assert "K == L" not in out, out


def test_f349_field_image_resolved_when_definition_always_runs() -> None:
    """Control: no return before the definition."""
    out = _simplify(
        """
        Game G(T F, Int n) {
            BitString<n> K;
            BitString<n> L;
            BitString<n> A = 0^n;
            Bool Initialize() {
                K <- BitString<n>;
                L <- BitString<n>;
                A = F.eval(K);
                Bool c <- Bool;
                if (c) { return true; }
                return false;
            }
            Bool Test() { return A == F.eval(L); }
        }
        """,
        "Test",
    )
    assert "K == L" in out, out


NS_MODINT = """
Primitive T(Int q, Int n) {
    deterministic injective BitString<n> encm(ModInt<q> x);
}
"""


def _simplify_modint(source: str) -> str:
    game = frog_parser.parse_game(source)
    result, _ = _apply_ns(game, NS_MODINT)
    return str(result.get_method("O"))


def _apply_ns(game: frog_ast.Game, primitive_src: str) -> tuple[frog_ast.Game, PipelineContext]:
    prim = frog_parser.parse_primitive_file(primitive_src)
    ctx = _ctx({"T": prim, "E": prim})
    return InjectiveEqualitySimplify().apply(game, ctx), ctx


def test_f348_int_arguments_to_modint_parameter_not_compared_as_ints() -> None:
    """F-348: ``encm(1) == encm(q + 1)`` holds (q + 1 = 1 mod q), but the
    integer comparison ``1 == q + 1`` is false."""
    out = _simplify_modint(
        """
        Game G(T E, Int q, Int n) {
            Void Initialize() { }
            Bool O() { return E.encm(1) == E.encm(q + 1); }
        }
        """
    )
    assert "1 == q + 1" not in out, out


def test_f348_modint_arguments_still_simplify() -> None:
    """Control: both arguments already have the parameter's type."""
    out = _simplify_modint(
        """
        Game G(T E, Int q, Int n) {
            ModInt<q> a;
            ModInt<q> b;
            Void Initialize() { a <- ModInt<q>; b <- ModInt<q>; }
            Bool O() { return E.encm(a) == E.encm(b); }
        }
        """
    )
    assert "a == b" in out, out
