import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _counter_guarded_field_to_local


@pytest.mark.parametrize(
    "game,expected",
    [
        # Basic: BitString field sampled in Initialize, used in count==h branch
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
            """
        Game Test() {
            Int count;
            Void Initialize() {
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                BitString<lambda> k <- BitString<lambda>;
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
        ),
        # RF field sampled in Initialize, used in count==h branch (RF allowed)
        (
            """
        Game Test() {
            RandomFunctions<BitString<lambda>, BitString<lambda>> RF;
            Int count;
            Void Initialize() {
                RF <- RandomFunctions<BitString<lambda>, BitString<lambda>>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    BitString<lambda> z = RF(x);
                    return z;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r;
                }
            }
        }""",
            """
        Game Test() {
            Int count;
            Void Initialize() {
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                RandomFunctions<BitString<lambda>, BitString<lambda>> RF <- RandomFunctions<BitString<lambda>, BitString<lambda>>;
                count = count + 1;
                if (count == 1) {
                    BitString<lambda> z = RF(x);
                    return z;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r;
                }
            }
        }""",
        ),
        # Field used outside a counter-guarded branch: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                return k + x;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                return k + x;
            }
        }""",
        ),
        # No counter increment: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
        ),
        # Field assigned in target method: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    BitString<lambda> result = k + x;
                    k <- BitString<lambda>;
                    return result;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    BitString<lambda> result = k + x;
                    k <- BitString<lambda>;
                    return result;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
        ),
        # Field used in two methods: no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle1(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    return x;
                }
            }
            BitString<lambda> Oracle2(BitString<lambda> x) {
                return k + x;
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle1(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    return x;
                }
            }
            BitString<lambda> Oracle2(BitString<lambda> x) {
                return k + x;
            }
        }""",
        ),
        # No counter field (no Int field initialized to 0): no transformation
        (
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                if (true) {
                    return k + x;
                } else {
                    return x;
                }
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Void Initialize() {
                k <- BitString<lambda>;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                if (true) {
                    return k + x;
                } else {
                    return x;
                }
            }
        }""",
        ),
        # Counter reset in method body: no transformation (counter not monotonic)
        (
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    count = 0;
                    return r + x;
                }
            }
        }""",
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == 1) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    count = 0;
                    return r + x;
                }
            }
        }""",
        ),
    ],
)
def test_counter_guarded_field_to_local(
    game: str,
    expected: str,
) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)
    transformed_ast = _counter_guarded_field_to_local(game_ast)
    print("EXPECTED", expected_ast)
    print("TRANSFORMED", transformed_ast)
    assert transformed_ast == expected_ast
