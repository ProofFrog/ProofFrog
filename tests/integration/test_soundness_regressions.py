"""End-to-end regression proofs for fixed engine soundness and completeness bugs.

Each case is a small proof from the soundness audit, run through ``prove``.
A ``reject`` proof claims two distinguishable games are interchangeable: it
used to print ``Proof Succeeded!`` and must now be refused. An ``accept``
proof is a true equivalence (or a positive control next to a reject proof)
that the engine used to reject, crash on, or loop on, and must now verify.

Each finding's proof and the files it imports live in
``soundness_regression_fixtures/F_<nnn>/``, copied from the audit's attack
artifacts. Findings whose fix already came with a targeted unit or
integration test are not repeated here; this module covers the ones that
had no public test. Every future soundness fix should add its attack proof
(and a positive control where one exists) to this table or pin a
dedicated test of its own.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "soundness_regression_fixtures"

# (finding, proof file, expected verdict, pass, defect fixed)
CASES = [
    ("F-062", "a2_probe.proof", "reject", "MergeProductSamples",
     "single-use scan blind to binders across a duplicate re-declaration"),
    ("F-101", "AttackA4.proof", "reject", "DeadGuardedAssignmentElimination",
     "a shadowed inner variable entailed a guard about the outer one"),
    ("F-152", "atk1b.proof", "reject", "InlineLocalTupleLiteral",
     "a tuple-element write v[k] = e was missed, so a stale literal was inlined"),
    ("F-153", "atk2.proof", "reject", "InlineLocalTupleLiteral",
     "an element or map write between declaration and use was invisible"),
    ("F-155", "atk4.proof", "reject", "InlineLocalTupleLiteral",
     "the read set ignored field-access bases such as M in |M.keys|"),
    ("F-166", "A2_sep.proof", "reject", "HoistFieldPureAlias",
     "nested, slice or field writes to the aliased field were missed"),
    ("F-168", "A4_sep.proof", "reject", "HoistFieldPureAlias",
     "the stability check ignored field-access bases; M[7] = 1 went unchecked"),
    ("F-176", "attack3.proof", "reject", "CrossMethodFieldAlias",
     "a nested field mutation was missed across methods"),
    ("F-185", "atk2.proof", "reject", "ForwardExpressionAlias",
     "element, slice and field writes were missed on one rewrite path"),
    ("F-189", "init_drop.proof", "reject", "SplitOpaqueTupleField",
     "split per-index fields dropped the field's initializer"),
    ("F-199", "A3.proof", "accept", "RedundantFieldCopy",
     "a declaration after the copy made the reconstruction diverge"),
    ("F-203", "attack4.proof", "reject", "DeduplicateDeterministicCalls",
     "a nested element write between the two deduplicated calls was missed"),
    ("F-204", "attack5.proof", "reject", "DeduplicateDeterministicCalls",
     "the read set ignored field-access bases such as M in |M.keys|"),
    ("F-207", "attack_a2.proof", "reject", "HoistDuplicateBranchCall",
     "only bare-variable writes to the hoist target were detected"),
    ("F-209", "attack_a4.proof", "reject", "HoistDuplicateBranchCall",
     "the read set ignored field-access bases such as M in |M.keys|"),
    ("F-223", "attack4.proof", "reject", "RefactorGroupElemFieldExp",
     "a non-deterministic exponent factor conflated independent draws"),
    ("F-227", "Atk1.proof", "reject", "HoistGroupExpToInitialize",
     "a hoisted expression's dependency on a field read was missed"),
    ("F-230", "Atk5.proof", "reject", "HoistGroupExpToInitialize",
     "a non-deterministic exponent was frozen to one draw"),
    ("F-233", "attack3.proof", "reject", "ExtractRepeatedTupleAccess",
     "an element write v[0] = e evaded the reassignment guard"),
    ("F-255", "attack5_typemap.proof", "accept", "ConcatEqualityDecompose",
     "a flat type map corrupted slice offsets (false rejection)"),
    ("F-255", "attack6_boolor.proof", "accept", "ConcatEqualityDecompose",
     "a flat type map confused Bool || with concatenation (false rejection)"),
    ("F-269", "attack3_poison.proof", "accept", "ModIntSimplification",
     "a flat type map rewrote a group element x^0 to 1 and crashed"),
    ("F-290", "attack3_reserved.proof", "reject", "UniformXorSimplification",
     "a reserved-prefix shadow survived renaming and consumed a loop element"),
    ("F-308", "attack_4.proof", "reject", "DeadNullGuardElimination",
     "a local reused across oracles hid a nullable type; a live guard was dropped"),
    ("F-323", "attack_c2.proof", "reject", "ExpandTuple",
     "a reserved-prefix shadow let element writes reach shadowed field components"),
    ("F-323", "attack_c2_control.proof", "accept", "ExpandTuple",
     "positive control for the attack above"),
]


@pytest.mark.parametrize(
    "finding, proof, expected, transform, defect",
    CASES,
    ids=[f"{c[0]}-{c[1].removesuffix('.proof')}" for c in CASES],
)
def test_regression_proof(
    finding: str, proof: str, expected: str, transform: str, defect: str
) -> None:
    path = FIXTURES / finding.replace("-", "_") / proof
    result = subprocess.run(
        [sys.executable, "-m", "proof_frog", "prove", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    context = f"{finding} ({transform}: {defect})\n{output}"
    if expected == "accept":
        assert result.returncode == 0, context
        assert "Proof Succeeded!" in output, context
    else:
        assert result.returncode != 0, context
        assert "Proof Failed!" in output, context
        # A crash also exits non-zero; only a refused hop counts.
        assert "Traceback" not in output, context


def test_every_fixture_directory_is_exercised() -> None:
    """A fixture directory with no table entry would silently test nothing."""
    listed = {finding.replace("-", "_") for finding, *_ in CASES}
    on_disk = {p.name for p in FIXTURES.glob("F_*") if p.is_dir()}
    assert on_disk == listed
