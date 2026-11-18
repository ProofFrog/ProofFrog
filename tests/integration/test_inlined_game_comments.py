"""``inlined-game`` ignores comments in the proof file (F-409).

``inlined-game``, the web endpoint ``/api/inlined-game`` and the MCP tool
``get_inlined_game`` build a one-step proof from the proof file's text
(``web_server._build_minimal_proof``), finding its blocks by keywords and
braces, so that the rest of the file need not parse. The search used to look
inside comments too: a header comment saying ``let:`` was taken for the
``let:`` block, and the built proof did not parse. Comments are now blanked
first, so a proof gives the same result with or without them.
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

export as CommentLet;
"""

# Comments holding block keywords (`let:`, `theorem:`, `games`, `assume:`),
# braces, a Game and a Reduction header, one in front of the import on its
# line, and an import path holding `//`, which is not a comment.
_COMMENTED = """\
/* Header. The let: block below names n; theorem: and games are
   listed after it. Braces in a comment are not code: { { {
Game Fake() { Int Get() { return 0; } }
*/ import './/CommentLet.game'; // the path's `//` is not a comment

// Reduction Phantom() compose CommentLet(n).Left against CommentLet(n).Adversary {
proof:

let:
    Int n; // theorem: CommentLet(n); games: are not here
    /* assume: nothing */

theorem:
    CommentLet(n);

games:
    CommentLet(n).Left against CommentLet(n).Adversary;
    CommentLet(n).Right against CommentLet(n).Adversary;
"""

# The same proof without its comments.
_PLAIN = """\
import './/CommentLet.game';

proof:

let:
    Int n;

theorem:
    CommentLet(n);

games:
    CommentLet(n).Left against CommentLet(n).Adversary;
    CommentLet(n).Right against CommentLet(n).Adversary;
"""

_STEP = "CommentLet(n).Left against CommentLet(n).Adversary"

_CANONICAL = "Game Left() {\n  Int Get() { \n    return n;\n  }\n}\n"

_POST_HEADERS = {"Origin": "http://127.0.0.1:localhost"}


@pytest.fixture
def proof_dir(tmp_path: Path) -> Path:
    (tmp_path / "CommentLet.game").write_text(_GAME, encoding="utf-8")
    (tmp_path / "commented.proof").write_text(_COMMENTED, encoding="utf-8")
    (tmp_path / "plain.proof").write_text(_PLAIN, encoding="utf-8")
    return tmp_path


def _inlined_game_cli(proof: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "inlined-game", str(proof), _STEP],
        capture_output=True,
        text=True,
        check=False,
    )
    detail: dict[str, object] = json.loads(result.stdout)
    return detail


# pylint: disable=protected-access


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a // b\nc", "a     \nc"),
        ("a /* b\nc */ d", "a     \n     d"),
        ("import 'x//y.game'; // z", "import 'x//y.game';     "),
        ("a /* b", "a /* b"),
        ("a/*b*/c", "a     c"),
    ],
    ids=["line", "block", "file_path", "unclosed_block", "between_tokens"],
)
def test_blank_comments(text: str, expected: str) -> None:
    assert web_server._blank_comments(text) == expected


def test_minimal_proof_is_the_same_with_comments() -> None:
    commented = web_server._build_minimal_proof(_COMMENTED, _STEP)
    plain = web_server._build_minimal_proof(_PLAIN, _STEP)
    assert commented is not None and plain is not None
    assert commented.split() == plain.split()


def test_theorem_in_a_comment_only_is_not_found() -> None:
    text = "// theorem: CommentLet(n);\nproof:\nlet:\n    Int n;\n"
    assert web_server._build_minimal_proof(text, _STEP) is None


# pylint: enable=protected-access


def test_cli_inlined_game_ignores_comments(proof_dir: Path) -> None:
    plain = _inlined_game_cli(proof_dir / "plain.proof")
    commented = _inlined_game_cli(proof_dir / "commented.proof")
    assert plain["success"] is True
    assert plain["canonical"] == _CANONICAL
    assert commented == plain


def test_web_inlined_game_ignores_comments(proof_dir: Path) -> None:
    app, _observer = create_app(str(proof_dir), watch=False)
    app.testing = True
    with app.test_client() as client:
        resp = client.post(
            "/api/inlined-game",
            data=json.dumps(
                {"path": "commented.proof", "content": _COMMENTED, "step_text": _STEP}
            ),
            content_type="application/json",
            headers=_POST_HEADERS,
        )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["success"] is True, body
    assert body["canonical"] == _CANONICAL
