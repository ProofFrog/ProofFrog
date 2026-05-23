from proof_frog.transforms._base import (
    NearMiss,
    PipelineContext,
    deduplicate_near_misses,
)
from proof_frog import frog_parser, frog_ast
from proof_frog.transforms.algebraic import (
    UniformXorSimplification,
    UniformModIntSimplification,
    XorCancellation,
)
from proof_frog.transforms.control_flow import BranchElimination
from proof_frog.transforms.inlining import (
    InlineSingleUseVariable,
    InlineSingleUseField,
    DeduplicateDeterministicCalls,
    HoistDeterministicCallToInitialize,
)
from proof_frog.transforms.sampling import MergeUniformSamples, SplitUniformSamples
from proof_frog.transforms.random_functions import (
    LocalRFToUniform,
    DistinctConstRFToUniform,
    LazyMapPairToSampledFunction,
    LocalFunctionFieldToLet,
)
from proof_frog.transforms.structural import UniformBijectionElimination
from proof_frog.visitors import NameTypeMap


def test_near_miss_dataclass():
    nm = NearMiss(
        transform_name="UniformXorSimplification",
        reason="Variable 'r' used 2 times (need exactly 1)",
        location=None,
        suggestion="Isolate the use of 'r' in a separate intermediate game",
        variable="r",
        method="Encrypt",
    )
    assert nm.transform_name == "UniformXorSimplification"
    assert nm.variable == "r"


def test_pipeline_context_has_near_misses():
    ctx = PipelineContext(
        variables={},
        proof_let_types=None,  # type: ignore[arg-type]
        proof_namespace={},
        subsets_pairs=[],
    )
    assert hasattr(ctx, "near_misses")
    assert ctx.near_misses == []


def test_pipeline_context_near_misses_independent():
    """Each PipelineContext gets its own near_misses list."""
    ctx1 = PipelineContext(
        variables={},
        proof_let_types=None,  # type: ignore[arg-type]
        proof_namespace={},
        subsets_pairs=[],
    )
    ctx2 = PipelineContext(
        variables={},
        proof_let_types=None,  # type: ignore[arg-type]
        proof_namespace={},
        subsets_pairs=[],
    )
    ctx1.near_misses.append(NearMiss("Test", "reason", None, None, None, None))
    assert len(ctx2.near_misses) == 0


def test_deduplicate_near_misses():
    """Near-misses with same (transform, method, variable) are deduplicated."""
    misses = [
        NearMiss("XOR", "reason 1", None, None, "r", "Encrypt"),
        NearMiss("XOR", "reason 2", None, None, "r", "Encrypt"),  # duplicate key
        NearMiss("XOR", "reason 3", None, None, "s", "Encrypt"),  # different variable
        NearMiss(
            "Inline", "reason 4", None, None, "r", "Encrypt"
        ),  # different transform
    ]
    deduped = deduplicate_near_misses(misses)
    assert len(deduped) == 3
    assert deduped[0].reason == "reason 1"
    assert deduped[1].variable == "s"
    assert deduped[2].transform_name == "Inline"


def _make_game(method_body: str) -> object:
    """Parse a minimal game with one method from a method body string."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<lambda> Encrypt(BitString<lambda> m) {\n"
        f"        {method_body}\n"
        "    }\n"
        "}"
    )
    return frog_parser.parse_game(game_src)


def _make_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_xor_near_miss_variable_used_twice():
    """XOR simplification reports near-miss when uniform var is used > 1 time."""
    game = _make_game(
        "BitString<lambda> u <- BitString<lambda>;\n"
        "        BitString<lambda> x = u + m;\n"
        "        return x + u;"
    )
    ctx = _make_ctx()
    xform = UniformXorSimplification()
    result = xform.apply(game, ctx)

    assert result == game  # transform should NOT have fired
    assert len(ctx.near_misses) >= 1
    nm = ctx.near_misses[0]
    assert nm.transform_name == "Uniform XOR Simplification"
    assert "u" in nm.reason
    assert nm.variable == "u"


def test_xor_no_near_miss_when_no_sample():
    """No near-miss when there's no uniform sample at all."""
    game = _make_game("return m;")
    ctx = _make_ctx()
    UniformXorSimplification().apply(game, ctx)
    assert len(ctx.near_misses) == 0


def test_inline_near_miss_variable_used_twice():
    """Inline single-use reports near-miss when variable used > 1 time."""
    game = _make_game(
        "BitString<lambda> ct = m + m;\n"
        "        BitString<lambda> x = ct + ct;\n"
        "        return x;"
    )
    ctx = _make_ctx()
    InlineSingleUseVariable().apply(game, ctx)

    ct_misses = [nm for nm in ctx.near_misses if nm.variable == "ct"]
    assert len(ct_misses) >= 1
    assert "2" in ct_misses[0].reason or "used" in ct_misses[0].reason.lower()


def test_inline_near_miss_free_var_modified():
    """Inline single-use reports near-miss when free var modified between decl and use."""
    game = _make_game(
        "BitString<lambda> k <- BitString<lambda>;\n"
        "        BitString<lambda> ct = k + m;\n"
        "        k <- BitString<lambda>;\n"
        "        return ct;"
    )
    ctx = _make_ctx()
    InlineSingleUseVariable().apply(game, ctx)

    ct_misses = [nm for nm in ctx.near_misses if nm.variable == "ct"]
    assert len(ct_misses) >= 1
    assert (
        "k" in ct_misses[0].reason.lower() or "modified" in ct_misses[0].reason.lower()
    )


# ---------------------------------------------------------------------------
# UniformModIntSimplification near-miss tests
# ---------------------------------------------------------------------------


def _make_modint_game(method_body: str) -> object:
    """Parse a minimal game with ModInt types."""
    game_src = (
        "Game TestGame() {\n"
        "    ModInt<q> Encrypt(ModInt<q> m) {\n"
        f"        {method_body}\n"
        "    }\n"
        "}"
    )
    return frog_parser.parse_game(game_src)


def test_modint_near_miss_variable_used_twice():
    """ModInt simplification reports near-miss when uniform var used > 1 time."""
    game = _make_modint_game(
        "ModInt<q> u <- ModInt<q>;\n"
        "        ModInt<q> x = u + m;\n"
        "        return x + u;"
    )
    ctx = _make_ctx()
    UniformModIntSimplification().apply(game, ctx)

    assert len(ctx.near_misses) >= 1
    nm = ctx.near_misses[0]
    assert nm.transform_name == "Uniform ModInt Simplification"
    assert "u" in nm.reason
    assert nm.variable == "u"


def test_modint_no_near_miss_when_no_sample():
    """No near-miss when there's no uniform ModInt sample."""
    game = _make_modint_game("return m;")
    ctx = _make_ctx()
    UniformModIntSimplification().apply(game, ctx)
    assert len(ctx.near_misses) == 0


# ---------------------------------------------------------------------------
# XorCancellation near-miss tests
# ---------------------------------------------------------------------------


def test_xor_cancellation_near_miss_modint_context():
    """XOR cancellation reports near-miss when ADD chain is in ModInt context."""
    game_src = (
        "Game TestGame() {\n"
        "    ModInt<q> Compute(ModInt<q> a) {\n"
        "        return a + a;\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = _make_ctx()
    XorCancellation().apply(game, ctx)

    assert len(ctx.near_misses) >= 1
    nm = ctx.near_misses[0]
    assert nm.transform_name == "XOR Cancellation"
    assert "modular arithmetic" in nm.reason.lower()


def test_xor_cancellation_no_near_miss_bitstring():
    """No near-miss when ADD chain is in bitstring context (fires normally)."""
    game = _make_game(
        "BitString<lambda> k <- BitString<lambda>;\n" "        return k + k + m;"
    )
    ctx = _make_ctx()
    XorCancellation().apply(game, ctx)
    # Transform should fire, so no near-miss expected
    assert (
        len([nm for nm in ctx.near_misses if nm.transform_name == "XOR Cancellation"])
        == 0
    )


# ---------------------------------------------------------------------------
# BranchElimination near-miss tests
# ---------------------------------------------------------------------------


def test_branch_elimination_near_miss_non_literal_condition():
    """Branch elimination reports near-miss when condition is not a literal."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<lambda> Encrypt(BitString<lambda> m, Bool b) {\n"
        "        if (b) {\n"
        "            return m;\n"
        "        }\n"
        "        return m;\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = _make_ctx()
    BranchElimination().apply(game, ctx)

    assert len(ctx.near_misses) >= 1
    nm = ctx.near_misses[0]
    assert nm.transform_name == "Branch Elimination"
    assert "compile-time constant" in nm.reason.lower()


def test_branch_elimination_no_near_miss_when_no_if():
    """No near-miss when there are no if-statements."""
    game = _make_game("return m;")
    ctx = _make_ctx()
    BranchElimination().apply(game, ctx)
    assert len(ctx.near_misses) == 0


# ---------------------------------------------------------------------------
# InlineSingleUseField near-miss tests
# ---------------------------------------------------------------------------


def test_inline_field_near_miss_cross_method():
    """InlineSingleUseField reports near-miss when a non-pure field with
    local free vars is used across methods."""
    game_src = (
        "Game TestGame() {\n"
        "    Int myfield;\n"
        "    Void Initialize() {\n"
        "        Int x = 42;\n"
        "        myfield = x + 1;\n"
        "    }\n"
        "    Int Query() {\n"
        "        return myfield;\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = _make_ctx()
    InlineSingleUseField().apply(game, ctx)

    field_misses = [nm for nm in ctx.near_misses if nm.variable == "myfield"]
    assert len(field_misses) >= 1
    assert "multiple methods" in field_misses[0].reason.lower()


# ---------------------------------------------------------------------------
# LocalRFToUniform near-miss tests
# ---------------------------------------------------------------------------


def test_local_rf_near_miss_called_twice():
    """LocalRFToUniform reports near-miss when RF is called more than once."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<lambda> Encrypt(BitString<lambda> m) {\n"
        "        Function<BitString<lambda>, BitString<lambda>> RF "
        "<- Function<BitString<lambda>, BitString<lambda>>;\n"
        "        BitString<lambda> a = RF(m);\n"
        "        BitString<lambda> b = RF(m);\n"
        "        return a + b;\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = _make_ctx()
    LocalRFToUniform().apply(game, ctx)

    rf_misses = [nm for nm in ctx.near_misses if nm.variable == "RF"]
    assert len(rf_misses) >= 1
    assert "2" in rf_misses[0].reason or "called" in rf_misses[0].reason.lower()


def test_local_rf_no_near_miss_when_no_rf():
    """No near-miss when there's no RF sample."""
    game = _make_game("return m;")
    ctx = _make_ctx()
    LocalRFToUniform().apply(game, ctx)
    assert len(ctx.near_misses) == 0


# ---------------------------------------------------------------------------
# DistinctConstRFToUniform near-miss tests
# ---------------------------------------------------------------------------


def _make_bitstring1_rf_game(body: str) -> object:
    """Parse a game with a BitString<1> Query method for RF-constant tests."""
    src = (
        "Game TestGame() {\n"
        "    BitString<2> Query() {\n"
        f"        {body}\n"
        "    }\n"
        "}"
    )
    return frog_parser.parse_game(src)


def test_distinct_const_rf_near_miss_non_literal_arg():
    """Reports near-miss when an RF argument is not a literal constant."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<2> Query(BitString<1> x) {\n"
        "        Function<BitString<1>, BitString<1>> RF "
        "<- Function<BitString<1>, BitString<1>>;\n"
        "        return RF(0b0) || RF(x);\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = _make_ctx()
    DistinctConstRFToUniform().apply(game, ctx)
    rf_misses = [nm for nm in ctx.near_misses if nm.variable == "RF"]
    assert len(rf_misses) == 1
    assert "literal" in rf_misses[0].reason.lower()


def test_distinct_const_rf_near_miss_duplicate_literal():
    """Reports near-miss when RF is called on duplicate literal constants."""
    game = _make_bitstring1_rf_game(
        "Function<BitString<1>, BitString<1>> RF "
        "<- Function<BitString<1>, BitString<1>>;\n"
        "        return RF(0b0) || RF(0b0);"
    )
    ctx = _make_ctx()
    DistinctConstRFToUniform().apply(game, ctx)
    rf_misses = [nm for nm in ctx.near_misses if nm.variable == "RF"]
    assert len(rf_misses) == 1
    assert "duplicate" in rf_misses[0].reason.lower()


def test_distinct_const_rf_no_near_miss_when_fires():
    """No near-miss when the transform successfully fires."""
    game = _make_bitstring1_rf_game(
        "Function<BitString<1>, BitString<1>> RF "
        "<- Function<BitString<1>, BitString<1>>;\n"
        "        return RF(0b0) || RF(0b1);"
    )
    ctx = _make_ctx()
    DistinctConstRFToUniform().apply(game, ctx)
    rf_misses = [nm for nm in ctx.near_misses if nm.variable == "RF"]
    assert len(rf_misses) == 0


# ---------------------------------------------------------------------------
# DeduplicateDeterministicCalls near-miss tests
# ---------------------------------------------------------------------------


def _make_nondet_namespace() -> dict:
    """Namespace with primitive G whose ``evaluate`` is NOT deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            BitString<n> evaluate(BitString<n> x);
        }
        """)
    return {"G": prim}


def _make_det_namespace() -> dict:
    """Namespace with primitive G whose ``evaluate`` is deterministic."""
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """)
    return {"G": prim}


def test_dedup_near_miss_nondeterministic_duplicates():
    """DeduplicateDeterministicCalls reports near-miss for duplicate
    non-deterministic calls."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<n> Compute(BitString<n> k) {\n"
        "        return [G.evaluate(k), G.evaluate(k)];\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=_make_nondet_namespace(),
        subsets_pairs=[],
    )
    DeduplicateDeterministicCalls().apply(game, ctx)

    dedup_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Deduplicate Deterministic Calls"
    ]
    assert len(dedup_misses) >= 1
    assert "not annotated deterministic" in dedup_misses[0].reason


def test_dedup_no_near_miss_when_deterministic():
    """No near-miss when duplicates ARE deterministic (transform fires)."""
    game_src = (
        "Game TestGame() {\n"
        "    BitString<n> Compute(BitString<n> k) {\n"
        "        return [G.evaluate(k), G.evaluate(k)];\n"
        "    }\n"
        "}"
    )
    game = frog_parser.parse_game(game_src)
    ctx = PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=_make_det_namespace(),
        subsets_pairs=[],
    )
    DeduplicateDeterministicCalls().apply(game, ctx)

    dedup_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Deduplicate Deterministic Calls"
    ]
    assert len(dedup_misses) == 0


# --- Uniform Bijection Elimination near-miss tests ---


def _make_bijection_ctx(
    primitives: dict[str, str] | None = None,
) -> PipelineContext:
    ns: dict[str, frog_ast.Primitive | None] = {}
    if primitives:
        for name, src in primitives.items():
            ns[name] = frog_parser.parse_primitive_file(src)
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace=ns,
        subsets_pairs=[],
    )


def test_bijection_near_miss_mixed_uses():
    """Near-miss when uniform var has some qualifying wraps but also bare uses."""
    game = frog_parser.parse_game(
        "Game TestGame() {\n"
        "    BitString<256> Compute() {\n"
        "        BitString<256> x <- BitString<256>;\n"
        "        BitString<256> a = K.Encode(x);\n"
        "        return x;\n"
        "    }\n"
        "}"
    )
    ctx = _make_bijection_ctx(
        {
            "K": (
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> v);"
                "}"
            )
        }
    )
    UniformBijectionElimination().apply(game, ctx)

    bijection_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Uniform Bijection Elimination"
    ]
    assert len(bijection_misses) == 1
    assert bijection_misses[0].variable == "x"
    assert "1 of 2" in bijection_misses[0].reason


def test_bijection_no_near_miss_when_eligible():
    """No near-miss when transform fires (all uses are qualifying wraps)."""
    game = frog_parser.parse_game(
        "Game TestGame() {\n"
        "    BitString<256> Compute() {\n"
        "        BitString<256> x <- BitString<256>;\n"
        "        return K.Encode(x);\n"
        "    }\n"
        "}"
    )
    ctx = _make_bijection_ctx(
        {
            "K": (
                "Primitive K() {"
                "  deterministic injective BitString<256> Encode(BitString<256> v);"
                "}"
            )
        }
    )
    UniformBijectionElimination().apply(game, ctx)

    bijection_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Uniform Bijection Elimination"
    ]
    assert len(bijection_misses) == 0


def test_bijection_no_near_miss_when_no_wraps():
    """No near-miss when there are zero qualifying wraps (nothing close)."""
    game = frog_parser.parse_game(
        "Game TestGame() {\n"
        "    BitString<256> Compute() {\n"
        "        BitString<256> x <- BitString<256>;\n"
        "        return x;\n"
        "    }\n"
        "}"
    )
    ctx = _make_bijection_ctx({})
    UniformBijectionElimination().apply(game, ctx)

    bijection_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Uniform Bijection Elimination"
    ]
    assert len(bijection_misses) == 0


def _make_hoist_ctx() -> PipelineContext:
    prim = frog_parser.parse_primitive_file("""
        Primitive G(Int n) {
            deterministic BitString<n> evaluate(BitString<n> x);
        }
        """)
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={"G": prim, "GG": prim},
        subsets_pairs=[],
    )


def test_hoist_near_miss_field_reassigned_in_oracle():
    """Hoist reports a near-miss when an arg-field is reassigned outside Initialize."""
    game = frog_parser.parse_game("""
        Game Foo(G GG) {
            BitString<n> seed;
            Void Initialize() {
                seed <- BitString<n>;
            }
            BitString<n> Get1() {
                return GG.evaluate(seed);
            }
            Void Reset() {
                seed <- BitString<n>;
            }
        }
        """)
    ctx = _make_hoist_ctx()
    HoistDeterministicCallToInitialize().apply(game, ctx)

    hoist_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Hoist Deterministic Call to Initialize"
    ]
    assert len(hoist_misses) >= 1
    nm = hoist_misses[0]
    assert "seed" in nm.reason


def test_hoist_no_near_miss_when_hoisting_succeeds():
    """No near-miss is reported when the transform fires."""
    game = frog_parser.parse_game("""
        Game Foo(G GG) {
            BitString<n> seed;
            Void Initialize() {
                seed <- BitString<n>;
            }
            BitString<n> Get1() {
                return GG.evaluate(seed);
            }
            BitString<n> Get2() {
                return GG.evaluate(seed);
            }
        }
        """)
    ctx = _make_hoist_ctx()
    HoistDeterministicCallToInitialize().apply(game, ctx)

    hoist_misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Hoist Deterministic Call to Initialize"
    ]
    assert len(hoist_misses) == 0


from proof_frog.transforms.random_functions import LazyMapToSampledFunction


def _lazy_map_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_lazy_map_near_miss_cardinality_use() -> None:
    game = frog_parser.parse_game(
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
    ctx = _lazy_map_ctx()
    result = LazyMapToSampledFunction().apply(game, ctx)
    assert result == game
    assert any(
        nm.transform_name == "Lazy Map To Sampled Function"
        and nm.method == "Size"
        and nm.variable == "T"
        for nm in ctx.near_misses
    )


def test_lazy_map_near_miss_explicit_initialize() -> None:
    game = frog_parser.parse_game(
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
    ctx = _lazy_map_ctx()
    LazyMapToSampledFunction().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map To Sampled Function"
        and nm.method == "Initialize"
        and nm.variable == "T"
        for nm in ctx.near_misses
    )


def test_lazy_map_no_near_miss_when_no_idiom() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> T;
            Int Size() {
                return |T|;
            }
        }
        """
    )
    ctx = _lazy_map_ctx()
    LazyMapToSampledFunction().apply(game, ctx)
    assert not any(
        nm.transform_name == "Lazy Map To Sampled Function"
        for nm in ctx.near_misses
    )


from proof_frog.transforms.map_iteration import LazyMapScan


def _lazy_scan_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_lazy_scan_near_miss_if_with_else() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            BitString<16> Oracle(BitString<8> arg) {
                for ([BitString<8>, BitString<16>] e in M.entries) {
                    if (e[0] == arg) {
                        return e[1];
                    } else {
                        return 0b0000000000000000;
                    }
                }
                return 0b0000000000000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    result = LazyMapScan().apply(game, ctx)
    assert result == game
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and nm.variable == "M"
        and "else" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_near_miss_key_references_loop_var() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Oracle() {
                for ([BitString<8>, BitString<8>] e in M.entries) {
                    if (e[0] == e[1]) {
                        return e[0];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    LazyMapScan().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and "loop variable" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_no_near_miss_when_no_scan() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<16>> M;
            Int Size() {
                return |M|;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    LazyMapScan().apply(game, ctx)
    assert not any(
        nm.transform_name == "Lazy Map Scan" for nm in ctx.near_misses
    )



_TRAPDOOR_TEST_PRIMITIVE_SRC = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic injective Bool Test(Input x, Image y);
}
"""


_NON_INJECTIVE_PRIMITIVE_SRC = """
Primitive T(Set I, Set Y) {
    Set Input = I;
    Set Image = Y;
    deterministic Bool Test(Input x, Image y);
}
"""


def _register_primitive(ctx: PipelineContext, src: str) -> None:
    prim = frog_parser.parse_string(src, frog_ast.FileType.PRIMITIVE)
    ctx.proof_namespace[prim.name] = prim
    ctx.proof_namespace["TT"] = prim


def test_lazy_scan_injective_near_miss_not_injective() -> None:
    game = frog_parser.parse_game(
        """
        Game G(T TT) {
            Map<TT.Image, BitString<8>> M;
            BitString<8> Oracle(TT.Input c) {
                for ([TT.Image, BitString<8>] e in M.entries) {
                    if (TT.Test(c, e[0])) {
                        return e[1];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    _register_primitive(ctx, _NON_INJECTIVE_PRIMITIVE_SRC)
    LazyMapScan().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and nm.variable == "M"
        and "not annotated injective" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_injective_near_miss_callee_not_primitive() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Map<BitString<8>, BitString<8>> M;
            BitString<8> Oracle(BitString<8> c) {
                for ([BitString<8>, BitString<8>] e in M.entries) {
                    if (TT.Test(c, e[0])) {
                        return e[1];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    LazyMapScan().apply(game, ctx)
    assert any(
        nm.transform_name == "Lazy Map Scan"
        and nm.method == "Oracle"
        and "not a primitive method" in nm.reason
        for nm in ctx.near_misses
    )


def test_lazy_scan_injective_no_near_miss_when_valid() -> None:
    game = frog_parser.parse_game(
        """
        Game G(T TT) {
            Map<TT.Image, BitString<8>> M;
            BitString<8> Oracle(TT.Input c) {
                for ([TT.Image, BitString<8>] e in M.entries) {
                    if (TT.Test(c, e[0])) {
                        return e[1];
                    }
                }
                return 0b00000000;
            }
        }
        """
    )
    ctx = _lazy_scan_ctx()
    _register_primitive(ctx, _TRAPDOOR_TEST_PRIMITIVE_SRC)
    LazyMapScan().apply(game, ctx)
    assert not any(
        nm.transform_name == "Lazy Map Scan" for nm in ctx.near_misses
    )


# --- MapKeyReindex near-miss tests --------------------------------------------


from proof_frog.transforms.map_reindex import MapKeyReindex  # noqa: E402


def _ctx_for_map_reindex(prim_src: str) -> PipelineContext:
    prim = frog_parser.parse_string(prim_src, frog_ast.FileType.PRIMITIVE)
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={"T": prim, "TT": prim},
        subsets_pairs=[],
    )


def test_map_key_reindex_near_miss_non_injective():
    prim_src = """
    Primitive T(Set I, Set Y) {
        Set Input = I;
        Set Image = Y;
        deterministic Image Eval(Input x);
    }
    """
    game_src = """
    Game G(T TT) {
        Map<TT.Input, BitString<16>> M;
        Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
        BitString<16>? Lookup(TT.Input a) {
            if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
            return None;
        }
    }
    """
    ctx = _ctx_for_map_reindex(prim_src)
    game = frog_parser.parse_game(game_src)
    MapKeyReindex().apply(game, ctx)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss for non-injective f"
    assert any("injective" in nm.reason for nm in misses)


def test_map_key_reindex_near_miss_non_deterministic():
    prim_src = """
    Primitive T(Set I, Set Y) {
        Set Input = I;
        Set Image = Y;
        injective Image Eval(Input x);
    }
    """
    game_src = """
    Game G(T TT) {
        Map<TT.Input, BitString<16>> M;
        Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
        BitString<16>? Lookup(TT.Input a) {
            if (TT.Eval(a) in M) { return M[TT.Eval(a)]; }
            return None;
        }
    }
    """
    ctx = _ctx_for_map_reindex(prim_src)
    game = frog_parser.parse_game(game_src)
    MapKeyReindex().apply(game, ctx)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss for non-deterministic f"
    assert any("deterministic" in nm.reason for nm in misses)


def test_map_key_reindex_near_miss_bare_e0():
    prim_src = """
    Primitive T(Set I, Set Y) {
        Set Input = I;
        Set Image = Y;
        deterministic injective Image Eval(Input x);
    }
    """
    game_src = """
    Game G(T TT) {
        Map<TT.Input, BitString<16>> M;
        Void Store(TT.Input a, BitString<16> s) { M[a] = s; }
        TT.Input Leak() {
            for ([TT.Input, BitString<16>] e in M.entries) {
                return e[0];
            }
            return 0;
        }
    }
    """
    ctx = _ctx_for_map_reindex(prim_src)
    game = frog_parser.parse_game(game_src)
    MapKeyReindex().apply(game, ctx)
    misses = [nm for nm in ctx.near_misses if nm.transform_name == "Map Key Reindex"]
    assert misses, "expected a near-miss for bare e[0] use"
    assert any("e[0]" in nm.reason or "wrapper" in nm.reason for nm in misses)


def _lazy_pair_ctx() -> PipelineContext:
    return PipelineContext(
        variables={},
        proof_let_types=NameTypeMap(),
        proof_namespace={},
        subsets_pairs=[],
    )


def test_lazy_map_pair_near_miss_cardinality():
    game_src = """
    Game G() {
        Map<BitString<8>, BitString<16>> M1;
        Map<BitString<8>, BitString<16>> M2;
        Int Count() { return |M1|; }
        BitString<16> Query(BitString<8> k) {
            if (k in M1) { return M1[k]; }
            else if (k in M2) { return M2[k]; }
            BitString<16> s <- BitString<16>;
            M1[k] = s;
            return s;
        }
    }
    """
    game = frog_parser.parse_game(game_src)
    ctx = _lazy_pair_ctx()
    LazyMapPairToSampledFunction().apply(game, ctx)
    misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Lazy Map Pair to Sampled Function"
    ]
    assert misses
    assert any("outside the lazy-lookup idiom" in nm.reason for nm in misses)


def test_lazy_map_pair_near_miss_missing_guard():
    game_src = """
    Game G() {
        Map<BitString<8>, BitString<16>> M1;
        Map<BitString<8>, BitString<16>> M2;
        BitString<16> QueryA(BitString<8> k) {
            if (k in M1) { return M1[k]; }
            BitString<16> s <- BitString<16>;
            M1[k] = s;
            return s;
        }
        BitString<16> QueryB(BitString<8> k) {
            if (k in M2) { return M2[k]; }
            BitString<16> s <- BitString<16>;
            M2[k] = s;
            return s;
        }
    }
    """
    game = frog_parser.parse_game(game_src)
    ctx = _lazy_pair_ctx()
    LazyMapPairToSampledFunction().apply(game, ctx)
    misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Lazy Map Pair to Sampled Function"
    ]
    assert misses
    assert any(
        "disjointness" in nm.reason or "guard" in nm.reason for nm in misses
    )


def test_lazy_map_pair_near_miss_mismatched_types():
    game_src = """
    Game G() {
        Map<BitString<8>, BitString<16>> M1;
        Map<BitString<8>, BitString<32>> M2;
        BitString<16> QueryA(BitString<8> k) {
            if (k in M1) { return M1[k]; }
            BitString<16> s <- BitString<16>;
            M1[k] = s;
            return s;
        }
        BitString<32> QueryB(BitString<8> k) {
            if (k in M2) { return M2[k]; }
            BitString<32> s <- BitString<32>;
            M2[k] = s;
            return s;
        }
    }
    """
    game = frog_parser.parse_game(game_src)
    ctx = _lazy_pair_ctx()
    LazyMapPairToSampledFunction().apply(game, ctx)
    misses = [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Lazy Map Pair to Sampled Function"
    ]
    assert misses
    assert any("type" in nm.reason for nm in misses)


# ---------------------------------------------------------------------------
# LocalFunctionFieldToLet near-misses
# ---------------------------------------------------------------------------


_BS8_TO_BS16 = frog_ast.FunctionType(
    frog_ast.BitStringType(frog_ast.Integer(8)),
    frog_ast.BitStringType(frog_ast.Integer(16)),
)


def _local_fn_ctx(
    *, sampled: set[str] = frozenset(), declared: set[str] = frozenset()
) -> PipelineContext:
    types = NameTypeMap()
    for name in sampled:
        types.set(name, _BS8_TO_BS16)
    for name in declared:
        types.set(name, _BS8_TO_BS16)
    return PipelineContext(
        variables={},
        proof_let_types=types,
        proof_namespace={},
        subsets_pairs=[],
        sampled_let_names=set(sampled),
    )


def _local_fn_misses(ctx: PipelineContext) -> list:
    return [
        nm
        for nm in ctx.near_misses
        if nm.transform_name == "Local Function Field To Let"
    ]


def test_local_fn_near_miss_reassigned() -> None:
    game = frog_parser.parse_game(
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
        """
    )
    ctx = _local_fn_ctx(sampled={"H"})
    LocalFunctionFieldToLet().apply(game, ctx)
    misses = _local_fn_misses(ctx)
    assert misses
    assert any("assigned outside" in nm.reason for nm in misses)


def test_local_fn_near_miss_non_call_use() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            Bool Eq() {
                return F == F;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """
    )
    ctx = _local_fn_ctx(sampled={"H"})
    LocalFunctionFieldToLet().apply(game, ctx)
    misses = _local_fn_misses(ctx)
    assert misses
    assert any("non-call" in nm.reason for nm in misses)


def test_local_fn_near_miss_h_referenced() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
            BitString<16> Other(BitString<8> y) { return H(y); }
        }
        """
    )
    ctx = _local_fn_ctx(sampled={"H"})
    LocalFunctionFieldToLet().apply(game, ctx)
    misses = _local_fn_misses(ctx)
    assert misses
    assert any("referenced in method" in nm.reason for nm in misses)


def test_local_fn_near_miss_declared_not_sampled() -> None:
    game = frog_parser.parse_game(
        """
        Game G() {
            Function<BitString<8>, BitString<16>> F;
            Void Initialize() {
                F <- Function<BitString<8>, BitString<16>>;
            }
            BitString<16> Hash(BitString<8> x) { return F(x); }
        }
        """
    )
    ctx = _local_fn_ctx(declared={"H"})
    LocalFunctionFieldToLet().apply(game, ctx)
    misses = _local_fn_misses(ctx)
    assert misses
    assert any(
        "declared (known deterministic)" in nm.reason for nm in misses
    )
