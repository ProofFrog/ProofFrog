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
