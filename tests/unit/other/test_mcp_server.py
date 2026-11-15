"""Tests for the MCP server, driven through an in-process MCP client.

Skipped without the mcp extra. With mcp installed (1.x or 2.x), proof_frog.mcp_server
must import, so breakage in it fails instead of skipping.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")

# pylint: disable=wrong-import-position
import anyio  # an mcp dependency

from proof_frog import mcp_server

# pylint: enable=wrong-import-position

EXAMPLES = Path(__file__).resolve().parents[3] / "examples"

TOOLS = {
    "version",
    "list_files",
    "read_file",
    "write_file",
    "describe",
    "parse",
    "check",
    "prove",
    "get_step_detail",
    "get_inlined_game",
    "get_canonicalization_trace",
    "get_step_after_transform",
}

PRIMITIVE = """\
Primitive PRF(Set KeySpace, Set Domain, Set Range) {
    Set Key = KeySpace;
    Set Input = Domain;
    Set Output = Range;

    deterministic Output evaluate(Key k, Input x);
}
"""


class _Session:
    """A connected client session, the same way an MCP client sees the server."""

    def __init__(self, session: Any, v2: bool) -> None:
        self._session = session
        self._v2 = v2

    async def call(self, tool: str, args: dict[str, Any]) -> tuple[str, bool]:
        """(text the client receives, whether the result is marked as an error)."""
        result = await self._session.call_tool(tool, args)
        text = "".join(c.text for c in result.content)
        return text, bool(result.is_error if self._v2 else result.isError)

    async def tool_names(self) -> set[str]:
        return {t.name for t in (await self._session.list_tools()).tools}

    async def resource_uris(self) -> set[str]:
        return {str(r.uri) for r in (await self._session.list_resources()).resources}


async def _with_session(body: Any) -> Any:
    # pylint: disable=import-outside-toplevel
    try:
        from mcp import Client  # mcp 2.x
    except ImportError:  # mcp 1.x
        from mcp.shared.memory import create_connected_server_and_client_session

        async with create_connected_server_and_client_session(
            mcp_server.mcp._mcp_server  # pylint: disable=protected-access
        ) as session:
            return await body(_Session(session, v2=False))
    async with Client(mcp_server.mcp) as client:
        return await body(_Session(client, v2=True))


def _call(tool: str, args: dict[str, Any]) -> tuple[str, bool]:
    async def body(s: _Session) -> tuple[str, bool]:
        return await s.call(tool, args)

    result: tuple[str, bool] = anyio.run(_with_session, body)
    return result


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(mcp_server, "_directory", str(tmp_path))
    return tmp_path


def test_tools_and_resource_registered() -> None:
    async def body(s: _Session) -> tuple[set[str], set[str]]:
        return await s.tool_names(), await s.resource_uris()

    names, uris = anyio.run(_with_session, body)
    assert names == TOOLS
    assert "prooffrog://language-reference" in uris


def test_write_read_parse(workdir: Path) -> None:
    _, err = _call("write_file", {"path": "sub/PRF.primitive", "content": PRIMITIVE})
    assert not err and (workdir / "sub" / "PRF.primitive").read_text() == PRIMITIVE
    text, err = _call("read_file", {"path": "sub/PRF.primitive"})
    assert not err and text == PRIMITIVE
    text, err = _call("parse", {"path": "sub/PRF.primitive"})
    assert not err and json.loads(text)["success"] is True


def test_errors_reach_the_client(workdir: Path) -> None:
    (workdir / "sub").mkdir()
    text, err = _call("read_file", {"path": "../outside.proof"})
    assert err and "outside the working directory" in text
    text, err = _call("read_file", {"path": ".git/config"})
    assert err and "hidden file" in text
    text, err = _call("list_files", {"subdirectory": "../"})
    assert err and "outside the working directory" in text
    text, err = _call("read_file", {"path": "missing.proof"})
    assert err and "FileNotFoundError" in text and "missing.proof" in text
    text, err = _call("read_file", {"path": "sub"})
    assert err and "IsADirectoryError" in text


def test_unexpected_exception_reaches_the_client(
    workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mcp 2.x hides a non-ToolError's message from the client; the server converts it."""

    def crash(_path: str) -> Any:
        raise RuntimeError("engine crashed")

    monkeypatch.setattr(mcp_server, "_capture_parse", crash)
    (workdir / "A.primitive").write_text(PRIMITIVE)
    text, err = _call("parse", {"path": "A.primitive"})
    assert err and "RuntimeError: engine crashed" in text


def test_list_files_through_symlinked_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    (real / "Proofs").mkdir(parents=True)
    (real / "Proofs" / "A.proof").write_text("")
    link = tmp_path / "link"
    link.symlink_to(real)
    monkeypatch.setattr(mcp_server, "_directory", str(link))
    text, err = _call("list_files", {"subdirectory": "Proofs"})
    assert not err
    tree = json.loads(text)
    assert tree["path"] == "Proofs"
    assert [c["path"] for c in tree["children"]] == [str(Path("Proofs") / "A.proof")]


def test_tool_calls_run_one_at_a_time(
    workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mcp 2.x runs sync tools on worker threads; the tools must not overlap."""
    active = 0
    most = 0
    guard = threading.Lock()

    def slow_parse(_path: str) -> tuple[str, bool, None, None]:
        nonlocal active, most
        with guard:
            active += 1
            most = max(most, active)
        time.sleep(0.2)
        with guard:
            active -= 1
        return "", True, None, None

    monkeypatch.setattr(mcp_server, "_capture_parse", slow_parse)
    (workdir / "A.primitive").write_text(PRIMITIVE)

    async def body(s: _Session) -> list[bool]:
        errors: list[bool] = []

        async def one() -> None:
            errors.append((await s.call("parse", {"path": "A.primitive"}))[1])

        async with anyio.create_task_group() as tg:
            for _ in range(3):
                tg.start_soon(one)
        return errors

    errors = anyio.run(_with_session, body)
    assert errors == [False, False, False]
    assert most == 1


@pytest.mark.skipif(
    not EXAMPLES.joinpath("Proofs").is_dir(),
    reason="examples submodule not checked out",
)
def test_prove_example(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "_directory", str(EXAMPLES))
    text, err = _call("prove", {"proof_path": "Proofs/KEM/KEMPRF_INDCPA.proof"})
    assert not err
    result = json.loads(text)
    assert result["success"] is True and result["hop_results"]
