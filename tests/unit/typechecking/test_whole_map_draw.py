"""A whole map is never drawn (ruling Q16).

FrogLang defines the element draw ``M[k] <- V;`` but not a draw of a whole
``Map<K, V>``: nothing says which keys the drawn map would hold. The type
checker refuses every draw that would draw a map, whatever the map's value
type, and points to ``Function<K, V>``, which gives a random table."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_REFUSED = "a whole map cannot be drawn"


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    semantic_analysis.CheckTypeVisitor({}, "test", {}).visit(game)


def _check_game_refused(
    source: str, capsys: pytest.CaptureFixture[str], message: str
) -> None:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "source, message",
    [
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Void Initialize() {
                    M <- Map<Bool, BitString<n>>;
                }
            }
            """,
            "Cannot sample from Map<Bool, BitString<n>>: a whole map cannot be"
            " drawn",
            id="field",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Bool Run() {
                    Map<Bool, BitString<n>> M <- Map<Bool, BitString<n>>;
                    return true;
                }
            }
            """,
            "Cannot sample from Map<Bool, BitString<n>>: a whole map cannot be"
            " drawn",
            id="typed_local",
        ),
        pytest.param(
            """
            Game G() {
                Map<Bool, Int> M;
                Void Initialize() {
                    M <- Map<Bool, Int>;
                }
            }
            """,
            "Cannot sample from Map<Bool, Int>: a whole map cannot be drawn",
            id="int_values",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set Table = Map<Bool, BitString<n>>;
                Table M;
                Void Initialize() {
                    M <- Table;
                }
            }
            """,
            "Cannot sample from Map<Bool, BitString<n>>: a whole map cannot be"
            " drawn",
            id="alias",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set Pair = [Map<Bool, BitString<n>>, BitString<n>];
                Bool Run() {
                    Pair p <- Pair;
                    return true;
                }
            }
            """,
            "a whole map cannot be drawn (it draws the map" " Map<Bool, BitString<n>>)",
            id="product_component",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set Pair = [BitString<n>, [Bool, Map<Bool, Bool>]];
                Bool Run() {
                    Pair p <- Pair;
                    return true;
                }
            }
            """,
            "a whole map cannot be drawn (it draws the map Map<Bool, Bool>)",
            id="nested_product_component",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Bool Run() {
                    Array<Map<Bool, BitString<n>>, 2> a
                        <- Array<Map<Bool, BitString<n>>, 2>;
                    return true;
                }
            }
            """,
            "a whole map cannot be drawn (it draws the map" " Map<Bool, BitString<n>>)",
            id="array_element",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Function<Bool, Map<Bool, BitString<n>>> H;
                Void Initialize() {
                    H <- Function<Bool, Map<Bool, BitString<n>>>;
                }
            }
            """,
            "Cannot sample from Function<Bool, Map<Bool, BitString<n>>>: a whole"
            " map cannot be drawn (it draws the map Map<Bool, BitString<n>>)",
            id="function_range",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<Map<Bool, BitString<n>>> S;
                Bool Run() {
                    Map<Bool, BitString<n>> M <-uniq[S] Map<Bool, BitString<n>>;
                    return true;
                }
            }
            """,
            _REFUSED,
            id="uniq",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<Map<Bool, BitString<n>>> S;
                Bool Run() {
                    Map<Bool, BitString<n>> M <- Map<Bool, BitString<n>> \\ S;
                    return true;
                }
            }
            """,
            _REFUSED,
            id="exclusion",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, Map<Bool, BitString<n>>> M;
                Void Initialize() {
                    M[true] <- Map<Bool, BitString<n>>;
                }
            }
            """,
            _REFUSED,
            id="element_holding_a_map",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Map<Bool, BitString<n>> Run() {
                    Map<Bool, BitString<n>> x <- M;
                    return x;
                }
            }
            """,
            _REFUSED,
            id="from_map_variable",
        ),
    ],
)
def test_whole_map_draw_is_refused(
    source: str, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _check_game_refused(source, capsys, message)


def test_hint_names_the_function_type(capsys: pytest.CaptureFixture[str]) -> None:
    _check_game_refused(
        """
        Game G(Int n) {
            Map<Bool, BitString<n>> M;
            Void Initialize() {
                M <- Map<Bool, BitString<n>>;
            }
        }
        """,
        capsys,
        "hint: draw a Function<Bool, BitString<n>> for a random table, or draw"
        " single entries with M[k] <- BitString<n>;",
    )


def test_hint_asks_for_a_finite_range_when_values_have_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The map's own value type would be refused as a Function's range, so the
    hint does not suggest it."""
    _check_game_refused(
        """
        Game G() {
            Map<Bool, Int> M;
            Void Initialize() {
                M <- Map<Bool, Int>;
            }
        }
        """,
        capsys,
        "hint: draw a Function<Bool, R> with a finite range R for a random"
        " table, or draw single entries with M[k] <- R;",
    )


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                BitString<n> Query(Bool b) {
                    if (!(b in M)) {
                        M[b] <- BitString<n>;
                    }
                    return M[b];
                }
            }
            """,
            id="element_draw",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Function<Bool, BitString<n>> H;
                Void Initialize() {
                    H <- Function<Bool, BitString<n>>;
                }
            }
            """,
            id="function_table",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Function<Map<Bool, Bool>, BitString<n>> H;
                Void Initialize() {
                    H <- Function<Map<Bool, Bool>, BitString<n>>;
                }
            }
            """,
            id="map_as_function_domain",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Void Initialize() {
                    Map<Bool, BitString<n>> N;
                    M = N;
                }
            }
            """,
            id="declared_and_assigned",
        ),
    ],
)
def test_map_without_a_whole_map_draw_is_accepted(source: str) -> None:
    _check_game(source)


# A proof whose game draws the scheme's table type through its alias, and
# proofs whose let: block samples an entry.
_PRIMITIVE = """\
Primitive Tables(Int n, Set TableSpace) {
    Int n = n;
    Set Table = TableSpace;

    Table Make(BitString<n> s);
}
"""

_MAP_SCHEME = """\
import 'Tables.primitive';

Scheme MapTables(Int n) extends Tables {
    Int n = n;
    Set Table = Map<Bool, BitString<n>>;

    Table Make(BitString<n> s) {
        Map<Bool, BitString<n>> M;
        M[true] = s;
        return M;
    }
}
"""

_STRING_SCHEME = """\
import 'Tables.primitive';

Scheme StringTables(Int n) extends Tables {
    Int n = n;
    Set Table = BitString<n>;

    Table Make(BitString<n> s) {
        return s;
    }
}
"""

_GAME = """\
import 'Tables.primitive';

Game Left(Tables E) {
    E.Table T;

    Void Initialize() {
        T <- E.Table;
    }

    E.Table Query() {
        return T;
    }
}

Game Right(Tables E) {
    E.Table T;

    Void Initialize() {
        T <- E.Table;
    }

    E.Table Query() {
        return T;
    }
}

export as TableDraw;
"""


def _write_files(tmp_path: Path) -> None:
    (tmp_path / "Tables.primitive").write_text(_PRIMITIVE)
    (tmp_path / "MapTables.scheme").write_text(_MAP_SCHEME)
    (tmp_path / "StringTables.scheme").write_text(_STRING_SCHEME)
    (tmp_path / "TableDraw.game").write_text(_GAME)


def _proof(scheme: str, extra_let: str = "") -> str:
    return (
        "import 'Tables.primitive';\n"
        f"import '{scheme}.scheme';\n"
        "import 'TableDraw.game';\n"
        "\n"
        "proof:\n"
        "let:\n"
        "    Int n;\n"
        f"    Tables E = {scheme}(n);\n"
        f"{extra_let}"
        "assume:\n"
        "theorem:\n"
        "    TableDraw(E);\n"
        "games:\n"
        "    TableDraw(E).Left against TableDraw(E).Adversary;\n"
        "    TableDraw(E).Right against TableDraw(E).Adversary;\n"
    )


def _check_proof(tmp_path: Path, content: str) -> None:
    _write_files(tmp_path)
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(content)
    root = frog_parser.parse_file(str(proof_path))
    semantic_analysis.check_well_formed(root, str(proof_path))


def test_scheme_alias_naming_a_map_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The game draws E.Table, which this scheme defines as a map."""
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_proof(tmp_path, _proof("MapTables"))
    assert (
        "Cannot sample from Map<Bool, BitString<n>>: a whole map cannot be drawn"
        in capsys.readouterr().err
    )


def test_scheme_alias_naming_a_bit_string_is_accepted(tmp_path: Path) -> None:
    """Control: the same game with a scheme whose table type is a bit string."""
    _check_proof(tmp_path, _proof("StringTables"))


def test_let_entry_with_a_map_range_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sampled let: entry draws each output from its range."""
    let = (
        "    Function<BitString<8>, Map<Bool, BitString<8>>> H"
        " <- Function<BitString<8>, Map<Bool, BitString<8>>>;\n"
    )
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_proof(tmp_path, _proof("StringTables", let))
    assert (
        "Cannot sample from Function<BitString<8>, Map<Bool, BitString<8>>>: a"
        " whole map cannot be drawn" in capsys.readouterr().err
    )


def test_let_entry_drawing_a_map_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only a Function may be sampled in a let: block, so a whole map is
    refused there too."""
    let = "    Map<Bool, BitString<8>> M <- Map<Bool, BitString<8>>;\n"
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_proof(tmp_path, _proof("StringTables", let))
    assert "only Function types can be sampled" in capsys.readouterr().err


_SET_GAME = """\
Game Left(Set R) {
    R x;

    Void Initialize() {
        x <- R;
    }

    R Query() {
        return x;
    }
}

Game Right(Set R) {
    R x;

    Void Initialize() {
        x <- R;
    }

    R Query() {
        return x;
    }
}

export as SetDraw;
"""


@pytest.mark.parametrize(
    "set_type, refused",
    [
        pytest.param("Map<Bool, BitString<8>>", True, id="map"),
        pytest.param("BitString<8>", False, id="bit_string_control"),
    ],
)
def test_set_parameter_given_a_map(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    set_type: str,
    refused: bool,
) -> None:
    """The game draws from its abstract Set parameter, which the proof gives a
    map type."""
    (tmp_path / "SetDraw.game").write_text(_SET_GAME)
    proof_path = tmp_path / "test.proof"
    proof_path.write_text(
        "import 'SetDraw.game';\n"
        "\n"
        "proof:\n"
        "let:\n"
        f"    Set R = {set_type};\n"
        "assume:\n"
        "theorem:\n"
        "    SetDraw(R);\n"
        "games:\n"
        "    SetDraw(R).Left against SetDraw(R).Adversary;\n"
        "    SetDraw(R).Right against SetDraw(R).Adversary;\n"
    )
    root = frog_parser.parse_file(str(proof_path))
    if not refused:
        semantic_analysis.check_well_formed(root, str(proof_path))
        return
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, str(proof_path))
    assert (
        "Cannot sample from Map<Bool, BitString<8>>: a whole map cannot be drawn"
        in capsys.readouterr().err
    )
