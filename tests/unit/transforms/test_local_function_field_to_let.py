"""Tests for the LocalFunctionFieldToLet transform pass.

The transform unifies a game-local sampled ``Function<K, V>`` field with
a let-bound sampled ``H : Function<K, V>`` of identical type, provided
``H`` is not otherwise referenced in the game.
"""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import LocalFunctionFieldToLet
from proof_frog.visitors import NameTypeMap


_BS8_TO_BS16 = frog_ast.FunctionType(
    frog_ast.BitStringType(frog_ast.Integer(8)),
    frog_ast.BitStringType(frog_ast.Integer(16)),
)


def _ctx(
    *,
    sampled: dict[str, frog_ast.FunctionType] | None = None,
    declared: dict[str, frog_ast.FunctionType] | None = None,
) -> PipelineContext:
    types = NameTypeMap()
    sampled_names: set[str] = set()
    for name, t in (sampled or {}).items():
        types.set(name, t)
        sampled_names.add(name)
    for name, t in (declared or {}).items():
        types.set(name, t)
    return PipelineContext(
        variables={},
        proof_let_types=types,
        proof_namespace={},
        subsets_pairs=[],
        sampled_let_names=sampled_names,
    )


def _apply_and_expect(
    game_src: str, expected_src: str, ctx: PipelineContext
) -> None:
    game = frog_parser.parse_game(game_src)
    result = LocalFunctionFieldToLet().apply(game, ctx)
    expected = frog_parser.parse_game(expected_src)
    assert result == expected, f"\nGOT:\n{result}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str, ctx: PipelineContext) -> None:
    game = frog_parser.parse_game(game_src)
    result = LocalFunctionFieldToLet().apply(game, ctx)
    assert result == game, f"\nGOT:\n{result}\n\nEXPECTED UNCHANGED:\n{game}"


def test_minimal_game_rewrites() -> None:
    _apply_and_expect(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                return F(x);
            }
        }
        """,
        """
        Game G() {
            Void Initialize() {
            }
            BitString<16> Hash(BitString<8> x) {
                return H(x);
            }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_multiple_oracles_rewrite() -> None:
    _apply_and_expect(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> A(BitString<8> x) { return F(x); }
            BitString<16> B(BitString<8> y) { return F(y); }
        }
        """,
        """
        Game G() {
            Void Initialize() {
            }
            BitString<16> A(BitString<8> x) { return H(x); }
            BitString<16> B(BitString<8> y) { return H(y); }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_complex_call_argument_preserved() -> None:
    _apply_and_expect(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            BitString<8> field2;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
                field2 <- BitString<8>;
            }
            BitString<16> Decaps(BitString<8> c) {
                if (c == field2) { return 0^16; }
                return F(c);
            }
        }
        """,
        """
        Game G() {
            BitString<8> field2;
            Void Initialize() {
                field2 <- BitString<8>;
            }
            BitString<16> Decaps(BitString<8> c) {
                if (c == field2) { return 0^16; }
                return H(c);
            }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_unrelated_function_field_stays() -> None:
    # Two Function fields, only F1 qualifies (F2 has no matching let).
    _apply_and_expect(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F1;
            Function<BitString<16>, BitString<8>> F2;
            Void Initialize() {
                F1 <- Function<BitString<8>, BitString<16>>;
                F2 <- Function<BitString<16>, BitString<8>>;
            }
            BitString<16> A(BitString<8> x) { return F1(x); }
            BitString<8> B(BitString<16> y) { return F2(y); }
        }
        """,
        """
        Game G() {
            Function<BitString<16>, BitString<8>> F2;
            Void Initialize() {
                F2 <- Function<BitString<16>, BitString<8>>;
            }
            BitString<16> A(BitString<8> x) { return H(x); }
            BitString<8> B(BitString<16> y) { return F2(y); }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_no_matching_let_is_noop() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """,
        _ctx(),
    )


def test_declared_not_sampled_let_is_noop() -> None:
    # H is declared (known deterministic) but not sampled → decline.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """,
        _ctx(declared={"H": _BS8_TO_BS16}),
    )


def test_type_mismatch_let_is_noop() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """,
        _ctx(
            sampled={
                "H": frog_ast.FunctionType(
                    frog_ast.BitStringType(frog_ast.Integer(16)),
                    frog_ast.BitStringType(frog_ast.Integer(8)),
                )
            }
        ),
    )


def test_f_not_sampled_in_initialize_is_noop() -> None:
    # F declared as a field but never sampled in Initialize → decline.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_h_referenced_in_game_is_noop() -> None:
    # H is already referenced in the game body (violates P-5).
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
            BitString<16> Other(BitString<8> y) { return H(y); }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )


def test_f_reassigned_outside_initialize_is_noop() -> None:
    # F is reassigned in an oracle → violates P-2.
    _apply_and_expect_unchanged(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                F <- Function<BitString<8>, BitString<16>>;
                return F(x);
            }
        }
        """,
        _ctx(sampled={"H": _BS8_TO_BS16}),
    )
