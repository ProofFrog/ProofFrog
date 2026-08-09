(* ============================================================ *)
(* Local-binder rename micro (Phase-2 Move 1) — VALIDATED EC      *)
(* TEMPLATE (regression tripwire).                                *)
(*                                                                *)
(* The target shape for a per-transform micro hop whose two flat   *)
(* states differ ONLY by a renaming of typed local binders — the   *)
(* `Alpha Rename` / `Variable Standardization` legs:               *)
(*                                                                *)
(*   state_0: a <$ d; c <@ E.enc(s, a);  return c;                 *)
(*   state_1: x <$ d; y <@ E.enc(s, x);  return y;                 *)
(*                                                                *)
(* `sim` is name-blind on locals, so `proc; sim.` closes the micro *)
(* under the chain's identical-state whole-glob coupling            *)
(* (`_glob_coupling`), exactly as for byte-identical bodies — even  *)
(* when a module global is passed DIRECTLY as an abstract-call arg  *)
(* (`E.enc(s, ...)`), PROVIDED the declare carries the state-module *)
(* write-restrictions (see below).                                  *)
(* The exporter's gate (`_rename_equal_projection`) fires ONLY     *)
(* when the two projected bodies are AST-equal after a positional  *)
(* renaming of typed local binders — fields, params, and statement *)
(* structure byte-identical — so the tactic is guaranteed to       *)
(* close, never a maybe-tactic.                                    *)
(*                                                                *)
(* Negative controls (validated at derivation time, 2026-08-09,    *)
(* by mutating THIS file; they cannot live here because a          *)
(* rejecting lemma would fail the tripwire):                       *)
(*  - goal-falsifying: sampling `__a0__` from a second             *)
(*    distribution dMessageSpace2 on the right → EC rejects at the *)
(*    rnd residual (`a{1} = __a0__{2}` across distinct distrs).    *)
(*  - coupling-falsifying: dropping the whole-glob conjunct from   *)
(*    micro_fwd's pre → EC rejects (the glob equality cannot be    *)
(*    established from `={m}` alone).                              *)
(* The Python-side decline mutations (field rename, reorder,       *)
(* shadowing) are unit-tested in                                   *)
(* tests/unit/export/test_rename_equal_gate.py.                    *)
(*                                                                *)
(* If this stops compiling, the Move 1 gate's target tactic must   *)
(* be re-derived before `_rename_equal_projection` can be trusted. *)
(* ============================================================ *)

require import AllCore Distr.

type MessageSpace, KeySpace, CiphertextSpace.
op dMessageSpace : MessageSpace distr.

module type Scheme = {
  proc enc(k : KeySpace, m : MessageSpace) : CiphertextSpace
}.

section.

(* state_0: source-named locals. *)
module State0 (E : Scheme) = {
  var s : KeySpace
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var a : MessageSpace;
    var c : CiphertextSpace;
    a <$ dMessageSpace;
    c <@ E.enc(s, a);
    return c;
  }
}.

(* state_1: the same body with both typed locals renamed
   (`Alpha Rename` shape — `__a0__`-style names as the engine mints). *)
module State1 (E : Scheme) = {
  var s : KeySpace
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var __a0__ : MessageSpace;
    var __a1__ : CiphertextSpace;
    __a0__ <$ dMessageSpace;
    __a1__ <@ E.enc(s, __a0__);
    return __a1__;
  }
}.

(* The declare must carry write-restrictions against the state modules a
   `sim`/`call` crosses — without `{-State0, -State1}` EC rejects with
   "The module E can write State1.s" and `sim` makes no progress. Real
   exports always emit these restriction lists. *)
declare module E <: Scheme {-State0, -State1}.

(* Forward micro under the chain's identical-state whole-glob coupling
   (`_glob_coupling` — exactly what `micro_pre` emits for a
   same-cardinality pair; the Q1 probe's `leg_alpha_rename` shape). *)
lemma micro_fwd :
  equiv [ State0(E).foo ~ State1(E).foo :
          ={m} /\ (glob State0(E)){1} = (glob State1(E)){2} ==>
          ={res} /\ (glob State0(E)){1} = (glob State1(E)){2} ].
proof.
  proc; sim.
qed.

(* Reversed micro (right-chain `_rev` orientation). *)
lemma micro_rev :
  equiv [ State1(E).foo ~ State0(E).foo :
          ={m} /\ (glob State1(E)){1} = (glob State0(E)){2} ==>
          ={res} /\ (glob State1(E)){1} = (glob State0(E)){2} ].
proof.
  proc; sim.
qed.

end section.
