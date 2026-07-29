"""Regression test for HoistDeterministicCallToInitialize's alias builder (F-170).

When Initialize ends `return F(x)`, the pass expands local single-assignment
aliases so `F(x)` with `x = k` earlier matches a hoisted `F(k)`. The alias
scan counted only top-level `Assignment` nodes, so a re-binding of `x` nested
in an if/for or via a Sample was missed -- making a coin-dependent `x` look
like a stable alias of `k`. It now requires the COMPLETE recursive write count
of the alias name to be exactly 1.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.inlining import HoistDeterministicCallToInitialize
from proof_frog.transforms._base import PipelineContext
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    plt = NameTypeMap()
    n = frog_ast.BitStringType(frog_ast.Variable("n"))
    plt.set("F", frog_ast.FunctionType(n, n))
    return PipelineContext(
        variables={},
        proof_let_types=plt,
        proof_namespace={"F": None},
        subsets_pairs=[],
    )


def _apply(src: str) -> str:
    game = frog_parser.parse_game(src)
    return str(HoistDeterministicCallToInitialize().apply(game, _ctx()))


def test_f170_declines_coin_dependent_alias() -> None:
    # x is re-bound in the if-branch, so `return F(x)` is coin-dependent and
    # must NOT be expanded to `F(k)`. The pass may still hoist O's F(k) into a
    # field, but Initialize's terminal `return F(x)` must be PRESERVED.
    out = _apply(
        """
        Game G(Int n) {
            BitString<n> k;
            Function<BitString<n>, BitString<n>> F;
            BitString<n> Initialize() {
                k <- BitString<n>;
                BitString<n> k2 <- BitString<n>;
                BitString<1> b <- BitString<1>;
                BitString<n> x = k;
                if (b == 1^1) { x = k2; }
                return F(x);
            }
            BitString<n> O() { return F(k); }
        }
        """
    )
    assert "F(x)" in out  # coin-dependent return preserved, not collapsed


def test_f170_still_expands_stable_alias() -> None:
    # x is assigned exactly once (`x = k`), so `return F(x)` IS `F(k)`: the
    # alias expands and the return collapses to the hoisted field. Positive
    # control -- the coin-dependent `F(x)` form must be gone.
    out = _apply(
        """
        Game G(Int n) {
            BitString<n> k;
            Function<BitString<n>, BitString<n>> F;
            BitString<n> Initialize() {
                k <- BitString<n>;
                BitString<n> x = k;
                return F(x);
            }
            BitString<n> O() { return F(k); }
        }
        """
    )
    assert "F(x)" not in out
