import pytest
from proof_frog import frog_parser
from proof_frog.transforms.sampling import _counter_guarded_chain_to_local


@pytest.mark.parametrize(
    "game,expected",
    [
        # Chain of length 1: sampled local + one field derived from it.
        # The existing CounterGuardedFieldToLocal handles only the bare-sample
        # case (field <- T). Here the field is `gr = G.generator ^ r`, a
        # computed value that depends on a sampled local.
        pytest.param(
            """
        Game Test(Group G) {
            GroupElem<G> gr;
            Int count;
            Void Initialize() {
                ModInt<G.order> r <- ModInt<G.order>;
                gr = G.generator ^ r;
                count = 0;
            }
            GroupElem<G> Oracle() {
                count = count + 1;
                if (count == 1) {
                    return gr;
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return G.generator ^ s;
                }
            }
        }""",
            """
        Game Test(Group G) {
            Int count;
            Void Initialize() {
                count = 0;
            }
            GroupElem<G> Oracle() {
                count = count + 1;
                if (count == 1) {
                    ModInt<G.order> r <- ModInt<G.order>;
                    GroupElem<G> gr = G.generator ^ r;
                    return gr;
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return G.generator ^ s;
                }
            }
        }""",
            id="single_field_from_sampled_local",
        ),
        # Chain of length 2: sampled local + two fields, second field
        # depends on first. This is the HashedDDH hybrid shape.
        pytest.param(
            """
        Game Test(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
            GroupElem<G> pk;
            GroupElem<G> gr;
            BitString<n> val;
            Int count;
            GroupElem<G> Initialize() {
                ModInt<G.order> a <- ModInt<G.order>;
                pk = G.generator ^ a;
                ModInt<G.order> r <- ModInt<G.order>;
                gr = G.generator ^ r;
                val = H(pk ^ r);
                count = 0;
                return pk;
            }
            [GroupElem<G>, BitString<n>] Oracle() {
                count = count + 1;
                if (count == 1) {
                    return [gr, val];
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return [G.generator ^ s, H(pk ^ s)];
                }
            }
        }""",
            """
        Game Test(Group G, Int n, Function<GroupElem<G>, BitString<n>> H) {
            GroupElem<G> pk;
            Int count;
            GroupElem<G> Initialize() {
                ModInt<G.order> a <- ModInt<G.order>;
                pk = G.generator ^ a;
                count = 0;
                return pk;
            }
            [GroupElem<G>, BitString<n>] Oracle() {
                count = count + 1;
                if (count == 1) {
                    ModInt<G.order> r <- ModInt<G.order>;
                    GroupElem<G> gr = G.generator ^ r;
                    BitString<n> val = H(pk ^ r);
                    return [gr, val];
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return [G.generator ^ s, H(pk ^ s)];
                }
            }
        }""",
            id="two_fields_sharing_sampled_local",
        ),
    ],
)
def test_counter_guarded_chain_rewrites(game: str, expected: str) -> None:
    game_ast = frog_parser.parse_game(game)
    expected_ast = frog_parser.parse_game(expected)
    assert _counter_guarded_chain_to_local(game_ast) == expected_ast


@pytest.mark.parametrize(
    "game",
    [
        # Negative: chain field is referenced outside the counter-guarded
        # branch (here `gr` is returned from Initialize too) — declines.
        pytest.param(
            """
        Game Test(Group G) {
            GroupElem<G> gr;
            Int count;
            GroupElem<G> Initialize() {
                ModInt<G.order> r <- ModInt<G.order>;
                gr = G.generator ^ r;
                count = 0;
                return gr;
            }
            GroupElem<G> Oracle() {
                count = count + 1;
                if (count == 1) {
                    return gr;
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return G.generator ^ s;
                }
            }
        }""",
            id="field_used_outside_target_branch",
        ),
        # Negative: the sampled local `r` is used outside the chain (here
        # Initialize uses it directly in its return expression) — declines.
        pytest.param(
            """
        Game Test(Group G) {
            GroupElem<G> gr;
            Int count;
            ModInt<G.order> Initialize() {
                ModInt<G.order> r <- ModInt<G.order>;
                gr = G.generator ^ r;
                count = 0;
                return r;
            }
            GroupElem<G> Oracle() {
                count = count + 1;
                if (count == 1) {
                    return gr;
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return G.generator ^ s;
                }
            }
        }""",
            id="local_used_outside_chain",
        ),
        # Negative: counter may fire multiple times because another method
        # writes to the counter — the hoist would duplicate sampling.
        pytest.param(
            """
        Game Test(Group G) {
            GroupElem<G> gr;
            Int count;
            Void Initialize() {
                ModInt<G.order> r <- ModInt<G.order>;
                gr = G.generator ^ r;
                count = 0;
            }
            GroupElem<G> Oracle() {
                count = count + 1;
                if (count == 1) {
                    return gr;
                } else {
                    ModInt<G.order> s <- ModInt<G.order>;
                    return G.generator ^ s;
                }
            }
            Void Reset() {
                count = 0;
            }
        }""",
            id="counter_reset_by_other_method",
        ),
    ],
)
def test_counter_guarded_chain_rejects_unsound(game: str) -> None:
    game_ast = frog_parser.parse_game(game)
    assert _counter_guarded_chain_to_local(game_ast) == game_ast
