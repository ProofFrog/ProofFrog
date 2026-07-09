(* ============================================================ *)
(* CFRG binding -- TWO-KEM init-backbone peel ALIGNMENT.         *)
(*                                                               *)
(* Models CK_expanded_LEAK_BIND hop_0_initialize / hop_2_init:   *)
(* both endpoints do the SAME four abstract keygens (KEM_PQ x2,  *)
(* KEM_T x2) and pack the same two hybrid decaps keys, but in    *)
(* DIFFERENT ORDER:                                              *)
(*   Game side (G):  interleaved  [PQ, T, PQ, T]                 *)
(*                   (keypair0 = PQ+T, then keypair1 = PQ+T)     *)
(*   Reduction (R):  blocked      [PQ, PQ, T, T]                 *)
(*                   (inner challenger C does both PQ keygens,   *)
(*                    then R does both T keygens)                *)
(*                                                               *)
(* The existing init-backbone peel emits (wp; call (_: true))*   *)
(* sized by the LEFT backbone.  `call (_: true)` couples the two *)
(* sides' CURRENT LAST call, so it requires them to be the SAME  *)
(* abstract procedure.  With the orders mismatched it pairs      *)
(* KEM_PQ.keygen{1} with KEM_T.keygen{2} -> EC: "KEM_PQ.keygen   *)
(* and KEM_T.keygen should be equal" (CK line 10523).           *)
(*                                                               *)
(* THE FIX a permutation-aware peel must emit: `swap` one side   *)
(* so both call backbones share the SAME callee order, THEN peel.*)
(* KEM_PQ and KEM_T are DISTINCT abstract modules (disjoint      *)
(* glob), so a keygen of one is independent of a keygen of the   *)
(* other and EC `swap` accepts reordering them.                  *)
(* ============================================================ *)

require import AllCore Distr.

type ek_pq, dk_pq, ek_t, dk_t.

module type KEMPQ = { proc keygen() : ek_pq * dk_pq }.
module type KEMT  = { proc keygen() : ek_t * dk_t }.

(* Game side: interleaved [PQ, T, PQ, T]; packs two hybrid decaps keys. *)
module G (KP : KEMPQ, KT : KEMT) = {
  var dk0 : dk_pq * dk_t * ek_t
  var dk1 : dk_pq * dk_t * ek_t
  proc initialize() : unit = {
    var ekp0, ekp1 : ek_pq; var dkp0, dkp1 : dk_pq;
    var ekt0, ekt1 : ek_t;  var dkt0, dkt1 : dk_t;
    (ekp0, dkp0) <@ KP.keygen();
    (ekt0, dkt0) <@ KT.keygen();
    (ekp1, dkp1) <@ KP.keygen();
    (ekt1, dkt1) <@ KT.keygen();
    dk0 <- (dkp0, dkt0, ekt0);
    dk1 <- (dkp1, dkt1, ekt1);
  }
}.

(* Inner PQ challenger: does BOTH PQ keygens, holds both PQ decaps keys. *)
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

(* Reduction side: blocked [PQ, PQ, T, T]; DECOMPOSED component fields. *)
module R (KP : KEMPQ, KT : KEMT) = {
  var dk_pq_0, dk_pq_1 : dk_pq
  var dk_t_0, dk_t_1 : dk_t
  var ek_t_0, ek_t_1 : ek_t
  proc initialize() : unit = {
    var t : ek_pq * dk_pq * ek_pq * dk_pq;
    var ekp0, ekp1 : ek_pq; var dkp0, dkp1 : dk_pq;
    var ekt0, ekt1 : ek_t;  var dkt0, dkt1 : dk_t;
    t <@ C(KP).initialize();
    (ekp0, dkp0, ekp1, dkp1) <- t;
    dk_pq_0 <- dkp0;
    dk_pq_1 <- dkp1;
    (ekt0, dkt0) <@ KT.keygen();
    (ekt1, dkt1) <@ KT.keygen();
    dk_t_0 <- dkt0; ek_t_0 <- ekt0;
    dk_t_1 <- dkt1; ek_t_1 <- ekt1;
  }
}.

(* The real decomposition coupling postcondition (packed game key = tuple of
   reduction components; reduction PQ component = challenger's own field). *)
lemma init_reorder (KP <: KEMPQ {-G, -C, -R}) (KT <: KEMT {-G, -C, -R, -KP}) :
  equiv [ G(KP, KT).initialize ~ R(KP, KT).initialize :
     ={glob KP, glob KT} ==>
       ={glob KP, glob KT}
    /\ G.dk0{1} = (R.dk_pq_0, R.dk_t_0, R.ek_t_0){2}
    /\ G.dk1{1} = (R.dk_pq_1, R.dk_t_1, R.ek_t_1){2}
    /\ R.dk_pq_0{2} = C.dk0{2}
    /\ R.dk_pq_1{2} = C.dk1{2} ].
proof.
  proc. inline C(KP).initialize.
  swap{2} 9 -7.
  wp. call (_: true).
  wp. call (_: true).
  wp. call (_: true).
  wp. call (_: true).
  auto.
qed.
