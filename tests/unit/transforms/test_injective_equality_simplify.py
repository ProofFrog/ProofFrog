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
