import pytest
from proof_frog import frog_parser, proof_engine


@pytest.mark.parametrize(
    "game,reduction,expected_game",
    [
        # Trivial oracle call
        (
            """Game Test() {
            Int oracle(Int arg) {
                return arg;
            }
        }""",
            """Reduction Trivial() compose Test() against Test().Adversary {
            Int oracle(Int arg) {
                return challenger.oracle(arg);
            }
        }""",
            """Game Inlined() {
            Int oracle(Int arg) {
                return arg;
            }
        }""",
        ),
        # With a variable declaration
        (
            """Game Test() {
            Int oracle(Int arg) {
                return arg;
            }
        }""",
            """Reduction Trivial() compose Test() against Test().Adversary {
            Int oracle(Int arg) {
                Int x;
                return challenger.oracle(arg);
            }
        }""",
            """Game Inlined() {
            Int oracle(Int arg) {
                Int x;
                return arg;
            }
        }""",
        ),
        # Assigning a variable from an oracle call
        (
            """Game Test() {
            Int oracle(Int arg) {
                Int x = 5;
                return arg;
            }
        }""",
            """Reduction Trivial() compose Test() against Test().Adversary {
            Int oracle(Int arg) {
                Int a = challenger.oracle(arg);
                return a;
            }
        }""",
            """Game Inlined() {
            Int oracle(Int arg) {
                Int x = 5;
                Int a = arg;
                return a;
            }
        }""",
        ),
        # Composing initialization
        (
            """Game Test() {
            Int a;
            Int Initialize() {
                a = 1;
                return 5;
            }
        }""",
            """Reduction Trivial() compose Test() against Test().Adversary {
            Int b;
            void Initialize(Int arg) {
                b = arg;
            }
        }""",
            """Game Inlined() {
            Int a;
            Int b;
            void Initialize() {
                a = 1;
                Int arg = 5;
                b = arg;
            }
        }""",
        ),
        # Composing finalization
        (
            """Game Test() {
            void Finalize(Bool b1) {
                Int x;
                return b1;
            }
        }""",
            """Reduction Trivial() compose Test() against Test().Adversary {
            void Finalize(Bool b2) {
                return !b2;
            }
        }""",
            """Game Inlined() {
            void Finalize(Bool b2) {
                Bool b1 = !b2;
                Int x;
                return b1;
            }
        }""",
        ),
        # Trivial Reduction with a parameterized game
        (
            """Game Test(Int a) {
            void oracle() {
                return a;
            }
        }""",
            """Reduction Trivial(Int b) compose Test(b) against Test(b).Adversary {
            void oracle() {
                return challenger.oracle();
            }
        }""",
            """Game Inlined(Int b) {
            void oracle() {
                return b;
            }
        }""",
        ),
    ],
)
def test_reduction(game: str, reduction: str, expected_game: str) -> None:
    game_ast = frog_parser.parse_game(game)
    reduction_ast = frog_parser.parse_reduction(reduction)
    expected_ast = frog_parser.parse_game(expected_game)

    result = proof_engine.apply_reduction(game_ast, reduction_ast, {})
    assert result == expected_ast
