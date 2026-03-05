"""Tests for parse error reporting, especially the missing-semicolon heuristic."""

from pathlib import Path

import pytest

from proof_frog.frog_parser import ParseError, parse_primitive_file


def _expect_error(tmp_path: Path, source: str) -> ParseError:
    prim_file = tmp_path / "Test.primitive"
    prim_file.write_text(source, encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        parse_primitive_file(str(prim_file))
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
