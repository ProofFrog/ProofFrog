"""Tests for ``HoistGroupExpToInitialize``.

When a non-Initialize method evaluates ``F ^ X`` where ``F`` is a single-
write ``GroupElem<G>`` field with a pure deterministic RHS and ``X`` is a
stable expression, this transform creates a fresh field caching
``F.rhs ^ X`` in Initialize and rewrites the use site to reference the new
field.  The inlined RHS form ``(F.rhs) ^ X`` is what's stored, so that
``GroupElem Simplification`` immediately following can fold any nested
power-of-power.
"""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.inlining import HoistGroupExpToInitialize


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> frog_ast.Game:
    game = frog_parser.parse_game(source)
    return HoistGroupExpToInitialize().apply(game, _ctx())


# --------------------------------------------------------------------------
# Positive
# --------------------------------------------------------------------------


def test_hoists_field1_caret_field2_with_local_base_var() -> None:
    """The motivating §4.3 case: ``field1 = G.generator ^ v1`` where v1 is a
    local in Initialize, and ``field1 ^ field2`` appears in Hash."""
    source = """
    Game G(Group G) {
        ModInt<G.order> field2;
        GroupElem<G> field1;

        Void Initialize() {
            field2 <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> v1 <- ModInt<G.order>;
            field1 = G.generator ^ v1;
        }
        Bool Hash(GroupElem<G> z) {
            return z == field1 ^ field2;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> field2;
        GroupElem<G> field1;
        GroupElem<G> _hge_0;

        Void Initialize() {
            field2 <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> v1 <- ModInt<G.order>;
            field1 = G.generator ^ v1;
            _hge_0 = (G.generator ^ v1) ^ field2;
        }
        Bool Hash(GroupElem<G> z) {
            return z == _hge_0;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


def test_hoists_when_base_rhs_uses_field() -> None:
    """If the base field's RHS uses cross-method-visible vars (a field),
    the transform still hoists — the new field's RHS inlines them."""
    source = """
    Game G(Group G) {
        ModInt<G.order> b;
        ModInt<G.order> sk;
        GroupElem<G> pk;

        Void Initialize() {
            b <- ModInt<G.order>;
            sk <-uniq[{0}] ModInt<G.order>;
            pk = G.generator ^ b;
        }
        Bool Q(GroupElem<G> z) {
            return z == pk ^ sk;
        }
    }
    """
    expected = """
    Game G(Group G) {
        ModInt<G.order> b;
        ModInt<G.order> sk;
        GroupElem<G> pk;
        GroupElem<G> _hge_0;

        Void Initialize() {
            b <- ModInt<G.order>;
            sk <-uniq[{0}] ModInt<G.order>;
            pk = G.generator ^ b;
            _hge_0 = (G.generator ^ b) ^ sk;
        }
        Bool Q(GroupElem<G> z) {
            return z == _hge_0;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(expected), str(got)


# --------------------------------------------------------------------------
# Negative
# --------------------------------------------------------------------------


def test_no_hoist_when_exponent_is_method_param() -> None:
    """The exponent ``X`` must be stable (cross-method-visible). Using a
    method parameter would change per call, so no hoist."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;

        Void Initialize() {
            ModInt<G.order> b <- ModInt<G.order>;
            pk = G.generator ^ b;
        }
        GroupElem<G> Apply(ModInt<G.order> k) {
            return pk ^ k;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_no_hoist_when_base_field_reassigned_outside_init() -> None:
    source = """
    Game G(Group G) {
        ModInt<G.order> sk;
        GroupElem<G> pk;

        Void Initialize() {
            sk <-uniq[{0}] ModInt<G.order>;
            ModInt<G.order> b <- ModInt<G.order>;
            pk = G.generator ^ b;
        }
        Void Update(GroupElem<G> q) {
            pk = q;
        }
        Bool Q(GroupElem<G> z) {
            return z == pk ^ sk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_no_hoist_when_base_field_not_groupelem() -> None:
    """``field ^ k`` where field is ``ModInt`` (integer exponentiation) is
    out of scope for this transform."""
    source = """
    Game G(Group G) {
        ModInt<G.order> n;

        Void Initialize() {
            ModInt<G.order> b <- ModInt<G.order>;
            n = b;
        }
        ModInt<G.order> Q() {
            return n ^ 2;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)


def test_no_hoist_when_no_field_caret_x_pattern_in_oracle() -> None:
    """If no oracle uses ``field ^ X``, no hoisting occurs."""
    source = """
    Game G(Group G) {
        GroupElem<G> pk;

        Void Initialize() {
            ModInt<G.order> b <- ModInt<G.order>;
            pk = G.generator ^ b;
        }
        GroupElem<G> Get() {
            return pk;
        }
    }
    """
    got = _apply(source)
    assert got == frog_parser.parse_game(source), str(got)
