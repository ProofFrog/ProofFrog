(* ============================================================ *)
(* CFRG binding -- composite-reduction coupling for a reduction  *)
(* that DECOMPOSES the game's packed key into component fields    *)
(* -- VALIDATED EC TEMPLATE (regression tripwire).               *)
(*                                                               *)
(* Models the real hop_0_initialize / hop_0_challenge boundary   *)
(* of the concrete-framework LEAK-BIND proofs                    *)
(* (CG/CK/UG/UK expanded, e.g. CG_expanded_LEAK_BIND_K_CT):      *)
(*                                                               *)
(*   Game side (Hybrid_Breakable):  var dk0 : dpq * scal * elem  *)
(*             a PACKED hybrid decaps key.                        *)
(*             Challenge reads dk0.`1 / dk0.`2 / dk0.`3.          *)
(*   Reduction side (R_PQ_Bind wrapping the KEM_PQ challenger):   *)
(*             var dk_pq_0 : dpq,  dk_t_0 : scal,  ek_t_0 : elem *)
(*             -- the DECOMPOSED components -- plus the inner     *)
(*             challenger C whose dk0 : dpq it forwards to.       *)
(*             Challenge reads dk_pq_0 / dk_t_0 / ek_t_0.         *)
(*                                                               *)
(* The current exporter (`_live_state_coupling` /                *)
(* `_composite_reduction_step`) emits, for each reduction field  *)
(* f, `other_game.f = reduction.f` -- correct for the Generic    *)
(* LEAK=>HON proofs (game and reduction share field NAMES), but  *)
(* WRONG here: the game has no field `dk_pq_0`, so EC rejects     *)
(* `Hybrid_...dk_pq_0` with "unknown variable" (CG line 12047,   *)
(* CK 10515). This is the next binding-layer wall for expanded   *)
(* LEAK.                                                          *)
(*                                                               *)
(* THE SOUND COUPLING (what a decomposition-aware synthesizer     *)
(* must emit): relate the game's PACKED field to the TUPLE of the *)
(* reduction's component fields, in the packing order read off    *)
(* the reduction's Initialize, plus the reduction<->challenger    *)
(* seam for the forwarded component --                            *)
(*   G.dk0{1} = (R.dk_pq_0, R.dk_t_0, R.ek_t_0){2}                *)
(*   /\ R.dk_pq_0{2} = C.dk0{2}                                   *)
(*                                                               *)
(* Lessons pinned:                                               *)
(*  L1. init micro ESTABLISHES the decomposition: `wp` reduces    *)
(*      G.dk0{1}=(R.dk_pq_0,R.dk_t_0,R.ek_t_0){2} to a tuple of   *)
(*      reflexivities via the packing assignment, and the three   *)
(*      coupled draws (abstract keygen + two samples) close with  *)
(*      `call (_: true)` / `rnd`.                                 *)
(*  L2. challenge micro CONSUMES it: the decomposition feeds the  *)
(*      per-component arg equalities dk0.`i{1} = <component>{2},   *)
(*      so the abstract decaps/exp calls couple with call (_:true)*)
(*  L3. NON-VACUITY: dropping the decomposition invariant makes   *)
(*      the challenge micro UNPROVABLE (the projection equalities *)
(*      are no longer derivable) -- see `challenge_micro_bad`.    *)
(* ============================================================ *)

require import AllCore Distr.

type dpq, scal, elem, ss, ct_pq, ct_t.

op dscal : scal distr.
axiom dscal_ll : is_lossless dscal.

module type Scheme = {
  proc keygen_pq() : dpq
  proc decaps_pq(dk : dpq, c : ct_pq) : ss
  proc exp(base : ct_t, s : scal) : elem
  proc combine(a : ss, b : elem, e : elem) : bool
}.

(* Game side: a single PACKED hybrid decaps key dk0 : dpq * scal * elem. *)
module G (K : Scheme) = {
  var dk0 : dpq * scal * elem
  proc initialize() : unit = {
    var dpq0 : dpq; var s0 : scal; var e0 : elem;
    dpq0 <@ K.keygen_pq();
    s0 <$ dscal;
    e0 <@ K.exp(witness, s0);
    dk0 <- (dpq0, s0, e0);
  }
  proc challenge(cpq : ct_pq, ctt : ct_t) : bool = {
    var a : ss; var b : elem; var r : bool;
    a <@ K.decaps_pq(dk0.`1, cpq);
    b <@ K.exp(ctt, dk0.`2);
    r <@ K.combine(a, b, dk0.`3);
    return r;
  }
}.

(* Inner KEM_PQ challenger: holds its own PQ decaps key. *)
module C (K : Scheme) = {
  var dk0 : dpq
  proc initialize() : unit = { dk0 <@ K.keygen_pq(); }
}.

(* Reduction side: DECOMPOSED component fields; delegates the PQ keygen to C. *)
module R (K : Scheme) = {
  var dk_pq_0 : dpq
  var dk_t_0 : scal
  var ek_t_0 : elem
  proc initialize() : unit = {
    var s0 : scal; var e0 : elem;
    C(K).initialize();
    dk_pq_0 <- C.dk0;
    s0 <$ dscal;
    e0 <@ K.exp(witness, s0);
    dk_t_0 <- s0;
    ek_t_0 <- e0;
  }
  proc challenge(cpq : ct_pq, ctt : ct_t) : bool = {
    var a : ss; var b : elem; var r : bool;
    a <@ K.decaps_pq(dk_pq_0, cpq);
    b <@ K.exp(ctt, dk_t_0);
    r <@ K.combine(a, b, ek_t_0);
    return r;
  }
}.

(* L1: init micro ESTABLISHES the decomposition coupling + the challenger seam. *)
lemma init_micro (K <: Scheme {-G, -C, -R}) :
  equiv [ G(K).initialize ~ R(K).initialize :
     ={glob K} ==>
       ={glob K}
    /\ G.dk0{1} = (R.dk_pq_0, R.dk_t_0, R.ek_t_0){2}
    /\ R.dk_pq_0{2} = C.dk0{2} ].
proof.
  proc. inline C(K).initialize.
  wp. call (_: true). rnd. wp. call (_: true). auto.
qed.

(* L2: challenge micro CONSUMES the decomposition; component arg equalities
   feed the three abstract calls, coupled name-independently. *)
lemma challenge_micro (K <: Scheme {-G, -C, -R}) :
  equiv [ G(K).challenge ~ R(K).challenge :
       ={cpq, ctt, glob K}
    /\ G.dk0{1} = (R.dk_pq_0, R.dk_t_0, R.ek_t_0){2}
       ==>
       ={res, glob K} ].
proof.
  proc.
  call (_: true). call (_: true). call (_: true). auto.
qed.

(* L3 (non-vacuity): WITHOUT the decomposition invariant the projection
   equalities dk0.`i{1} = <component>{2} are not derivable, so the abstract
   `decaps_pq` args differ and `call (_: true)` cannot close. Kept commented
   so the tripwire compiles; uncomment to reconfirm it FAILS.

lemma challenge_micro_bad (K <: Scheme {-G, -C, -R}) :
  equiv [ G(K).challenge ~ R(K).challenge :
       ={cpq, ctt, glob K} ==> ={res} ].
proof.
  proc. call (_: true). call (_: true). call (_: true). auto.
qed.
*)
