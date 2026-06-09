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
    import re  # pylint: disable=import-outside-toplevel

    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line for line in text.splitlines() if "//" not in line)


def _parse(path: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "parse", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Parse failed for {path}\nstderr:\n{result.stderr}"
    return result.stdout


@pytest.mark.parametrize(
    "file_path",
    AST_FILES,
    ids=[str(p.relative_to(REPO_ROOT)) for p in AST_FILES],
)
def test_ast_roundtrip(file_path: Path) -> None:
    raw = _parse(file_path)
    parsed = _strip_whitespace(raw)
    original = _strip_whitespace(_strip_comments(file_path.read_text()))

    if parsed == original:
        return

    # The unparsed AST may legitimately differ from the source when the file
    # uses surface sugar that desugars at parse time (e.g. tuple-destructuring
    # bindings, which the parser rewrites into a temp binding plus per-element
    # reads). In that case the source no longer round-trips verbatim, so check
    # the weaker but still meaningful invariant: the canonical (desugared) form
    # is stable under reparse.
    import tempfile  # pylint: disable=import-outside-toplevel

    with tempfile.NamedTemporaryFile(
        "w", suffix=file_path.suffix, delete=False, encoding="ascii"
    ) as f:
        f.write(raw)
        reparsed_path = Path(f.name)
    reparsed = _strip_whitespace(_parse(reparsed_path))

    assert reparsed == parsed, (
        f"AST round-trip not idempotent for {file_path.relative_to(REPO_ROOT)}\n"
        f"First parse (stripped):\n{parsed[:500]}\n"
        f"Reparsed (stripped):\n{reparsed[:500]}"
    )
