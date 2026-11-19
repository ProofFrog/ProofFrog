"""``inlined-game`` reads only the reduction a step names (F-412).

``inlined-game``, the web endpoint ``/api/inlined-game`` and the MCP tool
``get_inlined_game`` build a one-step proof from the proof file's text
(``web_server._build_minimal_proof``), so that a proof still being written
can be inspected. The builder used to copy every Reduction block, so an
unfinished reduction (a stub with no method, which does not parse) made every
step fail, even one that does not compose it. It now copies only the
reduction the step names; a step naming the stub still reports the stub's
parse error.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import web_server
from proof_frog.web_server import create_app

_GAME = """\
Game Left(Int n) {
    Int Get() {
        return n;
    }
}

Game Right(Int n) {
    Int Get() {
        return n;
    }
}

export as Stub;
"""

# R is written out; R_Stub, whose name starts with R's, is not finished.
_PROOF = """\
import 'Stub.game';

Reduction R(Int n) compose Stub(n) against Stub(n).Adversary {
    Int Get() {
        return challenger.Get();
    }
}

Reduction R_Stub(Int n) compose Stub(n) against Stub(n).Adversary {
    // to do
}

proof:

let:
    Int n;

theorem:
    Stub(n);

games:
    Stub(n).Left against Stub(n).Adversary;
    Stub(n).Right against Stub(n).Adversary;
"""

_PLAIN_STEP = "Stub(n).Left against Stub(n).Adversary"
_R_STEP = "Stub(n).Left compose R(n) against Stub(n).Adversary"
_STUB_STEP = "Stub(n).Left compose R_Stub(n) against Stub(n).Adversary"

_PLAIN_CANONICAL = "Game Left() {\n  Int Get() { \n    return n;\n  }\n}\n"
_R_CANONICAL = "Game Inlined() {\n  Int Get() { \n    return n;\n  }\n}\n"

_POST_HEADERS = {"Origin": "http://127.0.0.1:localhost"}


@pytest.fixture
def proof_dir(tmp_path: Path) -> Path:
    (tmp_path / "Stub.game").write_text(_GAME, encoding="utf-8")
    (tmp_path / "stub.proof").write_text(_PROOF, encoding="utf-8")
    return tmp_path


def _assert_stub_parse_error(output: object) -> None:
    # The stub's body holds no method, so its closing brace is unexpected.
    assert isinstance(output, str)
    assert "parse error" in output, output
    assert "mismatched input '}'" in output, output


# pylint: disable=protected-access


def test_minimal_proof_leaves_out_a_reduction_the_step_does_not_name() -> None:
    minimal = web_server._build_minimal_proof(_PROOF, _PLAIN_STEP)
    assert minimal is not None
    assert "Reduction" not in minimal


def test_minimal_proof_keeps_the_reduction_the_step_names() -> None:
    minimal = web_server._build_minimal_proof(_PROOF, _R_STEP)
    assert minimal is not None
    assert "Reduction R(Int n)" in minimal
    assert "R_Stub" not in minimal


def test_minimal_proof_keeps_a_named_stub() -> None:
    minimal = web_server._build_minimal_proof(_PROOF, _STUB_STEP)
    assert minimal is not None
    assert "Reduction R_Stub(Int n)" in minimal
    assert "Reduction R(Int n)" not in minimal


def test_minimal_proof_keeps_every_game() -> None:
    text = _PROOF.replace(
        "proof:",
        "Game G_A(Int n) {\n    Int Get() {\n        return n;\n    }\n}\n\nproof:",
    )
    minimal = web_server._build_minimal_proof(text, _PLAIN_STEP)
    assert minimal is not None
    assert "Game G_A(Int n)" in minimal


# pylint: enable=protected-access


def _inlined_game_cli(proof: Path, step: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "inlined-game", str(proof), step],
        capture_output=True,
        text=True,
        check=False,
    )
    detail: dict[str, object] = json.loads(result.stdout)
    return detail


@pytest.mark.parametrize(
    "step, canonical",
    [(_PLAIN_STEP, _PLAIN_CANONICAL), (_R_STEP, _R_CANONICAL)],
    ids=["no_reduction", "written_reduction"],
)
def test_cli_step_not_naming_the_stub(
    proof_dir: Path, step: str, canonical: str
) -> None:
    detail = _inlined_game_cli(proof_dir / "stub.proof", step)
    assert detail["success"] is True, detail
    assert detail["canonical"] == canonical


def test_cli_step_naming_the_stub(proof_dir: Path) -> None:
    detail = _inlined_game_cli(proof_dir / "stub.proof", _STUB_STEP)
    assert detail["success"] is False
    _assert_stub_parse_error(detail["output"])


def _inlined_game_web(proof_dir: Path, step: str) -> dict[str, object]:
    app, _observer = create_app(str(proof_dir), watch=False)
    app.testing = True
    with app.test_client() as client:
        resp = client.post(
            "/api/inlined-game",
            data=json.dumps(
                {"path": "stub.proof", "content": _PROOF, "step_text": step}
            ),
            content_type="application/json",
            headers=_POST_HEADERS,
        )
    assert resp.status_code == 200, resp.get_json()
    body: dict[str, object] = resp.get_json()
    return body


@pytest.mark.parametrize(
    "step, canonical",
    [(_PLAIN_STEP, _PLAIN_CANONICAL), (_R_STEP, _R_CANONICAL)],
    ids=["no_reduction", "written_reduction"],
)
def test_web_step_not_naming_the_stub(
    proof_dir: Path, step: str, canonical: str
) -> None:
    body = _inlined_game_web(proof_dir, step)
    assert body["success"] is True, body
    assert body["canonical"] == canonical


def test_web_step_naming_the_stub(proof_dir: Path) -> None:
    body = _inlined_game_web(proof_dir, _STUB_STEP)
    assert body["success"] is False
    _assert_stub_parse_error(body["output"])
