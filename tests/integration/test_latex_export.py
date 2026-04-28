import subprocess
from pathlib import Path

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
