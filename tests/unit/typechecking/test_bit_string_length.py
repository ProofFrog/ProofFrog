"""A bit-string length written as an integer literal is at least 1 (ruling Q17).

Every ``BitString`` length is at least 1, but nothing enforced it:
``BitString<0>`` and ``0^0`` type-checked. The structural rules now refuse a
length written as an integer literal below 1, or as a constant expression of
integer literals such as ``1 - 1``, in a type ``BitString<k>`` and in a
literal ``0^k`` / ``1^k``, wherever the file writes one. A length that names
a parameter or a proof ``let:`` entry is not checked. Name resolution runs
the rules on every parsed file, so imported files and the proof's own
``let:`` block, intermediate games and reductions are covered.
"""

from pathlib import Path

import pytest

from proof_frog import frog_ast, frog_parser, semantic_analysis, structural_rules


def _message(written: str, length: int) -> str:
    return f"{written} has length {length}: a bit-string length must be at least 1"


def _messages(root: frog_ast.ASTNode) -> list[str]:
    return [v.message for v in structural_rules.check_structural_rules(root)]


def _game_messages(fields: str, methods: str = "Void Initialize() { }") -> list[str]:
    return _messages(frog_parser.parse_game(f"""
        Game G(Int lambda) {{
            {fields}
            {methods}
        }}"""))


class TestRefusedTypes:
    @pytest.mark.parametrize(
        "fields, methods",
        [
            # A field, typed with and without a value.
            ("BitString<0> f;", "Void Initialize() { }"),
            ("BitString<0> f = 0^1;", "Void Initialize() { }"),
            # A typed local and a bare local declaration.
            ("", "Bool T() { BitString<0> x = 0^1; return true; }"),
            ("", "Bool T() { BitString<0> x; return true; }"),
            # A method parameter and a return type.
            ("", "Bool T(BitString<0> x) { return true; }"),
            ("", "BitString<0> T() { return 0^1; }"),
            # Sampling domains, both forms.
            ("", "Bool T() { BitString<1> x <- BitString<0>; return true; }"),
            (
                "Set<BitString<1>> S;",
                "Bool T() { BitString<1> x <-uniq[S] BitString<0>; return true; }",
            ),
            # Inside other types.
            ("Map<Int, BitString<0>> M;", "Void Initialize() { }"),
            ("[BitString<0>, Int] t;", "Void Initialize() { }"),
            ("Function<BitString<0>, BitString<1>> H;", "Void Initialize() { }"),
            ("Array<BitString<0>, 3> a;", "Void Initialize() { }"),
            ("BitString<0>? o;", "Void Initialize() { }"),
            ("Set<BitString<0>> S;", "Void Initialize() { }"),
            # A loop binder's type.
            (
                "Set<BitString<1>> S;",
                "Void Initialize() { for (BitString<0> e in S) { } }",
            ),
        ],
    )
    def test_literal_zero_length(self, fields: str, methods: str) -> None:
        assert _message("BitString<0>", 0) in _game_messages(fields, methods)

    @pytest.mark.parametrize(
        "written, length",
        [
            ("BitString<1 - 1>", 0),
            ("BitString<0 - 1>", -1),
            ("BitString<0 * 5>", 0),
            ("BitString<2 - (3 - 1)>", 0),
        ],
    )
    def test_constant_expression_below_one(self, written: str, length: int) -> None:
        assert _game_messages(f"{written} f;") == [_message(written, length)]

    def test_game_parameter(self) -> None:
        game = frog_parser.parse_game("""
            Game G(BitString<0> k) {
                Void Initialize() { }
            }""")
        assert _messages(game) == [_message("BitString<0>", 0)]

    def test_violation_is_at_the_type(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                Bool T() {
                    BitString<0> x;
                    return true;
                }
            }""")
        (violation,) = structural_rules.check_structural_rules(game)
        assert isinstance(violation.node, frog_ast.BitStringType)
        assert (violation.node.line_num, violation.node.column_num) == (4, 20)


class TestRefusedLiterals:
    @pytest.mark.parametrize(
        "written, length",
        [("0^0", 0), ("1^0", 0), ("0^(2 - 2)", 0), ("1^(1 - 3)", -2)],
    )
    def test_returned_literal(self, written: str, length: int) -> None:
        assert _game_messages("", f"BitString<1> T() {{ return {written}; }}") == [
            _message(written, length)
        ]

    def test_literal_in_a_set_literal(self) -> None:
        assert _game_messages(
            "", "Bool T(BitString<1> y) { return y in {0^1, 1^0}; }"
        ) == [_message("1^0", 0)]

    def test_literal_in_an_excluded_set(self) -> None:
        assert _game_messages(
            "",
            "Bool T() { BitString<1> x <- BitString<1> \\ {0^0}; return true; }",
        ) == [_message("0^0", 0)]

    def test_violation_is_at_the_literal(self) -> None:
        game = frog_parser.parse_game("""
            Game G() {
                BitString<1> T() {
                    return 1^0;
                }
            }""")
        (violation,) = structural_rules.check_structural_rules(game)
        assert isinstance(violation.node, frog_ast.BitStringLiteral)


class TestOtherFiles:
    def test_primitive(self) -> None:
        primitive = frog_parser.parse_string(
            """
            Primitive P(Int n) {
                Set Key = BitString<0>;
                BitString<1> F(Key k);
            }""",
            frog_ast.FileType.PRIMITIVE,
        )
        assert _messages(primitive) == [_message("BitString<0>", 0)]

    def test_scheme_alias_and_literal(self) -> None:
        scheme = frog_parser.parse_string(
            """
            Scheme S(Int n) extends P {
                Set Key = BitString<1 - 1>;
                BitString<1> F(BitString<1> k) {
                    return 1^0;
                }
            }""",
            frog_ast.FileType.SCHEME,
        )
        assert _messages(scheme) == [
            _message("BitString<1 - 1>", 0),
            _message("1^0", 0),
        ]

    def test_reduction(self) -> None:
        reduction = frog_parser.parse_reduction("""
            Reduction R() compose Pair() against Pair().Adversary {
                BitString<1> T() {
                    return 0^0;
                }
            }""")
        assert _messages(reduction) == [_message("0^0", 0)]


class TestAccepted:
    @pytest.mark.parametrize(
        "fields, methods",
        [
            ("BitString<1> f;", "Void Initialize() { }"),
            ("", "BitString<1> T() { return 0^1; }"),
            ("", "BitString<1> T() { return 1^1; }"),
            ("BitString<2 - 1> f;", "BitString<1> T() { return 0^(3 - 2); }"),
            # A length that names a parameter is not checked.
            ("BitString<lambda> f;", "BitString<lambda> T() { return 0^lambda; }"),
            ("BitString<lambda - 1> f;", "Void Initialize() { }"),
            ("BitString<lambda - lambda> f;", "Void Initialize() { }"),
            # A binary literal has at least one digit.
            ("", "BitString<1> T() { return 0b0; }"),
        ],
    )
    def test_length_at_least_one_or_not_constant(
        self, fields: str, methods: str
    ) -> None:
        assert not _game_messages(fields, methods)

    def test_unparameterized_bit_string_in_a_primitive(self) -> None:
        primitive = frog_parser.parse_string(
            """
            Primitive P(Int n) {
                Set Key = BitString;
                Key F(Key k);
            }""",
            frog_ast.FileType.PRIMITIVE,
        )
        assert not _messages(primitive)


# End to end through the type checker: an imported game, the proof's let:
# block and the proof's own intermediate game.

_ECHO = """\
Game Left(Int n) {
    BitString<n> Get(BitString<n> x) {
        return x;
    }
}

Game Right(Int n) {
    BitString<n> Get(BitString<n> x) {
        return x;
    }
}

export as Echo;
"""

_PROOF = """\
import 'Echo.game';

Game Mid(Int n) {
    BitString<n> Get(BitString<n> x) {
        MID_BODY
        return x;
    }
}

proof:

let:
    Int n;
    LET_ENTRY

assume:

theorem:
    Echo(n);

games:
    Echo(n).Left against Echo(n).Adversary;
    Mid(n) against Echo(n).Adversary;
    Echo(n).Right against Echo(n).Adversary;
"""


def _write_proof(
    tmp_path: Path, let_entry: str, mid_body: str, echo: str = _ECHO
) -> Path:
    (tmp_path / "Echo.game").write_text(echo)
    path = tmp_path / "echo.proof"
    path.write_text(
        _PROOF.replace("LET_ENTRY", let_entry).replace("MID_BODY", mid_body)
    )
    return path


def _check(path: Path) -> None:
    semantic_analysis.check_well_formed(frog_parser.parse_file(str(path)), str(path))


@pytest.mark.parametrize(
    "let_entry, mid_body, expected",
    [
        (
            "BitString<0> c = 0^1;",
            "",
            "echo.proof:14:4: error: " + _message("BitString<0>", 0),
        ),
        ("BitString<1> c = 1^0;", "", "echo.proof:14:21: error: " + _message("1^0", 0)),
        (
            "Function<BitString<0>, BitString<1>> H"
            " <- Function<BitString<0>, BitString<1>>;",
            "",
            "echo.proof:14:13: error: " + _message("BitString<0>", 0),
        ),
        (
            "",
            "BitString<1 - 1> e;",
            "echo.proof:5:8: error: " + _message("BitString<1 - 1>", 0),
        ),
    ],
    ids=["let_type", "let_value", "let_function", "intermediate_game"],
)
def test_proof_length_below_one_is_a_type_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    let_entry: str,
    mid_body: str,
    expected: str,
) -> None:
    path = _write_proof(tmp_path, let_entry, mid_body)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(path)
    assert expected in capsys.readouterr().err


def test_imported_game_length_below_one_is_a_type_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    echo = _ECHO.replace(
        "        return x;", "        BitString<0> e;\n        return x;", 1
    )
    path = _write_proof(tmp_path, "", "", echo)
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        _check(path)
    assert "Echo.game:3:8: error: " + _message("BitString<0>", 0) in (
        capsys.readouterr().err
    )


def test_proof_with_lengths_at_least_one_type_checks(tmp_path: Path) -> None:
    _check(_write_proof(tmp_path, "BitString<1> c = 1^1;", "BitString<n> e = 0^n;"))
