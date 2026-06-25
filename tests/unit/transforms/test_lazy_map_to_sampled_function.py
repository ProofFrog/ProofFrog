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


def test_self_referential_key_fails() -> None:
    """F-005: a key expression that reads the map itself (`(k in M)`) is
    history-dependent -- the assign-site write `M[key] = x` changes what the
    key reads on later calls -- so the idiom must not collapse to
    `return M(k in M);` (which is ill-typed besides)."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<Bool, BitString<8>> M;
            BitString<8> Lookup(Bool k) {
                if ((k in M) in M) {
                    return M[k in M];
                }
                BitString<8> x <- BitString<8>;
                M[k in M] = x;
                return x;
            }
        }
        """
    )


def test_field_initializer_fails() -> None:
    """Same blind spot as F-009 (pair sibling): a field-level initializer
    (`Map<...> M = preset;`) is missed by the Initialize-body scan and dropped
    by the rebuild, so a preset map must disqualify the rewrite."""
    _apply_and_expect_unchanged(
        """
        Game G(Map<BitString<8>, BitString<8>> preset) {
            Map<BitString<8>, BitString<8>> M = preset;
            BitString<8> Lookup(BitString<8> k) {
                if (k in M) {
                    return M[k];
                }
                BitString<8> x <- BitString<8>;
                M[k] = x;
                return x;
            }
        }
        """
    )


def test_dotted_out_of_idiom_write_fails() -> None:
    """F-006: an out-of-idiom write spelled as a FieldAccess (`this.M[k] = v`)
    is still a write to the map field and must disqualify the rewrite, even
    though it contains no bare `Variable(M)` node."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Lookup(BitString<8> k) {
                if (k in M) {
                    return M[k];
                }
                BitString<8> x <- BitString<8>;
                M[k] = x;
                return x;
            }
            Void Poison(BitString<8> k, BitString<8> v) {
                this.M[k] = v;
            }
        }
        """
    )


def test_dotted_initialize_prepopulation_fails() -> None:
    """F-006: a dotted pre-population write in Initialize (`this.M[c] = v`)
    must disqualify the rewrite; the map is not empty at the start of the
    oracle phase."""
    _apply_and_expect_unchanged(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            Void Initialize() {
                this.M[0b00000000] = 0b10101010;
            }
            BitString<8> Lookup(BitString<8> k) {
                if (k in M) {
                    return M[k];
                }
                BitString<8> x <- BitString<8>;
                M[k] = x;
                return x;
            }
        }
        """
    )


def test_defensive_guard_sample_var_in_key_expr() -> None:
    """AST-level defense: if the sample variable name `s` appears
    syntactically inside `key_expr`, the three structural occurrences of
    `key_expr` straddle the sample statement (if-condition occurrence is
    pre-sample, assign-index occurrence is post-sample). Collapsing them
    into a single evaluation would be unsound. Not reachable from
    well-typed FrogLang (no block-scoped shadowing), but guarded at the
    AST level per PROMPT.md skepticism item (4). This test directly
    constructs the pathological AST to verify the transform declines."""
    bs8 = frog_ast.BitStringType(frog_ast.Integer(8))
    map_type = frog_ast.MapType(bs8, bs8)
    # Parameter named "s" so key_expr = Variable("s") passes the
    # parameter-reference check; sample also declared as "s" to trigger
    # the shadowing shape.
    in_check = frog_ast.BinaryOperation(
        frog_ast.BinaryOperators.IN,
        frog_ast.Variable("s"),
        frog_ast.Variable("T"),
    )
    guard_body = frog_ast.Block(
        [
            frog_ast.ReturnStatement(
                frog_ast.ArrayAccess(
                    frog_ast.Variable("T"), frog_ast.Variable("s")
                )
            )
        ]
    )
    if_stmt = frog_ast.IfStatement([in_check], [guard_body])
    sample_stmt = frog_ast.Sample(bs8, frog_ast.Variable("s"), bs8)
    assign_stmt = frog_ast.Assignment(
        None,
        frog_ast.ArrayAccess(frog_ast.Variable("T"), frog_ast.Variable("s")),
        frog_ast.Variable("s"),
    )
    ret_stmt = frog_ast.ReturnStatement(frog_ast.Variable("s"))
    method = frog_ast.Method(
        frog_ast.MethodSignature("Hash", bs8, [frog_ast.Parameter(bs8, "s")]),
        frog_ast.Block([if_stmt, sample_stmt, assign_stmt, ret_stmt]),
    )
    game = frog_ast.Game(
        ("G", [], [frog_ast.Field(map_type, "T", None)], [method])
    )
    got = LazyMapToSampledFunction().apply(game, _ctx())
    assert got == game, (
        "Transform must decline when the sample variable name appears in "
        "the key expression."
    )
