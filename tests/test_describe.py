"""Tests for proof_frog/describe.py."""

import pytest
from pathlib import Path
from proof_frog.describe import describe_file
from proof_frog.frog_parser import ParseError

REPO_ROOT = Path(__file__).parent.parent
EXAMPLES = REPO_ROOT / "examples"


class TestDescribePrimitive:
    def test_symenc_fields(self) -> None:
        out = describe_file(str(EXAMPLES / "Primitives/SymEnc.primitive"))
        assert "Primitive: SymEnc" in out
        assert "Parameters:" in out
        assert "MessageSpace" in out
        assert "Methods:" in out
        assert "KeyGen" in out
        assert "Enc" in out
        assert "Dec" in out

    def test_prg_fields(self) -> None:
        out = describe_file(str(EXAMPLES / "Primitives/PRG.primitive"))
        assert "Primitive: PRG" in out
        assert "evaluate" in out

    def test_no_implementations(self) -> None:
        out = describe_file(str(EXAMPLES / "Primitives/SymEnc.primitive"))
        # describe should not include braces (method bodies)
        assert "{" not in out
        assert "return" not in out


class TestDescribeScheme:
    def test_otp_structure(self) -> None:
        out = describe_file(str(EXAMPLES / "Schemes/SymEnc/OTP.scheme"))
        assert "Scheme: OTP" in out
        assert "extends SymEnc" in out
        assert "Methods (signatures only):" in out
        assert "KeyGen" in out
        assert "Enc" in out

    def test_no_implementations(self) -> None:
        out = describe_file(str(EXAMPLES / "Schemes/SymEnc/OTP.scheme"))
        assert "return" not in out


class TestDescribeGame:
    def test_onetimesecrecy_structure(self) -> None:
        out = describe_file(str(EXAMPLES / "Games/SymEnc/OneTimeSecrecy.game"))
        assert "GameFile (export as: OneTimeSecrecy)" in out
        assert "Game Left" in out
        assert "Game Right" in out
        assert "Eavesdrop" in out

    def test_both_games_present(self) -> None:
        out = describe_file(str(EXAMPLES / "Games/SymEnc/OneTimeSecrecy.game"))
        lines = out.splitlines()
        game_lines = [l for l in lines if l.startswith("Game ")]
        assert len(game_lines) == 2

    def test_no_implementations(self) -> None:
        out = describe_file(str(EXAMPLES / "Games/SymEnc/OneTimeSecrecy.game"))
        assert "return" not in out


class TestDescribeProof:
    def test_proof_structure(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/OTUCimpliesOTS.proof"))
        assert "Proof:" in out
        assert "Let:" in out
        assert "Assume:" in out
        assert "Theorem:" in out
        assert "Games:" in out

    def test_theorem_present(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/OTUCimpliesOTS.proof"))
        assert "OneTimeSecrecy" in out

    def test_game_hops_listed(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/OTUCimpliesOTS.proof"))
        # Should list at least the first and last game steps
        assert "Left" in out
        assert "Right" in out


class TestDescribeErrors:
    def test_unknown_extension(self) -> None:
        with pytest.raises(ValueError, match="Unknown ProofFrog file type"):
            describe_file("something.txt")

    def test_nonexistent_file(self) -> None:
        with pytest.raises((ParseError, FileNotFoundError, OSError)):
            describe_file(str(EXAMPLES / "Primitives/DoesNotExist.primitive"))
