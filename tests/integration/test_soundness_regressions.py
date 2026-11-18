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
    ("F-002", "attack_d_kept_draw.proof", "reject", "FreshInputRFToUniform",
     "RF.domain was trusted to hold an oracle's plain queries of RF"),
    ("F-002", "control_all_fresh.proof", "accept", "FreshInputRFToUniform",
     "positive control: every query of RF is a <-uniq[RF.domain] draw"),
    ("F-002", "field_initializer_query.proof", "reject", "FreshInputRFToUniform",
     "a field initializer's queries of a let: random function were not seen"),
    ("F-002", "field_initializer_copy.proof", "reject", "FreshInputRFToUniform",
     "a field initializer's copy of a let: random function was not an escape"),
    ("F-002", "field_initializer_query_field_set.proof", "reject",
     "FreshInputRFToUniform",
     "the same field-initializer queries, with a field exclusion set"),
    ("F-031", "attack4.proof", "type_error", "type checker",
     "a scheme's writes to its own field were dropped as dead when inlined"),
    ("F-031", "scheme_state_capture.proof", "type_error", "type checker",
     "a written scheme field, left a bare name, was captured by a game field"),
    ("F-031", "scheme_field_grow.proof", "type_error", "type checker",
     "a written scheme field was read as its initializer after a write"),
    ("F-031", "scheme_state.proof", "type_error", "type checker",
     "a written scheme field, read and written by its bare name, was captured"),
    ("F-031", "scheme_const_control.proof", "accept", "type checker",
     "positive control: a scheme field no method writes is read as its value"),
    ("F-048", "J2.proof", "type_error", "MergeUniformSamples",
     "two draws were merged across a write to the local that is their length"),
    ("F-048", "merge_control.proof", "accept", "MergeUniformSamples",
     "positive control: draws whose length nothing writes are still merged"),
    ("F-062", "a2_probe.proof", "type_error", "MergeProductSamples",
     "single-use scan blind to binders across a duplicate re-declaration"),
    ("F-079", "attack5_element_count_blind.proof", "reject",
     "RemoveDuplicateFields",
     "a map copy read after an element write to its source was merged with it"),
    ("F-079", "control_no_write.proof", "accept", "RemoveDuplicateFields",
     "positive control: the same games without the element write"),
    ("F-101", "AttackA4.proof", "type_error", "DeadGuardedAssignmentElimination",
     "a shadowed inner variable entailed a guard about the outer one"),
    ("F-101", "attack_a4_local.proof", "type_error",
     "DeadGuardedAssignmentElimination",
     "a shadowing inner local entailed a guard about the outer local"),
    ("F-130", "alphacap.proof", "reject", "SimplifyIf",
     "branch locals were renamed to __alpha_1__, a let: entry a branch reads"),
    ("F-130", "alphacap_control.proof", "accept", "SimplifyIf",
     "positive control: branches alike up to their locals' names still merge"),
    ("F-149", "attack2a.proof", "reject", "InlineSingleUseVariable",
     "a write earlier in the branch holding the use was missed"),
    ("F-149", "loop_write.proof", "reject", "InlineSingleUseVariable",
     "a write in the loop body around the use was missed"),
    ("F-149", "inl3.proof", "reject", "InlineSingleUseVariable",
     "a ModInt product was inlined past writes to its factors in the branch"),
    ("F-149", "bare_inline.proof", "reject", "InlineSingleUseVariable",
     "the same, after a bare declaration is merged with its assignment"),
    ("F-149", "branch_control.proof", "accept", "InlineSingleUseVariable",
     "positive control: the branch writes another field before the use"),
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
    ("F-191", "field_init_read.proof", "reject", "SplitOpaqueTupleField",
     "a read of the split field in another field's initializer was left dangling"),
    ("F-191", "written_q.proof", "reject", "SplitOpaqueTupleField",
     "the same, with the dropped component the only difference between the games"),
    ("F-191", "written_q_control.proof", "accept", "SplitOpaqueTupleField",
     "positive control: a field starting from the split field's initial value"),
    ("F-199", "A3.proof", "type_error", "RedundantFieldCopy",
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
    ("F-290", "attack3_reserved.proof", "type_error", "UniformXorSimplification",
     "a reserved-prefix shadow survived renaming and consumed a loop element"),
    ("F-300", "attack_3.proof", "reject", "RemoveDuplicateFields",
     "an element write was skipped, so two maps it drives apart were merged"),
    ("F-300", "control.proof", "accept", "RemoveDuplicateFields",
     "positive control: a copy neither field's writes change is still merged"),
    ("F-301", "attack_4.proof", "reject", "RemoveDuplicateFields",
     "a <-uniq[S] insertion into S alone was skipped, so S was merged away"),
    ("F-302", "attack_5.proof", "reject", "RemoveDuplicateFields",
     "two fields with different initializers were merged"),
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
    ("F-326", "param_capture.proof", "reject", "StandardizeFieldNames",
     "the field rename rewrote a read of a same-named method parameter"),
    ("F-326", "param_target.proof", "reject", "StandardizeFieldNames",
     "a field read renamed to a method parameter's name read the parameter"),
    ("F-326", "param_renamed.proof", "reject", "StandardizeFieldNames",
     "the capture pair without the field that keeps the parameter's name"),
    ("F-326", "param_control.proof", "accept", "StandardizeFieldNames",
     "positive control: both oracles return their argument"),
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
    ("F-357", "exponent_constant.proof", "type_error", "ModIntCancellation",
     "a ModInt<q> exponent equal to the constant 2 was rebuilt as the Int 2"),
    ("F-357", "express_after_update.proof", "type_error", "ExpressAfterUpdate",
     "the moved value's ModInt<q> constant exponent was rebuilt as an Int"),
    ("F-357", "cancel_through_local.proof", "type_error", "CancelThroughLocal",
     "the substituted value's ModInt<q> constant exponent was rebuilt as an Int"),
    ("F-357", "zero_constant_control.proof", "type_error", "ModIntCancellation",
     "former positive control (a ModInt<q> zero cancels to 0); the type"
     " checker now refuses its ModInt<q> group exponent"),
    ("F-358", "stale_type.proof", "type_error", "BlockedLocalAbsorption",
     "a second round typed the re-declared local by the stale type map"),
    ("F-358", "stale_type_control.proof", "type_error", "BlockedLocalAbsorption",
     "former positive control (the Int re-declaring round fires); the type"
     " checker now refuses its ModInt<q> group exponent"),
    ("F-359", "gpfe_initializer.proof", "reject", "GeneratorPowerFieldToExponent",
     "another field's initializer kept naming the removed field, read as a let"),
    ("F-359", "gpfe_control.proof", "accept", "GeneratorPowerFieldToExponent",
     "positive control: no other field names the removed field; the pass fires"),
    ("F-359", "fusion_initializer.proof", "reject", "OffsetFusion",
     "another field's initializer kept naming the removed key, read as a let"),
    ("F-359", "fusion_control.proof", "accept", "OffsetFusion",
     "positive control: no other field names the removed key; the pass fires"),
    ("F-365", "untranslated_comparison.proof", "reject", "Z3 residual check",
     "an opaque ModInt comparison met a Bool literal; Z3 raised and the proof aborted"),
    ("F-365", "int_returned_as_modint.proof", "reject", "Z3 residual check",
     "a Z3 integer met an opaque ModInt value; Z3 raised and the proof aborted"),
    ("F-370", "coerced_literal_ring.proof", "reject",
     "ForwardLiteralFieldWrite",
     "the Int literal 1 forwarded for a ModInt<2> field holding 1 mod 2"),
    ("F-379", "zero_power_base.proof", "reject", "ForwardLiteralFieldWrite",
     "the Int literal 0 forwarded for a ModInt field into a power's base"),
    ("F-379", "zero_sum_power_base.proof", "reject",
     "ForwardLiteralFieldWrite",
     "the Int literal 0 forwarded for both reads of a ModInt sum, D + D"),
    ("F-379", "zero_offset_control.proof", "accept",
     "ForwardLiteralFieldWrite",
     "positive control: 0 still forwarded next to a ModInt operand of +"),
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
    ("F-372", "attack_and.proof", "reject", "method inliner",
     "a call in the right operand of && ran even when the left one was false"),
    ("F-372", "attack_or.proof", "reject", "method inliner",
     "a call in the right operand of || ran even when the left one was true"),
    ("F-372", "attack_elseif.proof", "reject", "method inliner",
     "a call in an else if condition ran even when an earlier one held"),
    ("F-372", "challenger_and_guarded.proof", "reject", "method inliner",
     "a challenger call in && was made on every trace; hop 3 is the false one"),
    ("F-372", "challenger_and.proof", "reject", "method inliner",
     "the same reduction against T, whose Left returns b after the if; hop 3"
     " is the false one"),
    ("F-372", "completeness_guarded_vs_and.proof", "accept", "method inliner",
     "b && P.Pick(S) is the guarded if (b) { return P.Pick(S); } return false;"),
    ("F-372", "control_no_effect.proof", "accept", "method inliner",
     "positive control: a call with no effect may still run on every trace"),
    ("F-372", "nested.proof", "reject", "method inliner",
     "the call in a && (b || f(x)) ran whenever a held, also when b did"),
    ("F-372", "nested_guarded_control.proof", "accept", "method inliner",
     "a && (b || P.Pick(S)) is its explicit short-circuit form"),
    ("F-372", "elseif_first.proof", "reject", "method inliner",
     "after an else if was split off, a call in the first condition's && ran"),
    ("F-372", "elseif_first_control.proof", "accept", "method inliner",
     "an if with a && site and an else if call is its explicit form"),
    ("F-372", "deferred_challenger.proof", "reject", "method inliner",
     "a && after a challenger call ran on every trace; hop 3 is the false one"),
    ("F-372", "init_and.proof", "type_error", "method inliner",
     "challenger.Initialize in the right operand of && ran on every trace"),
    ("F-372", "reorder.proof", "reject", "method inliner",
     "a hoisted && operand's challenger call ran before an earlier one"),
    ("F-372", "reorder_inc_first.proof", "reject", "method inliner",
     "the same, with Left in the order the reduction runs; hop 3 is false"),
    ("F-372", "reorder_control.proof", "accept", "method inliner",
     "positive control: the earlier challenger call stays ahead of the &&"),
    ("F-372", "bind_order_cond.proof", "reject", "method inliner",
     "a bound call jumped ahead of an earlier call before a hoisted &&"),
    ("F-372", "bind_order_cond_control.proof", "reject", "method inliner",
     "control: the earlier calls in statements of their own; hop 3 is false"),
    ("F-372", "bind_order_cond_true.proof", "accept", "method inliner",
     "positive control: both sides are the reduction as written"),
    ("F-372", "cond_name.proof", "reject", "method inliner",
     "a callee local named cond was declared under the && temporary's name"),
    ("F-372", "cond_name_control.proof", "accept", "method inliner",
     "positive control: the temporary and the callee's local stay apart"),
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
    ("F-378", "zero_power_base_var_exp.proof", "reject", "ModIntCancellation",
     "a ModInt zero power base was rebuilt as the Int 0, dropping the modulus"),
    ("F-378", "zero_operand_control.proof", "accept", "ModIntCancellation",
     "positive control: a ModInt zero under +, * and == still cancels to 0"),
    ("F-381", "bubble_dup.proof", "reject", "BubbleSortFieldAssignment",
     "the second of two equal statements got the first one's graph node"),
    ("F-381", "cancel_dup.proof", "reject", "BubbleSortFieldAssignment",
     "the same, once a ModInt cancellation makes the two statements equal"),
    ("F-381", "sort_past_dup.proof", "accept", "BubbleSortFieldAssignment",
     "positive control: an independent write still moves past equal statements"),
    ("F-382", "dup_order.proof", "reject", "RemoveDuplicateFields",
     "deleting a pair's second write also deleted an equal write elsewhere"),
    ("F-382", "exp_dup.proof", "reject", "RemoveDuplicateFields",
     "the same, once a group field is rewritten as an exponent field"),
    ("F-382", "same_order_control.proof", "accept", "RemoveDuplicateFields",
     "positive control: fields updated in the same order everywhere merge"),
    ("F-382", "opposite_order_control.proof", "accept", "RemoveDuplicateFields",
     "positive control: opposite orders merge, each method keeping one write"),
    ("F-383", "param_write.proof", "reject", "instantiation",
     "a game's write to its own parameter went to the argument and was dropped"),
    ("F-383", "map_write.proof", "reject", "instantiation",
     "an element write to a game's Map parameter wrote the caller's map"),
    ("F-383", "reduction_write.proof", "reject", "instantiation",
     "a reduction's write to its own parameter was dropped"),
    ("F-383", "scheme_write.proof", "type_error", "instantiation",
     "a scheme's write to its own parameter was dropped, each call starting over"),
    ("F-383", "copy_start.proof", "reject", "instantiation",
     "a field copying a written parameter's starting value must not follow it"),
    ("F-383", "copy_start_unread.proof", "reject", "RemoveUnnecessaryFields",
     "a field read only by another field's initializer must stay declared"),
    ("F-383", "field_control.proof", "accept", "instantiation",
     "positive control: a written parameter counts like an explicit field"),
    ("F-383", "shadow_local_control.proof", "accept", "instantiation",
     "positive control: a write to a shadowing local leaves the parameter alone"),
    ("F-384", "alias_redraw.proof", "reject", "instantiation",
     "a field copying another field's starting value followed its later draws"),
    ("F-384", "count_start.proof", "reject", "instantiation",
     "a field copying an initialized counter's start followed the count"),
    ("F-384", "call_once.proof", "reject", "instantiation",
     "a field initialized by one method call called it again at every read"),
    ("F-384", "challenger_initializer.proof", "reject", "instantiation",
     "a challenger field's initializer read a reduction field of the same name"),
    ("F-384", "copy_source.proof", "reject", "InlineSingleUseField",
     "a field read only by a kept initializer was dropped, the initializer dangling"),
    ("F-384", "written_copy.proof", "reject", "InlineSingleUseField",
     "a written field's initializer read a written field that was then dropped"),
    ("F-384", "parameter_copy.proof", "reject", "InlineSingleUseField",
     "a copy of a written parameter's start lost the parameter's field"),
    ("F-384", "reduction_copy_source.proof", "reject", "InlineSingleUseField",
     "copy_source in a reduction: its fields need the snapshot too"),
    ("F-384", "reduction_written_copy.proof", "reject", "InlineSingleUseField",
     "written_copy in a reduction: its fields need the snapshot too"),
    ("F-384", "scheme_reads_written.proof", "type_error", "instantiation",
     "a scheme field copying a written field's start cannot stay a field"),
    ("F-384", "scheme_method_call.proof", "type_error", "instantiation",
     "a scheme field initialized by a method call cannot stay a field"),
    ("F-384", "unwritten_control.proof", "accept", "instantiation",
     "positive control: a field copying an unwritten field is read as it"),
    ("F-384", "function_value_control.proof", "accept", "instantiation",
     "positive control: a field initialized by a Function call is read as it"),
    ("F-384", "start_value_control.proof", "accept", "instantiation",
     "positive control: a copy of a written field's start is read as that start"),
    ("F-384", "j1.proof", "reject", "instantiation",
     "a Function field copying RF before Initialize draws RF was read as RF"),
    ("F-384", "j2.proof", "reject", "instantiation",
     "a field copying a's start was read as a after Initialize overwrote a"),
    ("F-385", "dedup_loop.proof", "reject", "DeduplicateDeterministicCalls",
     "two calls in one loop were merged though the loop writes their argument"),
    ("F-385", "last_loop.proof", "reject", "DeduplicateDeterministicCalls",
     "a write after the last call, in the loop holding it, was missed"),
    ("F-385", "uniq_grow.proof", "reject", "DeduplicateDeterministicCalls",
     "a <-uniq[S] draw between the calls grew the S their argument reads"),
    ("F-385", "dedup_loop_control.proof", "accept",
     "DeduplicateDeterministicCalls",
     "positive control: the loop never writes the argument; the calls merge"),
    ("F-386", "nested.proof", "reject", "RefactorGroupElemFieldExp",
     "a redraw of the shared exponent inside an if between the fields was missed"),
    ("F-386", "nested_loop.proof", "reject", "RefactorGroupElemFieldExp",
     "a redraw of the shared exponent inside a loop between the fields was missed"),
    ("F-386", "nested_control.proof", "accept", "RefactorGroupElemFieldExp",
     "positive control: the branch between the fields writes another variable"),
    ("F-387", "a2s.proof", "reject", "FreshInputRFToUniform",
     "a let: primitive given H queried it out of sight (field exclusion set)"),
    ("F-387", "a2.proof", "reject", "FreshInputRFToUniform",
     "a let: primitive given H queried it out of sight (H.domain)"),
    ("F-387", "a2s_wrap.proof", "reject", "FreshInputRFToUniform",
     "the primitive holding H reached the game through a scheme"),
    ("F-387", "lffl.proof", "reject", "LocalFunctionFieldToLet",
     "a game's own random function was unified with a let H a primitive holds"),
    ("F-387", "a3.proof", "reject", "FreshInputRFToUniform",
     "a let: scheme given H queried it in its field initializers"),
    ("F-387", "a2s_control.proof", "accept", "FreshInputRFToUniform",
     "positive control: the let: primitive is not given H"),
    ("F-387", "lffl_control.proof", "accept", "LocalFunctionFieldToLet",
     "positive control: no primitive is given H; F is unified with H"),
    ("F-388", "v9.proof", "reject", "RemoveUnnecessaryFields",
     "a field read only by an initializer took its query of H with it"),
    ("F-388", "v9lf.proof", "reject", "LocalFunctionFieldToLet",
     "the same deletion hid H's query from Local Function Field To Let"),
    ("F-388", "dangle2.proof", "reject", "RemoveUnnecessaryFields",
     "a field read only by another field's initializer was deleted"),
    ("F-389", "a4.proof", "reject", "proof let: evaluation",
     "a let: entry calling a sampled function crashed prove"),
    ("F-389", "a4b.proof", "reject", "FreshInputRFToUniform",
     "the same values of H passed to the game directly"),
    ("F-389", "let_value_control.proof", "accept", "proof let: evaluation",
     "positive control: a let: entry H(0b0) is read as H's value at 0b0"),
    ("F-389", "letcall_draw.proof", "type_error", "proof let: evaluation",
     "a let: entry H(R.Draw()) would read as a fresh draw at every use"),
    ("F-389", "letcall_draw_via_value.proof", "type_error",
     "proof let: evaluation",
     "the same draw in a let: entry of its own, itself a fresh draw at each use"),
    ("F-389", "letcall_fixed_control.proof", "accept", "proof let: evaluation",
     "positive control: H(R.Fixed()), a deterministic argument, is a value"),
    ("F-389", "sr.proof", "reject", "FreshInputRFToUniform",
     "let: values H(0b0), H(0b1) handed to a scheme revealed H's queries"),
    ("F-389", "sr_control.proof", "accept", "FreshInputRFToUniform",
     "positive control: the scheme holds plain let: values, not H's"),
    ("F-390", "group_write.proof", "type_error", "structural rules",
     "a game wrote the group parameter its GroupElem<A> field's type names"),
    ("F-390", "group_swap.proof", "type_error", "structural rules",
     "the same, with the element recomputed after the write on one side"),
    ("F-390", "group_read_control.proof", "accept", "structural rules",
     "positive control: a group parameter read, never written"),
    ("F-391", "key_once.proof", "accept", "method inliner",
     "a field initializer calling a scheme method crashed prove"),
    ("F-391", "init_call.proof", "reject", "method inliner",
     "a reduction field initializer calling the challenger crashed prove"),
    ("F-391", "counter_once.proof", "accept", "method inliner",
     "positive control: that call is made once, before Initialize"),
    ("F-391", "counter_none.proof", "reject", "method inliner",
     "the same call against a counter never bumped"),
    ("F-391", "challenger_field_draw.proof", "reject", "method inliner",
     "a challenger field drawn by a scheme call under a reduction's Initialize"),
    ("F-391", "before_init.proof", "type_error", "challenger placement",
     "a reduction field initializer called the challenger before its Initialize"),
    ("F-391", "init_in_field.proof", "type_error", "challenger placement",
     "a reduction field initializer called challenger.Initialize"),
    ("F-392", "sq.proof", "accept", "SymbolicComputation",
     "k * k folded to SymPy's k**2, parsed back as FrogLang, crashed prove"),
    ("F-392", "sq_wrong.proof", "reject", "SymbolicComputation",
     "k * k against k + k crashed prove the same way"),
    ("F-392", "cat.proof", "accept", "type checker, MergeUniformSamples",
     "the length k * k + n of a concatenation was printed as k**2 + n"),
    ("F-392", "cat_wrong.proof", "reject", "type checker, MergeUniformSamples",
     "the same concatenation against one padded with zeros"),
    ("F-392", "split.proof", "accept", "type checker, SplitUniformSamples",
     "the length of the slice c[0 : k * k] was printed as k**2"),
    ("F-392", "split_wrong.proof", "reject", "type checker, SplitUniformSamples",
     "the same slice against a string of zeros"),
    ("F-393", "bf.proof", "accept", "RemoveUnreachable",
     "a let: Bool as an if condition crashed Remove Unreachable's Z3 call"),
    ("F-393", "bf_wrong.proof", "reject", "RemoveUnreachable",
     "a let: Bool branch against a constant crashed prove the same way"),
    ("F-393", "bf_twice_control.proof", "accept", "RemoveUnreachable",
     "positive control: a repeated test of the let: Bool is still dead"),
    ("F-394", "injective_param_write.proof", "reject", "InjectiveEqualitySimplify",
     "v = F.Enc(k) was read after the oracle wrote its own parameter k"),
    ("F-394", "injective_param_write_control.proof", "accept",
     "InjectiveEqualitySimplify",
     "positive control: the oracle never writes k, so v still encodes it"),
    ("F-394", "concat_param_write.proof", "reject", "ConcatEqualityDecompose",
     "v = a || b was decomposed after the oracle wrote its own parameter a"),
    ("F-394", "concat_param_write_control.proof", "accept",
     "ConcatEqualityDecompose",
     "positive control: the oracle never writes a, so v still holds a || b"),
    ("F-395", "letdraw.proof", "type_error", "proof let: evaluation",
     "a let: entry R.Draw() was read as a fresh draw at every use"),
    ("F-395", "letcall_xor.proof", "type_error", "proof let: evaluation",
     "a draw nested in a let: value H(R.Draw()) + 0^m, read anew at every use"),
    ("F-395", "letfixed_control.proof", "accept", "proof let: evaluation",
     "positive control: a let: entry R.Fixed() calls a deterministic method"),
    ("F-397", "read_then_inc.proof", "reject", "method inliner",
     "a returned field read was evaluated after a later call's write to it"),
    ("F-397", "read_then_inc_plus_zero.proof", "reject", "method inliner",
     "the same, with Left as the reduction computes it; hop 3 is false"),
    ("F-397", "read_then_inc_control.proof", "reject", "method inliner",
     "control: the two calls in separate statements; hop 3 is false"),
    ("F-397", "read_then_inc_true.proof", "accept", "method inliner",
     "positive control: the count is read before the increment"),
    ("F-397", "completeness_plus_zero.proof", "accept", "SymbolicComputation",
     "completeness: an Int r + 0 is r, which read_then_inc.proof's hop 1 needs"),
    ("F-397", "bind_order.proof", "reject", "method inliner",
     "a bound call jumped ahead of an earlier call that conflicts with it"),
    ("F-397", "bind_order_control.proof", "reject", "method inliner",
     "control: the earlier calls in statements of their own; hop 3 is false"),
    ("F-397", "bind_order_true.proof", "accept", "method inliner",
     "positive control: both sides are the reduction as written"),
    ("F-397", "funcpos.proof", "reject", "method inliner",
     "a call in the callee position ran before an earlier read it writes"),
    ("F-397", "funcpos_phase1.proof", "reject", "method inliner",
     "the same while the reduction is resolved alone; hop 3 is false"),
    ("F-397", "funcpos_true.proof", "accept", "method inliner",
     "positive control: both sides are the reduction as written"),
    ("F-398", "letcap.proof", "reject", "StandardizeFieldNames",
     "a field was renamed to field1, a let: Int the game reads"),
    ("F-398", "letcap_control.proof", "accept", "StandardizeFieldNames",
     "positive control: the let: Int c is not a minted name; fields renamed"),
    ("F-398", "argcap.proof", "reject", "StandardizeParameters",
     "a parameter was renamed to arg1, a let: Int the method reads"),
    ("F-398", "argcap_control.proof", "accept", "StandardizeParameters",
     "positive control: the let: Int c is not a minted name; parameters renamed"),
    ("F-399", "initializer_draw.proof", "reject", "ExpandTuple",
     "a split field's read in another field's initializer was left dangling"),
    ("F-399", "initializer_draw_control.proof", "accept", "ExpandTuple",
     "positive control: the games differ only in a component nothing reads"),
    ("F-399", "call_initializer.proof", "accept", "ExpandTuple",
     "a product field initialized by a call crashed the split"),
    ("F-399", "product_default.proof", "accept", "ExpandTuple",
     "a tuple's default is the tuple of its components' defaults (6.9)"),
    ("F-401", "field_shadow.proof", "reject", "InjectiveEqualitySimplify",
     "a local shadowing the field v's value reads counted as never changing "
     "(the pipeline renames it apart first; unit tests pin the pass)"),
    ("F-401", "field_shadow_control.proof", "accept",
     "InjectiveEqualitySimplify",
     "positive control: v encodes the field, so v == F.Enc(m) is field == m"),
    ("F-403", "empty_body_drop.proof", "reject", "method inliner",
     "an empty callee body dropped the binding of an argument that draws"),
    ("F-403", "empty_body_control.proof", "accept", "method inliner",
     "positive control: a call-free argument to an empty body has no effect"),
    ("F-404", "many.proof", "reject", "method inlining",
     "calls left after the 200-round inlining cap were read as opaque calls"),
    ("F-404", "few.proof", "reject", "method inlining",
     "the same games with 5 calls: inlining finishes, the draw is kept"),
    ("F-404", "cap_control.proof", "accept", "method inlining",
     "positive control: a game inlined in exactly 200 rounds is resolved"),
    ("F-405", "capture.proof", "reject", "method inliner",
     "a callee's local in a branch kept its name and captured the argument"),
    ("F-405", "capture_control.proof", "accept", "method inliner",
     "positive control: no argument is named like the callee's local"),
    ("F-405", "capture_same_name.proof", "accept", "method inliner",
     "the attack's call against its true value, the caller's b"),
    ("F-405", "decl_capture.proof", "reject", "method inliner",
     "a callee's bare declaration kept its name and captured the argument"),
    ("F-405", "decl_control.proof", "accept", "method inliner",
     "the same call against its true value"),
    ("F-405", "for_capture.proof", "reject", "method inliner",
     "a callee's for binder kept its name and captured the argument"),
    ("F-405", "for_control.proof", "accept", "method inliner",
     "the same call against its true value"),
    ("F-405", "index_clash.proof", "reject", "method inliner",
     "a call nested in an inlined body at the same index reused its local's name"),
    ("F-405", "index_control.proof", "accept", "method inliner",
     "the same calls against their true value"),
    ("F-405", "param_clash.proof", "reject", "method inliner",
     "the same, for the binding of a parameter the callee writes"),
    ("F-405", "param_control.proof", "accept", "method inliner",
     "the same calls against their true value"),
    ("F-405", "return_clash.proof", "reject", "method inliner",
     "the same, for the bindings of a callee's returned ModInt values"),
    ("F-405", "return_control.proof", "accept", "method inliner",
     "the same calls against their true value"),
    ("F-406", "bs0_direct.proof", "reject", "TopologicalSort",
     "a draw from BitString<0> minus its one element was dropped as dead code"),
    ("F-406", "cond_call.proof", "reject", "method inliner",
     "a callee making that draw counted as having no effect, so the call in "
     "the right operand of && was inlined unconditionally"),
    ("F-406", "cond_call_control.proof", "accept", "method inliner",
     "positive control: the same games with a draw from BitString<1> \\ {0b0}"),
    ("F-406", "dead_draw_control.proof", "accept", "TopologicalSort",
     "positive control: an unused draw from BitString<1> \\ {0b0} is dropped"),
    ("F-406", "early_return.proof", "reject", "TopologicalSort",
     "the same empty draw was moved past an early return"),
    ("F-406", "early_return_control.proof", "accept", "TopologicalSort",
     "positive control: a draw from BitString<1> \\ {0b0} moves past it"),
    ("F-406", "field_draw.proof", "reject", "RemoveUnnecessaryFields",
     "an unread field drawn from the same empty domain was removed"),
    ("F-406", "field_draw_control.proof", "accept", "RemoveUnnecessaryFields",
     "positive control: an unread field drawn from BitString<1> \\ {0b0} goes"),
    ("F-407", "void_return_empty.proof", "type_error", "method inliner",
     "return T.Take(true); in a Void method lost its return when the empty "
     "callee body replaced it, so the update after the if ran"),
    ("F-407", "void_return_body.proof", "type_error", "method inliner",
     "the same, with a callee body that has a statement but no return"),
    ("F-407", "void_return_control.proof", "type_error", "method inliner",
     "the same return as the method's last statement, also refused"),
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
    ("LOCAL-FN-FIELD-INIT", "field_initializer_reads_let.proof", "reject",
     "LocalFunctionFieldToLet",
     "a field initializer queried the let: function the field was replaced by"),
    ("LOCAL-FN-FIELD-INIT", "field_initializer_control.proof", "accept",
     "LocalFunctionFieldToLet",
     "positive control: the field initializer does not read the let: function"),
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
    ("SAMPLE-RANGE", "int_range.proof", "type_error", "type checker",
     "a random function with an Int range was drawn"),
    ("SAMPLE-RANGE", "optional_range.proof", "type_error", "type checker",
     "a random function with an optional range was drawn"),
    ("SAMPLE-RANGE", "alias_range.proof", "type_error", "type checker",
     "a random function whose range alias has an Int component was drawn"),
    ("SAMPLE-RANGE", "int_map_value.proof", "type_error", "type checker",
     "a map with Int values was drawn"),
    ("SAMPLE-RANGE", "let_int_range.proof", "type_error", "type checker",
     "a let: entry drew a random function with an Int range"),
    ("SAMPLE-RANGE", "finite_range_control.proof", "accept", "type checker",
     "positive control: a random function with a finite range and Int domain"),
    ("SAMPLE-RANGE", "let_finite_range_control.proof", "accept",
     "type checker",
     "positive control: a let: entry draws a function with a finite range"),
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
    ("LOCAL-REDECLARATION", "redeclared_local.proof", "type_error",
     "type checker", "a local was declared twice in one block"),
    ("LOCAL-REDECLARATION", "shadowed_local.proof", "type_error",
     "type checker", "an inner block shadowed a local of its enclosing block"),
    ("LOCAL-REDECLARATION", "shadowed_by_loop_binder.proof", "type_error",
     "type checker", "a for binder shadowed a local of its enclosing block"),
    ("LOCAL-REDECLARATION", "sibling_locals_control.proof", "accept",
     "type checker", "positive control: locals of one name in sibling blocks"),
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
    ("STATE-RELATIONS", "mask_third_use.proof", "reject",
     "UniformModIntRepeatedMask",
     "a capped use count let a third, bare use of the uniform slip through"),
    ("STATE-RELATIONS", "false_invariant.proof", "reject",
     "FieldInvariantElimination",
     "pk == g^sk holds after Initialize but an oracle breaks it"),
    ("STATE-RELATIONS", "branch_invariant.proof", "reject",
     "FieldInvariantElimination",
     "pk == g^sk is preserved on one branch of an oracle only"),
    ("STATE-RELATIONS", "true_invariant_control.proof", "accept",
     "FieldInvariantElimination", "positive control: a preserved pk == g^sk"),
    ("STATE-RELATIONS", "coerced_invariant.proof", "type_error",
     "FieldInvariantElimination",
     "a ModInt field holding an Int reduced mod q was related to the raw Int"),
    ("STATE-RELATIONS", "coerced_absorption.proof", "type_error",
     "BlockedLocalAbsorption",
     "moving a ModInt local's Int initializer dropped its reduction mod q"),
    ("STATE-RELATIONS", "coerced_literal.proof", "type_error",
     "ForwardLiteralFieldWrite",
     "the literal 7 was forwarded for a ModInt field holding 7 mod q"),
    ("STATE-RELATIONS", "absorbed_key.proof", "reject",
     "BlockedLocalAbsorption",
     "a read of the local in the use's l-value M[x] was not counted"),
    ("STATE-RELATIONS", "drawn_exponent.proof", "reject",
     "GeneratorPowerFieldToExponent",
     "two non-deterministic calls in the written exponent cancelled"),
    ("STATE-RELATIONS", "drawn_fixed_key.proof", "reject", "OffsetFusion",
     "two non-deterministic calls in the fixed key's exponent cancelled"),
]
# fmt: on

# (finding, proof file) -> the error a type_error case must fail with.
TYPE_ERROR = {
    ("F-031", "attack4.proof"): (
        "error: Method Reset writes the scheme field 'used': a scheme field may"
        " not be written in a method body"
    ),
    ("F-031", "scheme_state_capture.proof"): (
        "error: Method Next writes the scheme field 'c': a scheme field may not"
        " be written in a method body"
    ),
    ("F-031", "scheme_field_grow.proof"): (
        "error: Method Grow writes the scheme field 'len': a scheme field may"
        " not be written in a method body"
    ),
    ("F-031", "scheme_state.proof"): (
        "error: Method Bump writes the scheme field 'cnt': a scheme field may"
        " not be written in a method body"
    ),
    ("F-048", "J2.proof"): (
        "error: The size in BitString<n> names local 'n', which is assigned or"
        " sampled"
    ),
    ("F-372", "init_and.proof"): (
        "error: R.Initialize must call challenger.Initialize where it is"
        " always evaluated, not in the right operand of && or ||"
    ),
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
    ("F-383", "scheme_write.proof"): (
        "error: Cannot instantiate BumpCounter: one of its methods writes its "
        "parameter 'n'"
    ),
    # The scheme's write to its own field is refused before instantiation.
    ("F-384", "scheme_reads_written.proof"): (
        "error: Method Next writes the scheme field 'c': a scheme field may not"
        " be written in a method body"
    ),
    ("F-384", "scheme_method_call.proof"): (
        "error: Cannot instantiate KeyedSource: the initializer of its field "
        "'k', S.Draw(), calls a method or reads a field one of the scheme's "
        "methods writes"
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
    ("SAMPLE-RANGE", "int_range.proof"): (
        "error: Cannot sample from Function<BitString<n>, Int>: its range Int"
        " has no uniform distribution"
    ),
    ("SAMPLE-RANGE", "optional_range.proof"): (
        "error: Cannot sample from Function<BitString<n>, BitString<n>?>: its"
        " range BitString<n>? has no uniform distribution"
    ),
    ("SAMPLE-RANGE", "alias_range.proof"): (
        "error: Cannot sample from Function<BitString<n>, [Int, BitString<n>]>:"
        " its range [Int, BitString<n>] has the component Int, which has no"
        " uniform distribution"
    ),
    ("SAMPLE-RANGE", "int_map_value.proof"): (
        "error: Cannot sample from Map<Bool, Int>: its value type Int has no"
        " uniform distribution"
    ),
    ("SAMPLE-RANGE", "let_int_range.proof"): (
        "let_int_range.proof:8:4: error: Cannot sample from"
        " Function<BitString<n>, Int>: its range Int has no uniform distribution"
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
    # A local is declared once and does not shadow an enclosing local (the
    # ruling of 2026-06-28), so these shapes no longer reach the passes.
    ("F-101", "attack_a4_local.proof"): (
        "error: Local 'x' shadows the local 'x' of an enclosing block of method O"
    ),
    ("F-062", "a2_probe.proof"): (
        "error: Local 'a' is declared twice in one block of method O"
    ),
    ("F-199", "A3.proof"): (
        "error: Local 'v' is declared twice in one block of method Initialize"
    ),
    ("F-290", "attack3_reserved.proof"): (
        "error: Local '__u' shadows the local '__u' of an enclosing block of"
        " method O"
    ),
    ("LOCAL-REDECLARATION", "redeclared_local.proof"): (
        "error: Local 'k' is declared twice in one block of method Draw"
    ),
    ("LOCAL-REDECLARATION", "shadowed_local.proof"): (
        "error: Local 'x' shadows the local 'x' of an enclosing block of method F"
    ),
    ("LOCAL-REDECLARATION", "shadowed_by_loop_binder.proof"): (
        "error: Local 'i' shadows the local 'i' of an enclosing block of method F"
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
    ("F-357", "exponent_constant.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-357", "express_after_update.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-357", "cancel_through_local.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-357", "zero_constant_control.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-358", "stale_type.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-358", "stale_type_control.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("STATE-RELATIONS", "coerced_invariant.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("STATE-RELATIONS", "coerced_absorption.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("STATE-RELATIONS", "coerced_literal.proof"): (
        "error: Exponent of a GroupElem<G> must have type Int or"
        " ModInt<G.order>, got ModInt<q>"
    ),
    ("F-389", "letcall_draw.proof"): (
        "error: let: entry 'c' = H(R.Draw()) makes a non-deterministic call"
    ),
    ("F-389", "letcall_draw_via_value.proof"): (
        "error: let: entry 'x' = R.Draw() makes a non-deterministic call"
    ),
    ("F-390", "group_write.proof"): (
        "error: The group in GroupElem<A> names parameter 'A', which is"
        " assigned or sampled"
    ),
    ("F-390", "group_swap.proof"): (
        "error: The group in GroupElem<A> names parameter 'A', which is"
        " assigned or sampled"
    ),
    ("F-391", "before_init.proof"): (
        "error: the initializer of R.y calls the challenger before"
        " challenger.Initialize"
    ),
    ("F-391", "init_in_field.proof"): (
        "error: the initializer of R.y calls challenger.Initialize; it may only"
        " be called from Initialize"
    ),
    ("F-395", "letdraw.proof"): (
        "error: let: entry 'c' = R.Draw() makes a non-deterministic call"
    ),
    ("F-395", "letcall_xor.proof"): (
        "error: let: entry 'c' = H(R.Draw()) + 0^m makes a non-deterministic call"
    ),
    # A Void method contains no return (ruling Q18).
    ("F-407", "void_return_empty.proof"): (
        "VR.game:8:12: error: Method Test has return type Void but contains a"
        " return statement: a Void method has no return"
    ),
    ("F-407", "void_return_body.proof"): (
        "VR.game:8:12: error: Method Test has return type Void but contains a"
        " return statement: a Void method has no return"
    ),
    ("F-407", "void_return_control.proof"): (
        "VRC.game:8:8: error: Method Test has return type Void but contains a"
        " return statement: a Void method has no return"
    ),
}

# (finding, proof file) -> the hop a reject case must fail at. Every other
# hop in these proofs is true and must still pass.
FAILED_STEP = {
    ("F-372", "challenger_and_guarded.proof"): (
        "Step 3 failed: Counter().Right compose R() -> TG().Right"
    ),
    # Hop 1 also needs Guarded True Return To Condition: the composed game
    # returns true in the guarded branch, T().Left returns b after the if.
    ("F-372", "challenger_and.proof"): (
        "Step 3 failed: Counter().Right compose R() -> T().Right"
    ),
    ("F-372", "deferred_challenger.proof"): (
        "Step 3 failed: Echo().Right compose R(P) -> TT_temp(P).Right"
    ),
    ("F-373", "challenger_write.proof"): (
        "Step 1 failed: Probe(n).Left -> Echo(n).Left compose R(n)"
    ),
    ("F-383", "reduction_write.proof"): (
        "Step 1 failed: ParamWrite(n).Left -> Echo(n).Real compose R(n)"
    ),
    # Without the snapshot on the reduction, step 2 verifies, and steps 1 and
    # 3 fail in its place (the games' own fields get the snapshot).
    ("F-372", "reorder_inc_first.proof"): (
        "Step 3 failed: Ctr().Right compose R(P) -> TRI(P).Right"
    ),
    ("F-384", "reduction_copy_source.proof"): (
        "Step 2 failed: Ping().Real compose R7() -> Ping().Real compose R9()"
    ),
    ("F-384", "reduction_written_copy.proof"): (
        "Step 2 failed: Ping().Real compose R7() -> Ping().Real compose R9()"
    ),
    ("F-391", "counter_none.proof"): (
        "Step 3 failed: Ctr(n).Ideal compose R(n) -> OnceOrNone(n).Right"
    ),
    ("F-391", "challenger_field_draw.proof"): (
        "Step 3 failed: KI(S).Real compose R(S) -> Twice(S).Right"
    ),
    # Hop 1 also needs Symbolic Computation to drop Inc's Int `+ 0`.
    ("F-397", "read_then_inc.proof"): (
        "Step 3 failed: Cnt().Right compose R() -> RO().Right"
    ),
    ("F-397", "read_then_inc_plus_zero.proof"): (
        "Step 3 failed: Cnt().Right compose R() -> ROZ().Right"
    ),
    ("F-397", "read_then_inc_control.proof"): (
        "Step 3 failed: Cnt().Right compose R() -> RO().Right"
    ),
    ("F-397", "bind_order.proof"): (
        "Step 3 failed: CD2().Right compose R(P) -> TB(P).Right"
    ),
    ("F-397", "bind_order_control.proof"): (
        "Step 3 failed: CD2().Right compose R(P) -> TB(P).Right"
    ),
    ("F-397", "funcpos.proof"): (
        "Step 1 failed: TF().Left -> CF().Left compose R()"
    ),
    ("F-397", "funcpos_phase1.proof"): (
        "Step 3 failed: CF().Right compose R(P) -> TF2().Right"
    ),
    ("F-372", "bind_order_cond.proof"): (
        "Step 3 failed: CDB().Right compose R(P) -> TC(P).Right"
    ),
    ("F-372", "bind_order_cond_control.proof"): (
        "Step 3 failed: CDB().Right compose R(P) -> TC(P).Right"
    ),
    # The hop fails because a game could not be inlined, not on a difference.
    ("F-404", "many.proof"): (
        "Step 1 failed: G_many(P).Left -> G_many(P).Right\n"
        "    G_many(P).Left: inlining did not finish within 200 rounds"
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
