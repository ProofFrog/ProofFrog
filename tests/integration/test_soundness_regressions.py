"""End-to-end regression proofs for fixed engine soundness and completeness bugs.

Each case is a small proof from the soundness audit, run through ``prove``.
A ``reject`` proof claims two distinguishable games are interchangeable: it
used to print ``Proof Succeeded!`` and must now be refused. An ``accept``
proof is a true equivalence (or a positive control next to a reject proof)
that the engine used to reject, crash on, or loop on, and must now verify.
A ``reject-bound`` proof verifies but claims a ``bound:`` that is not an
upper bound on what it establishes: the claim used to be reported verified
and must now be reported ``NOT verified``, failing ``prove``.
A ``type_error`` proof uses a construct the type checker now refuses
because the engine mishandled it: the proof used to print
``Proof Succeeded!`` and must now fail type checking with the message
listed for it in ``TYPE_ERROR``.

Each finding's proof and the files it imports live in
``soundness_regression_fixtures/F_<nnn>/``, copied from the audit's attack
artifacts. A bug found outside the audit has a descriptive ID instead, with
its fixtures in the matching directory (``Z3-FIELD-ACCESS`` in
``Z3_FIELD_ACCESS/``). A reject case listed in ``FAILED_STEP`` must fail at
that step, so an earlier, true hop cannot fail in its place. Findings whose fix already came with a targeted unit or
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

# fmt: off
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
    ("F-177", "read_before_write.proof", "reject", "CrossMethodFieldAlias",
     "a local read before its one write was expanded through the later RHS"),
    ("F-177", "read_after_write_control.proof", "accept",
     "CrossMethodFieldAlias", "positive control for the attack above"),
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
    ("MEMBER-READ-IF-CONDITION-ALIAS", "stale_definition.proof", "reject",
     "IfConditionAliasSubstitution",
     "a field read only via M.keys escaped the Initialize-only check"),
    ("MEMBER-READ-IF-CONDITION-ALIAS", "stable_definition.proof", "accept",
     "IfConditionAliasSubstitution", "positive control for the attack above"),
    ("MEMBER-READ-INJECTIVE-EQUALITY", "stale_local.proof", "reject",
     "InjectiveEqualitySimplify",
     "a local's call read M only via M.keys; M[y] = true went unchecked"),
    ("MEMBER-READ-INJECTIVE-EQUALITY", "stale_field.proof", "reject",
     "InjectiveEqualitySimplify",
     "a field's definition read M only via M.keys; M[y] = true went unchecked"),
    ("MEMBER-READ-INJECTIVE-EQUALITY", "stable_reads.proof", "accept",
     "InjectiveEqualitySimplify", "positive control for the attacks above"),
    ("MEMBER-READ-CONCAT-EQUALITY", "stale_concat.proof", "reject",
     "ConcatEqualityDecompose",
     "a local's concat read M only via M.keys; M[y] = true went unchecked"),
    ("MEMBER-READ-CONCAT-EQUALITY", "stable_concat.proof", "accept",
     "ConcatEqualityDecompose", "positive control for the attack above"),
    ("ARITH-PRECEDENCE", "sum_reorder.proof", "reject", "SymbolicComputation",
     "+ bound tighter than -, so SymPy's a - b + 3 re-parsed as a - (b + 3)"),
    ("ARITH-PRECEDENCE", "same_level_control.proof", "accept", "parser",
     "positive control: + with -, and * with /, share left-associative levels"),
    ("ARITH-PRECEDENCE", "claimed_bound.proof", "reject-bound", "parser",
     "2 - 1 + 1 in a bound: clause read as 2 - (1 + 1), so a too-small claim passed"),
    ("FRESH-INPUT-DROPPED-DRAW", "dropped_size.proof", "reject",
     "FreshInputRFToUniform",
     "the rewrite dropped the draw and its insertion into an observable set"),
    ("FRESH-INPUT-DROPPED-DRAW", "dropped_member.proof", "reject",
     "FreshInputRFToUniform",
     "the rewrite dropped the draw, so a membership test lost the drawn point"),
    ("FRESH-INPUT-LATER-QUERY", "later_query.proof", "reject",
     "FreshInputRFToUniform",
     "an oracle query recorded by an insertion may run after the draw"),
    ("FRESH-INPUT-LATER-QUERY", "const_query.proof", "reject",
     "FreshInputRFToUniform",
     "an oracle query on a recorded constant may run after the draw"),
    ("FRESH-INPUT-LATER-QUERY", "tuple_query.proof", "reject",
     "FreshInputRFToUniform",
     "an oracle query recording a tuple component may run after the draw"),
    ("FRESH-INPUT-LATER-QUERY", "same_call.proof", "reject",
     "FreshInputRFToUniform",
     "a recorded query after the draw in the same call may hit the draw"),
    ("FRESH-INPUT-LATER-QUERY", "init_draw.proof", "reject",
     "FreshInputRFToUniform",
     "a draw in Initialize precedes every recorded oracle query"),
    ("FRESH-INPUT-LATER-QUERY", "init_first.proof", "accept",
     "FreshInputRFToUniform",
     "positive control: the recorded query is in Initialize, before the draw"),
    ("Z3-FIELD-ACCESS", "group_equality.proof", "reject", "Z3 residual check",
     "G.generator == G.identity encoded as G == G"),
    ("Z3-FIELD-ACCESS", "group_branch.proof", "reject", "RemoveUnreachable",
     "G.generator == G.identity encoded as G == G; the final return was deleted"),
    ("Z3-FIELD-ACCESS", "map_branch.proof", "reject", "RemoveUnreachable",
     "M.keys == M.values encoded as M == M; the final return was deleted"),
    ("DUP-FIELDS-MEMBER-READ", "member_read.proof", "reject", "RemoveDuplicateFields",
     "a write to M between two writes of A[|M.keys|] went unseen; f merged into g"),
    ("DUP-FIELDS-MEMBER-READ", "member_read_control.proof", "accept",
     "RemoveDuplicateFields", "positive control for the attack above"),
    ("GAME-SELF-CALL", "self_call.proof", "type_error", "TopologicalSort",
     "a game's call of its own oracle was dropped as side-effect free"),
    ("GAME-SELF-CALL", "reduction_self_call.proof", "type_error",
     "TopologicalSort",
     "a reduction's call of its own oracle was dropped as side-effect free"),
    ("GAME-SELF-CALL", "scheme_this_call_control.proof", "accept",
     "type checker", "positive control: a scheme still calls itself via this."),
    ("MEMBER-ASSIGN", "keys_write.proof", "type_error", "RemoveUnreachable",
     "M.keys = S was read as no write to M; a live branch was deleted"),
    ("MEMBER-ASSIGN", "element_write_control.proof", "accept", "type checker",
     "positive control: a map element write M[k] = v is still accepted"),
]
# fmt: on

# (finding, proof file) -> the error a type_error case must fail with.
TYPE_ERROR = {
    ("GAME-SELF-CALL", "self_call.proof"): (
        "error: Game 'Calls' may not call its own method 'Inc'"
    ),
    ("GAME-SELF-CALL", "reduction_self_call.proof"): (
        "error: Reduction 'R' may not call its own method 'Inc'"
    ),
    ("MEMBER-ASSIGN", "keys_write.proof"): (
        "error: Cannot assign to 'M.keys': 'M.keys' is a member access"
    ),
}

# (finding, proof file) -> the hop a reject case must fail at. In these
# proofs step 1 is a true equivalence that must still pass.
FAILED_STEP = {
    ("Z3-FIELD-ACCESS", "group_equality.proof"): (
        "Step 2 failed: Swapped(G) -> GroupEquality(G).Right"
    ),
    ("Z3-FIELD-ACCESS", "group_branch.proof"): (
        "Step 2 failed: Swapped(G) -> GroupBranch(G).Right"
    ),
    ("Z3-FIELD-ACCESS", "map_branch.proof"): (
        "Step 1 failed: MapBranch().Left -> MapBranch().Right"
    ),
}


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
    elif expected == "reject-bound":
        assert result.returncode != 0, context
        assert "Claimed bound NOT verified" in output, context
        assert "Traceback" not in output, context
    elif expected == "type_error":
        assert result.returncode != 0, context
        assert "Traceback" not in output, context
        assert TYPE_ERROR[(finding, proof)] in output, context
        assert "Proof Succeeded!" not in output, context
    else:
        assert result.returncode != 0, context
        assert "Proof Failed!" in output, context
        # A crash also exits non-zero; only a refused hop counts.
        assert "Traceback" not in output, context
        failed_step = FAILED_STEP.get((finding, proof))
        if failed_step is not None:
            assert failed_step in output, context
            assert "(1 step(s) failed:" in output, context


def test_every_fixture_directory_is_exercised() -> None:
    """A fixture directory with no table entry would silently test nothing."""
    listed = {finding.replace("-", "_") for finding, *_ in CASES}
    on_disk = {p.name for p in FIXTURES.iterdir() if p.is_dir()}
    assert on_disk == listed
