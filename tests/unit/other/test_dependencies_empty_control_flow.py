"""remove_unnecessary_fields drops control-flow shells emptied by dead-code
removal, so their conditions stop keeping dead values alive."""

from proof_frog import dependencies, frog_parser


def _apply_twice(src: str) -> str:
    game = frog_parser.parse_game(src)
    game = dependencies.remove_unnecessary_fields(game)
    return str(dependencies.remove_unnecessary_fields(game))


def test_empty_if_shell_and_its_operands_are_pruned() -> None:
    src = """
    Game G(Int k) {
        Bool bad;
        Void Initialize() {
            bad = false;
        }
        BitString<k> Dec(BitString<k> a, BitString<k> b) {
            BitString<k> x = a + b;
            if (x != a) {
                bad = true;
            }
            return a;
        }
    }
    """
    expected = """
    Game G(Int k) {
        BitString<k> Dec(BitString<k> a, BitString<k> b) {
            return a;
        }
    }
    """
    assert _apply_twice(src) == str(frog_parser.parse_game(expected))


def test_empty_loop_shell_is_pruned() -> None:
    src = """
    Game G(Int k) {
        Map<BitString<k>, BitString<k>> T;
        Bool bad;
        Void Initialize() {
            bad = false;
        }
        BitString<k> Dec(BitString<k> a) {
            for ([BitString<k>, BitString<k>] e in T.entries) {
                if (e[0] == a) {
                    bad = true;
                }
            }
            return a;
        }
    }
    """
    expected = """
    Game G(Int k) {
        BitString<k> Dec(BitString<k> a) {
            return a;
        }
    }
    """
    assert _apply_twice(src) == str(frog_parser.parse_game(expected))


def test_nonempty_if_is_kept() -> None:
    src = """
    Game G(Int k) {
        BitString<k> Dec(BitString<k> a, BitString<k> b) {
            if (a == b) {
                return b;
            }
            return a;
        }
    }
    """
    assert _apply_twice(src) == str(frog_parser.parse_game(src))
