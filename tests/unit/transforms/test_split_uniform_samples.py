import pytest
from sympy import Symbol
from proof_frog import frog_parser
from proof_frog import frog_ast
from proof_frog.transforms.sampling import SplitUniformSampleTransformer


@pytest.mark.parametrize(
    "method,expected",
    [
        # Basic split: two slices covering the full range
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # Three-way split
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                BitString<lambda> c = z[2 * lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> z_2 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                BitString<lambda> c = z_2;
            }
            """,
        ),
        # Different sized slices
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<2 * lambda> z_1 <- BitString<2 * lambda>;
                BitString<lambda> a = z_0;
                BitString<2 * lambda> b = z_1;
            }
            """,
        ),
        # Partial split: slices don't cover the full range (gaps allowed)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # No split: variable used in non-slice context
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z;
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<2 * lambda> b = z;
            }
            """,
        ),
        # Slices used directly in return
        (
            """
            BitString<2 * lambda> f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                return a || b;
            }
            """,
            """
            BitString<2 * lambda> f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                return a || b;
            }
            """,
        ),
        # Duplicate slices: same bounds are deduplicated and split
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[0 : lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_0;
            }
            """,
        ),
        # No split: truly overlapping slices (different bounds that overlap)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<2 * lambda> a = z[0 : 2 * lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<2 * lambda> a = z[0 : 2 * lambda];
                BitString<2 * lambda> b = z[lambda : 3 * lambda];
            }
            """,
        ),
        # Partial split: gap at the start (only use tail of sample)
        (
            """
            Void f() {
                BitString<3 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[lambda : 2 * lambda];
                BitString<lambda> b = z[2 * lambda : 3 * lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
            }
            """,
        ),
        # No split: non-uniform sample (type != sampled_from)
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<3 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
            }
            """,
        ),
        # Slice used directly in an expression (not just assignment)
        (
            """
            BitString<lambda> f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                return z[lambda : 2 * lambda];
            }
            """,
            """
            BitString<lambda> f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                return z_1;
            }
            """,
        ),
        # Partial split: single slice (only one part used)
        (
            """
            Void f() {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
            }
            """,
            """
            Void f() {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> a = z_0;
            }
            """,
        ),
        # Coexisting slice of an UNRELATED variable: the _SliceReplacer must
        # leave non-target slices unchanged. Previously transform_slice
        # returned None for non-matching slices, which the Transformer's
        # specific-method dispatch propagated as the new value, corrupting
        # the AST (None ended up where the unrelated Slice should be).
        (
            """
            BitString<lambda> f(BitString<2 * lambda> w) {
                BitString<2 * lambda> z <- BitString<2 * lambda>;
                BitString<lambda> a = z[0 : lambda];
                BitString<lambda> b = z[lambda : 2 * lambda];
                return w[0 : lambda] || a || b;
            }
            """,
            """
            BitString<lambda> f(BitString<2 * lambda> w) {
                BitString<lambda> z_0 <- BitString<lambda>;
                BitString<lambda> z_1 <- BitString<lambda>;
                BitString<lambda> a = z_0;
                BitString<lambda> b = z_1;
                return w[0 : lambda] || a || b;
            }
            """,
        ),
    ],
)
def test_split_uniform_samples(
    method: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_method(method)
    expected_ast = frog_parser.parse_method(expected)

    transformed_ast = SplitUniformSampleTransformer(
        {"lambda": Symbol("lambda")}
    ).transform(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert expected_ast == transformed_ast


# ---------------------------------------------------------------------------
# F-034: minted split-piece names must be fresh in scope.
# ---------------------------------------------------------------------------


def test_f034_minted_name_avoids_planted_collision() -> None:
    """A pre-existing binding named ``z_0`` (the default first split-piece
    name) must not be captured by the minted sample. The split still fires,
    but the minted name is bumped to a fresh suffix, leaving the author's
    ``z_0`` use intact."""
    method = """
        Void f() {
            BitString<lambda> z_0 <- BitString<lambda>;
            BitString<2 * lambda> z <- BitString<2 * lambda>;
            BitString<lambda> a = z[0 : lambda];
            BitString<lambda> b = z[lambda : 2 * lambda];
            BitString<lambda> c = a + z_0;
        }
        """
    game_ast = frog_parser.parse_method(method)
    transformed = SplitUniformSampleTransformer({"lambda": Symbol("lambda")}).transform(
        game_ast
    )

    text = str(transformed)
    stmts = transformed.block.statements
    # The split fired: the original 2*lambda sample of z is gone, replaced by
    # the split pieces (no slice of z remains).
    assert "z[0 : lambda]" not in text
    # The author's z_0 binding is preserved -- the minted piece did NOT reuse
    # the name z_0 (which would rebind a + z_0 to z_0 + z_0).
    sample_names = [s.var.name for s in stmts if isinstance(s, frog_ast.Sample)]
    # z_0 is still sampled exactly once (the author's), and the minted pieces
    # used distinct fresh names (z_1, z_2 by suffix-bumping).
    assert sample_names.count("z_0") == 1
    assert len(sample_names) == 3  # author's z_0 + two fresh split pieces
    # The final assignment still references the author's z_0, not a split piece.
    assert "a + z_0" in text or "z_0 + a" in text


def test_f034_clean_case_still_mints_z0() -> None:
    """No collision: the first split piece keeps the canonical ``z_0`` name."""
    method = """
        Void f() {
            BitString<2 * lambda> z <- BitString<2 * lambda>;
            BitString<lambda> a = z[0 : lambda];
            BitString<lambda> b = z[lambda : 2 * lambda];
        }
        """
    expected = """
        Void f() {
            BitString<lambda> z_0 <- BitString<lambda>;
            BitString<lambda> z_1 <- BitString<lambda>;
            BitString<lambda> a = z_0;
            BitString<lambda> b = z_1;
        }
        """
    transformed = SplitUniformSampleTransformer({"lambda": Symbol("lambda")}).transform(
        frog_parser.parse_method(method)
    )
    assert transformed == frog_parser.parse_method(expected)


# ---------------------------------------------------------------------------
# F-035: decline when the sampled name is redeclared in the same block.
# ---------------------------------------------------------------------------


def test_f035_declines_on_same_block_redeclaration() -> None:
    """A same-scope redeclaration of the sampled name introduces a second
    binding whose slices a block-wide rewrite would wrongly capture. The
    pass must decline (leave the block unchanged)."""
    method = """
        Void f() {
            BitString<8> z = 0b10101010;
            BitString<4> w = z[0 : 4];
            BitString<8> z <- BitString<8>;
            BitString<4> a = z[0 : 4];
        }
        """
    game_ast = frog_parser.parse_method(method)
    transformed = SplitUniformSampleTransformer({}).transform(game_ast)
    # Declined: unchanged (the uniform sample of z is still present).
    assert transformed == game_ast


def test_f035_clean_case_single_declaration_still_fires() -> None:
    """No redeclaration: the single-declaration case still splits."""
    method = """
        Void f() {
            BitString<2 * lambda> z <- BitString<2 * lambda>;
            BitString<lambda> a = z[0 : lambda];
            BitString<lambda> b = z[lambda : 2 * lambda];
        }
        """
    expected = """
        Void f() {
            BitString<lambda> z_0 <- BitString<lambda>;
            BitString<lambda> z_1 <- BitString<lambda>;
            BitString<lambda> a = z_0;
            BitString<lambda> b = z_1;
        }
        """
    transformed = SplitUniformSampleTransformer({"lambda": Symbol("lambda")}).transform(
        frog_parser.parse_method(method)
    )
    assert transformed == frog_parser.parse_method(expected)


def test_f032_declines_when_slice_index_reassigned() -> None:
    """F-032: both slices are textually `z[i : i + 4]`, but `i = i + 4` between
    them makes them the non-overlapping ranges `z[0:4]` and `z[4:8]`.  Resolving
    `i` by name to one symbol would dedup them to a single fresh piece, turning
    the uniform `z[0:4] xor z[4:8]` into 0.  The pass must DECLINE."""
    method = """
        BitString<4> f() {
            Int i = 0;
            BitString<8> z <- BitString<8>;
            BitString<4> a = z[i : i + 4];
            i = i + 4;
            BitString<4> b = z[i : i + 4];
            return a + b;
        }
        """
    parsed = frog_parser.parse_method(method)
    transformed = SplitUniformSampleTransformer({}).transform(parsed)
    assert transformed == parsed, "split fired across a reassigned slice index"


def test_f032_constant_bounds_still_split() -> None:
    """Positive control: with constant (non-reassigned) bounds the split still
    fires."""
    method = """
        BitString<4> f() {
            BitString<8> z <- BitString<8>;
            BitString<4> a = z[0 : 4];
            BitString<4> b = z[4 : 8];
            return a + b;
        }
        """
    parsed = frog_parser.parse_method(method)
    transformed = SplitUniformSampleTransformer({}).transform(parsed)
    assert transformed != parsed, "constant-bound split should still fire"


def test_f036_out_of_bounds_slice_declines() -> None:
    """F-036: `z[4:8]` on a BitString<4> reads outside the sampled range -- an
    undefined out-of-bounds read, NOT an independent uniform sub-sample. The
    split must decline (else it fabricates a fresh uniform for undefined bits)."""
    method = """
        BitString<4> f() {
            BitString<4> z <- BitString<4>;
            return z[4 : 8];
        }
        """
    transformed = SplitUniformSampleTransformer({}).transform(
        frog_parser.parse_method(method)
    )
    assert "z[4 : 8]" in str(transformed)  # not split


def test_f036_in_bounds_constant_slices_still_split() -> None:
    """Positive control: fully in-bounds constant slices of a BitString<8> still
    split into independent uniform pieces."""
    method = """
        Void f() {
            BitString<8> z <- BitString<8>;
            BitString<4> a = z[0 : 4];
            BitString<4> b = z[4 : 8];
        }
        """
    transformed = SplitUniformSampleTransformer({}).transform(
        frog_parser.parse_method(method)
    )
    text = str(transformed)
    assert "z[0 : 4]" not in text and "z[4 : 8]" not in text  # split


def test_f033_signed_offset_slices_not_split() -> None:
    """F-033: slices `z[0:n]` and `z[n+c : n+c+n]` of a `BitString<n+n+c>` are
    disjoint only when `c >= 0` (or `c <= -2n`). The offset `c` appears only
    inside a compound length, so its sign is unconstrained -- at `c = -n` (legal:
    the sampled length `n+n+c = n` is nonnegative) both slices are `z[0:n]`, the
    same bits. The pass must NOT assume `c` positive and split them into
    independent samples (it previously did, via blanket positivity)."""
    game = frog_parser.parse_game(
        """
        Game Real(Int n, Int c) {
            Bool Query() {
                BitString<n + n + c> z <- BitString<n + n + c>;
                BitString<n> a = z[0 : n];
                BitString<n> b = z[n + c : n + c + n];
                return a == b;
            }
        }
        """
    )
    result = SplitUniformSampleTransformer(
        {"n": Symbol("n"), "c": Symbol("c")}
    ).transform(game)
    assert result == game, "slices with a signed-offset gap must not be split"


def test_f033_standalone_length_gap_still_split() -> None:
    """F-033 positive control: when the gap between slices is a STANDALONE
    BitString length symbol (`m` from a `BitString<m>` pad), well-formedness
    forces `m >= 0`, so the slices are genuinely disjoint and the split must
    still fire -- the fix restricts positivity to standalone length symbols, it
    does not blanket-decline symbolic gaps."""
    game = frog_parser.parse_game(
        """
        Game G(Int n, Int m) {
            BitString<n + m + n> Query() {
                BitString<n + m + n> z <- BitString<n + m + n>;
                BitString<n> a = z[0 : n];
                BitString<m> pad = z[n : n + m];
                BitString<n> b = z[n + m : n + m + n];
                return a || pad || b;
            }
        }
        """
    )
    result = SplitUniformSampleTransformer(
        {"n": Symbol("n"), "m": Symbol("m")}
    ).transform(game)
    assert result != game, "slices gapped by a standalone length must still split"
