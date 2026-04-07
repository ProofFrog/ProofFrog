"""Tests for the --json CLI output flag."""

import json
import os

from click.testing import CliRunner

from proof_frog.proof_frog import cli

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
PRIMITIVE = os.path.join(EXAMPLES, "Primitives", "PRG.primitive")
GAME = os.path.join(EXAMPLES, "Games", "PRG", "PRGSecurity.game")
PROOF = os.path.join(EXAMPLES, "joy_old", "5", "5_3.proof")


def _run(*args: str) -> tuple[int, dict]:  # type: ignore[type-arg]
    result = CliRunner().invoke(cli, list(args))
    return result.exit_code, json.loads(result.output)


# ── parse ──────────────────────────────────────────────────────────────


def test_parse_json_success() -> None:
    code, data = _run("parse", "--json", PRIMITIVE)
    assert code == 0
    assert data["success"] is True
    assert "output" in data


def test_parse_json_missing_file() -> None:
    code, data = _run("parse", "--json", "nonexistent.primitive")
    assert code == 0
    assert data["success"] is False


def test_parse_no_json_missing_file() -> None:
    result = CliRunner().invoke(cli, ["parse", "nonexistent.primitive"])
    assert result.exit_code == 1


# ── check ──────────────────────────────────────────────────────────────


def test_check_json_success() -> None:
    code, data = _run("check", "--json", PRIMITIVE)
    assert code == 0
    assert data["success"] is True
    assert "well-formed" in data["output"]


def test_check_json_missing_file() -> None:
    code, data = _run("check", "--json", "nonexistent.primitive")
    assert code == 0
    assert data["success"] is False


def test_check_no_json_missing_file() -> None:
    result = CliRunner().invoke(cli, ["check", "nonexistent.primitive"])
    assert result.exit_code == 1


# ── prove ──────────────────────────────────────────────────────────────


def test_prove_json_success() -> None:
    code, data = _run("prove", "--json", PROOF)
    assert code == 0
    assert data["success"] is True
    assert isinstance(data["hop_results"], list)
    assert len(data["hop_results"]) > 0
    hop = data["hop_results"][0]
    assert "step_num" in hop
    assert "valid" in hop
    assert "kind" in hop


def test_prove_json_missing_file() -> None:
    code, data = _run("prove", "--json", "nonexistent.proof")
    assert code == 0
    assert data["success"] is False


def test_prove_no_json_missing_file() -> None:
    result = CliRunner().invoke(cli, ["prove", "nonexistent.proof"])
    assert result.exit_code == 1


# ── describe ───────────────────────────────────────────────────────────


def test_describe_json_success() -> None:
    code, data = _run("describe", "--json", PRIMITIVE)
    assert code == 0
    assert data["success"] is True
    assert len(data["output"]) > 0


def test_describe_json_missing_file() -> None:
    code, data = _run("describe", "--json", "nonexistent.primitive")
    assert code == 0
    assert data["success"] is False


def test_describe_no_json_missing_file() -> None:
    result = CliRunner().invoke(cli, ["describe", "nonexistent.primitive"])
    assert result.exit_code == 1
