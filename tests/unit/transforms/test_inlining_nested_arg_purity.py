"""Regression tests: purity gates see through nested call arguments.

A "deterministic" outer call whose ARGUMENT contains a non-deterministic
(abstract-primitive) call is itself non-deterministic (i.i.d. per ruling
7.A.6). Passes that inline such a call by treating the outer call as pure
correlate independent draws. This pins the nested-argument gate for
InlineMultiUsePureExpression (F-194). (F-202, the analogous fix in the shared
`_DeterministicCallCollector`, is deferred -- it broke two CFRG proofs.)
"""

from proof_frog import frog_parser
from proof_frog.transforms.inlining import (
    InlineMultiUsePureExpressionTransformer,
)


def _multiuse(method_src: str, function_var_names=None) -> str:
    game = frog_parser.parse_game("Game G() {\n" + method_src + "\n}")
    return str(
        InlineMultiUsePureExpressionTransformer(function_var_names).transform(game)
    )


def test_f194_declines_function_let_call_with_nondet_argument() -> None:
    # H is a deterministic Function-let, but its argument P.Sample(0^n) is an
    # abstract-primitive draw. Inlining `v = H(P.Sample(0^n))` into two uses
    # would duplicate the draw -> declined (v survives).
    out = _multiuse(
        """
        Bool O() {
            Bool v = H(P.Sample());
            return v == v;
        }
        """,
        function_var_names={"H"},
    )
    assert "Bool v = H(P.Sample())" in out


def test_f194_still_inlines_function_let_call_with_pure_argument() -> None:
    # H(k) with a plain variable argument is deterministic -> inlined at both
    # uses (the declaration is removed).
    out = _multiuse(
        """
        Bool O(Int k) {
            Bool v = H(k);
            return v == v;
        }
        """,
        function_var_names={"H"},
    )
    assert "Bool v = H(k)" not in out
