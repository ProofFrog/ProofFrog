import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_export_latex_cli_help() -> None:
    r = subprocess.run(
        ["python", "-m", "proof_frog", "export-latex", "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "export-latex" in r.stdout.lower() or "latex" in r.stdout.lower()


def _sweep_files() -> list[Path]:
    primitives = sorted((REPO / "examples/Primitives").glob("*.primitive"))
    schemes = sorted((REPO / "examples/Schemes/PRG").glob("*.scheme"))
    games = sorted((REPO / "examples/Games/PRG").glob("*.game"))[:2]
    proofs = sorted((REPO / "examples/Proofs/PRG").glob("*.proof"))[:1]
    return primitives + schemes + games + proofs


@pytest.mark.parametrize(
    "src", _sweep_files(), ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_export_sweep(src: Path) -> None:
    from proof_frog.export.latex.exporter import export_file

    out = export_file(str(src))
    assert r"\begin{document}" in out
    assert r"\end{document}" in out


def test_export_latex_composition_flag(tmp_path: Path) -> None:
    out = tmp_path / "ddh.tex"
    r = subprocess.run(
        [
            "python",
            "-m",
            "proof_frog",
            "export-latex",
            "examples/Proofs/Group/DDH_implies_CDH.proof",
            "--composition",
            "inlined",
            "-o",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    assert r"\begin{document}" in text and r"\end{document}" in text


def test_export_latex_no_standalone_flag(tmp_path: Path) -> None:
    out = tmp_path / "frag.tex"
    r = subprocess.run(
        [
            "python",
            "-m",
            "proof_frog",
            "export-latex",
            "examples/Schemes/PRG/TriplingPRG.scheme",
            "--no-standalone",
            "-o",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    # A fragment has no document wrapper but keeps macros and body, and lists
    # the required packages in a commented preamble header.
    assert r"\documentclass" not in text
    assert r"\begin{document}" not in text
    assert r"\providecommand{\TriplingPRG}" in text
    assert r"% \usepackage" in text
