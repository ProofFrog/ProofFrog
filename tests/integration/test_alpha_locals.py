"""An earlier inlined call must not change a later oracle's local names."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "alpha_locals_fixtures"
PROOF = FIXTURES / "alpha_locals.proof"
REPO_ROOT = Path(__file__).parents[2]


def _prove(proof: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", "--sequential", str(proof)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_inlined_return_slot_has_method_local_canonical_name() -> None:
    result = _prove(PROOF)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Step 1/1" in result.stdout
    assert "Proof Succeeded!" in result.stdout

    canonical = []
    for step in (0, 1):
        detail = subprocess.run(
            [sys.executable, "-m", "proof_frog", "step-detail", str(PROOF), str(step)],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
        )
        canonical.append(json.loads(detail.stdout)["canonical"])
    assert canonical[0].split("Int Send", 1)[1] == canonical[1].split("Int Send", 1)[1]
    assert "__a" not in canonical[0]
    assert "v1 = S.Draw()" in canonical[0]


def _reserved(name: str) -> str:
    return (
        f"error: '{name}' is reserved: identifiers of the form __a<N>__ are"
        " the engine's fresh names"
    )


def test_shadowing_declaration_pair_with_reserved_name_is_refused() -> None:
    """The pair (same meaning up to the shadowing local's name) shadows a
    field with ``__a5__``, which the type checker refuses since ruling Q7
    (2026-11-06): it stops there, before any hop."""
    result = _prove(FIXTURES / "shadowed_field_ok.proof")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert _reserved("__a5__") in output, output
    assert "Step 1/1" not in result.stdout


def _write_parameter_pair(tmp_path: Path, left_name: str, right_name: str) -> Path:
    (tmp_path / "Pair.game").write_text(
        """Game Left(BitString<8> k, BitString<8> j) {
    Set<BitString<8>> seen;
    BitString<8> O(Bool c) {
        if (c) { k <-uniq[seen] BitString<8>; }
        return k;
    }
}
Game Right(BitString<8> k, BitString<8> j) {
    Set<BitString<8>> seen;
    BitString<8> O(Bool c) {
        if (c) { j <-uniq[seen] BitString<8>; }
        return j;
    }
}
export as Pair;
""",
        encoding="utf-8",
    )
    proof = tmp_path / "different_parameters.proof"
    proof.write_text(
        f"""import 'Pair.game';
proof:
let:
    BitString<8> {left_name};
    BitString<8> {right_name};
assume:
theorem:
    Pair({left_name}, {right_name});
games:
    Pair({left_name}, {right_name}).Left against Pair({left_name}, {right_name}).Adversary;
    Pair({left_name}, {right_name}).Right against Pair({left_name}, {right_name}).Adversary;
""",
        encoding="utf-8",
    )
    return proof


@pytest.mark.parametrize("left_name,right_name", [("v1", "v2"), ("p", "q")])
def test_distinct_proof_parameters_are_not_local_alpha_equivalent(
    tmp_path: Path, left_name: str, right_name: str
) -> None:
    result = _prove(_write_parameter_pair(tmp_path, left_name, right_name))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Step 1/1" in result.stdout
    assert "failed" in result.stdout.lower()


def test_reserved_proof_parameter_names_are_refused(tmp_path: Path) -> None:
    """``__a1__`` and ``__a2__`` as proof parameters (once a third case of the
    test above) are refused by the type checker since ruling Q7."""
    result = _prove(_write_parameter_pair(tmp_path, "__a1__", "__a2__"))
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert _reserved("__a1__") in output, output
    assert "Step 1/1" not in result.stdout
