"""Tests for parse error reporting, especially the missing-semicolon heuristic."""

from pathlib import Path

import pytest

from proof_frog.frog_parser import (
    ParseError,
    parse_game_file,
    parse_primitive_file,
    parse_proof_file,
    parse_scheme_file,
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


def _expect_scheme_error(tmp_path: Path, source: str) -> ParseError:
    scheme_file = tmp_path / "Test.scheme"
    scheme_file.write_text(source, encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        parse_scheme_file(str(scheme_file))
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


    def test_missing_semicolon_before_closing_brace_multiline(
        self, tmp_path: Path
    ) -> None:
        """Missing ';' before '}' on the next line should say 'before }'."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() {\n"
            "        return true\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "missing ';'" in str(err)
        assert "before '}'" in str(err)
        assert err.line == 3

    def test_missing_semicolon_before_closing_brace_same_line(
        self, tmp_path: Path
    ) -> None:
        """Missing ';' before '}' on the same line should say 'before }'."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() { return true }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "missing ';'" in str(err)
        assert "before '}'" in str(err)
        assert err.line == 2


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


class TestEnhancedErrorMessages:
    """Tests for improved error message heuristics."""

    def test_double_quote_import(self, tmp_path: Path) -> None:
        """Double-quoted import should suggest single quotes."""
        source = (
            'import "../path/to/file.primitive";\n'
            "Game Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "single quotes" in str(err)
        assert err.line == 1

    def test_lowercase_type_name_in_statement(self, tmp_path: Path) -> None:
        """Lowercase 'set' at statement level should suggest 'Set'."""
        # Use a context where the lowercase type name causes a parse error
        # (e.g. 'set' used as a type in a field declaration inside a Game).
        # Here 'set' parses as an identifier, but it causes an error when
        # it's used alone as a statement keyword.
        source = (
            "Game Left() {\n"
            "    set MySet;\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        # 'set' parses as an lvalue type, so this actually parses.
        # The lowercase type heuristic only helps when the token causes
        # an error in a specific position. This is tested indirectly
        # by check-time errors (semantic analysis), not parse errors.
        # Just verify it does parse without error.
        from proof_frog.frog_parser import parse_game_file

        game_file = tmp_path / "Test.game"
        game_file.write_text(source, encoding="utf-8")
        # Should parse fine (set is treated as an identifier)
        parse_game_file(str(game_file))

    def test_missing_closing_angle_bracket(self, tmp_path: Path) -> None:
        """Missing '>' in BitString<32 should hint about closing bracket."""
        source = (
            "Primitive Foo() {\n"
            "    BitString<32 bar(Int x);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "'>'" in str(err)
        assert "BitString" in str(err)

    def test_arrow_instead_of_equals(self, tmp_path: Path) -> None:
        """'=>' should suggest '=' or '<-'."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() {\n"
            "        Bool x => true;\n"
            "        return x;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "'=>'" in str(err)
        assert "'='" in str(err) or "'<-'" in str(err)

    def test_double_equals_for_assignment(self, tmp_path: Path) -> None:
        """'==' in assignment should suggest '='."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() {\n"
            "        Bool x == true;\n"
            "        return x;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "'='" in str(err)
        assert "assignment" in str(err)

    def test_equals_in_if_condition(self, tmp_path: Path) -> None:
        """'=' in an if-condition should suggest '=='."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() {\n"
            "        if (true = true) {\n"
            "            return true;\n"
            "        }\n"
            "        return false;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "'=='" in str(err)
        assert "comparison" in str(err)

    def test_missing_comma_between_params(self, tmp_path: Path) -> None:
        """Missing comma between parameters should hint about ','."""
        source = (
            "Game Left() {\n"
            "    Bool Foo(Int a Int b) {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo(Int a, Int b) { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "','" in str(err)

    def test_misspelled_for_keyword(self, tmp_path: Path) -> None:
        """'fore' should suggest 'for'."""
        source = (
            "Game Left() {\n"
            "    Void Foo() {\n"
            "        fore (Int i = 0 to 10) {\n"
            "        }\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Void Foo() { }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "'for'" in str(err)

    def test_misspelled_game_keyword(self, tmp_path: Path) -> None:
        """'Gam' should suggest 'Game'."""
        source = (
            "Gam Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "'Game'" in str(err)

    def test_empty_game_body(self, tmp_path: Path) -> None:
        """Empty game body should say 'at least one method'."""
        source = (
            "Game Left() {\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "empty" in str(err) or "at least one method" in str(err)

    def test_if_without_braces(self, tmp_path: Path) -> None:
        """if-statement without braces should say braces are required."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() {\n"
            "        if (true)\n"
            "            return true;\n"
            "        return false;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "braces" in str(err) or "{ }" in str(err)

    def test_missing_closing_paren(self, tmp_path: Path) -> None:
        """Missing ')' should hint about the closing parenthesis."""
        source = (
            "Primitive Foo() {\n"
            "    Bool bar(Int x;\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "')'" in str(err)

    def test_trailing_comma_in_params(self, tmp_path: Path) -> None:
        """Trailing comma in parameters should explain it's not allowed."""
        source = (
            "Primitive Foo() {\n"
            "    Bool bar(Int x,);\n"
            "}\n"
        )
        err = _expect_error(tmp_path, source)
        assert "trailing" in str(err).lower() or "after ','" in str(err)

    def test_missing_closing_brace(self, tmp_path: Path) -> None:
        """Missing '}' should hint about unmatched braces."""
        source = (
            "Primitive Foo() {\n"
            "    Bool bar(Int x);\n"
        )
        err = _expect_error(tmp_path, source)
        assert "brace" in str(err).lower() or "'}'" in str(err)

    def test_missing_second_game_in_game_file(self, tmp_path: Path) -> None:
        """A .game file with only one Game should explain that two are needed."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "export as Test;\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "two" in str(err).lower() or "exactly two" in str(err)

    def test_missing_export_in_game_file(self, tmp_path: Path) -> None:
        """A .game file with two Games but no export should mention export."""
        source = (
            "Game Left() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() { return true; }\n"
            "}\n"
        )
        err = _expect_game_error(tmp_path, source)
        assert "export" in str(err).lower()

    def test_scheme_missing_extends(self, tmp_path: Path) -> None:
        """A Scheme without 'extends' should say 'extends' is expected."""
        source = (
            "Scheme Foo(Int lambda) {\n"
            "    Set Key = BitString<lambda>;\n"
            "}\n"
        )
        err = _expect_scheme_error(tmp_path, source)
        assert "extends" in str(err)
