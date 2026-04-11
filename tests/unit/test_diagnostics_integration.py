"""Integration tests for diagnostic output from the prove --json command."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _run_prove_json(proof_path: str, cwd: Path = REPO_ROOT) -> dict:
    """Run `prove --json` and return the parsed JSON output."""
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", "--json", proof_path],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    # The command should always produce JSON on stdout, even for failing proofs
    assert result.stdout.strip(), f"No JSON output produced.\nstderr: {result.stderr}"
    return json.loads(result.stdout)


def test_passing_proof_has_null_diagnosis() -> None:
    """A passing proof should have hop_results where every diagnosis is null."""
    proof_path = "examples/Proofs/SymEnc/ModOTP_INDOT.proof"
    data = _run_prove_json(proof_path)

    assert data["success"] is True
    assert "hop_results" in data
    assert len(data["hop_results"]) > 0

    for hop in data["hop_results"]:
        assert "diagnosis" in hop
        assert hop["diagnosis"] is None, (
            f"Step {hop['step_num']} should have null diagnosis but got: "
            f"{hop['diagnosis']}"
        )
        assert hop["valid"] is True


def test_failing_proof_has_diagnosis() -> None:
    """A broken proof should produce a non-null diagnosis with summary and explanations."""
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    proof_dir = os.path.join(tmpdir, "prooffrog_diag_test")
    os.makedirs(proof_dir, exist_ok=True)

    # Write a minimal primitive
    primitive_content = """\
Primitive SimplePrim(Int n) {
    Set Msg = BitString<n>;
    Msg DoSomething(Msg m);
}
"""
    with open(os.path.join(proof_dir, "Simple.primitive"), "w") as f:
        f.write(primitive_content)

    # Write a game pair where Left and Right differ
    game_content = """\
import 'Simple.primitive';

Game Left(SimplePrim P) {
    P.Msg Query(P.Msg m) {
        P.Msg r <- P.Msg;
        return r;
    }
}

Game Right(SimplePrim P) {
    P.Msg Query(P.Msg m) {
        return m;
    }
}

export as SimpleSec;
"""
    with open(os.path.join(proof_dir, "SimpleSec.game"), "w") as f:
        f.write(game_content)

    # Write a scheme that just returns m (deterministic, not random)
    scheme_content = """\
import 'Simple.primitive';

Scheme SimpleScheme(Int n) extends SimplePrim {
    Set Msg = BitString<n>;

    Msg DoSomething(Msg m) {
        return m;
    }
}
"""
    with open(os.path.join(proof_dir, "SimpleScheme.scheme"), "w") as f:
        f.write(scheme_content)

    # Write a proof that tries to show SimpleSec holds for SimpleScheme.
    # Left inlines to: r <- BitString<n>; return r  (uniform random)
    # Right inlines to: return m  (just returns input)
    # These are NOT equivalent, so the hop should fail with diagnosis.
    proof_content = """\
import 'Simple.primitive';
import 'SimpleScheme.scheme';
import 'SimpleSec.game';

proof:

let:
    Int n;
    SimplePrim P = SimpleScheme(n);

assume:

theorem:
    SimpleSec(P);

games:
    SimpleSec(P).Left against SimpleSec(P).Adversary;
    SimpleSec(P).Right against SimpleSec(P).Adversary;
"""
    proof_path = os.path.join(proof_dir, "Broken.proof")
    with open(proof_path, "w") as f:
        f.write(proof_content)

    data = _run_prove_json(proof_path, cwd=Path(proof_dir))

    assert data["success"] is False
    assert "hop_results" in data
    assert len(data["hop_results"]) >= 1

    # Find the failing hop
    failing_hops = [h for h in data["hop_results"] if not h["valid"]]
    assert (
        len(failing_hops) >= 1
    ), f"Expected at least one failing hop but all passed: {data['hop_results']}"

    diag = failing_hops[0]["diagnosis"]
    assert diag is not None, (
        f"Failing hop should have a diagnosis but got None. " f"Hop: {failing_hops[0]}"
    )
    assert "summary" in diag
    assert isinstance(diag["summary"], str)
    assert len(diag["summary"]) > 0

    assert "explanations" in diag
    assert isinstance(diag["explanations"], list)
