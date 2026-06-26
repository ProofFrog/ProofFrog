"""RC4 name-capture / non-fresh-temp distinguisher tests for sampling.py.

Two findings in ``SplitUniformSamples`` (verdict:
``extras/docs/transforms/audit-2026-06/verdicts/sampling/SplitUniformSamples.md``
sections 3 and 8):

* F-034 -- split-piece names ``f"{var}_{i}"`` were minted with no freshness
  check, so a pre-existing binding named e.g. ``z_0`` was captured/rebound by
  the minted ``z_0`` (attack3).
* F-035 -- the bare-use guard scanned only the post-sample statements while
  ``_SliceReplacer`` rewrote the WHOLE block, so a same-scope redeclaration of
  the sampled name let a pre-sample slice be rebound to a split piece
  (attack6f).

For each finding we assert end-to-end through ``ProofEngine.check_equivalent``:

* the NEGATIVE distinguisher (the attack game pair from the audit) is REJECTED;
  and
* a POSITIVE control whose corresponding sound split still fires, so the fix is
  principled (mints fresh / declines only on real hazard, not always).

The attack fragments are taken verbatim from
``extras/docs/transforms/audit-2026-06/attacks/SplitUniformSamples/``.
"""

from __future__ import annotations

from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    engine = ProofEngine()
    engine.variables["lambda"] = Symbol("lambda", positive=True, integer=True)
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    return engine


# ---------------------------------------------------------------------------
# F-034 -- minted split-piece name capture (attack3)
# ---------------------------------------------------------------------------


def test_f034_minted_name_capture_rejected() -> None:
    """attack3: the author's ``z_0`` plus a split of ``z`` into ``z[0:4]`` /
    ``z[4:8]``. The buggy mint named a split piece ``z_0`` too, rebinding
    ``a + z_0`` to ``z_0 + z_0 = 0^4``. Real is a uniform pair; Random returns
    ``[0^4, r]``. Distinguisher (first component == 0^4) has advantage 15/16,
    so a sound engine must REJECT."""
    real = frog_parser.parse_game("""
        Game Real() {
            [BitString<4>, BitString<4>] Query() {
                BitString<4> z_0 <- BitString<4>;
                BitString<8> z <- BitString<8>;
                BitString<4> a = z[0 : 4];
                BitString<4> b = z[4 : 8];
                return [a + z_0, b];
            }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random() {
            [BitString<4>, BitString<4>] Query() {
                BitString<4> r <- BitString<4>;
                return [0^4, r];
            }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


def test_f034_split_still_fires_no_collision() -> None:
    """Positive control: same split shape but no pre-existing ``z_0``. The
    split fires (``z`` -> two independent uniforms), so the game equals its
    explicitly-split twin -- the fresh-name fix must not block this."""
    real = frog_parser.parse_game("""
        Game Real() {
            [BitString<4>, BitString<4>] Query() {
                BitString<8> z <- BitString<8>;
                BitString<4> a = z[0 : 4];
                BitString<4> b = z[4 : 8];
                return [a, b];
            }
        }
        """)
    split = frog_parser.parse_game("""
        Game Split() {
            [BitString<4>, BitString<4>] Query() {
                BitString<4> a <- BitString<4>;
                BitString<4> b <- BitString<4>;
                return [a, b];
            }
        }
        """)
    assert _engine().check_equivalent(real, split).valid


# ---------------------------------------------------------------------------
# F-035 -- scan/rewrite scope mismatch via same-block redeclaration (attack6f)
# ---------------------------------------------------------------------------


def test_f035_redeclaration_capture_rejected() -> None:
    """attack6f: ``z`` is declared as a constant, sliced into ``w``, then
    redeclared as a uniform sample. The block-wide rewrite rebound the
    pre-sample ``w = z[0:4]`` to the split piece, erasing the visible constant.
    Real and Random return different constants in the second component
    (advantage 1), so a sound engine must REJECT."""
    real = frog_parser.parse_game("""
        Game Real() {
            [Bool, BitString<4>] Query() {
                BitString<8> z = 0b10101010;
                BitString<4> w = z[0 : 4];
                BitString<8> z <- BitString<8>;
                BitString<4> a = z[0 : 4];
                return [a == w, w];
            }
        }
        """)
    random = frog_parser.parse_game("""
        Game Random() {
            [Bool, BitString<4>] Query() {
                BitString<8> z = 0b00000000;
                BitString<4> w = z[0 : 4];
                BitString<8> z <- BitString<8>;
                BitString<4> a = z[0 : 4];
                return [a == w, w];
            }
        }
        """)
    assert not _engine().check_equivalent(real, random).valid


def test_f035_split_still_fires_no_redeclaration() -> None:
    """Positive control: a single declaration of the sampled name (no
    redeclaration hazard). The split fires, so the game equals its
    explicitly-split twin -- the redeclaration guard must not block this."""
    real = frog_parser.parse_game("""
        Game Real() {
            [BitString<4>, BitString<4>] Query() {
                BitString<8> z <- BitString<8>;
                BitString<4> a = z[0 : 4];
                BitString<4> b = z[4 : 8];
                return [a, b];
            }
        }
        """)
    split = frog_parser.parse_game("""
        Game Split() {
            [BitString<4>, BitString<4>] Query() {
                BitString<4> a <- BitString<4>;
                BitString<4> b <- BitString<4>;
                return [a, b];
            }
        }
        """)
    assert _engine().check_equivalent(real, split).valid
