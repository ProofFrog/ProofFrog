"""Tests for proof_frog/describe.py."""

import pytest
from pathlib import Path
from proof_frog.describe import describe_file
from proof_frog.frog_parser import ParseError

REPO_ROOT = Path(__file__).parent.parent.parent.parent
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
        out = describe_file(str(EXAMPLES / "Games/SymEnc/INDOT.game"))
        assert "GameFile (export as: INDOT)" in out
        assert "Game Left" in out
        assert "Game Right" in out
        assert "Eavesdrop" in out

    def test_both_games_present(self) -> None:
        out = describe_file(str(EXAMPLES / "Games/SymEnc/INDOT.game"))
        lines = out.splitlines()
        game_lines = [l for l in lines if l.startswith("Game ")]
        assert len(game_lines) == 2

    def test_no_implementations(self) -> None:
        out = describe_file(str(EXAMPLES / "Games/SymEnc/INDOT.game"))
        assert "return" not in out


class TestDescribeProof:
    def test_proof_structure(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/INDOT$_implies_INDOT.proof"))
        assert "Proof:" in out
        assert "Let:" in out
        assert "Assume:" in out
        assert "Theorem:" in out
        assert "Games:" in out

    def test_theorem_present(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/INDOT$_implies_INDOT.proof"))
        assert "INDOT" in out

    def test_game_hops_listed(self) -> None:
        out = describe_file(str(EXAMPLES / "Proofs/SymEnc/INDOT$_implies_INDOT.proof"))
        # Should list at least the first and last game steps
        assert "Left" in out
        assert "Right" in out


class TestDescribeFunctionType:
    def test_random_function_type_in_game(self, tmp_path: Path) -> None:
        game_file = tmp_path / "RFTest.game"
        game_file.write_text(
            "Game Left() {\n"
            "    Function<BitString<8>, BitString<16>> RF;\n"
            "    Void Initialize() {\n"
            "        RF <- Function<BitString<8>, BitString<16>>;\n"
            "    }\n"
            "    BitString<16> Lookup(BitString<8> x) {\n"
            "        BitString<16> z = RF(x);\n"
            "        return z;\n"
            "    }\n"
            "}\n"
            "\n"
            "Game Right() {\n"
            "    Void Initialize() { }\n"
            "    BitString<16> Lookup(BitString<8> x) {\n"
            "        BitString<16> z <- BitString<16>;\n"
            "        return z;\n"
            "    }\n"
            "}\n"
            "\n"
            "export as RFTest;\n",
            encoding="utf-8",
        )
        out = describe_file(str(game_file))
        assert "Function" in out
        assert "RF" in out


class TestDescribeErrors:
    def test_unknown_extension(self) -> None:
        with pytest.raises(ValueError, match="Unknown ProofFrog file type"):
            describe_file("something.txt")

    def test_nonexistent_file(self) -> None:
        with pytest.raises((ParseError, FileNotFoundError, OSError)):
            describe_file(str(EXAMPLES / "Primitives/DoesNotExist.primitive"))
