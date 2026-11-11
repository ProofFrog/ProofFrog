"""A bare declaration that shadows a field, reached through a reserved name.

These games shadow a field with a local named ``__a5__``, a name the
alpha-renamer leaves alone, so the shadowing declaration reached the
statement sort, which must not float it above a read of the field. Since
ruling Q7 (2026-11-06) the type checker refuses identifiers of the form
``__a<N>__`` as the engine's fresh names, so no well-typed proof reaches
the sort this way: each proof must now stop at type checking. The
dependency edges behind the attacks stay pinned by unit tests that build
the syntax tree directly (``tests/unit/other/test_dependencies.py``).
"""

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "shadowed_declaration_fixtures"
REPO_ROOT = Path(__file__).parents[2]
RESERVED = (
    "error: '__a5__' is reserved: identifiers of the form __a<N>__ are the"
    " engine's fresh names"
)


def _prove(proof_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "proof_frog",
            "prove",
            "--sequential",
            str(FIXTURES / proof_name),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def _assert_refused(result: subprocess.CompletedProcess[str]) -> None:
    """The type checker refuses the reserved name; no hop is checked."""
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert RESERVED in output, output
    assert "Proof Succeeded!" not in output, output
    assert "Proof Failed!" not in output, output


def test_shadowing_declaration_attack_is_refused() -> None:
    """Left reads the field, Right the uninitialized local; they differ."""
    _assert_refused(_prove("shadowed_field.proof"))


def test_shadowing_map_declaration_attack_is_refused() -> None:
    """The same hole with no unassigned read on either side: the shadowing
    local is a map, empty once declared, so Right's membership test is a
    well-defined ``false`` where Left's (on the field) is ``true``."""
    _assert_refused(_prove("shadowed_map_field.proof"))


def test_shadowing_declaration_control_is_refused() -> None:
    """The former sound twin (the field read and an independent draw trade
    places, both above the shadowing declaration) uses the same reserved
    name, so it is refused too."""
    _assert_refused(_prove("shadowed_map_field_control.proof"))
