"""Tests for UniformModIntSimplification, including the loop-reuse soundness
guard (audit F-132c): a uniform ModInt sampled OUTSIDE a loop and consumed
INSIDE it is reused once per iteration, so the "used exactly once" absorption
`acc = acc + t` -> `acc = t` would change the distribution (`2t` even-only vs
uniform `t`) and must be declined."""

from proof_frog import frog_parser, visitors
from proof_frog.transforms.algebraic import UniformModIntSimplification
from proof_frog.transforms._base import PipelineContext


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=visitors.NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(source: str) -> str:
    game = frog_parser.parse_game(source)
    return str(UniformModIntSimplification().apply(game, _ctx()))


def test_sample_outside_loop_use_inside_not_absorbed() -> None:
    """Negative: sample outside a >=2-iteration loop, additive use inside ->
    decline (the value is reused across iterations)."""
    result = _apply(
        """
        Game G() {
            ModInt<16> acc;
            ModInt<16> Probe() {
                acc = 0;
                ModInt<16> t <- ModInt<16>;
                for (ModInt<16> i in {1, 2}) {
                    acc = acc + t;
                }
                return acc;
            }
        }
        """
    )
    assert "acc = acc + t" in result, f"loop-reused uniform was absorbed:\n{result}"


def test_plain_non_loop_absorption_still_fires() -> None:
    """Positive control: ordinary single-use absorption is unchanged."""
    result = _apply(
        """
        Game G() {
            ModInt<16> Probe(ModInt<16> m) {
                ModInt<16> u <- ModInt<16>;
                return u + m;
            }
        }
        """
    )
    assert "return u" in result and "u + m" not in result


def test_sample_inside_loop_fresh_each_iteration_still_fires() -> None:
    """Positive control: when the sample is INSIDE the loop body, each
    iteration draws a fresh value used once, so the absorption is sound."""
    result = _apply(
        """
        Game G() {
            ModInt<16> acc;
            ModInt<16> Probe() {
                acc = 0;
                for (ModInt<16> i in {1, 2}) {
                    ModInt<16> t <- ModInt<16>;
                    acc = acc + t;
                }
                return acc;
            }
        }
        """
    )
    assert "acc = t" in result


def test_loop_reuse_emits_near_miss() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            ModInt<16> acc;
            ModInt<16> Probe() {
                acc = 0;
                ModInt<16> t <- ModInt<16>;
                for (ModInt<16> i in {1, 2}) {
                    acc = acc + t;
                }
                return acc;
            }
        }
        """
    )
    ctx = _ctx()
    UniformModIntSimplification().apply(game, ctx)
    assert any(
        nm.transform_name == "Uniform ModInt Simplification"
        and "reused across" in nm.reason
        for nm in ctx.near_misses
    )
