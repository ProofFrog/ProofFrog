"""Integration tests for the ``GroupExponentWrapper`` recognizer on
``MapKeyReindex``: ``x ↦ x^k`` on ``GroupElem<G>`` under
``requires G.order is prime;`` + ``k`` known-nonzero."""

from __future__ import annotations

from proof_frog import frog_ast, frog_parser, visitors
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.map_reindex import MapKeyReindex


def _ctx_with_requirements(
    requirements: list[frog_ast.StructuralRequirement] | None = None,
    group_name: str = "G",
) -> PipelineContext:
    ns: frog_ast.Namespace = {group_name: None}
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace=ns,
        subsets_pairs=[],
        requirements=requirements or [],
    )


def _prime_requirement_on(group_name: str) -> frog_ast.StructuralRequirement:
    return frog_ast.StructuralRequirement(
        kind="prime",
        target=frog_ast.FieldAccess(frog_ast.Variable(group_name), "order"),
    )


_GAME_EXP_REINDEX = """
Game G(Group G) {
    ModInt<G.order> sk = 0;
    GroupElem<G> pk = G.generator;
    Map<GroupElem<G>, BitString<16>> M;

    Void Initialize() {
        ModInt<G.order> sk <-uniq[{0}] ModInt<G.order>;
        pk = G.generator ^ sk;
    }
    Void Store(GroupElem<G> a, BitString<16> s) {
        M[a] = s;
    }
    BitString<16>? Scan(GroupElem<G> y) {
        for ([GroupElem<G>, BitString<16>] e in M.entries) {
            if (e[0] ^ sk == y) {
                return e[1];
            }
        }
        return None;
    }
}
"""


def _apply(game_src: str, ctx: PipelineContext) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return MapKeyReindex().apply(game, ctx)


def test_group_exp_reindex_fires_under_prime_order_and_nonzero() -> None:
    ctx = _ctx_with_requirements([_prime_requirement_on("G")])
    got = _apply(_GAME_EXP_REINDEX, ctx)
    got_str = str(got)
    # After reindex: writes wrap the raw key as `a^sk`, loop body strips the
    # wrapper (bare `e[0] == y`).  The map type stays GroupElem<G> because
    # exponentiation is endomorphic on the group.
    assert "M[a ^ sk] = s;" in got_str, got_str
    assert "e[0] == y" in got_str, got_str
    assert "Map<GroupElem<G>, BitString<16>>" in got_str


def test_group_exp_reindex_blocked_without_prime_requirement() -> None:
    ctx = _ctx_with_requirements([])  # no `G.order is prime` requirement
    got = _apply(_GAME_EXP_REINDEX, ctx)
    # Unchanged game, near-miss emitted.
    assert "M[a] = s;" in str(got)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss citing the missing requirement"
    assert any("prime" in nm.reason for nm in misses), [nm.reason for nm in misses]


_GAME_EXP_PLAIN_SAMPLE = """
Game G(Group G) {
    ModInt<G.order> sk = 0;
    GroupElem<G> pk = G.generator;
    Map<GroupElem<G>, BitString<16>> M;

    Void Initialize() {
        ModInt<G.order> sk <- ModInt<G.order>;
        pk = G.generator ^ sk;
    }
    Void Store(GroupElem<G> a, BitString<16> s) {
        M[a] = s;
    }
    BitString<16>? Scan(GroupElem<G> y) {
        for ([GroupElem<G>, BitString<16>] e in M.entries) {
            if (e[0] ^ sk == y) {
                return e[1];
            }
        }
        return None;
    }
}
"""


def test_group_exp_reindex_blocked_when_sk_not_known_nonzero() -> None:
    ctx = _ctx_with_requirements([_prime_requirement_on("G")])
    got = _apply(_GAME_EXP_PLAIN_SAMPLE, ctx)
    # Unchanged.
    assert "M[a] = s;" in str(got)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss citing the non-nonzero exponent"
    assert any("nonzero" in nm.reason for nm in misses), [nm.reason for nm in misses]
