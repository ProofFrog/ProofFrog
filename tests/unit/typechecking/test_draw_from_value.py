"""A draw's domain is a type, never a set or map value (ruling Q20).

``frog_ast.Variable`` stands for both a value and a type name, so for a field
``Set<BitString<n>> S`` the draw ``Set<BitString<n>> U <- S;`` used to check as
a draw from the type of ``S``: a draw of a whole set, which nothing defines.
The type checker refuses a draw whose domain names a value declared with a
``Set<T>`` or ``Map<K, V>`` type, in both sampling forms. A name declared with
the bare kind ``Set`` is a type and may still be drawn from, and a set value
may still be excluded from a draw (``T \\ S``, ``<-uniq[S] T``)."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis

_NOT_A_TYPE = "not a type (a draw's domain must be a type)"


def _check_game(source: str) -> None:
    game = frog_parser.parse_game(source)
    semantic_analysis.CheckTypeVisitor({}, "test", {}).visit(game)


def _check_game_refused(source: str, capsys: pytest.CaptureFixture[str]) -> str:
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_game(source)
    return capsys.readouterr().err


@pytest.mark.parametrize(
    "source, message",
    [
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                Bool Run() {
                    Set<BitString<n>> U <- S;
                    return true;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<BitString<n>>,"
            f" {_NOT_A_TYPE}",
            id="game_field",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                Set<BitString<n>> U;
                Void Initialize() {
                    U <- S;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<BitString<n>>",
            id="game_field_into_field",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Bool Run() {
                    Set<BitString<n>> T = {0^n};
                    Set<BitString<n>> U <- T;
                    return true;
                }
            }
            """,
            "Cannot sample from T: T is a value of type Set<BitString<n>>",
            id="typed_local",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Bool Run() {
                    Set<BitString<n>> T;
                    Set<BitString<n>> U <- T;
                    return true;
                }
            }
            """,
            "Cannot sample from T: T is a value of type Set<BitString<n>>",
            id="declared_local",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Bool Run(Set<BitString<n>> T) {
                    Set<BitString<n>> U <- T;
                    return true;
                }
            }
            """,
            "Cannot sample from T: T is a value of type Set<BitString<n>>",
            id="method_parameter",
        ),
        pytest.param(
            """
            Game G(Int n, Set<BitString<n>> T) {
                Bool Run() {
                    Set<BitString<n>> U <- T;
                    return true;
                }
            }
            """,
            "Cannot sample from T: T is a value of type Set<BitString<n>>",
            id="game_parameter",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                BitString<n> Run() {
                    BitString<n> x <- S;
                    return x;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<BitString<n>>",
            id="element_of_a_set",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                Set<Set<BitString<n>>> W;
                Bool Run() {
                    Set<BitString<n>> U <-uniq[W] S;
                    return true;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<BitString<n>>",
            id="uniq",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                Set<Set<BitString<n>>> W;
                Bool Run() {
                    Set<BitString<n>> U <- S \\ W;
                    return true;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<BitString<n>>",
            id="exclusion",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<Set<BitString<n>>> S;
                Bool Run() {
                    Set<Set<BitString<n>>> U <- S;
                    return true;
                }
            }
            """,
            "Cannot sample from S: S is a value of type Set<Set<BitString<n>>>",
            id="set_of_sets",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Bool Run() {
                    Set<Bool> K <- M.keys;
                    return true;
                }
            }
            """,
            "Cannot sample from M.keys: M.keys is a value of type Set<Bool>",
            id="map_keys",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Bool Run() {
                    Set<BitString<n>> V <- M.values;
                    return true;
                }
            }
            """,
            "Cannot sample from M.values: M.values is a value of type"
            " Set<BitString<n>>",
            id="map_values",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Bool Run() {
                    Set<[Bool, BitString<n>]> E <- M.entries;
                    return true;
                }
            }
            """,
            "Cannot sample from M.entries: M.entries is a value of type",
            id="map_entries",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Function<Bool, BitString<n>> H;
                Void Initialize() {
                    H <- Function<Bool, BitString<n>>;
                }
                Bool Run() {
                    Set<Bool> D <- H.domain;
                    return true;
                }
            }
            """,
            "Cannot sample from H.domain: H.domain is a value of type Set<Bool>",
            id="function_domain",
        ),
    ],
)
def test_draw_from_a_set_value_is_refused(
    source: str, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert message in _check_game_refused(source, capsys)


def test_hint_names_the_element_type(capsys: pytest.CaptureFixture[str]) -> None:
    err = _check_game_refused(
        """
        Game G(Int n) {
            Set<BitString<n>> S;
            BitString<n> Run() {
                BitString<n> x <- S;
                return x;
            }
        }
        """,
        capsys,
    )
    assert (
        "hint: draw from a type such as BitString<n>; to leave out the members"
        " of S, draw from BitString<n> \\ S"
    ) in err


@pytest.mark.parametrize(
    "element",
    [
        pytest.param("Int", id="int"),
        pytest.param("BitString<n>?", id="optional"),
        pytest.param("Set<BitString<n>>", id="set"),
    ],
)
def test_no_hint_when_the_element_type_cannot_be_drawn(
    element: str, capsys: pytest.CaptureFixture[str]
) -> None:
    err = _check_game_refused(
        f"""
        Game G(Int n) {{
            Set<{element}> S;
            Bool Run() {{
                Set<{element}> U <- S;
                return true;
            }}
        }}
        """,
        capsys,
    )
    assert _NOT_A_TYPE in err
    assert "hint:" not in err


def test_map_variable_keeps_the_whole_map_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A draw from a map variable is refused as a whole-map draw (ruling Q16)
    before this check runs, with that message only."""
    err = _check_game_refused(
        """
        Game G(Int n) {
            Map<Bool, BitString<n>> M;
            Map<Bool, BitString<n>> Run() {
                Map<Bool, BitString<n>> x <- M;
                return x;
            }
        }
        """,
        capsys,
    )
    assert "a whole map cannot be drawn" in err
    assert _NOT_A_TYPE not in err


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            """
            Game G(Set K) {
                K Run() {
                    K x <- K;
                    return x;
                }
            }
            """,
            id="set_parameter",
        ),
        pytest.param(
            """
            Game G(Set K) {
                Set Key = K;
                Key Run() {
                    Key x <- Key;
                    return x;
                }
            }
            """,
            id="set_alias",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                BitString<n> Run() {
                    BitString<n> x <- BitString<n> \\ S;
                    return x;
                }
            }
            """,
            id="excluded_set_value",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Set<BitString<n>> S;
                BitString<n> Run() {
                    BitString<n> x <-uniq[S] BitString<n>;
                    return x;
                }
            }
            """,
            id="uniq_set_value",
        ),
        pytest.param(
            """
            Game G(Int n) {
                Map<Bool, BitString<n>> M;
                Bool Run() {
                    Bool b <- Bool \\ M.keys;
                    return b;
                }
            }
            """,
            id="excluded_map_keys",
        ),
    ],
)
def test_draw_from_a_type_is_accepted(source: str) -> None:
    _check_game(source)


# A primitive with a type alias (`Key`) and a value field (`S`), a scheme with a
# value parameter, and proofs whose intermediate game draws from a proof `let:`
# entry.
_PRIMITIVE = """\
Primitive Pool(Int n, Set KeySpace, Set<BitString<n>> T) {
    Int n = n;
    Set Key = KeySpace;
    Set<BitString<n>> S = T;

    Key Pick(BitString<n> s);
}
"""

_SCHEME = """\
import 'Pool.primitive';

Scheme BitPool(Int n, Set<BitString<n>> T) extends Pool {
    Int n = n;
    Set Key = BitString<n>;
    Set<BitString<n>> S = T;

    Key Pick(BitString<n> s) {
        return s;
    }
}
"""

_SCHEME_DRAWING_ITS_PARAMETER = """\
import 'Pool.primitive';

Scheme ParamPool(Int n, Set<BitString<n>> T) extends Pool {
    Int n = n;
    Set Key = BitString<n>;
    Set<BitString<n>> S = T;

    Key Pick(BitString<n> s) {
        Set<BitString<n>> U <- T;
        return s;
    }
}
"""

_SCHEME_DRAWING_ITS_FIELD = """\
import 'Pool.primitive';

Scheme FieldPool(Int n, Set<BitString<n>> T) extends Pool {
    Int n = n;
    Set Key = BitString<n>;
    Set<BitString<n>> S = T;

    Key Pick(BitString<n> s) {
        Set<BitString<n>> U <- this.S;
        return s;
    }
}
"""


def _member_game(draw: str) -> str:
    return (
        "import 'Pool.primitive';\n"
        "\n"
        "Game Left(Pool E) {\n"
        "    Bool Query() {\n"
        f"        {draw}\n"
        "        return true;\n"
        "    }\n"
        "}\n"
        "\n"
        "Game Right(Pool E) {\n"
        "    Bool Query() {\n"
        f"        {draw}\n"
        "        return true;\n"
        "    }\n"
        "}\n"
        "\n"
        "export as MemberDraw;\n"
    )


_KEY_GAME = """\
import 'Pool.primitive';

Game Left(Pool E) {
    E.Key k;

    Void Initialize() {
        k <- E.Key;
    }

    E.Key Query() {
        return k;
    }
}

Game Right(Pool E) {
    E.Key k;

    Void Initialize() {
        k <- E.Key;
    }

    E.Key Query() {
        return k;
    }
}

export as KeyDraw;
"""


def _write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def _check_file(path: str) -> None:
    semantic_analysis.check_well_formed(frog_parser.parse_file(path), path)


def _write_common(tmp_path: Path) -> None:
    _write(tmp_path, "Pool.primitive", _PRIMITIVE)
    _write(tmp_path, "BitPool.scheme", _SCHEME)
    _write(tmp_path, "KeyDraw.game", _KEY_GAME)


def test_scheme_parameter_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_common(tmp_path)
    path = _write(tmp_path, "ParamPool.scheme", _SCHEME_DRAWING_ITS_PARAMETER)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_file(path)
    assert (
        "Cannot sample from T: T is a value of type Set<BitString<n>>"
        in capsys.readouterr().err
    )


def test_scheme_field_through_this_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_common(tmp_path)
    path = _write(tmp_path, "FieldPool.scheme", _SCHEME_DRAWING_ITS_FIELD)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_file(path)
    assert (
        "Cannot sample from this.S: this.S is a value of type Set<BitString<n>>"
        in capsys.readouterr().err
    )


def test_scheme_without_a_value_draw_is_accepted(tmp_path: Path) -> None:
    _write_common(tmp_path)
    _check_file(str(tmp_path / "BitPool.scheme"))


def test_member_declared_as_a_set_value_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`E.S` is a field of the primitive declared `Set<BitString<n>>`."""
    _write_common(tmp_path)
    path = _write(
        tmp_path,
        "MemberDraw.game",
        _member_game("Set<BitString<E.n>> U <- E.S;"),
    )
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_file(path)
    assert (
        "Cannot sample from E.S: E.S is a value of type Set<BitString<n>>"
        in capsys.readouterr().err
    )


def test_member_declared_as_a_set_alias_is_accepted(tmp_path: Path) -> None:
    """`E.Key` is declared with the bare kind `Set`: a type."""
    _write_common(tmp_path)
    _check_file(_write(tmp_path, "MemberDraw.game", _member_game("E.Key k <- E.Key;")))


def _proof(game: str, step: str, extra_let: str = "") -> str:
    return (
        "import 'Pool.primitive';\n"
        "import 'BitPool.scheme';\n"
        "import 'KeyDraw.game';\n"
        "\n"
        f"{game}\n"
        "proof:\n"
        "let:\n"
        "    Int n;\n"
        f"{extra_let}"
        "    Set<BitString<n>> W;\n"
        "    BitPool E = BitPool(n, W);\n"
        "assume:\n"
        "theorem:\n"
        "    KeyDraw(E);\n"
        "games:\n"
        "    KeyDraw(E).Left against KeyDraw(E).Adversary;\n"
        f"    {step} against KeyDraw(E).Adversary;\n"
        "    KeyDraw(E).Right against KeyDraw(E).Adversary;\n"
    )


def _mid_game(parameters: str, draw: str) -> str:
    return (
        f"Game Mid({parameters}) {{\n"
        "    E.Key k;\n"
        "\n"
        "    Void Initialize() {\n"
        f"        {draw}\n"
        "        k <- E.Key;\n"
        "    }\n"
        "\n"
        "    E.Key Query() {\n"
        "        return k;\n"
        "    }\n"
        "}\n"
    )


def test_let_entry_declared_as_a_set_value_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The intermediate game draws from its parameter `V`, which the step
    gives the proof's `let:` entry `W`, declared `Set<BitString<n>>`."""
    _write_common(tmp_path)
    game = _mid_game(
        "Int n, Set<BitString<n>> V, BitPool E", "Set<BitString<n>> U <- V;"
    )
    path = _write(tmp_path, "test.proof", _proof(game, "Mid(n, W, E)"))
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_file(path)
    assert (
        "Cannot sample from W: W is a value of type Set<BitString<n>>"
        in capsys.readouterr().err
    )


def test_scheme_field_of_a_let_instance_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`E.S` of the `let:` instance `BitPool(n, W)` reads the field's
    initializer, the `let:` entry `W`."""
    _write_common(tmp_path)
    game = _mid_game("BitPool E", "Set<BitString<E.n>> U <- E.S;")
    path = _write(tmp_path, "test.proof", _proof(game, "Mid(E)"))
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check_file(path)
    assert "is a value of type Set<BitString<n>>" in capsys.readouterr().err


def test_let_set_kind_is_accepted(tmp_path: Path) -> None:
    """A proof `let:` entry `Set K;` is a type."""
    _write_common(tmp_path)
    game = _mid_game("Set J, BitPool E", "J j <- J;")
    path = _write(
        tmp_path, "test.proof", _proof(game, "Mid(K, E)", extra_let="    Set K;\n")
    )
    _check_file(path)
