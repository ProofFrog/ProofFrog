"""Tests for intra-scheme method calls via the 'this' keyword."""

from pathlib import Path

import pytest

from proof_frog import frog_parser, semantic_analysis


_HELPER_PRIMITIVE = """\
Primitive HelperPrimitive(Set KeySpace) {
    Set Key = KeySpace;

    Key KeyGen();
    Key DeriveKey(Key seed);
}
"""


def _write_primitives(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "HelperPrimitive.primitive").write_text(_HELPER_PRIMITIVE)


class TestThisKeywordTypeChecking:
    def test_this_method_call_type_checks(self, tmp_path: Path) -> None:
        """A scheme method calling another method via this.Method() should type-check."""
        _write_primitives(tmp_path)
        source = (
            "import 'fixtures/HelperPrimitive.primitive';\n\n"
            "Scheme MyScheme(Int lambda) extends HelperPrimitive {\n"
            "    Set Key = BitString<lambda>;\n\n"
            "    Key DeriveKey(Key seed) {\n"
            "        return seed;\n"
            "    }\n\n"
            "    Key KeyGen() {\n"
            "        Key seed <- Key;\n"
            "        return this.DeriveKey(seed);\n"
            "    }\n"
            "}\n"
        )
        file_path = str(tmp_path / "test.scheme")
        Path(file_path).write_text(source)
        root = frog_parser.parse_file(file_path)
        # Should not raise
        semantic_analysis.check_well_formed(root, file_path)

    def test_this_nonexistent_method_fails(self, tmp_path: Path) -> None:
        """Calling this.NonExistent() should fail type checking."""
        _write_primitives(tmp_path)
        source = (
            "import 'fixtures/HelperPrimitive.primitive';\n\n"
            "Scheme MyScheme(Int lambda) extends HelperPrimitive {\n"
            "    Set Key = BitString<lambda>;\n\n"
            "    Key DeriveKey(Key seed) {\n"
            "        return seed;\n"
            "    }\n\n"
            "    Key KeyGen() {\n"
            "        Key seed <- Key;\n"
            "        return this.NonExistent(seed);\n"
            "    }\n"
            "}\n"
        )
        file_path = str(tmp_path / "test.scheme")
        Path(file_path).write_text(source)
        root = frog_parser.parse_file(file_path)
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            semantic_analysis.check_well_formed(root, file_path)

    def test_this_wrong_arg_type_fails(self, tmp_path: Path) -> None:
        """Calling this.Method() with wrong argument types should fail."""
        _write_primitives(tmp_path)
        source = (
            "import 'fixtures/HelperPrimitive.primitive';\n\n"
            "Scheme MyScheme(Int lambda) extends HelperPrimitive {\n"
            "    Set Key = BitString<lambda>;\n\n"
            "    Key DeriveKey(Key seed) {\n"
            "        return seed;\n"
            "    }\n\n"
            "    Key KeyGen() {\n"
            "        Bool flag = true;\n"
            "        return this.DeriveKey(flag);\n"
            "    }\n"
            "}\n"
        )
        file_path = str(tmp_path / "test.scheme")
        Path(file_path).write_text(source)
        root = frog_parser.parse_file(file_path)
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            semantic_analysis.check_well_formed(root, file_path)

    def test_this_outside_scheme_fails(self) -> None:
        """Using 'this' in a game (outside scheme) should fail."""
        source = (
            "Game G() {\n"
            "    Void Initialize() {\n"
            "        Bool x = this.foo;\n"
            "    }\n"
            "}\n"
        )
        game = frog_parser.parse_game(source)
        with pytest.raises(semantic_analysis.FailedTypeCheck):
            semantic_analysis.CheckTypeVisitor({}, "test", {}).visit(game)
