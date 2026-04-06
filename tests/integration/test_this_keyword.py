"""Integration tests for intra-scheme method calls via the 'this' keyword."""

from pathlib import Path

from click.testing import CliRunner

from proof_frog.proof_frog import cli

_PRIMITIVE = """\
Primitive TwoMethodPrimitive(Set KeySpace, Set SeedSpace) {
    Set Key = KeySpace;
    Set Seed = SeedSpace;

    Key DeriveKey(Seed seed);
    Key KeyGen();
}
"""

_SCHEME = """\
import 'TwoMethodPrimitive.primitive';

Scheme TwoMethodScheme(Int lambda) extends TwoMethodPrimitive {
    Set Key = BitString<lambda>;
    Set Seed = BitString<lambda>;

    Key DeriveKey(Seed seed) {
        return seed;
    }

    Key KeyGen() {
        Seed s <- Seed;
        return this.DeriveKey(s);
    }
}
"""


def test_check_scheme_with_this(tmp_path: Path) -> None:
    """A scheme using this.Method() should pass the check command."""
    (tmp_path / "TwoMethodPrimitive.primitive").write_text(_PRIMITIVE)
    scheme_path = tmp_path / "TwoMethodScheme.scheme"
    scheme_path.write_text(_SCHEME)

    result = CliRunner().invoke(cli, ["check", str(scheme_path)])
    assert result.exit_code == 0, f"check failed:\n{result.output}"
    assert "well-formed" in result.output
