"""The engine against FrogLang's default-value semantics.

FROGLANG_REFERENCE.md section 6.9: a variable read before it is assigned
holds its type's default (for most types one fixed but unspecified value),
a partial operation returns an unspecified value, and evaluation never
fails. The engine may therefore drop an unused read of such a value and
treat two reads of the same type's default as equal, but must assume
nothing else about the value: an adversary may know it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# name -> (fields, Left's body, Right's body, return type, expected)
CASES = {
    # Unused reads of a default or of a partial operation are dropped.
    "DeadFieldRead": ("Int f;", "Int v = f; return 0;", "return 0;", "Int", "accept"),
    "DeadMapRead": (
        "Map<Int, Int> M;",
        "Int v = M[k]; return 0;",
        "return 0;",
        "Int",
        "accept",
    ),
    "DeadLocalRead": ("", "Int x; Int v = x; return 0;", "return 0;", "Int", "accept"),
    "DeadDivision": ("", "Int v = 1 / k; return 0;", "return 0;", "Int", "accept"),
    # Two fields of one type hold the same default until assigned.
    "SameTypeDefaults": ("Int f; Int g;", "return f;", "return g;", "Int", "accept"),
    # Nothing else is known about an unspecified value.
    "FieldDefaultVsInput": (
        "Int f;",
        "return f == k;",
        "return false;",
        "Bool",
        "reject",
    ),
    "AbsentKeyVsInput": (
        "Map<Int, Int> M;",
        "return M[k] == k;",
        "return false;",
        "Bool",
        "reject",
    ),
}


def _write_case(directory: Path, name: str) -> Path:
    fields, left, right, return_type, _ = CASES[name]
    games = "\n\n".join(
        f"Game {side}() {{\n    {fields}\n"
        f"    {return_type} Q(Int k) {{\n        {body}\n    }}\n}}"
        for side, body in (("Left", left), ("Right", right))
    )
    (directory / f"{name}.game").write_text(f"{games}\n\nexport as {name};\n")
    proof = directory / f"{name}.proof"
    proof.write_text(
        f"import '{name}.game';\n\nproof:\n\nlet:\n\nassume:\n\n"
        f"theorem:\n    {name}();\n\ngames:\n"
        f"    {name}().Left against {name}().Adversary;\n"
        f"    {name}().Right against {name}().Adversary;\n"
    )
    return proof


@pytest.mark.parametrize("name", sorted(CASES))
def test_default_value_semantics(name: str, tmp_path: Path) -> None:
    proof = _write_case(tmp_path, name)
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(proof)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert "Traceback" not in output, output
    if CASES[name][4] == "accept":
        assert result.returncode == 0, output
        assert "Proof Succeeded!" in output, output
    else:
        assert result.returncode != 0, output
        assert "Proof Failed!" in output, output
