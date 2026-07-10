(* ============================================================ *)
(* CFRG binding -- CG NG-group init-backbone peel.               *)
(*                                                               *)
(* Models CG_expanded_LEAK_BIND hop_0/hop_4_initialize:          *)
(* the T "KEM" is an NG group whose per-index keygen is          *)
(*   seed <$ d; dk_T <@ NG.randomscalar seed;                    *)
(*   r <@ NG.generator(); ek_T <@ NG.exp r dk_T                  *)
(* where randomscalar/generator/exp are DETERMINISTIC + glob-NG- *)
(* preserving (they have _det phoare axioms), so EC `swap` will   *)
(* NOT reorder them past each other ("not independent -- reads    *)
(* glob NG written by the second").                              *)
(*                                                               *)
(*   Game G:      interleaved  [PQ, s, rs, gen, exp,             *)
(*                              PQ, s, rs, gen, exp]             *)
(*   Reduction R: grouped      [PQ, PQ (via C), s, s,           *)
(*                              rs, rs, gen, exp, gen, exp]      *)
(*                                                               *)
(* The plain (wp; call/rnd)* peel can't align (call couples the  *)
(* two sides' current last event -- mismatched here).  Swap-      *)
(* alignment of the NG calls is IMPOSSIBLE (glob NG).            *)
(*                                                               *)
(* VALIDATED IN-PLACE ROUTE (no functional-twin modules needed): *)
(*  1. swap{1} the game's keygens + samples to the FRONT,        *)
(*     grouped like the reduction (a KEM_PQ.keygen / seed sample *)
(*     is glob-disjoint from the NG calls, so moving it left      *)
(*     past them is an EC-legal swap -- only the NG calls among   *)
(*     THEMSELVES are swap-immovable).                            *)
(*  2. seq-split the aligned probabilistic prefix (keygens+       *)
(*     samples) from the deterministic NG suffix, with a          *)
(*     coupling invariant that ALSO couples the seeds             *)
(*     (s0{1}=s0{2}) -- so the seeds are concrete in the suffix.  *)
(*  3. prefix: rnd/rnd/call/call peel + auto.                     *)
(*  4. suffix: functionalize every NG call FORWARD-VALUE          *)
(*     (call{i} (NG_<m>_det g <functional args over the coupled   *)
(*     seeds>)) back-to-front; skip => /#.                        *)
(* The seed coupling in step 2 is load-bearing: exists*-ing a     *)
(* seed BEFORE its sample (garbage value) makes the residual      *)
(* s0L=fs0 unprovable -- the seq makes the seeds post-sample.     *)
(* ============================================================ *)

require import AllCore Distr.

type ek_pq, dk_pq.
type elt, scalar, seed.

op ev_randomscalar : seed -> scalar.
op ev_generator : elt.
op ev_exp : elt -> scalar -> elt.

op dseed : seed distr.
axiom dseed_ll : is_lossless dseed.

module type KEMPQ = { proc keygen() : ek_pq * dk_pq }.

module type NGT = {
  proc randomscalar(s : seed) : scalar
  proc generator() : elt
  proc exp(base : elt, e : scalar) : elt
}.

(* Deterministic + glob-preserving specs for the NG ops (the export's
   NG_<m>_det declare-axioms). *)
axiom NG_randomscalar_det (NG <: NGT) (g : (glob NG)) (a0 : seed) :
  phoare[ NG.randomscalar : (glob NG) = g /\ s = a0 ==>
          (glob NG) = g /\ res = ev_randomscalar a0 ] = 1%r.
axiom NG_generator_det (NG <: NGT) (g : (glob NG)) :
  phoare[ NG.generator : (glob NG) = g ==>
          (glob NG) = g /\ res = ev_generator ] = 1%r.
axiom NG_exp_det (NG <: NGT) (g : (glob NG)) (a0 : elt) (a1 : scalar) :
  phoare[ NG.exp : (glob NG) = g /\ base = a0 /\ e = a1 ==>
          (glob NG) = g /\ res = ev_exp a0 a1 ] = 1%r.

(* Game side: interleaved. *)
module G (KP : KEMPQ, NG : NGT) = {
  var dk0 : dk_pq * scalar * elt
  var dk1 : dk_pq * scalar * elt
  proc initialize() : unit = {
    var ekp0, ekp1 : ek_pq; var dkp0, dkp1 : dk_pq;
    var s0, s1 : seed; var dt0, dt1 : scalar;
    var r0, r1 : elt; var et0, et1 : elt;
    (ekp0, dkp0) <@ KP.keygen();
    s0 <$ dseed;
    dt0 <@ NG.randomscalar(s0);
    r0 <@ NG.generator();
    et0 <@ NG.exp(r0, dt0);
    (ekp1, dkp1) <@ KP.keygen();
    s1 <$ dseed;
    dt1 <@ NG.randomscalar(s1);
    r1 <@ NG.generator();
    et1 <@ NG.exp(r1, dt1);
    dk0 <- (dkp0, dt0, et0);
    dk1 <- (dkp1, dt1, et1);
  }
}.

(* Inner PQ challenger: both PQ keygens. *)
module C (KP : KEMPQ) = {
  var dk0 : dk_pq
  var dk1 : dk_pq
  proc initialize() : ek_pq * dk_pq * ek_pq * dk_pq = {
    var ekp0, ekp1 : ek_pq; var dkp0, dkp1 : dk_pq;
    (ekp0, dkp0) <@ KP.keygen();
    (ekp1, dkp1) <@ KP.keygen();
    dk0 <- dkp0;
    dk1 <- dkp1;
    return (ekp0, dkp0, ekp1, dkp1);
  }
}.

(* Reduction side: grouped. *)
module R (KP : KEMPQ, NG : NGT) = {
  var dk_pq_0, dk_pq_1 : dk_pq
  var dk_t_0, dk_t_1 : scalar
  var ek_t_0, ek_t_1 : elt
  proc initialize() : unit = {
    var t : ek_pq * dk_pq * ek_pq * dk_pq;
    var ekp0, ekp1 : ek_pq; var dkp0, dkp1 : dk_pq;
    var s0, s1 : seed; var dt0, dt1 : scalar;
    var r0, r1 : elt; var et0, et1 : elt;
    t <@ C(KP).initialize();
    (ekp0, dkp0, ekp1, dkp1) <- t;
    dk_pq_0 <- dkp0;
    dk_pq_1 <- dkp1;
    s0 <$ dseed;
    s1 <$ dseed;
    dt0 <@ NG.randomscalar(s0);
    dt1 <@ NG.randomscalar(s1);
    r0 <@ NG.generator();
    et0 <@ NG.exp(r0, dt0);
    r1 <@ NG.generator();
    et1 <@ NG.exp(r1, dt1);
    dk_t_0 <- dt0; ek_t_0 <- et0;
    dk_t_1 <- dt1; ek_t_1 <- et1;
  }
}.

lemma init_reorder (KP <: KEMPQ {-G, -C, -R}) (NG <: NGT {-G, -C, -R, -KP}) :
  equiv [ G(KP, NG).initialize ~ R(KP, NG).initialize :
     ={glob KP, glob NG} ==>
       ={glob KP, glob NG}
    /\ G.dk0{1} = (R.dk_pq_0, R.dk_t_0, R.ek_t_0){2}
    /\ G.dk1{1} = (R.dk_pq_1, R.dk_t_1, R.ek_t_1){2}
    /\ R.dk_pq_0{2} = C.dk0{2}
    /\ R.dk_pq_1{2} = C.dk1{2} ].
proof.
proc.
inline C(KP).initialize.
swap{1} 6 -4.
wp.
swap{1} 7 -3.
seq 4 10 : ((glob KP){1} = (glob KP){2} /\ (glob NG){1} = (glob NG){2} /\ dkp0{1} = R.dk_pq_0{2} /\ dkp1{1} = R.dk_pq_1{2} /\ R.dk_pq_0{2} = C.dk0{2} /\ R.dk_pq_1{2} = C.dk1{2} /\ s0{1} = s0{2} /\ s1{1} = s1{2}).
rnd; rnd; wp; call (_: true); call (_: true); auto.
exists* (glob NG){2}, s0{2}, s1{2}; elim* => g2 es0 es1.
call{2} (NG_exp_det NG g2 ev_generator (ev_randomscalar es1)); call{2} (NG_generator_det NG g2); call{2} (NG_exp_det NG g2 ev_generator (ev_randomscalar es0)); call{2} (NG_generator_det NG g2); call{2} (NG_randomscalar_det NG g2 es1); call{2} (NG_randomscalar_det NG g2 es0).
exists* (glob NG){1}, s0{1}, s1{1}; elim* => g1 fs0 fs1.
call{1} (NG_exp_det NG g1 ev_generator (ev_randomscalar fs1)); call{1} (NG_generator_det NG g1); call{1} (NG_randomscalar_det NG g1 fs1); call{1} (NG_exp_det NG g1 ev_generator (ev_randomscalar fs0)); call{1} (NG_generator_det NG g1); call{1} (NG_randomscalar_det NG g1 fs0).
skip => /#.
qed.
