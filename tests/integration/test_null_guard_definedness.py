"""End-to-end checks that DeadNullGuardElimination does not drop the read of
a possibly-unassigned variable.

A null guard on a tuple literal can never fire.  Removing it removes the
evaluation of the tuple, or leaves the declaration holding it unused.  When
the tuple reads a variable that may be unassigned, that read is something
the adversary observes, so the guard has to stay.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine

FIXTURES = Path(__file__).parent / "null_guard_definedness_fixtures"


@pytest.mark.parametrize(
    "name, accepted",
    [
        ("GuardUnassignedField", False),
        ("GuardUnassignedLocal", False),
        ("GuardAssignedField", True),
        ("DeclUnassignedField", False),
        ("DeclAssignedField", True),
    ],
)
def test_fixture_proof(name: str, accepted: bool) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(FIXTURES / f"{name}.proof")],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    if accepted:
        assert result.returncode == 0, output
        assert "Proof Succeeded!" in output
    else:
        assert result.returncode != 0, output
        assert "Proof Failed!" in output


def _equal(left: str, right: str) -> bool:
    return (
        ProofEngine()
        .check_equivalent(frog_parser.parse_game(left), frog_parser.parse_game(right))
        .valid
    )


def _game(initialize: str, body: str) -> str:
    return f"""
        Game G() {{
            Bool f;
            {initialize}
            Void Store(Bool v) {{ f = v; }}
            Int Query(Int x) {{
                {body}
            }}
        }}
        """


_INITIALIZE = "Void Initialize() { f = false; }"

_GUARDED_BODIES = [
    # The guard tests the tuple directly.
    "if ([x, f] == None) { return 0; } return x;",
    "if (None == [x, f]) { return 0; } return x;",
    # The guard tests a local holding the tuple.
    "[Int, Bool]? t = [x, f]; if (t == None) { return 0; } return x;",
    # The guard tests a local copied from the field.
    "Bool? t = f; if (t == None) { return 0; } return x;",
]


@pytest.mark.parametrize("body", _GUARDED_BODIES)
def test_guard_reading_unassigned_field_rejected(body: str) -> None:
    """Only Store assigns f.  Query called first reads it unassigned on the
    guarded side and not at all on the other."""
    assert not _equal(_game("", body), _game("", "return x;"))


@pytest.mark.parametrize("body", _GUARDED_BODIES)
def test_guard_reading_initialized_field_accepted(body: str) -> None:
    """Control: Initialize assigns f, so the guard is dead."""
    assert _equal(_game(_INITIALIZE, body), _game(_INITIALIZE, "return x;"))
