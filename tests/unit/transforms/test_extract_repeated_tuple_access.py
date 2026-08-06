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
