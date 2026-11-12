"""Names a pass creates are fresh (F-369, F-370 part (b)).

A pass that adds a new field or local to a game takes its name from
``fresh_name(base, game_names(game))``. Such a name must not already be
bound or mentioned in the game: a new local named like an existing field
captures the field's reads, and an existing local named like the new one
captures the rewritten reads. On a clash ``fresh_name`` picks another name.
"""

from proof_frog import frog_parser
from proof_frog.transforms._base import fresh_name, game_names


# --- the shared helpers -----------------------------------------------------


def test_fresh_name_keeps_a_free_base() -> None:
    taken = {"a", "b"}
    assert fresh_name("v@0", taken) == "v@0"
    assert "v@0" in taken


def test_fresh_name_avoids_taken_names_and_its_own_results() -> None:
    taken = {"v@0", "v@0@fresh1"}
    first = fresh_name("v@0", taken)
    second = fresh_name("v@0", taken)
    assert first == "v@0@fresh2"
    assert second == "v@0@fresh3"
    assert {first, second} <= taken


def test_game_names_covers_every_kind_of_binding_and_reference() -> None:
    game = frog_parser.parse_game("""
        Game T(Int n, Group G) {
            BitString<n> f;
            Set S = BitString<n>;
            Void Initialize() {
                f <- BitString<n>;
            }
            BitString<n> Q(BitString<n> m, Bool c) {
                BitString<n> bare;
                BitString<n> local = m;
                for (Int i = 0 to n) {
                    local = local + f;
                }
                if (c) {
                    bare = 0^n;
                }
                return E.Enc(bare, local);
            }
        }
        """)
    names = game_names(game)
    # parameters, fields, method parameters, bare and typed locals, a loop
    # binder, and free names (a scheme, a type name, a group parameter)
    assert {"n", "G", "f", "S", "m", "c", "bare", "local", "i", "E"} <= names
