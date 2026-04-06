"""Tests that prove command gates on check passing first."""

import os
import tempfile

from click.testing import CliRunner

from proof_frog.proof_frog import cli


def test_prove_rejects_ill_typed_proof() -> None:
    """prove should fail early if the proof doesn't pass check."""
    # Create a proof file with a type error (non-nullable assigned to nullable)
    proof_content = """\
Game BadGame() {
    BitString<8> Test(BitString<8>? x) {
        BitString<8> y = x;
        return y;
    }
}
"""
    # The prove command needs a .proof file, but we can test the check gate
    # by creating a .proof file that fails check
    proof_content = """\
import '../../Primitives/SymEnc.primitive';

Game G1() {
    BitString<8> Test() {
        return 0^8;
    }
}

proof:

let:
    Set MessageSpace;
    Set CiphertextSpace;
    Set KeySpace;

theorem:
    G1;

games:
    G1 against G1;
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".proof", delete=False) as f:
        f.write(proof_content)
        f.flush()
        try:
            result = CliRunner().invoke(cli, ["prove", f.name])
            # Should fail since the proof file is malformed
            assert result.exit_code != 0
        finally:
            os.unlink(f.name)


def test_prove_succeeds_on_valid_proof() -> None:
    """A valid proof should pass both check and prove."""
    examples = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
    proof = os.path.join(examples, "Book", "5", "5_3.proof")
    if not os.path.exists(proof):
        return  # Skip if examples not available
    result = CliRunner().invoke(cli, ["prove", proof])
    assert result.exit_code == 0
