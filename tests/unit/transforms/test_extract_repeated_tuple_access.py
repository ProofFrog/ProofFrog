import pytest
from proof_frog import frog_parser
from proof_frog.transforms.inlining import ExtractRepeatedTupleAccessTransformer


def _transform_and_compare(source: str, expected: str) -> None:
    game = frog_parser.parse_game(source)
    expected_ast = frog_parser.parse_game(expected)
    result = ExtractRepeatedTupleAccessTransformer().transform(game)
    assert result == expected_ast, f"\nGot:\n{result}\nExpected:\n{expected_ast}"


@pytest.mark.parametrize(
    "source,expected",
    [
        # 1. Basic extraction: v1[0] used twice -> extracted to named variable
        (
            """
            Game Test() {
                [Int, Int] v1;
                [Int, Int] Initialize() {
                    [Int, Int] v1 = [1, 2];
                    return [v1[0], v1[0]];
                }
            }
            """,
            """
            Game Test() {
                [Int, Int] v1;
                [Int, Int] Initialize() {
                    [Int, Int] v1 = [1, 2];
                    Int __cse_v1_0__ = v1[0];
                    return [__cse_v1_0__, __cse_v1_0__];
                }
            }
            """,
        ),
        # 2. No extraction for single use: v1[0] used once
        (
            """
            Game Test() {
                [Int, Int] v1;
                Int Initialize() {
                    [Int, Int] v1 = [1, 2];
                    return v1[0];
                }
            }
            """,
            """
            Game Test() {
                [Int, Int] v1;
                Int Initialize() {
                    [Int, Int] v1 = [1, 2];
                    return v1[0];
                }
            }
            """,
        ),
        # 3. Different indices each used once -> no extraction
        (
            """
            Game Test() {
                [Int, Int] v1;
                [Int, Int] Initialize() {
                    [Int, Int] v1 = [1, 2];
                    return [v1[0], v1[1]];
                }
            }
            """,
            """
            Game Test() {
                [Int, Int] v1;
                [Int, Int] Initialize() {
                    [Int, Int] v1 = [1, 2];
                    return [v1[0], v1[1]];
                }
            }
            """,
        ),
        # 4. GenericFor loop binder as tuple: e[0] used twice inside loop
        # body -> extracted at top of loop body
        (
            """
            Game Test() {
                Set<[Int, Int]> T;
                Int Loop() {
                    Int acc = 0;
                    for ([Int, Int] e in T) {
                        acc = e[0] + e[0];
                    }
                    return acc;
                }
            }
            """,
            """
            Game Test() {
                Set<[Int, Int]> T;
                Int Loop() {
                    Int acc = 0;
                    for ([Int, Int] e in T) {
                        Int __cse_e_0__ = e[0];
                        acc = __cse_e_0__ + __cse_e_0__;
                    }
                    return acc;
                }
            }
            """,
        ),
        # 5. Method parameters ARE hoisted when no full tuple-literal
        # reconstruction ``[c[0], c[1]]`` exists in the block (which
        # would block ``SimplifyTuple``'s fold-back).  Symmetrises games
        # whose source extracts ``v = c[0]`` against games whose source
        # uses ``c[0]`` inline.
        (
            """
            Game Test() {
                Int Decaps([Int, Int] c) {
                    return c[0] + c[0];
                }
            }
            """,
            """
            Game Test() {
                Int Decaps([Int, Int] c) {
                    Int __cse_c_0__ = c[0];
                    return __cse_c_0__ + __cse_c_0__;
                }
            }
            """,
        ),
        # 6. Method parameters are NOT hoisted when a full tuple-literal
        # reconstruction ``[c[0], c[1]]`` is present, since extracting
        # would block ``SimplifyTuple``'s ``[c[0], c[1]] -> c`` fold-back.
        (
            """
            Game Test() {
                Bool Decaps([Int, Int] c, Set<[Int, Int]> S) {
                    Int x = c[0] + c[0];
                    return [c[0], c[1]] in S;
                }
            }
            """,
            """
            Game Test() {
                Bool Decaps([Int, Int] c, Set<[Int, Int]> S) {
                    Int x = c[0] + c[0];
                    return [c[0], c[1]] in S;
                }
            }
            """,
        ),
        # 7. Shadowed redeclaration in an earlier branch block: the nested
        # v[1] refers to a different (inner) v, and the outer v[1] appears
        # only once after the outer definition -> no extraction. Previously
        # both occurrences were counted together, firing an extraction whose
        # replacement could never reach the nested occurrence, so the
        # transform re-fired on every pass and recursed forever.
        (
            """
            Game Test() {
                Int Run(Bool choice) {
                    if (choice) {
                        [Int, Int] v = [1, 2];
                        return v[1];
                    }
                    [Int, Int] v = [3, 4];
                    return v[1];
                }
            }
            """,
            """
            Game Test() {
                Int Run(Bool choice) {
                    if (choice) {
                        [Int, Int] v = [1, 2];
                        return v[1];
                    }
                    [Int, Int] v = [3, 4];
                    return v[1];
                }
            }
            """,
        ),
        # 8. Mirror of case 7: the shadowing redeclaration sits AFTER the
        # outer definition. Here the replacement step WOULD reach the nested
        # occurrence, so counting it would capture a different variable --
        # blocked instead by the reassignment guard, which treats the inner
        # declaration as a write to `v` after its definition. Pinned so a
        # future change to that guard cannot silently open a capture (or
        # revive the recursion) on this side.
        (
            """
            Game Test() {
                Int Run(Bool choice) {
                    [Int, Int] v = [3, 4];
                    if (choice) {
                        [Int, Int] v = [1, 2];
                        return v[1];
                    }
                    return v[1];
                }
            }
            """,
            """
            Game Test() {
                Int Run(Bool choice) {
                    [Int, Int] v = [3, 4];
                    if (choice) {
                        [Int, Int] v = [1, 2];
                        return v[1];
                    }
                    return v[1];
                }
            }
            """,
        ),
    ],
)
def test_extract_repeated_tuple_access(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


@pytest.mark.parametrize(
    "source,expected",
    [
        # Slice on method parameter used twice -> hoisted at top of body.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    if (m[0 : K] == m[0 : K]) {
                        return m[0 : K];
                    }
                    return m[0 : K];
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    BitString<K - 0> __cse_slice_m_0__ = m[0 : K];
                    if (__cse_slice_m_0__ == __cse_slice_m_0__) {
                        return __cse_slice_m_0__;
                    }
                    return __cse_slice_m_0__;
                }
            }
            """,
        ),
        # Slice used once -> no extraction.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    return m[0 : K];
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    return m[0 : K];
                }
            }
            """,
        ),
        # Slice with different bounds used once each -> no extraction.
        (
            """
            Game Test() {
                Int N;
                Int K;
                [BitString, BitString] F(BitString<N> m) {
                    return [m[0 : K], m[K : N]];
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                [BitString, BitString] F(BitString<N> m) {
                    return [m[0 : K], m[K : N]];
                }
            }
            """,
        ),
        # Slice on block-local variable: extraction inserted after def.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F() {
                    BitString<N> m <- BitString<N>;
                    BitString<K> a = m[0 : K];
                    BitString<K> b = m[0 : K];
                    return a;
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F() {
                    BitString<N> m <- BitString<N>;
                    BitString<K - 0> __cse_slice_m_0__ = m[0 : K];
                    BitString<K> a = __cse_slice_m_0__;
                    BitString<K> b = __cse_slice_m_0__;
                    return a;
                }
            }
            """,
        ),
        # Reassigned base after first use -> no extraction.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    BitString<K> a = m[0 : K];
                    m = m;
                    BitString<K> b = m[0 : K];
                    return a;
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(BitString<N> m) {
                    BitString<K> a = m[0 : K];
                    m = m;
                    BitString<K> b = m[0 : K];
                    return a;
                }
            }
            """,
        ),
        # Shadowed redeclaration in an earlier branch block -- the slice-phase
        # analogue of case 7 above. The nested m[0 : K] belongs to a different
        # (inner) m, so only one occurrence follows the outer definition and
        # nothing is hoisted. Counting both fires a hoist whose replacement
        # cannot reach the nested occurrence; because the inserted extraction
        # itself contains a fresh m[0 : K], the count stays at 2 and the
        # transform recurses until the recursion limit.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(Bool choice) {
                    if (choice) {
                        BitString<N> m <- BitString<N>;
                        return m[0 : K];
                    }
                    BitString<N> m <- BitString<N>;
                    return m[0 : K];
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(Bool choice) {
                    if (choice) {
                        BitString<N> m <- BitString<N>;
                        return m[0 : K];
                    }
                    BitString<N> m <- BitString<N>;
                    return m[0 : K];
                }
            }
            """,
        ),
        # Mirror of the case above, with the shadowing redeclaration AFTER
        # the outer definition -- the slice-phase analogue of tuple case 8.
        # Declined by `reassigns_or_rebinds` (the inner sample rebinds `m`),
        # not by the post-definition count; pinned so neither guard can
        # regress unnoticed.
        (
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(Bool choice) {
                    BitString<N> m <- BitString<N>;
                    if (choice) {
                        BitString<N> m <- BitString<N>;
                        return m[0 : K];
                    }
                    return m[0 : K];
                }
            }
            """,
            """
            Game Test() {
                Int N;
                Int K;
                BitString<K> F(Bool choice) {
                    BitString<N> m <- BitString<N>;
                    if (choice) {
                        BitString<N> m <- BitString<N>;
                        return m[0 : K];
                    }
                    return m[0 : K];
                }
            }
            """,
        ),
    ],
)
def test_extract_repeated_slice(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)


# ---------------------------------------------------------------------------
# Tuple-typed game fields as bases
# ---------------------------------------------------------------------------
#
# A repeated read ``f[i]`` of a product-typed field is extracted into one local
# at the top of the block, so a game that reads ``f[1]`` inline twice matches
# one that re-derived the tuple and holds ``v = f[1]``. ``K.Get()`` stands for
# an opaque call returning a pair, so no other pass splits the field.

_FIELD_GAME = """
Game Test() {{
    [Int, Int] f;
    {init_ret} Initialize() {{
        {init}
    }}
{methods}
}}
"""


def _field_game(
    methods: str, init: str = "f = K.Get();", init_ret: str = "Void"
) -> str:
    return _FIELD_GAME.format(init=init, init_ret=init_ret, methods=methods)


def test_field_repeated_access_is_extracted() -> None:
    """A field Initialize assigns at top level, read twice in an oracle."""
    _transform_and_compare(
        _field_game("""
    Bool Q(Int a, Int b) {
        return F(f[1], a) == F(f[1], b);
    }"""),
        _field_game("""
    Bool Q(Int a, Int b) {
        Int __cse_f_1__ = f[1];
        return F(__cse_f_1__, a) == F(__cse_f_1__, b);
    }"""),
    )


def test_field_with_initializer_is_extracted() -> None:
    """A declared initializer makes the field defined before any oracle."""
    source = """
    Game Test() {
        [Int, Int] f = [1, 2];
        Int Q() {
            return f[0] + f[0];
        }
    }
    """
    expected = """
    Game Test() {
        [Int, Int] f = [1, 2];
        Int Q() {
            Int __cse_f_0__ = f[0];
            return __cse_f_0__ + __cse_f_0__;
        }
    }
    """
    _transform_and_compare(source, expected)


@pytest.mark.parametrize(
    "source",
    [
        # Assigned only by another oracle: Q may run first and read f while it
        # is unassigned. Extracting at the top of the block adds that read on
        # a path where the original made none (Q2's early return), and reading
        # an unassigned variable is observable.
        _field_game(
            """
    Void Store() { f = K.Get(); }
    Int Q2(Bool c) {
        if (c) { return 0; }
        return f[1] + f[1];
    }""",
            init="",
        ),
        # Initialize may return before assigning f (F-349 shape): f can still
        # be unassigned when an oracle reads it.
        _field_game(
            """
    Int Q(Bool c) {
        if (c) { return 0; }
        return f[1] + f[1];
    }""",
            init="if (K.Flag()) { return 0; } f = K.Get(); return 1;",
            init_ret="Int",
        ),
        # The block writes f between the two reads: the second read sees the
        # new value, so one shared local would return the stale component.
        _field_game("""
    Int Q() {
        Int x = f[1];
        f = K.Get();
        return x + f[1];
    }"""),
        # An element write is a write too.
        _field_game("""
    Int Q(Int v) {
        Int x = f[1];
        f[1] = v;
        return x + f[1];
    }"""),
        # A call to another method of the game may write f between the reads.
        _field_game("""
    Void Reset() { f = K.Get(); }
    Int Q() {
        Int x = f[1];
        Reset();
        return x + f[1];
    }"""),
        # A branch declares a local named f. The reads after the branch are of
        # the field and extracting them would be harmless, but field handling
        # is keyed by name, so the pass declines for any method that binds
        # the field's name (the audit's RC4 rule for name-based field logic;
        # the write/rebind check also declines here).
        _field_game("""
    Int Q(Bool c) {
        if (c) {
            [Int, Int] f = [1, 2];
            return f[1];
        }
        return f[0] + f[0];
    }"""),
    ],
)
def test_field_access_not_extracted(source: str) -> None:
    _transform_and_compare(source, source)


def test_field_access_not_extracted_in_initialize() -> None:
    """Inside Initialize a read may precede the assignment that defines the
    field, so fields are never bases there."""
    source = _field_game(
        "",
        init="f = K.Get(); Int x = f[1] + f[1];",
    )
    _transform_and_compare(source, source)
