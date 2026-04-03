"""Tests for path traversal protections in web_server, mcp_server, and frog_parser."""

from pathlib import Path
from unittest.mock import patch

import pytest

from proof_frog.web_server import _safe_path
from proof_frog.frog_parser import resolve_import_path

try:
    from proof_frog.mcp_server import _safe_resolve, _PathOutsideDirectory

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False


# ---------------------------------------------------------------------------
# _safe_path (web_server)
# ---------------------------------------------------------------------------


class TestSafePath:
    """Tests for web_server._safe_path."""

    def test_normal_relative_path(self, tmp_path: Path) -> None:
        (tmp_path / "file.proof").touch()
        result = _safe_path(str(tmp_path), "file.proof")
        assert result is not None
        assert result == tmp_path / "file.proof"

    def test_nested_relative_path(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "file.proof").touch()
        result = _safe_path(str(tmp_path), "sub/file.proof")
        assert result is not None
        assert result == sub / "file.proof"

    def test_dotdot_traversal_rejected(self, tmp_path: Path) -> None:
        result = _safe_path(str(tmp_path), "../../../etc/passwd")
        assert result is None

    def test_absolute_path_outside_rejected(self, tmp_path: Path) -> None:
        result = _safe_path(str(tmp_path), "/etc/passwd")
        assert result is None

    def test_prefix_sibling_directory_rejected(self, tmp_path: Path) -> None:
        """Regression: '/base_evil' must not pass when base is '/base'."""
        base = tmp_path / "data"
        sibling = tmp_path / "data_evil"
        base.mkdir()
        sibling.mkdir()
        (sibling / "secret.txt").touch()
        result = _safe_path(str(base), "../data_evil/secret.txt")
        assert result is None

    def test_empty_path_returns_base(self, tmp_path: Path) -> None:
        result = _safe_path(str(tmp_path), "")
        assert result is not None
        assert result == tmp_path

    def test_symlink_escape_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret")
        inside = tmp_path / "inside"
        inside.mkdir()
        link = inside / "escape"
        link.symlink_to(outside)
        result = _safe_path(str(inside), "escape/secret.txt")
        assert result is None

    def test_git_directory_rejected(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]")
        assert _safe_path(str(tmp_path), ".git/config") is None

    def test_nested_dotdir_rejected(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub" / ".hidden"
        sub.mkdir(parents=True)
        (sub / "secret").touch()
        assert _safe_path(str(tmp_path), "sub/.hidden/secret") is None

    def test_dotfile_rejected(self, tmp_path: Path) -> None:
        (tmp_path / ".env").touch()
        assert _safe_path(str(tmp_path), ".env") is None


# ---------------------------------------------------------------------------
# _safe_resolve (mcp_server)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_MCP, reason="mcp package not installed")
class TestMcpSafeResolve:
    """Tests for mcp_server._safe_resolve."""

    def test_normal_path(self, tmp_path: Path) -> None:
        (tmp_path / "test.proof").touch()
        with patch("proof_frog.mcp_server._directory", str(tmp_path)):
            result = _safe_resolve("test.proof")
            assert result == str((tmp_path / "test.proof").resolve())

    def test_dotdot_rejected(self, tmp_path: Path) -> None:
        with patch("proof_frog.mcp_server._directory", str(tmp_path)):
            with pytest.raises(_PathOutsideDirectory):
                _safe_resolve("../../../etc/passwd")

    def test_absolute_outside_rejected(self, tmp_path: Path) -> None:
        with patch("proof_frog.mcp_server._directory", str(tmp_path)):
            with pytest.raises(_PathOutsideDirectory):
                _safe_resolve("/etc/passwd")

    def test_sibling_prefix_rejected(self, tmp_path: Path) -> None:
        base = tmp_path / "data"
        base.mkdir()
        sibling = tmp_path / "data_evil"
        sibling.mkdir()
        with patch("proof_frog.mcp_server._directory", str(base)):
            with pytest.raises(_PathOutsideDirectory):
                _safe_resolve("../data_evil/secret")

    def test_git_directory_rejected(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]")
        with patch("proof_frog.mcp_server._directory", str(tmp_path)):
            with pytest.raises(_PathOutsideDirectory):
                _safe_resolve(".git/config")

    def test_dotfile_rejected(self, tmp_path: Path) -> None:
        (tmp_path / ".env").touch()
        with patch("proof_frog.mcp_server._directory", str(tmp_path)):
            with pytest.raises(_PathOutsideDirectory):
                _safe_resolve(".env")


# ---------------------------------------------------------------------------
# resolve_import_path with allowed_root
# ---------------------------------------------------------------------------


class TestResolveImportPath:
    """Tests for frog_parser.resolve_import_path with allowed_root."""

    def test_without_allowed_root_permits_traversal(self, tmp_path: Path) -> None:
        proof = tmp_path / "sub" / "test.proof"
        proof.parent.mkdir()
        proof.touch()
        result = resolve_import_path("../../outside.primitive", str(proof))
        # Should resolve without error (no sandbox)
        assert "outside.primitive" in result

    def test_allowed_root_permits_valid_import(self, tmp_path: Path) -> None:
        primitives = tmp_path / "Primitives"
        primitives.mkdir()
        (primitives / "SKE.primitive").touch()
        proofs = tmp_path / "Proofs"
        proofs.mkdir()
        proof = proofs / "test.proof"
        proof.touch()
        result = resolve_import_path(
            "../Primitives/SKE.primitive", str(proof), allowed_root=str(tmp_path)
        )
        assert result.endswith("SKE.primitive")

    def test_allowed_root_rejects_traversal(self, tmp_path: Path) -> None:
        inner = tmp_path / "project"
        inner.mkdir()
        proof = inner / "test.proof"
        proof.touch()
        with pytest.raises(ValueError, match="resolves outside"):
            resolve_import_path(
                "../../etc/passwd", str(proof), allowed_root=str(inner)
            )

    def test_allowed_root_rejects_absolute_outside(self, tmp_path: Path) -> None:
        proof = tmp_path / "test.proof"
        proof.touch()
        with pytest.raises(ValueError, match="resolves outside"):
            resolve_import_path(
                "/etc/passwd", str(proof), allowed_root=str(tmp_path)
            )

    def test_allowed_root_accepts_absolute_inside(self, tmp_path: Path) -> None:
        (tmp_path / "file.primitive").touch()
        proof = tmp_path / "test.proof"
        proof.touch()
        result = resolve_import_path(
            str(tmp_path / "file.primitive"),
            str(proof),
            allowed_root=str(tmp_path),
        )
        assert result.endswith("file.primitive")
