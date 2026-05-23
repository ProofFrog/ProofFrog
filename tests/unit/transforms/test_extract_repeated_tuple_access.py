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
        # 5. Method parameters are NOT hoisted (would break tuple fold).
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
                    return c[0] + c[0];
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
    ],
)
def test_extract_repeated_slice(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)
