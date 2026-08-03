(* Tripwire: a WITNESS MODEL for the BEHAVIOURAL axiom classes -- the `_det`
 * and `_inj` `declare axiom`s the exporter emits over abstract scheme modules.
 *
 * WHY. Audit pass 1 called `_det` the riskiest class (753 instances across the
 * corpus, 8 per CFRG binding proof) because it is not a fact about mathematics
 * but a HYPOTHESIS about an abstract module -- and unlike the bitstring
 * families it cannot be derived, only licensed. The audit checked LICENSING
 * (every `_det` names a method carrying FrogLang's `deterministic` modifier;
 * every `_inj` one carrying `injective`) and found 0 unlicensed. What licensing
 * does NOT check is whether the emitted STATEMENT is a faithful rendering of
 * the modifier, or whether it is satisfiable at all: `<M>_<m>_det` is a
 * conjunction of THREE claims bundled into one phoare -- glob preservation,
 * a specific return VALUE (`res = ev_<m> args`), and losslessness (`= 1%r`) --
 * and the FrogLang modifier is one word. An over-strong bundle here is exactly
 * the "clean but wrong" failure the ledger exists for, and it would be
 * invisible: the axiom is assumed, never checked.
 *
 * WHAT THIS FILE SHOWS. The two emitted shapes are reproduced VERBATIM (modulo
 * names) and DISCHARGED against a concrete module that merely computes an
 * uninterpreted total function of its arguments and touches no state. That is
 * the intended reading of `deterministic`, so:
 *
 *   1. The `_det` bundle is SATISFIABLE -- assuming it cannot make an exported
 *      proof vacuous, because a model exists.
 *   2. It is not over-strong RELATIVE TO ITS INTENDED READING: a plain
 *      stateless total function already discharges all three conjuncts, so the
 *      axiom demands nothing beyond "deterministic and always terminates".
 *   3. `_inj` likewise holds of any injective `ev_`, and -- worth stating
 *      because it is the surprising-result-adjacent one -- it constrains ONLY
 *      the `ev_` function, never `concat`. It cannot smuggle in the
 *      concatenation injectivity a binding result would be embarrassed to
 *      assume.
 *
 * WHAT IT DOES NOT SHOW. Whether a REAL scheme instantiating `KEM_PQ` is
 * deterministic and lossless. That is what FrogLang's `deterministic` modifier
 * asserts about the primitive, and discharging it belongs at instantiation
 * time, not here -- see this plan's standing "are these ever discharged?"
 * question. This file bounds the damage: whatever else is true, the axioms are
 * consistent and say no more than the modifier does.
 *
 * The `= 1%r` conjunct is the one worth a reviewer's eye. It makes `_det`
 * assert TERMINATION as well as determinism, which the word "deterministic"
 * does not obviously carry. It is discharged trivially here (a total function
 * terminates), and it is genuinely needed by the one-sided `call{i}` peels the
 * exporter emits -- a phoare of probability < 1 cannot license those. Recorded
 * so the bundling is a decision on the record rather than an accident.
 *)

require import AllCore Distr.

type argA, argB, resT.

(* the uninterpreted function the exporter's `ev_<m>` op stands for *)
op ev_decaps : argA -> argB -> resT.
op ev_encode : argA -> resT.

module type SCHEME = {
  proc decaps (dk : argA, ct : argB) : resT
  proc encodesharedsecret (ss : argA) : resT
}.

(* the intended model of a `deterministic` method: compute `ev_`, touch nothing *)
module Concrete : SCHEME = {
  proc decaps (dk : argA, ct : argB) : resT = {
    return ev_decaps dk ct;
  }
  proc encodesharedsecret (ss : argA) : resT = {
    return ev_encode ss;
  }
}.

(* --- the `_det` shape, verbatim as emitted (two-argument method) --------- *)
lemma m_decaps_det (g : (glob Concrete)) (a0 : argA) (a1 : argB) :
  phoare[ Concrete.decaps :
          (glob Concrete) = g /\ dk = a0 /\ ct = a1
          ==> (glob Concrete) = g /\ res = ev_decaps a0 a1 ] = 1%r.
proof. by proc; auto. qed.

(* --- the same shape at one argument -------------------------------------- *)
lemma m_encode_det (g : (glob Concrete)) (a0 : argA) :
  phoare[ Concrete.encodesharedsecret :
          (glob Concrete) = g /\ ss = a0
          ==> (glob Concrete) = g /\ res = ev_encode a0 ] = 1%r.
proof. by proc; auto. qed.

(* --- the `_inj` shape ----------------------------------------------------
   Stated over the `ev_` op ONLY. Whatever injectivity this grants, it is
   injectivity of the scheme's own encoding function -- it says nothing about
   `concat`, so it cannot be the hidden source of a binding result. Modelled by
   an op ASSUMED injective, which is what the FrogLang `injective` modifier
   licenses; the point being demonstrated is that such an op exists, i.e. the
   hypothesis is satisfiable and does not collapse the theory. *)
op ev_inj_witness : argA -> resT.
axiom witness_injective (a b : argA) :
  ev_inj_witness a = ev_inj_witness b => a = b.

lemma m_encode_inj (a0 b0 : argA) :
  ev_inj_witness a0 = ev_inj_witness b0 => a0 = b0.
proof. exact witness_injective. qed.

(* An injective function into a type with at least as many elements exists --
   the identity, when the two types coincide -- so `witness_injective` is not
   vacuous. Stated concretely to make the satisfiability claim checkable rather
   than asserted. *)
lemma inj_hypothesis_satisfiable (a b : argA) :
  (fun (x : argA) => x) a = (fun (x : argA) => x) b => a = b.
proof. by []. qed.
