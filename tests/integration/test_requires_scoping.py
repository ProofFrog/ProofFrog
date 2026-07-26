"""F-333: scheme ``requires A == B`` equality licenses are scoped to the
theorem's dependency cone.

A never-composed decoy scheme instantiated only in the ``let:`` block used
to inject an equality license (``Y == Z`` over two independent opaque
proof parameters) into a single global pool, which then rewrote the
sampling domain of an UNRELATED theorem game -- silently narrowing an
unconditional theorem to the diagonal and false-accepting a hop between
games distinguishable with advantage 1/2.

`_extract_subsets_pairs` now honors a scheme's ``requires`` only when the
scheme is reachable from the theorem / games sequence / helpers (see
`_theorem_dependency_cone`). The decoy is referenced nowhere but ``let:``,
so its license no longer applies and the false hop is rejected -- while a
scheme the theorem actually composes (e.g. KEMPRF, whose
``requires K.SharedSecret == BitString<F.lambda>`` is a legitimate
hypothesis of the scheme under test) is unaffected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

_TRIVIAL_PRIMITIVE = """
Primitive Trivial(Set A0, Set B0) {
    Set TA = A0;
    Set TB = B0;
    Bool Noop();
}
"""

_DECOY_SCHEME = """
import 'trivial.primitive';

Scheme DummyYZ(Set A0, Set B0) extends Trivial {
    requires A0 == B0;

    Set TA = A0;
    Set TB = B0;

    Bool Noop() {
        return true;
    }
}
"""

# Real draws twice from Y and reports a collision (prob 1/|Y|); Random draws
# from Z (prob 1/|Z|). Distinguishable with advantage 1/2 at |Y|=1, |Z|=2.
_ATTACK_GAME = """
Game Real(Set Y, Set Z) {
    Bool Get() {
        Y y1 <- Y;
        Y y2 <- Y;
        return y1 == y2;
    }
}

Game Random(Set Y, Set Z) {
    Bool Get() {
        Z z1 <- Z;
        Z z2 <- Z;
        return z1 == z2;
    }
}

export as AttackYZ;
"""

# The decoy DummyYZ(Y, Z) is instantiated but NEVER composed into AttackYZ.
_DECOY_PROOF = """
import 'trivial.primitive';
import 'dummy_yz.scheme';
import 'attack_yz.game';

proof:

let:
    Set Y;
    Set Z;
    DummyYZ D = DummyYZ(Y, Z);

theorem:
    AttackYZ(Y, Z);

games:
    AttackYZ(Y, Z).Real against AttackYZ(Y, Z).Adversary;
    AttackYZ(Y, Z).Random against AttackYZ(Y, Z).Adversary;
"""


def _prove(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_decoy_scheme_requires_license_does_not_leak(tmp_path: Path) -> None:
    (tmp_path / "trivial.primitive").write_text(_TRIVIAL_PRIMITIVE)
    (tmp_path / "dummy_yz.scheme").write_text(_DECOY_SCHEME)
    (tmp_path / "attack_yz.game").write_text(_ATTACK_GAME)
    proof = tmp_path / "attack_yz.proof"
    proof.write_text(_DECOY_PROOF)

    result = _prove(proof)
    # The unconditional theorem AttackYZ(Y, Z) must NOT be narrowed to Y == Z
    # by a decoy scheme's requires clause: the hop is rejected.
    assert result.returncode != 0, result.stdout
    assert "Proof Failed" in result.stdout, result.stdout


def test_requires_in_theorem_cone_still_honored() -> None:
    # Positive control: KEMPRF is the scheme under test, so its
    # `requires K.SharedSecret == BitString<F.lambda>` is legitimately
    # honored and the proof succeeds. (Also exercised by the full corpus in
    # tests/integration/test_proofs.py; asserted here as F-333's paired
    # in-cone control.)
    kemprf = REPO_ROOT / "examples/Proofs/KEM/KEMPRF_INDCPA.proof"
    if not kemprf.exists():
        import pytest

        pytest.skip("examples submodule not checked out")
    result = _prove(kemprf)
    assert result.returncode == 0, result.stdout
    assert "Proof Succeeded" in result.stdout, result.stdout
