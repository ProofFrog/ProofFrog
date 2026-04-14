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
    ],
)
def test_extract_repeated_tuple_access(source: str, expected: str) -> None:
    _transform_and_compare(source, expected)
