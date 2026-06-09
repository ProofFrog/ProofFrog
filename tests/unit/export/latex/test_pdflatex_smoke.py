"""Part 5: pdflatex smoke-compile guard.

Exports a representative spread of FrogLang files to LaTeX and runs
``pdflatex`` on each, asserting a clean exit. Skipped entirely unless
``pdflatex`` is on PATH, so it never blocks contributors without a TeX
install (and is a no-op in CI images that lack one).

Catches the class of regressions that plagued v1 -- undefined macros, empty
``\\procedure`` bodies, malformed math -- which unit tests on the rendered
string cannot see.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proof_frog.export.latex.exporter import export_file

REPO = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="pdflatex not on PATH"
)

# (path, composition) pairs spanning module kinds, destructuring, reductions,
# top-level intermediate games, induction, and both proof composition modes.
CASES = [
    ("examples/Schemes/PRG/TriplingPRG.scheme", "symbolic"),
    ("examples/Games/Group/DDH.game", "symbolic"),
    ("examples/Proofs/Group/DDH_implies_CDH.proof", "symbolic"),
    ("examples/Proofs/Group/DDH_implies_CDH.proof", "inlined"),
    ("examples/Proofs/PubKeyEnc/ElGamal_INDCPA_MultiChal.proof", "symbolic"),
    ("examples/Proofs/PubKeyEnc/ElGamal_INDCPA_MultiChal.proof", "inlined"),
]


@pytest.mark.parametrize("rel_path,composition", CASES)
def test_export_compiles_under_pdflatex(
    rel_path: str, composition: str, tmp_path: Path
) -> None:
    tex = export_file(str(REPO / rel_path), composition=composition)
    name = Path(rel_path).stem + "_" + composition
    tex_file = tmp_path / f"{name}.tex"
    tex_file.write_text(tex, encoding="ascii")
    result = subprocess.run(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_file.name,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"pdflatex failed for {rel_path} ({composition}):\n" f"{result.stdout[-3000:]}"
    )
    assert (tmp_path / f"{name}.pdf").exists()
