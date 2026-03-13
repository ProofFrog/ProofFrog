import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


_FROG_EXTENSIONS = {".primitive", ".scheme", ".game", ".proof"}


def _collect_files() -> list[Path]:
    files: list[Path] = []
    # Direct children of Primitives (flat directory)
    files.extend(
        p
        for p in (REPO_ROOT / "examples/Primitives").iterdir()
        if p.is_file() and p.suffix in _FROG_EXTENSIONS
    )
    # All files recursively in Schemes and Games
    files.extend(
        p
        for p in (REPO_ROOT / "examples/Schemes").rglob("*")
        if p.is_file() and p.suffix in _FROG_EXTENSIONS
    )
    files.extend(
        p
        for p in (REPO_ROOT / "examples/Games").rglob("*")
        if p.is_file() and p.suffix in _FROG_EXTENSIONS
    )
    # Only .proof files in Proofs
    files.extend((REPO_ROOT / "examples/Proofs").rglob("*.proof"))
    return sorted(files)


AST_FILES = _collect_files()


def _strip_whitespace(text: str) -> str:
    return "".join(text.split())


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if "//" not in line)


@pytest.mark.parametrize(
    "file_path",
    AST_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in AST_FILES],
)
def test_ast_roundtrip(file_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "parse", str(file_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Parse failed for {file_path.relative_to(REPO_ROOT)}\n"
        f"stderr:\n{result.stderr}"
    )

    parsed = _strip_whitespace(result.stdout)
    original = _strip_whitespace(_strip_comments(file_path.read_text()))

    assert parsed == original, (
        f"AST round-trip mismatch for {file_path.relative_to(REPO_ROOT)}\n"
        f"Original (stripped):\n{original[:500]}\n"
        f"Parsed (stripped):\n{parsed[:500]}"
    )
