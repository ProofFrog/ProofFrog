(*
   CFRG binding -- CHALLENGE-oracle case-split ELIMINATION.

   The green-cell blocker for the concrete expanded-LEAK binding proofs
   (CG/CK/UG/UK): hop_0/2/4_challenge relate the game's DIRECT hybrid-binding
   challenge to the reduction R_PQ_Bind's CASE-SPLIT challenge, and the engine
   proves them equal by DISSOLVING the case-split (the two canonical forms are
   byte-identical). This tripwire pins the EC tactic STRATEGY the exporter must
   synthesize for that dissolution.

   Game challenge (direct):
     kdf0 = concat encss(decaps dk0 ct0pq) rest0;
     kdf1 = concat encss(decaps dk1 ct1pq) rest1;
     return H kdf0 = H kdf1 /\ ct0 <> ct1

   Reduction challenge (case-split, challenger.Challenge inlined to the KEM_PQ
   Breakable predicate):
     if (kdf0 = kdf1 /\ ct0pq <> ct1pq)
       return decaps dk0 ct0pq = decaps dk1 ct1pq /\ ct0pq <> ct1pq;
     return H kdf0 = H kdf1 /\ ct0 <> ct1

   SOUNDNESS of the elimination: in the branch, kdf0 = kdf1 and concat is
   injective on its components, so encss(decaps dk0 ct0pq) = encss(decaps dk1
   ct1pq); encss is injective, hence decaps dk0 ct0pq = decaps dk1 ct1pq -- the
   KEM_PQ predicate's first conjunct is true, and ct0pq <> ct1pq is the branch
   guard, so the reduction returns true. The hybrid predicate is also true
   there: kdf0 = kdf1 => H kdf0 = H kdf1, and ct0pq <> ct1pq => ct0 <> ct1. So
   both branches equal the hybrid predicate. The two facts consumed (concat
   component-injectivity + encss injectivity) are the concat/slice +
   Encode-injectivity axioms the real export must thread; here they are modelled
   as an injective concat op + an encss_inj axiom.

   THE STRATEGY: proc; couple the abstract calls; case the guard; each side smt
   from the injectivity facts. If this stops compiling, the
   case-split-elimination synthesizer's target must be re-derived.
*)

require import AllCore.

type dk, ct_pq, ct_t, ss, comp_t, kdf, kout.

(* A concrete concat modelled injectively: kdf carries the PQ shared
   secret encoding and the rest; equality of two kdfs gives equality of
   both components (the concat/slice injectivity the real proof uses). *)
op mk_kdf : ss -> comp_t -> kdf.
axiom mk_kdf_inj (a a' : ss) (b b' : comp_t) :
  mk_kdf a b = mk_kdf a' b' => a = a' /\ b = b'.

op encss : ss -> ss.
axiom encss_inj (a a' : ss) : encss a = encss a' => a = a'.

op rest : dk -> ct_pq -> ct_t -> comp_t.   (* the T-side + label components *)
op hyb_ct_neq : (ct_pq * ct_t) -> (ct_pq * ct_t) -> bool.
(* the hybrid ct-inequality: ct0 <> ct1 iff a component differs. In the
   branch (ct0pq <> ct1pq) it holds. *)
axiom hyb_ct_neq_pq (c0 c1 : ct_pq * ct_t) :
  c0.`1 <> c1.`1 => hyb_ct_neq c0 c1.

module type KEMPQ = { proc decaps(k : dk, c : ct_pq) : ss }.

(* The KDF is DETERMINISTIC (a function of its input): in the real export
   H.evaluate is a `deterministic` method, modelled by an op `ev_evaluate`
   plus a `H_evaluate_det` phoare axiom, and the challenge tactic
   functionalizes the two calls to it so `kdf0 = kdf1 => H kdf0 = H kdf1`.
   Here we model that determinism directly with a pure op `hop`. *)
op hop : kdf -> kout.

(* Shared state: the two hybrid decaps keys' PQ components. *)
module St = {
  var dk0 : dk
  var dk1 : dk
}.

(* kdf_in for key i from ciphertext ci (PQ decaps encoded, then rest). *)
module Common (K : KEMPQ) = {
  proc kdf_of(k : dk, c : ct_pq * ct_t) : ss * kdf = {
    var s : ss;
    s <@ K.decaps(k, c.`1);
    return (s, mk_kdf (encss s) (rest k c.`1 c.`2));
  }
}.

(* Game side: direct hybrid predicate. *)
module G (K : KEMPQ) = {
  proc challenge(ct0 ct1 : ct_pq * ct_t) : bool = {
    var s0, s1 : ss; var kdf0, kdf1 : kdf;
    (s0, kdf0) <@ Common(K).kdf_of(St.dk0, ct0);
    (s1, kdf1) <@ Common(K).kdf_of(St.dk1, ct1);
    return hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
  }
}.

(* Reduction side: case-split; the challenger.Challenge branch inlined to
   the KEM_PQ Breakable predicate `decaps = decaps /\ ct_pq differ`. *)
module R (K : KEMPQ) = {
  proc challenge(ct0 ct1 : ct_pq * ct_t) : bool = {
    var s0, s1 : ss; var kdf0, kdf1 : kdf; var r : bool;
    (s0, kdf0) <@ Common(K).kdf_of(St.dk0, ct0);
    (s1, kdf1) <@ Common(K).kdf_of(St.dk1, ct1);
    if (kdf0 = kdf1 /\ ct0.`1 <> ct1.`1) {
      r <- s0 = s1 /\ ct0.`1 <> ct1.`1;
    } else {
      r <- hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
    }
    return r;
  }
}.

(* The two challenges are equal: the case-split dissolves. The strategy the
   exporter must synthesize: couple the abstract decaps calls, then close the
   wp-collapsed conditional post by case analysis on the guard, discharging
   each branch from the injectivity + determinism facts. *)
lemma challenge_casesplit_elim (K <: KEMPQ {-St}) :
  equiv [ G(K).challenge ~ R(K).challenge :
     ={arg, glob St, glob K} ==> ={res} ].
proof.
  proc.
  inline Common(K).kdf_of.
  wp.
  call (_: true).
  wp.
  call (_: true).
  wp.
  skip => />.
  smt(mk_kdf_inj encss_inj hyb_ct_neq_pq).
qed.
