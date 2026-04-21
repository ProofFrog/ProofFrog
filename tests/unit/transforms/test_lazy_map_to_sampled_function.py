"""Tests for the LazyMapToSampledFunction transform pass."""

from proof_frog import frog_ast, frog_parser
from proof_frog.transforms._base import PipelineContext
from proof_frog.transforms.random_functions import LazyMapToSampledFunction
from proof_frog.visitors import NameTypeMap


def _ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def _apply(game_src: str) -> frog_ast.Game:
    game = frog_parser.parse_game(game_src)
    return LazyMapToSampledFunction().apply(game, _ctx())


def _apply_and_expect(game_src: str, expected_src: str) -> None:
    got = _apply(game_src)
    expected = frog_parser.parse_game(expected_src)
    assert got == expected, f"\nGOT:\n{got}\n\nEXPECTED:\n{expected}"


def _apply_and_expect_unchanged(game_src: str) -> None:
    original = frog_parser.parse_game(game_src)
    got = LazyMapToSampledFunction().apply(original, _ctx())
    assert got == original, f"\nGOT:\n{got}\n\nEXPECTED UNCHANGED:\n{original}"


def test_basic_hash_idiom() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x);
            }
        }
        """,
    )


def test_extra_map_read_outside_idiom_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
            Int Count(BitString<8> x) {
                if (x in T) {
                    return 1;
                }
                return 0;
            }
        }
        """
    )


def test_map_cardinality_use_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_initialize_touches_map_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T[0b00000000] = 0b0000000000000000;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_idiom_with_prefix_statements_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                Int n = |T|;
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )


def test_wrong_shape_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                return s;
            }
        }
        """
    )


def test_no_idiom_at_all_fails() -> None:
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
        }
        """
    )


def test_multiple_methods_all_idiom() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> HashA(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
            BitString<16> HashB(BitString<8> y) {
                if (y in T) {
                    return T[y];
                }
                BitString<16> s <- BitString<16>;
                T[y] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> HashA(BitString<8> x) {
                return T(x);
            }
            BitString<16> HashB(BitString<8> y) {
                return T(y);
            }
        }
        """,
    )


def test_idiom_with_prefix_not_touching_map() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x, Int i) {
                Int j = i + 1;
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x, Int i) {
                Int j = i + 1;
                return T(x);
            }
        }
        """,
    )


def test_initialize_present_no_map_refs_ok() -> None:
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int counter;
            Void Initialize() {
                counter = 0;
            }
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<8>, BitString<16>> T;
            Int counter;
            Void Initialize() {
                T <- Function<BitString<8>, BitString<16>>;
                counter = 0;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x);
            }
        }
        """,
    )


def test_expression_keyed_idiom() -> None:
    """Key is a pure, parameter-referencing expression — matcher should match."""
    _apply_and_expect(
        """
        Game G() {
            Map<BitString<4>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x[0:4] in T) {
                    return T[x[0:4]];
                }
                BitString<16> s <- BitString<16>;
                T[x[0:4]] = s;
                return s;
            }
        }
        """,
        """
        Game G() {
            Function<BitString<4>, BitString<16>> T;
            Void Initialize() {
                T <- Function<BitString<4>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) {
                return T(x[0:4]);
            }
        }
        """,
    )


def test_expression_keyed_idiom_needs_parameter() -> None:
    """Key expression must reference a parameter (otherwise the 'map entry
    per caller input' interpretation is invalid)."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            BitString<4> c;
            Map<BitString<4>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (c in T) {
                    return T[c];
                }
                BitString<16> s <- BitString<16>;
                T[c] = s;
                return s;
            }
        }
        """
    )


def test_pipeline_collapses_sample_between_duplicate_in_checks() -> None:
    """When the sample is hoisted between two identical `k in M` checks
    (as produced by LazyMapScan iterations), the pipeline should still
    canonicalize the map to a sampled Function."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.transforms._base import run_pipeline
    from proof_frog.transforms.pipelines import CORE_PIPELINE

    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                if (x in T) {
                    return T[x];
                }
                T[x] = s;
                return s;
            }
        }
        """
    )
    result = run_pipeline(game, CORE_PIPELINE, _ctx())
    t_field = next(f for f in result.fields if f.name == "T")
    assert isinstance(t_field.type, frog_ast.FunctionType)
    hash_method = next(
        m for m in result.methods if m.signature.name == "Hash"
    )
    assert len(hash_method.block.statements) == 1


def test_integration_via_core_pipeline() -> None:
    """With LazyMapToSampledFunction in the pipeline, a lazy Hash oracle
    canonicalizes such that the Map field becomes a sampled Function."""
    # pylint: disable=import-outside-toplevel
    from proof_frog.transforms._base import run_pipeline
    from proof_frog.transforms.pipelines import CORE_PIPELINE

    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            BitString<16> Hash(BitString<8> x) {
                if (x in T) {
                    return T[x];
                }
                BitString<16> s <- BitString<16>;
                T[x] = s;
                return s;
            }
        }
        """
    )
    result = run_pipeline(game, CORE_PIPELINE, _ctx())
    t_field = next(f for f in result.fields if f.name == "T")
    assert isinstance(t_field.type, frog_ast.FunctionType)
    hash_method = next(
        m for m in result.methods if m.signature.name == "Hash"
    )
    assert len(hash_method.block.statements) == 1
