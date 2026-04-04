"""Tests for the UniqueRFSimplification transform pass."""

import pytest
from proof_frog import frog_ast, frog_parser
from proof_frog.transforms.random_functions import (
    UniqueRFSimplificationTransformer,
    UniqueRFSimplification,
)
from proof_frog.transforms._base import PipelineContext


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic: r dead after RF call -> z <- R, UniqueSample removed
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z <- BitString<16>;
                return z;
            }
            """,
        ),
        # r alive after RF call: DOES simplify (all RF calls are guarded)
        (
            """
            [BitString<8>, BitString<16>] f(BitString<16> m) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return [r, m + z];
            }
            """,
            """
            [BitString<8>, BitString<16>] f(BitString<16> m) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z <- BitString<16>;
                return [r, m + z];
            }
            """,
        ),
        # Plain Set as unique set (not RF.domain): DOES simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                Set<BitString<8>> Q;
                BitString<8> r <-uniq[Q] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                Set<BitString<8>> Q;
                BitString<8> r <-uniq[Q] BitString<8>;
                BitString<16> z <- BitString<16>;
                return z;
            }
            """,
        ),
        # RF1.domain guarding RF2 call: should NOT simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF1;
                RandomFunctions<BitString<8>, BitString<16>> RF2;
                RF1 <- RandomFunctions<BitString<8>, BitString<16>>;
                RF2 <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF1.domain] BitString<8>;
                BitString<16> z = RF2(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF1;
                RandomFunctions<BitString<8>, BitString<16>> RF2;
                RF1 <- RandomFunctions<BitString<8>, BitString<16>>;
                RF2 <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF1.domain] BitString<8>;
                BitString<16> z = RF2(r);
                return z;
            }
            """,
        ),
        # Sampled var doesn't match RF arg: should NOT simplify
        (
            """
            BitString<16> f(BitString<8> x) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
        ),
        # Not uniquely sampled (plain sample): should NOT simplify
        (
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <- BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                RandomFunctions<BitString<8>, BitString<16>> RF;
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
                BitString<8> r <- BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
        ),
    ],
)
def test_unique_rf_simplification(
    method: str,
    expected: str,
) -> None:
    method_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = method_ast
    while True:
        new_ast = UniqueRFSimplificationTransformer().transform(transformed_ast)
        if new_ast == transformed_ast:
            break
        transformed_ast = new_ast

    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


def _make_ctx() -> PipelineContext:
    """Minimal PipelineContext for game-level tests."""
    return PipelineContext(
        variables={},
        proof_let_types={},
        proof_namespace={},
        subsets_pairs=[],
    )


def test_local_unique_set_not_simplified() -> None:
    """If the unique set is a local variable (not a game field), the RF
    should NOT be simplified.  A local set resets each oracle call, so
    the same value could be drawn across calls, violating cross-call
    distinctness required for RF replacement."""
    game = frog_parser.parse_game(
        """
        Game G() {
            RandomFunctions<BitString<8>, BitString<16>> RF;
            BitString<16> Query() {
                Set<BitString<8>> localS;
                BitString<8> r <-uniq[localS] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
        }
        """
    )
    result = UniqueRFSimplification().apply(game, _make_ctx())
    # RF(r) should NOT be replaced because localS is not a game field
    assert result == game, (
        "RF with local unique set should not be simplified"
    )


def test_duplicate_rf_arg_not_simplified() -> None:
    """If the same uniquely-sampled variable is used as argument to two
    RF calls, both calls return the same value (RF is a function).
    Replacing both with independent samples is wrong."""
    game = frog_parser.parse_game(
        """
        Game G() {
            Set<BitString<8>> S;
            RandomFunctions<BitString<8>, BitString<16>> RF;
            Void Initialize() {
                RF <- RandomFunctions<BitString<8>, BitString<16>>;
            }
            [BitString<16>, BitString<16>] Query() {
                BitString<8> r <-uniq[S] BitString<8>;
                BitString<16> z1 = RF(r);
                BitString<16> z2 = RF(r);
                return [z1, z2];
            }
        }
        """
    )
    result = UniqueRFSimplification().apply(game, _make_ctx())
    # RF(r) should NOT be replaced because r is used for two RF calls
    assert result == game, (
        "RF with duplicate argument variable should not be simplified"
    )
