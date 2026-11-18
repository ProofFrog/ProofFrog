"""The step-inspection commands refuse an ill-formed proof ``let:`` entry
(ruling Q13, F-400).

A ``let:`` value is a constant, read as its expression wherever the entry is
used, so an entry whose value makes a non-deterministic call is ill-formed:
each use would make the call again. ``step-detail``, ``inlined-game``,
``canonicalization-trace``, ``step-after-transform`` and ``export-latex`` set
a proof up without type checking it, and used to show ``c = R.Draw()`` as a
fresh draw at each use (``return [R.Draw(), R.Draw()];``). Proof set-up now
refuses such an entry itself, so each of them reports the refusal.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import web_server

_FIXTURES = Path(__file__).parent / "soundness_regression_fixtures" / "F_395"

# (proof, its refused entry's text)
_ILL_FORMED = [
    ("letdraw.proof", "let: entry 'c' = R.Draw() makes a non-deterministic call"),
    (
        "letcall_xor.proof",
        "let: entry 'c' = H(R.Draw()) + 0^m makes a non-deterministic call",
    ),
]

_STEP = {
    "letdraw.proof": "LetDraw(n, R, c).Left against LetDraw(n, R, c).Adversary",
    "letcall_xor.proof": (
        "LetCallDraw(n, m, R, H, c).Left against LetCallDraw(n, m, R, H, c).Adversary"
    ),
}


def _copy_fixtures(tmp_path: Path) -> Path:
    # Comments included: their header comments say "let:", which inlined-game's
    # block extraction (`_build_minimal_proof`) once took for the block (F-409).
    for source in _FIXTURES.iterdir():
        shutil.copy(source, tmp_path / source.name)
    return tmp_path


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("proof, message", _ILL_FORMED)
def test_step_detail_reports_refused_let_entry(
    tmp_path: Path, proof: str, message: str
) -> None:
    result = _cli("step-detail", str(_copy_fixtures(tmp_path) / proof), "0")
    detail = json.loads(result.stdout)
    assert detail["success"] is False
    assert detail["canonical"] == ""
    assert message in detail["output"]


def test_step_detail_shows_deterministic_let_value(tmp_path: Path) -> None:
    result = _cli(
        "step-detail", str(_copy_fixtures(tmp_path) / "letfixed_control.proof"), "0"
    )
    detail = json.loads(result.stdout)
    assert detail["success"] is True
    assert "R.Fixed()" in detail["canonical"]


@pytest.mark.parametrize("proof, message", _ILL_FORMED)
def test_inlined_game_reports_refused_let_entry(
    tmp_path: Path, proof: str, message: str
) -> None:
    result = _cli("inlined-game", str(_copy_fixtures(tmp_path) / proof), _STEP[proof])
    detail = json.loads(result.stdout)
    assert detail["success"] is False
    assert message in detail["output"]


def test_inlined_game_shows_deterministic_let_value(tmp_path: Path) -> None:
    result = _cli(
        "inlined-game",
        str(_copy_fixtures(tmp_path) / "letfixed_control.proof"),
        "LetFixed(n, R, c).Left against LetFixed(n, R, c).Adversary",
    )
    detail = json.loads(result.stdout)
    assert detail["success"] is True
    assert "R.Fixed()" in detail["canonical"]


@pytest.mark.parametrize("proof, message", _ILL_FORMED)
def test_trace_and_step_after_transform_report_refused_let_entry(
    tmp_path: Path, proof: str, message: str
) -> None:
    path = str(_copy_fixtures(tmp_path) / proof)
    # pylint: disable=protected-access
    trace = web_server._capture_canonicalization_trace(path, 0)
    after = web_server._capture_step_after_transform(path, 0, "Remove Duplicate Fields")
    # pylint: enable=protected-access
    for result in (trace, after):
        assert result["success"] is False
        assert message in result["error"]


@pytest.mark.parametrize("proof, message", _ILL_FORMED)
def test_export_latex_reports_refused_let_entry(
    tmp_path: Path, proof: str, message: str
) -> None:
    out = tmp_path / "out.tex"
    result = _cli("export-latex", str(_copy_fixtures(tmp_path) / proof), "-o", str(out))
    assert result.returncode == 1
    assert message in result.stderr
    assert "Traceback" not in result.stderr
    assert not out.exists()
