"""Part B: full pdflatex compile gate over every example proof.

The manual export+compile sweep that surfaced the v3 bug classes (double
sub/superscripts, unescaped specials, macro/builtin collisions, math-unsafe
fallbacks) is promoted here into a permanent regression gate: every
``examples/**/*.proof`` is exported (symbolic composition) and compiled under
``pdflatex``, plus a spread of ``.scheme`` / ``.game`` modules that exercise
the side-by-side game path and tuple-destructuring rendering.

Skipped entirely unless ``pdflatex`` is on PATH, so it is a no-op for
contributors and CI images without a TeX install. Marked ``slow`` so the whole
sweep can be deselected with ``-m "not slow"``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.latex.exporter import export_file

REPO = Path(__file__).resolve().parents[4]

pytestmark = [
    pytest.mark.skipif(
        shutil.which("pdflatex") is None, reason="pdflatex not on PATH"
    ),
    pytest.mark.slow,
]

PROOFS = sorted(
    p.relative_to(REPO).as_posix() for p in (REPO / "examples").glob("**/*.proof")
)

# Module files spanning the new side-by-side two-game rendering, schemes with
# tuple destructuring, and a PRG scheme.
MODULES = [
    "examples/Games/PRG/PRGSecurity.game",
    "examples/Games/Group/DDH.game",
    "examples/Games/PubKeyEnc/INDCPA.game",
    "examples/Schemes/PRG/TriplingPRG.scheme",
    "examples/Schemes/PubKeyEnc/ElGamal.scheme",
]


def _safe_name(rel_path: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in rel_path)


def _assert_compiles(rel_path: str, composition: str, tmp_path: Path) -> None:
    tex = export_file(str(REPO / rel_path), composition=composition)
    name = _safe_name(rel_path)
    tex_file = tmp_path / f"{name}.tex"
    tex_file.write_text(tex, encoding="ascii")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"pdflatex failed for {rel_path} ({composition}):\n{result.stdout[-3000:]}"
    )
    assert (tmp_path / f"{name}.pdf").exists()


@pytest.mark.parametrize("rel_path", PROOFS)
def test_proof_compiles_under_pdflatex(rel_path: str, tmp_path: Path) -> None:
    _assert_compiles(rel_path, "symbolic", tmp_path)


@pytest.mark.parametrize("rel_path", MODULES)
def test_module_compiles_under_pdflatex(rel_path: str, tmp_path: Path) -> None:
    _assert_compiles(rel_path, "symbolic", tmp_path)
