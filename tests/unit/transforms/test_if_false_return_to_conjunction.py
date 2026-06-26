"""Tests for IfFalseReturnToConjunction.

Covers absorbing ``if (P) { return false; } ...; return BoolExpr;`` into
``...; return !P && BoolExpr;`` when intervening statements are
side-effect-free typed-local declarations.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.control_flow import IfFalseReturnToConjunction
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx(namespace: frog_ast.Namespace | None = None) -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=namespace or {},
        subsets_pairs=[],
    )


def _apply(source: str, namespace: frog_ast.Namespace | None = None) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return IfFalseReturnToConjunction().apply(game, _ctx(namespace))


def test_adjacent_if_false_return_absorbs() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            return x != 0;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int x, Int y) {
            return x != 0 && x != y;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_pure_intervening_locals_absorbed() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            Int z = x + y;
            Bool b = z != 0;
            return b;
        }
    }
    """
    expected = """
    Game G() {
        Bool Check(Int x, Int y) {
            Int z = x + y;
            Bool b = z != 0;
            return b && x != y;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(expected)


def test_does_not_fire_with_sample_in_between() -> None:
    # A Sample is a side effect; absorbing would change observable
    # randomness when P holds.
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            BitString<8> r <- BitString<8>;
            return r != 0^8;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


def test_does_not_fire_when_early_return_is_not_false() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return true;
            }
            return x != 0;
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


# --------------------------------------------------------------------------
# Soundness gap regression test (Gap G: RHS side-effect detection)
# --------------------------------------------------------------------------


NS_NONDET_HELPER = """
Primitive T() {
    Int Helper(Int x);
}
"""


def test_gap_g_typed_local_rhs_with_nondet_call_blocks_absorption() -> None:
    """Gap G distinguisher: a typed-local declaration whose RHS calls a
    non-deterministic helper (which may mutate game-visible state) cannot
    be hoisted past the early ``if (P) { return false; }`` — when ``P``
    holds, the original skips the call entirely."""
    prim = frog_parser.parse_primitive_file(NS_NONDET_HELPER)
    namespace: frog_ast.Namespace = {"T": prim}
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            }
            Int z = T.Helper(x);
            return z == 1;
        }
    }
    """
    # Post-fix: the RHS contains a non-deterministic FuncCall, so the
    # transform refuses to absorb the early return.
    assert _apply(source, namespace) == frog_parser.parse_game(source)


def test_does_not_fire_when_if_has_else_block() -> None:
    source = """
    Game G() {
        Bool Check(Int x, Int y) {
            if (x == y) {
                return false;
            } else {
                return true;
            }
        }
    }
    """
    assert _apply(source) == frog_parser.parse_game(source)


# ---------------------------------------------------------------------------
# RC3 determinism guard (F-116): the guard P and the trailing return Q are
# evaluated on the P-true path that the original short-circuited; a
# non-deterministic call in either must block the rewrite.
# ---------------------------------------------------------------------------


def _nondet_namespace() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file("Primitive P(Int n) { Bool f(Int x); }")
    return {"P": prim, "F": prim}


def _det_namespace() -> frog_ast.Namespace:
    prim = frog_parser.parse_primitive_file(
        "Primitive D(Int n) { deterministic Bool f(Int x); }"
    )
    return {"D": prim, "F": prim}


def test_does_not_fire_with_nondeterministic_trailing_return() -> None:
    """The trailing ``return F.f(x)`` is non-deterministic; conjoining it
    would evaluate the call on the ``x == 0`` (P-true) path that the
    original skipped, so the pass must decline."""
    source = """
    Game G(P F, Int n) {
        Bool Test(Int x) {
            if (x == 0) {
                return false;
            }
            return F.f(x);
        }
    }
    """
    ns = _nondet_namespace()
    game = frog_parser.parse_game(source)
    ctx = _ctx(ns)
    result = IfFalseReturnToConjunction().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "If False Return To Conjunction" for nm in ctx.near_misses
    )


def test_does_not_fire_with_nondeterministic_guard() -> None:
    """The guard ``F.f(x)`` is re-evaluated in ``Q && !F.f(x)``; a
    non-deterministic guard blocks the rewrite."""
    source = """
    Game G(P F, Int n) {
        Bool Test(Int x, Bool q) {
            if (F.f(x)) {
                return false;
            }
            return q;
        }
    }
    """
    game = frog_parser.parse_game(source)
    assert IfFalseReturnToConjunction().apply(game, _ctx(_nondet_namespace())) == game


def test_fires_with_deterministic_trailing_return() -> None:
    """Control: a deterministic ``D.f(x)`` trailing return is conjoined as
    usual."""
    source = """
    Game G(D F, Int n) {
        Bool Test(Int x) {
            if (x == 0) {
                return false;
            }
            return F.f(x);
        }
    }
    """
    game = frog_parser.parse_game(source)
    result = IfFalseReturnToConjunction().apply(game, _ctx(_det_namespace()))
    assert result != game  # fired


# ---------------------------------------------------------------------------
# RC4 capture/movement guard (F-114): the negated guard !P is moved past the
# intervening typed-local declarations. If one of those declarations rebinds a
# variable that P reads, the moved guard would read the wrong binding -- decline.
# ---------------------------------------------------------------------------


def test_does_not_fire_when_intervening_decl_rebinds_guard_var() -> None:
    """A shadowing declaration ``Int a = M[b];`` rebinds ``a``, which the
    guard ``a == b`` reads. Moving ``a != b`` past the declaration would read
    the new local instead of the parameter; the pass must decline."""
    source = """
    Game G(Int n) {
        Bool O(Int a, Int b) {
            if (a == b) {
                return false;
            }
            Int a = b + 1;
            return a == 0 || a == 1;
        }
    }
    """
    game = frog_parser.parse_game(source)
    ctx = _ctx()
    result = IfFalseReturnToConjunction().apply(game, ctx)
    assert result == game  # declined
    assert any(
        nm.transform_name == "If False Return To Conjunction"
        and "wrong binding" in nm.reason
        for nm in ctx.near_misses
    )


def test_fires_when_intervening_decl_does_not_touch_guard_vars() -> None:
    """Control: the intervening declaration ``Int z = a + b;`` introduces a
    fresh name not read by the guard, so moving ``a != b`` past it is safe and
    the rewrite fires."""
    source = """
    Game G(Int n) {
        Bool O(Int a, Int b) {
            if (a == b) {
                return false;
            }
            Int z = a + b;
            return z == 0 || z == 1;
        }
    }
    """
    game = frog_parser.parse_game(source)
    result = IfFalseReturnToConjunction().apply(game, _ctx())
    assert result != game  # fired
