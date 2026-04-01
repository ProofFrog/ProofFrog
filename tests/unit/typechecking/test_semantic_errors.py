"""Tests for enhanced semantic error messages (hints, suggestions)."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis


def _check_error_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source: str,
    ext: str = ".primitive",
) -> str:
    """Write source to a temp file, run check, return captured stderr."""
    file_path = tmp_path / f"Test{ext}"
    file_path.write_text(source)
    root = frog_parser.parse_file(str(file_path))
    with pytest.raises(semantic_analysis.FailedTypeCheck):
        semantic_analysis.check_well_formed(root, str(file_path))
    return capsys.readouterr().err


class TestUndefinedVariableSuggestions:
    def test_close_match_suggests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Undefined variable with a close match should show a hint."""
        source = (
            "Game Left() {\n"
            "    Bool Foo(Int mLeft, Int mRight) {\n"
            "        return mLft == mRight;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo(Int mLeft, Int mRight) {\n"
            "        return mLeft == mRight;\n"
            "    }\n"
            "}\n"
            "export as Test;\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source, ext=".game")
        assert "not defined" in stderr
        assert "hint" in stderr
        assert "mLeft" in stderr

    def test_no_close_match_no_hint(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Undefined variable with no close match should have no hint."""
        source = (
            "Primitive Foo() {\n"
            "    Set Test = xyzzy;\n\n"
            "    Int f();\n"
            "}\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source)
        assert "not defined" in stderr
        assert "  hint:" not in stderr

    def test_lowercase_type_suggests_capitalized(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Lowercase type name in a parameter should suggest the capitalized form."""
        # Use a primitive where 'int' appears as a parameter type —
        # this hits the in_parameter_type branch of visit_variable.
        source = (
            "Primitive Foo(int x) {\n"
            "    Int y = x;\n\n"
            "    Void f();\n"
            "}\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source)
        assert "not defined" in stderr
        assert "  hint:" in stderr
        assert "Int" in stderr
        assert "capitalized" in stderr


class TestUndefinedGameSuggestions:
    def test_misspelled_primitive_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Misspelled primitive name in 'extends' should suggest the correct one."""
        prim = tmp_path / "MyPrimitive.primitive"
        prim.write_text("Primitive MyPrimitive() {\n    Void f();\n}\n")
        source = (
            "import 'MyPrimitive.primitive';\n\n"
            "Scheme Sch() extends MyPrimitiv {\n"
            "    Void f() {}\n"
            "}\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source, ext=".scheme")
        assert "not defined" in stderr
        assert "  hint:" in stderr
        assert "MyPrimitive" in stderr


class TestTypeAliasDisplay:
    def test_return_type_shows_alias(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Return type mismatch should show type alias like E.Message."""
        prim = tmp_path / "Enc.primitive"
        prim.write_text(
            "Primitive Enc(Set KS, Set MS) {\n"
            "    Set Key = KS;\n"
            "    Set Message = MS;\n"
            "    Key KeyGen();\n"
            "    Message Encrypt(Key k);\n"
            "}\n"
        )
        game = tmp_path / "Test.game"
        game.write_text(
            "import 'Enc.primitive';\n\n"
            "Game Left(Enc E) {\n"
            "    E.Key Foo() {\n"
            "        E.Key k = E.KeyGen();\n"
            "        E.Message m = E.Encrypt(k);\n"
            "        return m;\n"
            "    }\n"
            "}\n"
            "Game Right(Enc E) {\n"
            "    E.Key Foo() {\n"
            "        return E.KeyGen();\n"
            "    }\n"
            "}\n"
            "export as Test;\n"
        )
        root = frog_parser.parse_file(str(game))
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            semantic_analysis.check_well_formed(root, str(game))
        stderr = capsys.readouterr().err
        # Should show the alias E.Message for the raw type MS
        assert "E.Message" in stderr
        assert "return type of Foo" in stderr


class TestMethodNotFoundSuggestions:
    def test_misspelled_method_in_paired_game(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Misspelled method name should suggest the correct one."""
        source = (
            "Game Left() {\n"
            "    Bool Fooo() {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo() {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "export as Test;\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source, ext=".game")
        assert "does not exist in paired game" in stderr
        assert "  hint:" in stderr
        assert "Foo" in stderr

    def test_same_name_different_signature(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Same method name but different params should show both signatures."""
        source = (
            "Game Left() {\n"
            "    Bool Foo(Int x, Bool y) {\n"
            "        return y;\n"
            "    }\n"
            "}\n"
            "Game Right() {\n"
            "    Bool Foo(Int x) {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "export as Test;\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source, ext=".game")
        assert "different signatures" in stderr
        assert "Left" in stderr
        assert "Right" in stderr

    def test_game_param_count_mismatch_shows_counts(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Games with different parameter counts should show the counts."""
        source = (
            "Game Left(Int a) {\n"
            "    Bool Foo() {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "Game Right(Int a, Int b) {\n"
            "    Bool Foo() {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
            "export as Test;\n"
        )
        stderr = _check_error_stderr(tmp_path, capsys, source, ext=".game")
        assert "Left" in stderr
        assert "Right" in stderr
        assert "1" in stderr
        assert "2" in stderr


class TestImportPathSuggestions:
    def test_typo_in_import_filename(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Typo in import filename should suggest the correct file."""
        prim = tmp_path / "MyPrimitive.primitive"
        prim.write_text("Primitive MyPrimitive() {\n    Void f();\n}\n")
        source = (
            "import 'MyPrimitiv.primitive';\n\n"
            "Game Left(MyPrimitive P) {\n"
            "    Void Foo() {}\n"
            "}\n"
            "Game Right(MyPrimitive P) {\n"
            "    Void Foo() {}\n"
            "}\n"
            "export as Test;\n"
        )
        file_path = tmp_path / "Test.game"
        file_path.write_text(source)
        root = frog_parser.parse_file(str(file_path))
        with pytest.raises(FileNotFoundError) as exc_info:
            semantic_analysis.check_well_formed(root, str(file_path))
        assert "MyPrimitive.primitive" in str(exc_info.value)
