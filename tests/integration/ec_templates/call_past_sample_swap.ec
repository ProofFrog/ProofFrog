(* ============================================================ *)
(* Abstract-call-past-independent-sample reorder (B3 blocker B)   *)
(* — VALIDATED EC TEMPLATE (regression tripwire).                 *)
(*                                                               *)
(* The hand-derived, EasyCrypt-compiling target shape the         *)
(* exporter must emit for a per-transform micro hop where one     *)
(* canonicalization step (e.g. `Inline Single-Use Variables`)     *)
(* REORDERS an abstract scheme call past an INDEPENDENT sample:    *)
(*                                                               *)
(*   state_0: k <@ E.keygen(); mPrime <$ d; c <@ E.enc(k,mPrime)  *)
(*   state_1: mPrime <$ d; k <@ E.keygen(); c <@ E.enc(k,mPrime)  *)
(*                                                               *)
(* Three load-bearing facts:                                      *)
(*  1. A sample `mPrime <$ d` is glob-independent, so EC's `swap`  *)
(*     CAN move it past an abstract call `k <@ E.keygen()` (which  *)
(*     touches only `glob E`). This is what distinguishes it from  *)
(*     the stateless-reorder case (two abstract calls past each    *)
(*     other), which `swap` rejects and which needs the `Ideal`    *)
(*     statelessness machinery.                                    *)
(*  2. The reorder is a whole-body permutation of the two RENDERED *)
(*     flat-state modules, so `swap{1} <pos> <delta>` reorders the *)
(*     lemma's left side (module argument 1) to match the right.   *)
(*  3. After the swap the two bodies are identical, so the canned  *)
(*     `sp; wp; sim` suffix the multi-module emitter already uses  *)
(*     closes the remainder (`sim` matches the abstract calls).    *)
(*                                                               *)
(* The exporter computes the `swap` from the rendered flat-state   *)
(* modules (what EC sees), NOT from the raw transform-application  *)
(* ASTs (`app.game_before`/`app.game_after`), which are normalized *)
(* differently (separately-canonicalized `game_before`; a nested   *)
(* `return` that only the EC hoister flattens at render time) and  *)
(* so hide the reorder. See `chain_emitter._rendered_state_swaps`. *)
(*                                                               *)
(* If this stops compiling, the exporter's target tactic for the   *)
(* call-past-sample reorder must be re-derived before               *)
(* `_rendered_state_swaps` can be trusted.                         *)
(* ============================================================ *)

require import AllCore Distr.

type MessageSpace, KeySpace, CiphertextSpace.
op dMessageSpace : MessageSpace distr.

module type Scheme = {
  proc keygen() : KeySpace
  proc enc(k : KeySpace, m : MessageSpace) : CiphertextSpace
}.

section.
declare module E <: Scheme.

(* state_0: keygen BEFORE the independent sample. *)
module State0 (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var k : KeySpace;
    var mPrime : MessageSpace;
    var c : CiphertextSpace;
    k <@ E.keygen();
    mPrime <$ dMessageSpace;
    c <@ E.enc(k, mPrime);
    return c;
  }
}.

(* state_1: sample BEFORE keygen (reordered; hoisted return as the
   exporter renders it). *)
module State1 (E : Scheme) = {
  proc foo(m : MessageSpace) : CiphertextSpace = {
    var mPrime : MessageSpace;
    var _r0 : KeySpace;
    var _r1 : CiphertextSpace;
    mPrime <$ dMessageSpace;
    _r0 <@ E.keygen();
    _r1 <@ E.enc(_r0, mPrime);
    return _r1;
  }
}.

(* Forward micro: state_0 ~ state_1. Move the sample (pos 2) to the
   front to match the right side, then close with the canned suffix. *)
lemma micro_fwd :
  equiv [ State0(E).foo ~ State1(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  swap{1} 2 -1.
  sp; wp; sim.
qed.

(* Reversed micro: state_1 ~ state_0. Move keygen (pos 2) to the front. *)
lemma micro_rev :
  equiv [ State1(E).foo ~ State0(E).foo : ={m, glob E} ==> ={res, glob E} ].
proof.
  proc.
  swap{1} 2 -1.
  sp; wp; sim.
qed.

end section.
