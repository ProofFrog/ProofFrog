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
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
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
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(r);
                return [r, m + z];
            }
            """,
            """
            [BitString<8>, BitString<16>] f(BitString<16> m) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
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
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                Set<BitString<8>> Q;
                BitString<8> r <-uniq[Q] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
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
                Function<BitString<8>, BitString<16>> RF1;
                Function<BitString<8>, BitString<16>> RF2;
                RF1 <- Function<BitString<8>, BitString<16>>;
                RF2 <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF1.domain] BitString<8>;
                BitString<16> z = RF2(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF1;
                Function<BitString<8>, BitString<16>> RF2;
                RF1 <- Function<BitString<8>, BitString<16>>;
                RF2 <- Function<BitString<8>, BitString<16>>;
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
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <-uniq[RF.domain] BitString<8>;
                BitString<16> z = RF(x);
                return z;
            }
            """,
            """
            BitString<16> f(BitString<8> x) {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
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
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
                BitString<8> r <- BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
            """,
            """
            BitString<16> f() {
                Function<BitString<8>, BitString<16>> RF;
                RF <- Function<BitString<8>, BitString<16>>;
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
    game = frog_parser.parse_game("""
        Game G() {
            Function<BitString<8>, BitString<16>> RF;
            BitString<16> Query() {
                Set<BitString<8>> localS;
                BitString<8> r <-uniq[localS] BitString<8>;
                BitString<16> z = RF(r);
                return z;
            }
        }
        """)
    result = UniqueRFSimplification().apply(game, _make_ctx())
    # RF(r) should NOT be replaced because localS is not a game field
    assert result == game, "RF with local unique set should not be simplified"


def test_exclusion_set_modified_not_simplified() -> None:
    """If the exclusion set is explicitly modified by user code, the RF
    should NOT be simplified.  FrogLang semantics implicitly maintain
    exclusion sets; explicit modification breaks cross-call uniqueness."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<BitString<8>> S;
            Function<BitString<8>, BitString<16>> RF;
            Void Initialize() {
                RF <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Query() {
                BitString<8> r <-uniq[S] BitString<8>;
                BitString<16> z = RF(r);
                S = S;
                return z;
            }
        }
        """)
    result = UniqueRFSimplification().apply(game, _make_ctx())
    assert (
        result == game
    ), "RF should not be simplified when the exclusion set is explicitly modified"


def test_duplicate_rf_arg_not_simplified() -> None:
    """If the same uniquely-sampled variable is used as argument to two
    RF calls, both calls return the same value (RF is a function).
    Replacing both with independent samples is wrong."""
    game = frog_parser.parse_game("""
        Game G() {
            Set<BitString<8>> S;
            Function<BitString<8>, BitString<16>> RF;
            Void Initialize() {
                RF <- Function<BitString<8>, BitString<16>>;
            }
            [BitString<16>, BitString<16>] Query() {
                BitString<8> r <-uniq[S] BitString<8>;
                BitString<16> z1 = RF(r);
                BitString<16> z2 = RF(r);
                return [z1, z2];
            }
        }
        """)
    result = UniqueRFSimplification().apply(game, _make_ctx())
    # RF(r) should NOT be replaced because r is used for two RF calls
    assert (
        result == game
    ), "RF with duplicate argument variable should not be simplified"


def test_aliased_rf_not_simplified() -> None:
    """F-019: copying the function field into a local (``g = RF``) lets it be
    re-queried through the alias on an adversary-chosen input. The call-site
    walk only sees direct ``RF(...)`` calls, so the escape must be detected
    separately and block the rewrite -- otherwise the guarded site becomes an
    independent sample while the aliased query survives."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Function<BitString<n>, BitString<n>> RF;
            Set<BitString<n>> S;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<n>>;
            }
            [BitString<n>, BitString<n>] Chal() {
                BitString<n> r <-uniq[S] BitString<n>;
                BitString<n> z = RF(r);
                return [r, z];
            }
            BitString<n> Probe(BitString<n> x) {
                Function<BitString<n>, BitString<n>> g = RF;
                BitString<n> y = g(x);
                return y;
            }
        }
        """)
    result = UniqueRFSimplification().apply(game, _make_ctx())
    assert result == game, "aliased RF must not be simplified (F-019)"


def test_rf_passed_as_argument_not_simplified() -> None:
    """F-019: passing the function field as a method argument is also an
    escape that the call-site walk cannot follow."""
    game = frog_parser.parse_game("""
        Game G(Int n) {
            Function<BitString<n>, BitString<n>> RF;
            Set<BitString<n>> S;
            Void Initialize() {
                RF <- Function<BitString<n>, BitString<n>>;
            }
            BitString<n> Chal() {
                BitString<n> r <-uniq[S] BitString<n>;
                BitString<n> z = RF(r);
                sink(RF);
                return z;
            }
        }
        """)
    result = UniqueRFSimplification().apply(game, _make_ctx())
    assert result == game, "RF passed as an argument must not be simplified (F-019)"


def test_dotted_nondomain_exclusion_set_modified_not_simplified() -> None:
    """F-020: a non-``.domain`` dotted exclusion set is NOT auto-maintained, so
    an explicit field assignment to it must still be detected. Previously every
    dotted set name was exempted unconditionally."""
    from proof_frog.transforms.random_functions import _exclusion_set_modified

    game = frog_parser.parse_game("""
        Game G(Int n) {
            Set<BitString<n>> S;
            BitString<n> Query(BitString<n> v) {
                S.field = v;
                return v;
            }
        }
        """)
    # A `.domain` set is auto-maintained -> not flagged.
    assert not _exclusion_set_modified(game, "RF.domain")
    # A non-`.domain` dotted set with an explicit field assignment IS flagged.
    assert _exclusion_set_modified(game, "S.field")
