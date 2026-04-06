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
        # Guard uses game parameter (constant across calls): allowed
        (
            """
        Game Test(Int h) {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == h) {
                    return k + x;
                } else {
                    BitString<lambda> r <- BitString<lambda>;
                    return r + x;
                }
            }
        }""",
            """
        Game Test(Int h) {
            Int count;
            Void Initialize() {
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                BitString<lambda> k <- BitString<lambda>;
                count = count + 1;
                if (count == h) {
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
            Function<BitString<lambda>, BitString<lambda>> RF;
            Int count;
            Void Initialize() {
                RF <- Function<BitString<lambda>, BitString<lambda>>;
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
                Function<BitString<lambda>, BitString<lambda>> RF <- Function<BitString<lambda>, BitString<lambda>>;
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


@pytest.mark.parametrize(
    "game",
    [
        # Soundness: field in multiple counter-guarded branches (same if-chain)
        # k read on call 1 (ctr==1) AND call 2 (ctr==2) — must NOT transform
        pytest.param(
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
                } else if (count == 2) {
                    return k + x;
                } else {
                    return x;
                }
            }
        }""",
            id="multiple_branches_same_if",
        ),
        # Soundness: field in multiple counter-guarded branches (separate ifs)
        pytest.param(
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                BitString<lambda> result = x;
                count = count + 1;
                if (count == 1) {
                    result = k + x;
                }
                if (count == 2) {
                    result = k + x;
                }
                return result;
            }
        }""",
            id="multiple_branches_separate_ifs",
        ),
        # Soundness: field referenced in guard condition expression
        # ctr == k means k is evaluated every call
        pytest.param(
            """
        Game Test() {
            Int k;
            Int count;
            Void Initialize() {
                k <- Int;
                count = 0;
            }
            Int Oracle(Int x) {
                count = count + 1;
                if (count == k) {
                    return x;
                } else {
                    return x + 1;
                }
            }
        }""",
            id="field_in_guard_condition",
        ),
        # Soundness: guard expression uses method parameter (adversary-controlled)
        # Adversary calls Oracle(1) then Oracle(2) — branch fires both times
        pytest.param(
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
            }
            BitString<lambda> Oracle(Int i, BitString<lambda> x) {
                count = count + 1;
                if (count == i) {
                    return k + x;
                } else {
                    return x;
                }
            }
        }""",
            id="guard_uses_method_parameter",
        ),
        # Soundness: guard expression uses mutable game field
        pytest.param(
            """
        Game Test() {
            BitString<lambda> k;
            Int count;
            Int target;
            Void Initialize() {
                k <- BitString<lambda>;
                count = 0;
                target = 1;
            }
            BitString<lambda> Oracle(BitString<lambda> x) {
                count = count + 1;
                if (count == target) {
                    target = target + 1;
                    return k + x;
                } else {
                    return x;
                }
            }
        }""",
            id="guard_uses_mutable_field",
        ),
        # Soundness: counter reset by another oracle method
        # Adversary calls Oracle1 (ctr=1, branch fires, k read),
        # then Reset (ctr=0), then Oracle1 again (ctr=1, branch fires, k read).
        # Original: same k both times. Transformed: fresh k each time.
        pytest.param(
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
            Void Reset() {
                count = 0;
            }
        }""",
            id="counter_reset_by_other_method",
        ),
        # Soundness: counter incremented in another oracle method too
        # Another method also increments the counter, changing which call
        # number triggers the branch in the target method.
        pytest.param(
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
            Void Oracle2() {
                count = count - 1;
            }
        }""",
            id="counter_decremented_by_other_method",
        ),
    ],
)
def test_counter_guarded_rejects_unsound_cases(game: str) -> None:
    """Verify the transform does NOT fire on cases that would be unsound."""
    game_ast = frog_parser.parse_game(game)
    transformed_ast = _counter_guarded_field_to_local(game_ast)
    # The transform should be a no-op — the game should be unchanged
    assert transformed_ast == game_ast
