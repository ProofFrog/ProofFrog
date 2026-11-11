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
    ("F-101", "AttackA4.proof", "type_error", "DeadGuardedAssignmentElimination",
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
    ("F-202", "attack3.proof", "reject", "DeduplicateDeterministicCalls",
     "F.Eval(F.Gen()) twice was merged, sharing one draw of the nested Gen"),
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
    ("F-232", "attack2.proof", "reject", "ExtractRepeatedTupleAccess",
     "a repeated slice was hoisted out of the branch binding its bound j"),
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
    ("F-303", "attack_1.proof", "reject", "TopologicalSort",
     "a return was hoisted above a draw whose domain may be empty"),
    ("F-303", "type_draw_control.proof", "accept", "TopologicalSort",
     "positive control: dead draws from non-empty domains are still dropped"),
    ("F-305", "attack_3.proof", "reject", "TopologicalSort",
     "a draw from an empty domain over a local set was pruned as dead code"),
    ("F-305", "void_probe.proof", "reject", "TopologicalSort",
     "the same draw in a Void oracle, which has no return to pin it"),
    ("F-305", "type_draw_control.proof", "accept", "TopologicalSort",
     "positive control for the attacks above"),
    ("F-308", "attack_4.proof", "reject", "DeadNullGuardElimination",
     "a local reused across oracles hid a nullable type; a live guard was dropped"),
    ("F-318", "attack_1.proof", "reject", "RemoveUnnecessaryFields",
     "a draw whose domain may be empty was deleted because its result was unused"),
    ("F-318", "type_draw_control.proof", "accept", "RemoveUnnecessaryFields",
     "positive control for the attack above"),
    ("F-323", "attack_c2.proof", "reject", "ExpandTuple",
     "a reserved-prefix shadow let element writes reach shadowed field components"),
    ("F-323", "attack_c2_control.proof", "accept", "ExpandTuple",
     "positive control for the attack above"),
    ("F-327", "attack_1.proof", "reject", "StabilizeIndependentStatements",
     "a draw whose domain may be empty was moved across an if that returns"),
    ("F-327", "used_draw.proof", "reject", "StabilizeIndependentStatements",
     "the same move with the draw's result used after the if"),
    ("F-327", "type_draw_control.proof", "accept", "StabilizeIndependentStatements",
     "positive control: a draw from a type still moves across the if"),
    ("F-356", "cmp_local.proof", "reject", "RedundantCopy",
     "ModInt<q> x = b (b an Int) holds b mod q, but x was read as b"),
    ("F-356", "cmp_field.proof", "reject", "InlineSingleUseField",
     "a ModInt field assigned an Int was read as the Int in another method"),
    ("F-356", "reassign.proof", "reject", "CollapseAssignment, RedundantCopy",
     "x = b into a declared ModInt local was read as b"),
    ("F-356", "tuple_literal.proof", "reject", "InlineLocalTupleLiteral",
     "[b, b] stored into a [ModInt<q>, Int] slot was read back unreduced"),
    ("F-356", "inline_arg.proof", "reject", "method inliner",
     "an Int argument was substituted for a ModInt parameter"),
    ("F-356", "inline_return.proof", "reject", "method inliner",
     "a call returning ModInt was replaced by the returned Int expression"),
    ("F-356", "exact_store_control.proof", "accept", "RedundantCopy",
     "positive control: a ModInt stored into a ModInt local is still forwarded"),
    ("F-356", "kept_arg_control.proof", "accept", "method inliner",
     "positive control: the kept parameter conversion matches one written out"),
    ("F-356", "kept_return_control.proof", "accept", "method inliner",
     "positive control: the kept return conversion matches one written out"),
    ("F-356", "field_init.proof", "reject", "instantiation",
     "a ModInt<q> field initialized with the Int q was read as q"),
    ("F-356", "field_init_int_compare.proof", "type_error", "instantiation",
     "in a proof, a ModInt<q> field with an Int initializer was typed Int"),
    ("F-356", "scheme_field_init.proof", "type_error", "instantiation",
     "a scheme's ModInt<q> field initialized with the Int q was read as q"),
    ("F-356", "field_init_typed_control.proof", "accept", "instantiation",
     "positive control: an initializer of the field's type is still read"),
    ("F-356", "field_init_literal.proof", "reject", "instantiation",
     "a ModInt<2> field initialized with the literal 1 was read as the Int 1"),
    ("F-356", "field_init_zero.proof", "type_error", "instantiation",
     "in a proof, a ModInt<2> field initialized with 0 was typed Int"),
    ("F-356", "scheme_field_literal.proof", "type_error", "instantiation",
     "a scheme's ModInt<2> field initialized with the literal 1 was read as 1"),
    ("F-356", "scheme_field_typed_control.proof", "accept", "instantiation",
     "positive control: a scheme field initializer of its type is still read"),
    ("F-361", "collateral_poison_powpow.proof", "type_error",
     "GroupElemSimplification",
     "a let GroupElem<G> t retyped the game's field t in H; (t^x)^y was folded"),
    ("F-361", "attack_N5.proof", "type_error", "group-exponent folds",
     "lets Int x, y retyped ModInt<q> fields; g^(x+y)/g^y was folded to g^x"),
    ("F-361", "shadowed_powpow_control.proof", "accept",
     "GroupElemSimplification",
     "positive control: a field in G still folds next to a let t in H"),
    ("F-361", "step_assumption_control.proof", "accept", "ApplyAssumptions",
     "positive control: a step assumption follows the rename of a field named like a let"),
    ("F-362", "control_E_noguard.proof", "reject", "instantiation",
     "a game field n captured the let n carried into the game by inlined S.Get()"),
    ("F-362", "collision_control.proof", "accept", "instantiation",
     "positive control: a field named like the let keeps its own reads"),
    ("F-363", "attack_dedup_nondet_arg.proof", "reject",
     "DeduplicateDeterministicCalls",
     "R.Det(R.Draw()) twice was merged although each call draws its argument"),
    ("F-363", "control_dedup_det_arg.proof", "accept",
     "DeduplicateDeterministicCalls",
     "positive control: equal calls on a parameter argument are still merged"),
    ("F-363", "control_dedup_let_function_arg.proof", "accept",
     "DeduplicateDeterministicCalls",
     "positive control: an argument calling a let: Function is deterministic"),
    ("F-364", "power_of_zero_sum.proof", "reject", "ModIntSimplification",
     "x ^ 0 became the Int 1, so x^0 + x^0 == x - x folded to the false 2 == 0"),
    ("F-364", "zero_subterm.proof", "reject", "ModIntSimplification",
     "next to a zero sub-term, (0 + 1) + 1 == 0 still folded to 2 == 0"),
    ("F-364", "modulus_one.proof", "reject", "ModIntSimplification",
     "x ^ 0 became the Int 1, but in ModInt<1> the one is 0: 1 == 0 was false"),
    ("F-364", "zero_base.proof", "reject", "ModIntSimplification",
     "(x - x) ^ 0 became the Int 0 ^ 0, which Symbolic Computation folded to 1"),
    ("F-364", "power_of_zero_control.proof", "accept", "ModIntSimplification",
     "positive control: x^0 * y, and x ^ 0 returned or stored as ModInt<q>"),
    ("F-365", "untranslated_comparison.proof", "reject", "Z3 residual check",
     "an opaque ModInt comparison met a Bool literal; Z3 raised and the proof aborted"),
    ("F-365", "int_returned_as_modint.proof", "reject", "Z3 residual check",
     "a Z3 integer met an opaque ModInt value; Z3 raised and the proof aborted"),
    ("F-371", "dup.proof", "reject", "method inliner",
     "an argument that draws, read twice by the callee, was drawn twice"),
    ("F-371", "dropped_arg.proof", "reject", "method inliner",
     "an argument whose draw may not complete was dropped as never read"),
    ("F-371", "pure_arg_control.proof", "accept", "method inliner",
     "positive control: an argument without calls is still substituted"),
    ("F-371", "det_call_arg_control.proof", "accept", "method inliner",
     "positive control: a bound deterministic call read twice is forwarded"),
    ("F-371", "single_read_control.proof", "accept", "method inliner",
     "positive control: a bound draw read once is forwarded into its read"),
    ("F-371", "unread_draw_control.proof", "accept", "method inliner",
     "positive control: an unread bound draw from a type is removed"),
    ("F-373", "param_write.proof", "reject", "method inliner",
     "a callee's x = 0^n; on its parameter assigned the caller's variable"),
    ("F-373", "param_element_write.proof", "reject", "method inliner",
     "a callee's X[k] = 0^n; on its Map parameter wrote the caller's map"),
    ("F-373", "sample_write.proof", "reject", "method inliner",
     "a callee's draw into its parameter overwrote the caller's variable"),
    ("F-373", "uniq_insert.proof", "reject", "method inliner",
     "a callee's <-uniq[S] draw inserted into the caller's set"),
    ("F-373", "tuple_element_write.proof", "reject", "method inliner",
     "a callee's A[0] = 0^n; on its tuple parameter wrote the caller's tuple"),
    ("F-373", "challenger_write.proof", "reject", "method inliner",
     "a challenger oracle's write to its parameter assigned the reduction's"
     " variable"),
    ("F-373", "param_write_control.proof", "accept", "method inliner",
     "positive control: the caller reads the written parameter's returned value"),
    ("F-373", "expr_arg_control.proof", "accept", "method inliner",
     "an expression argument was substituted into the callee's write"),
    ("F-374", "param_store.proof", "reject", "instantiation",
     "an Int argument for a ModInt<q> game parameter was read unreduced"),
    ("F-374", "param_literal.proof", "reject", "instantiation",
     "an Int literal argument for a ModInt<2> game parameter was read as an Int"),
    ("F-374", "scheme_param_store.proof", "type_error", "instantiation",
     "an Int argument for a ModInt<q> scheme parameter was read unreduced"),
    ("F-374", "param_store_control.proof", "accept", "instantiation",
     "positive control: a converting game parameter is kept as a field"),
    ("F-375", "lit_local.proof", "reject", "InlineMultiUsePureExpression",
     "a ModInt<2> local holding the literal 1 was forwarded as the Int 1"),
    ("F-375", "zero_local.proof", "reject", "InlineMultiUsePureExpression",
     "a ModInt<q> local holding the literal 0 was forwarded as the Int 0"),
    ("F-375", "literal_store_control.proof", "accept",
     "InlineMultiUsePureExpression",
     "positive control: a local of its value's ModInt type is still forwarded"),
    ("F-376", "crash_neg_distinct.proof", "reject", "ApplyAssumptions",
     "the Int negation -n was handed to the solver, which aborted the proof"),
    ("F-376", "crash_neg_control.proof", "accept", "ApplyAssumptions",
     "a true hop next to a step assumption aborted on the Int negation -n"),
    ("F-377", "zero_over_zero.proof", "reject", "SymbolicComputation",
     "0 / 0 was folded with Python floor division, which aborted the proof"),
    ("F-377", "int_division_condition.proof", "type_error", "Z3FormulaVisitor",
     "0 / 0 in an if condition was divided with Python true division"),
    ("F-377", "modint_int_division.proof", "type_error", "ModIntSimplification",
     "a ModInt division of zeros became the Int 0 / 0 of the other game"),
    ("F-377", "division_by_zero_control.proof", "type_error", "SymbolicComputation",
     "true equivalences around division by zero aborted the proof"),
    ("F-377", "modint_division_by_zero_control.proof", "accept",
     "SymbolicComputation",
     "positive control: the equivalences above with ModInt<q> division"),
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
    ("ARITH-PRECEDENCE", "same_level_control.proof", "type_error", "parser",
     "positive control: + with -, and * with /, share left-associative levels"),
    ("ARITH-PRECEDENCE", "same_level_modint_control.proof", "accept", "parser",
     "positive control: the levels above, with * and / on ModInt<q>"),
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
    ("RF-ALIAS-CALL", "local_alias.proof", "reject", "FreshInputRFToUniform",
     "a query through a local copy K = H was not seen as a query to H"),
    ("RF-ALIAS-CALL", "field_alias.proof", "reject", "FreshInputRFToUniform",
     "a query through a field copy of H was not seen as a query to H"),
    ("RF-ALIAS-CALL", "returned_function.proof", "reject",
     "FreshInputRFToUniform",
     "an oracle returned H itself, so the adversary could evaluate it"),
    ("RF-ALIAS-CALL", "direct_calls.proof", "accept", "UniqueRFSimplification",
     "positive control: H sampled once and only called directly"),
    ("RF-REASSIGNED", "reset_param.proof", "reject", "UniqueRFSimplification",
     "an oracle replaced H by an adversary-chosen function"),
    ("RF-REASSIGNED", "reset_field.proof", "reject", "UniqueRFSimplification",
     "an oracle replaced H by another random function the adversary queries"),
    ("RF-REASSIGNED", "init_reassign.proof", "reject", "UniqueRFSimplification",
     "Initialize overwrote H after sampling it"),
    ("RF-REASSIGNED", "init_challenge.proof", "reject",
     "ChallengeExclusionRFToUniform",
     "Initialize overwrote H before evaluating it at the challenge point"),
    ("RF-REASSIGNED", "reset_other.proof", "accept", "UniqueRFSimplification",
     "positive control: the oracle writes another Function field, not H"),
    ("RF-UNANALYZED-CALL", "else_if_call.proof", "reject",
     "UniqueRFSimplification",
     "an H query in an else-if condition was not checked against the draws"),
    ("RF-UNANALYZED-CALL", "else_if_other.proof", "accept",
     "UniqueRFSimplification",
     "positive control: the else-if condition queries another function"),
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
    ("REDUCTION-WRITTEN-FIELD", "reduction_counter_control.proof", "accept",
     "instantiation",
     "a reduction field its method writes was read as its initializer"),
    ("SAMPLE-COMPONENTS", "optional_component.proof", "type_error",
     "type checker", "a product draw with an optional component was accepted"),
    ("SAMPLE-COMPONENTS", "int_component.proof", "type_error", "type checker",
     "a product draw with an Int component was accepted"),
    ("SAMPLE-COMPONENTS", "finite_components_control.proof", "accept",
     "type checker", "positive control: a product of finite types is drawn"),
    ("F-367", "written_field_length.proof", "type_error", "type checker",
     "a type length named a field an oracle writes"),
    ("F-367", "written_local_length.proof", "type_error", "type checker",
     "a literal length named a local written after its declaration"),
    ("F-367", "constant_length_control.proof", "accept", "type checker",
     "positive control: lengths naming never-written variables"),
    ("F-366", "reserved_name.proof", "type_error", "type checker",
     "a user-written __a7__ name survived alpha renaming as a fresh name"),
    ("F-366", "parameter_shadowing.proof", "type_error", "type checker",
     "a local shadowed a method parameter"),
    ("F-366", "distinct_names_control.proof", "accept", "type checker",
     "positive control: locals that do not reuse a parameter's name"),
    ("EXPONENT-MODULUS", "other_modulus.proof", "type_error", "type checker",
     "a group exponent of type ModInt<q> was read modulo the group order"),
    ("EXPONENT-MODULUS", "other_group.proof", "type_error", "type checker",
     "a scalar of another group was used as an exponent"),
    ("EXPONENT-MODULUS", "order_exponents_control.proof", "accept",
     "type checker", "positive control: ModInt<G.order> and Int exponents"),
    ("INT-DIVISION", "int_division.proof", "type_error", "type checker",
     "division on Int, which the numeric back ends read three ways"),
    ("INT-DIVISION", "modint_division_control.proof", "accept",
     "type checker", "positive control: division on ModInt<q>"),
]
# fmt: on

# (finding, proof file) -> the error a type_error case must fail with.
TYPE_ERROR = {
    ("F-356", "field_init_int_compare.proof"): (
        "error: Cannot compare different types ModInt<q> and Int"
    ),
    ("F-356", "scheme_field_init.proof"): (
        "error: Cannot instantiate ModField: its field 'f' stores its "
        "initializer q in type ModInt<q>"
    ),
    ("F-356", "field_init_zero.proof"): (
        "error: Can not use operator - with types ModInt<2> and Int"
    ),
    ("F-356", "scheme_field_literal.proof"): (
        "error: Cannot instantiate LiteralModField: its field 'f' stores its "
        "initializer 1 in type ModInt<2>"
    ),
    ("F-374", "scheme_param_store.proof"): (
        "error: Cannot instantiate ParamModTest: its parameter 'x' of type "
        "ModInt<q> is given q (of type Int)"
    ),
    ("GAME-SELF-CALL", "self_call.proof"): (
        "error: Game 'Calls' may not call its own method 'Inc'"
    ),
    ("GAME-SELF-CALL", "reduction_self_call.proof"): (
        "error: Reduction 'R' may not call its own method 'Inc'"
    ),
    ("MEMBER-ASSIGN", "keys_write.proof"): (
        "error: Cannot assign to 'M.keys': 'M.keys' is a member access"
    ),
    ("SAMPLE-COMPONENTS", "optional_component.proof"): (
        "error: Cannot sample from [BitString<n>?, BitString<n>]: its component"
        " BitString<n>? has no uniform distribution"
    ),
    ("SAMPLE-COMPONENTS", "int_component.proof"): (
        "error: Cannot sample from [Int, BitString<n>]: its component Int has"
        " no uniform distribution"
    ),
    ("F-367", "written_field_length.proof"): (
        "error: The size in BitString<m> names field 'm', which is assigned or"
        " sampled"
    ),
    ("F-367", "written_local_length.proof"): (
        "error: The size in 0^k names local 'k', which is assigned or sampled"
    ),
    ("F-366", "reserved_name.proof"): (
        "error: '__a7__' is reserved: identifiers of the form __a<N>__ are the"
        " engine's fresh names"
    ),
    ("F-366", "parameter_shadowing.proof"): (
        "error: Local 'x' shadows the parameter 'x' of method F"
    ),
    ("EXPONENT-MODULUS", "other_modulus.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("EXPONENT-MODULUS", "other_group.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<H.order>"
    ),
    ("INT-DIVISION", "int_division.proof"): ("error: Cannot use operator / on Int"),
    ("F-101", "AttackA4.proof"): (
        "error: Local 'x' shadows the parameter 'x' of method O"
    ),
    ("F-361", "collateral_poison_powpow.proof"): (
        "error: Exponent of a GroupElem<H> must have type Int or"
        " ModInt<H.order>, got ModInt<G.order>"
    ),
    ("F-361", "attack_N5.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-377", "int_division_condition.proof"): ("error: Cannot use operator / on Int"),
    ("F-377", "modint_int_division.proof"): ("error: Cannot use operator / on Int"),
    ("F-377", "division_by_zero_control.proof"): (
        "error: Cannot use operator / on Int"
    ),
    ("ARITH-PRECEDENCE", "same_level_control.proof"): (
        "error: Cannot use operator / on Int"
    ),
}

# (finding, proof file) -> the hop a reject case must fail at. Every other
# hop in these proofs is true and must still pass.
FAILED_STEP = {
    ("F-373", "challenger_write.proof"): (
        "Step 1 failed: Probe(n).Left -> Echo(n).Left compose R(n)"
    ),
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
