"""Tests for the MCP server's tools, called in-process (skipped without the mcp extra)."""

import asyncio
from pathlib import Path
from typing import Any

import pytest

mcp_server = pytest.importorskip("proof_frog.mcp_server")

EXAMPLES = Path(__file__).resolve().parents[3] / "examples"


def _call(tool: str, args: dict[str, Any]) -> tuple[str, bool]:
    """(text, is_error). A ToolError is what the SDK sends to the client with is_error
    set; UnexpectedToolError (a crash, whose message the client never sees) fails."""
    # pylint: disable-next=import-outside-toplevel
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

    try:
        result = asyncio.run(mcp_server.mcp.call_tool(tool, args))
    except UnexpectedToolError:
        raise
    except ToolError as e:
        return str(e), True
    return "".join(c.text for c in result.content), bool(result.is_error)


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(mcp_server, "_directory", str(tmp_path))
    return tmp_path


def test_tools_registered() -> None:
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {
        "read_file",
        "write_file",
        "parse",
        "check",
        "prove",
        "get_step_detail",
    } <= names


def test_write_read_parse(workdir: Path) -> None:
    src = (EXAMPLES / "Primitives" / "PRF.primitive").read_text(encoding="utf-8")
    _, err = _call("write_file", {"path": "sub/PRF.primitive", "content": src})
    assert not err and (workdir / "sub" / "PRF.primitive").is_file()
    text, err = _call("read_file", {"path": "sub/PRF.primitive"})
    assert not err and text == src
    text, err = _call("parse", {"path": "sub/PRF.primitive"})
    assert not err and '"success": true' in text


def test_errors_reach_the_client(workdir: Path) -> None:
    text, err = _call("read_file", {"path": "../outside.proof"})
    assert err and "outside the working directory" in text
    text, err = _call("read_file", {"path": ".git/config"})
    assert err and "hidden file" in text
    text, err = _call("read_file", {"path": "missing.proof"})
    assert err and "missing.proof" in text


@pytest.mark.skipif(
    not EXAMPLES.joinpath("Proofs").is_dir(),
    reason="examples submodule not checked out",
)
def test_prove_example(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "_directory", str(EXAMPLES))
    text, err = _call("prove", {"proof_path": "Proofs/KEM/KEMPRF_INDCPA.proof"})
    assert not err and '"success": true' in text
