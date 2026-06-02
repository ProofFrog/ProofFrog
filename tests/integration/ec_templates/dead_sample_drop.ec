(* ============================================================ *)
(* Dead-sample-drop synthesis (B3, part 1) — VALIDATED EC        *)
(* TEMPLATE (regression tripwire).                               *)
(*                                                               *)
(* The hand-derived, EasyCrypt-compiling target shape the        *)
(* exporter must emit for a per-transform micro hop where one    *)
(* side carries an EXTRA, INDEPENDENT, DEAD sample (a `<$` whose  *)
(* bound variable is never used downstream) that `Topological    *)
(* Sorting` drops on the other side. The current `_permutation_  *)
(* swaps` synthesizer cannot handle this (the two bodies are not  *)
(* whole-body permutations — they differ in length), so without   *)
(* this recipe such micros fall back to admit.                   *)
(*                                                               *)
(* Three load-bearing ideas:                                     *)
(*  1. The dropped sample's distribution is LOSSLESS, so a one-   *)
(*     sided sample that feeds nothing leaves the relational     *)
(*     post-condition unchanged. The exporter already emits       *)
(*     `axiom d<Type>_ll : is_lossless d<Type>` for every Set-    *)
(*     derived distribution, so no new axioms are needed.        *)
(*  2. The extra sample is moved to the FRONT with `swap{S}` (it  *)
(*     is independent, so this is always valid), then split off   *)
(*     with `seq` and discharged one-sided with `rnd{S}; auto;    *)
(*     smt(d<Type>_ll)`. `S` is the side that carries the extra   *)
(*     sample: 1 for the forward micro (state_k ~ state_{k+1}),    *)
(*     2 for the reversed micro (state_{k+1} ~ state_k).          *)
(*  3. After the drop the two bodies are identical, so a plain    *)
(*     `sim` closes the remainder.                                *)
(*                                                               *)
(* If this stops compiling, the exporter's target tactic for      *)
(* dead-sample-drop micros must be re-derived before the          *)
(* `_dead_sample_drop` synthesizer can be trusted.                *)
(* ============================================================ *)

require import AllCore Distr.

type MessageSpace, KeySpace, CiphertextSpace.
op dMessageSpace : MessageSpace distr.
axiom dMessageSpace_ll : is_lossless dMessageSpace.

module type Scheme = {
  proc keygen() : KeySpace
  proc enc(k : KeySpace, m : MessageSpace) : CiphertextSpace
}.

section.
declare module E <: Scheme.

(* "long" side: a dead mPrime sample at the LEADING position. *)
module Long_lead (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var mPrime : MessageSpace;
    var k : KeySpace;
    var c : CiphertextSpace;
    mPrime <$ dMessageSpace;
    k <@ E.keygen();
    c <@ E.enc(k, m);
    return c;
  }
}.

(* "long" side: a dead mPrime sample at a NON-leading position (2). *)
module Long_mid (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var mPrime : MessageSpace;
    var k : KeySpace;
    var c : CiphertextSpace;
    k <@ E.keygen();
    mPrime <$ dMessageSpace;
    c <@ E.enc(k, m);
    return c;
  }
}.

module Short (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var k : KeySpace;
    var c : CiphertextSpace;
    k <@ E.keygen();
    c <@ E.enc(k, m);
    return c;
  }
}.

(* Forward, leading drop: extra sample on the LEFT -> rnd{1}, no swap. *)
lemma drop_fwd_lead :
  equiv [ Long_lead(E).foo ~ Short(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  seq 1 0 : (={m, glob E}).
  + rnd{1}; auto; smt(dMessageSpace_ll).
  sim.
qed.

(* Reversed, leading drop: extra sample on the RIGHT -> rnd{2}, no swap. *)
lemma drop_rev_lead :
  equiv [ Short(E).foo ~ Long_lead(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  seq 0 1 : (={m, glob E}).
  + rnd{2}; auto; smt(dMessageSpace_ll).
  sim.
qed.

(* Forward, non-leading drop: swap the dead sample to the front first. *)
lemma drop_fwd_mid :
  equiv [ Long_mid(E).foo ~ Short(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  swap{1} 2 -1.
  seq 1 0 : (={m, glob E}).
  + rnd{1}; auto; smt(dMessageSpace_ll).
  sim.
qed.

(* "long" side: TWO dead samples (positions 1 and 3 here). *)
module Long_two (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var mPrime : MessageSpace;
    var mPrime2 : MessageSpace;
    var k : KeySpace;
    var c : CiphertextSpace;
    mPrime <$ dMessageSpace;
    k <@ E.keygen();
    mPrime2 <$ dMessageSpace;
    c <@ E.enc(k, m);
    return c;
  }
}.

(* Forward, two drops: drop each in turn (front -> seq -> rnd), then sim. *)
lemma drop_fwd_two :
  equiv [ Long_two(E).foo ~ Short(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  seq 1 0 : (={m, glob E}).
  + rnd{1}; auto; smt(dMessageSpace_ll).
  swap{1} 2 -1.
  seq 1 0 : (={m, glob E}).
  + rnd{1}; auto; smt(dMessageSpace_ll).
  sim.
qed.

end section.
