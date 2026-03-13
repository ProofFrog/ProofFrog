"""Tests for parse error reporting, especially the missing-semicolon heuristic."""

from pathlib import Path

import pytest

from proof_frog.frog_parser import (
    ParseError,
    parse_game_file,
    parse_primitive_file,
    parse_proof_file,
)


def _expect_error(tmp_path: Path, source: str) -> ParseError:
    prim_file = tmp_path / "Test.primitive"
    prim_file.write_text(source, encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        parse_primitive_file(str(prim_file))
    return exc_info.value


def _expect_game_error(tmp_path: Path, source: str) -> ParseError:
    game_file = tmp_path / "Test.game"
    game_file.write_text(source, encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        parse_game_file(str(game_file))
    return exc_info.value


def _expect_proof_error(tmp_path: Path, source: str) -> ParseError:
    proof_file = tmp_path / "Test.proof"
    proof_file.write_text(source, encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        parse_proof_file(str(proof_file))
    return exc_info.value


class TestMissingSemicolonHeuristic:
    """When a semicolon is missing, the error should point to the previous line."""

    def test_missing_semicolon_between_fields(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda\n"  # missing semicolon
            "    BitString<lambda> bar(BitString<lambda> x);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "missing ';'" in str(err)
        assert err.line == 2
        assert "Int lambda = lambda" in err.source_line

    def test_missing_semicolon_on_function_decl(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda;\n"
            "    BitString<lambda> bar(BitString<lambda> x)\n"  # missing semicolon
            "    BitString<lambda> baz(BitString<lambda> y);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "missing ';'" in str(err)
        assert err.line == 3

    def test_missing_semicolon_with_blank_line(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda\n"  # missing semicolon
            "\n"
            "    BitString<lambda> bar(BitString<lambda> x);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "missing ';'" in str(err)
        assert err.line == 2

    def test_column_points_to_end_of_line(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda\n"  # missing semicolon
            "    BitString<lambda> bar(BitString<lambda> x);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert err.column == len("    Int lambda = lambda")

    def test_error_message_mentions_next_token(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda\n"  # missing semicolon
            "    BitString<lambda> bar(BitString<lambda> x);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "on next line" in str(err)


class TestNormalParseErrors:
    """Standard parse errors should still report the offending token directly."""

    def test_unexpected_token_after_semicolon(self, tmp_path: Path) -> None:
        """A line ending with ';' should never trigger the missing-';' heuristic."""
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda;\n"
            "    BitString<lambda> bar(BitString<lambda> +);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "missing ';'" not in str(err)

    def test_error_has_source_line(self, tmp_path: Path) -> None:
        source = (
            "Primitive Foo(Int lambda) {\n"
            "    Int lambda = lambda;\n"
            "    BitString<lambda> bar(BitString<lambda> +);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert err.source_line != ""

    def test_error_on_first_line_no_heuristic(self, tmp_path: Path) -> None:
        """Errors on line 1 should not trigger the heuristic (no previous line)."""
        source = "notakeyword {\n}\n"
        err = _expect_error(tmp_path, source)
        assert "missing ';'" not in str(err)
        assert err.line == 1


class TestErrorSelectionHeuristic:
    """When ANTLR recovery produces cascading errors, the heuristic should
    pick the most useful one rather than the first or last blindly."""

    def test_missing_param_name_points_to_comma(self, tmp_path: Path) -> None:
        """Missing parameter name (e.g. 'Int ,' instead of 'Int n,') should
        point to the comma, not to a later cascading token."""
        source = (
            "Game Left(Int , Int b) {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right(Int a, Int b) {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert err.line == 1
        assert err.token == ","
        assert err.column == 14

    def test_missing_param_name_mentions_expecting(self, tmp_path: Path) -> None:
        """The error message should indicate what was expected."""
        source = (
            "Game Left(Int , Int b) {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right(Int a, Int b) {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "identifier" in str(err)

    def test_missing_operator_in_type_points_to_right_token(
        self, tmp_path: Path
    ) -> None:
        """Missing operator in a type expression (e.g. 'BitString<n  n>')
        should point to the second operand, not to a closing brace."""
        source = (
            "Game Left(Int n) {\n"
            "    BitString<n  n> Foo() { return Zeros(n); }\n"
            "}\n"
            "Game Right(Int n) {\n"
            "    BitString<n> Foo() { return Zeros(n); }\n"
            "}\n"
            "export Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert err.line == 2
        assert err.token == "n"

    def test_misspelled_game_keyword_points_to_typo(self, tmp_path: Path) -> None:
        """A misspelled 'Game' keyword should point to the typo, not to
        a cascading error inside the previous block."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "ame Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert err.line == 4
        assert err.token == "ame"

    def test_misspelled_game_keyword_message_mentions_game(
        self, tmp_path: Path
    ) -> None:
        """The error message should mention that 'Game' was expected."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "ame Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "Game" in str(err)

    def test_misspelled_keyword_in_proof_helper(self, tmp_path: Path) -> None:
        """A misspelled keyword in a proof file with many helper blocks should
        still point to the actual typo, not to cascading noise inside
        a preceding block."""
        source = (
            "Game Helper1() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "ame Helper2() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "proof:\n"
            "let:\n"
            "theorem:\n"
            "    Foo();\n"
            "games:\n"
        )
        err = _expect_proof_error(tmp_path, source)
        assert err.token == "ame"
        assert err.line == 4
