(* ============================================================ *)
(* UK/CG seedbased PK-binding: the INIT-oracle peel must         *)
(* FUNCTIONALIZE the keygen det-call chain so the ek-derivation  *)
(* coupling is provable in the init post.                        *)
(*                                                               *)
(* Models hop_0_initialize of UK_seedbased_LEAK_BIND_K_PK: both  *)
(* the game (Gm) and the reduction (R) run the seedbased KeyGen  *)
(*   seed  <$ dseed;                                             *)
(*   full  <- G.evaluate(seed);        [PRG stretch]             *)
(*   spq   <- sl_pq full;  st <- sl_t full;                      *)
(*   tpq   <- KP.derivekeypair(spq);   [KEM_PQ]                  *)
(*   tt    <- KT.derivekeypair(st);    [KEM_T]                   *)
(*   ek    <- (tpq.1, tt.1);           [hybrid EncapsKey]        *)
(* storing (ek, seed) in its own fields.  The live-state         *)
(* coupling includes the ek-DERIVATION conjunct                  *)
(*   (R.ek, R.seed) =                                            *)
(*     ( ( fst (ev_dkp_pq (sl_pq (ev_evaluate seed))),           *)
(*         fst (ev_dkp_t  (sl_t  (ev_evaluate seed))) ), seed )  *)
(* which links R's OPAQUE held EncapsKey to the seed-derived     *)
(* component keys the KDF binds -- WITHOUT it a PK redundancy    *)
(* cannot reach R.ek.                                            *)
(*                                                               *)
(* THE BLOCKER (iter 7): the historical init backbone peel uses  *)
(* abstract `call (_: true)`, so tpq/tt stay free vars -- never  *)
(* `ev_dkp_pq ...` -- and the ek-coupling post is UNPROVABLE.    *)
(*                                                               *)
(* THE FIX (validated here): a top-down `seq 1 1` peel that      *)
(* FUNCTIONALIZES each det call on BOTH sides with its `_det`    *)
(* phoare via `exists* (glob M){i}, arg{i}; elim*; call{i}       *)
(* (M_m_det g a)`.  `seq` captures the live proc locals at each  *)
(* point (NOT inline-frozen names), so the args are in scope.    *)
(*                                                               *)
(* NON-VACUITY: `init_bad` (abstract `call (_: true)`) is kept   *)
(* commented -- it leaves the ek-coupling open (a wrong coupling *)
(* an admit would swallow), so the functionalization is required.*)
(* ============================================================ *)

require import AllCore Distr.

type seed_t, full_t, spq_t, st_t, ekpq_t, dkpq_t, ekt_t, dkt_t.

op dseed : seed_t distr.
axiom dseed_ll : is_lossless dseed.

(* functional values of the deterministic methods *)
op ev_evaluate : seed_t -> full_t.
op ev_dkp_pq   : spq_t -> ekpq_t * dkpq_t.
op ev_dkp_t    : st_t  -> ekt_t  * dkt_t.
op sl_pq : full_t -> spq_t.
op sl_t  : full_t -> st_t.

module type PRG   = { proc evaluate(seed : seed_t) : full_t }.
module type KEMPQ = { proc derivekeypair(seed : spq_t) : ekpq_t * dkpq_t }.
module type KEMT  = { proc derivekeypair(seed : st_t)  : ekt_t  * dkt_t }.

(* determinism specs (the exporter's `<M>_<m>_det` axioms) *)
axiom G_evaluate_det (G <: PRG) (g : (glob G)) (a0 : seed_t) :
  phoare[ G.evaluate : (glob G) = g /\ seed = a0
          ==> (glob G) = g /\ res = ev_evaluate a0 ] = 1%r.
axiom KP_derivekeypair_det (KP <: KEMPQ) (g : (glob KP)) (a0 : spq_t) :
  phoare[ KP.derivekeypair : (glob KP) = g /\ seed = a0
          ==> (glob KP) = g /\ res = ev_dkp_pq a0 ] = 1%r.
axiom KT_derivekeypair_det (KT <: KEMT) (g : (glob KT)) (a0 : st_t) :
  phoare[ KT.derivekeypair : (glob KT) = g /\ seed = a0
          ==> (glob KT) = g /\ res = ev_dkp_t a0 ] = 1%r.

(* game side: stores the EncapsKey (gek) + DecapsKey/seed (gseed). *)
module Gm (G : PRG) (KP : KEMPQ) (KT : KEMT) = {
  var gek : ekpq_t * ekt_t
  var gseed : seed_t
  proc initialize() : unit = {
    var seed, full, spq, st, tpq, tt;
    seed <$ dseed;
    full <@ G.evaluate(seed);
    spq  <- sl_pq full;
    st   <- sl_t full;
    tpq  <@ KP.derivekeypair(spq);
    tt   <@ KT.derivekeypair(st);
    gek   <- (tpq.`1, tt.`1);
    gseed <- seed;
  }
}.

(* reduction side: identical body, stores rek + rseed. *)
module R (G : PRG) (KP : KEMPQ) (KT : KEMT) = {
  var rek : ekpq_t * ekt_t
  var rseed : seed_t
  proc initialize() : unit = {
    var seed, full, spq, st, tpq, tt;
    seed <$ dseed;
    full <@ G.evaluate(seed);
    spq  <- sl_pq full;
    st   <- sl_t full;
    tpq  <@ KP.derivekeypair(spq);
    tt   <@ KT.derivekeypair(st);
    rek   <- (tpq.`1, tt.`1);
    rseed <- seed;
  }
}.

(* The init micro ESTABLISHES the full coupling incl. the ek-derivation. *)
lemma init_ek_peel
  (G <: PRG {-Gm, -R}) (KP <: KEMPQ {-Gm, -R, -G})
  (KT <: KEMT {-Gm, -R, -G, -KP}) :
  equiv [ Gm(G, KP, KT).initialize ~ R(G, KP, KT).initialize :
      ={glob G, glob KP, glob KT} ==>
        ={glob G, glob KP, glob KT}
     /\ Gm.gek{1} = R.rek{2}
     /\ Gm.gseed{1} = R.rseed{2}
     /\ (R.rek{2}, R.rseed{2}) =
        ( ( (ev_dkp_pq (sl_pq (ev_evaluate R.rseed{2}))).`1,
            (ev_dkp_t  (sl_t  (ev_evaluate R.rseed{2}))).`1 ),
          R.rseed{2} ) ].
proof.
  proc.
  (* the seed sample: couple seed{1}=seed{2}. *)
  seq 1 1 : (={glob G, glob KP, glob KT, seed}).
  + rnd; skip => />.
  (* functionalize G.evaluate on both sides. *)
  seq 1 1 : (={glob G, glob KP, glob KT, seed}
             /\ full{1} = ev_evaluate seed{1}
             /\ full{2} = ev_evaluate seed{2}).
  + exists* (glob G){1}, seed{1}; elim* => g1 s1.
    exists* (glob G){2}, seed{2}; elim* => g2 s2.
    call{1} (G_evaluate_det G g1 s1).
    call{2} (G_evaluate_det G g2 s2).
    skip => />.
  (* the two deterministic slices. *)
  seq 2 2 : (={glob G, glob KP, glob KT, seed}
             /\ full{1} = ev_evaluate seed{1}
             /\ full{2} = ev_evaluate seed{2}
             /\ spq{1} = sl_pq full{1} /\ st{1} = sl_t full{1}
             /\ spq{2} = sl_pq full{2} /\ st{2} = sl_t full{2}).
  + wp; skip => />.
  (* functionalize KP.derivekeypair on both sides. *)
  seq 1 1 : (={glob G, glob KP, glob KT, seed}
             /\ full{1} = ev_evaluate seed{1} /\ full{2} = ev_evaluate seed{2}
             /\ spq{1} = sl_pq full{1} /\ st{1} = sl_t full{1}
             /\ spq{2} = sl_pq full{2} /\ st{2} = sl_t full{2}
             /\ tpq{1} = ev_dkp_pq spq{1} /\ tpq{2} = ev_dkp_pq spq{2}).
  + exists* (glob KP){1}, spq{1}; elim* => g1 a1.
    exists* (glob KP){2}, spq{2}; elim* => g2 a2.
    call{1} (KP_derivekeypair_det KP g1 a1).
    call{2} (KP_derivekeypair_det KP g2 a2).
    skip => />.
  (* functionalize KT.derivekeypair on both sides. *)
  seq 1 1 : (={glob G, glob KP, glob KT, seed}
             /\ full{1} = ev_evaluate seed{1} /\ full{2} = ev_evaluate seed{2}
             /\ spq{1} = sl_pq full{1} /\ st{1} = sl_t full{1}
             /\ spq{2} = sl_pq full{2} /\ st{2} = sl_t full{2}
             /\ tpq{1} = ev_dkp_pq spq{1} /\ tpq{2} = ev_dkp_pq spq{2}
             /\ tt{1} = ev_dkp_t st{1} /\ tt{2} = ev_dkp_t st{2}).
  + exists* (glob KT){1}, st{1}; elim* => g1 a1.
    exists* (glob KT){2}, st{2}; elim* => g2 a2.
    call{1} (KT_derivekeypair_det KT g1 a1).
    call{2} (KT_derivekeypair_det KT g2 a2).
    skip => />.
  (* the two field stores; everything is now in ev-form. *)
  wp; skip => />.
qed.

(* NON-VACUITY: the historical abstract peel does NOT close it -- keep tpq/tt
   free (never ev_dkp_pq/ev_dkp_t), so the ek-derivation conjunct is left
   OPEN.  This is exactly the real hop_0_initialize failure (the full UK PK
   export rejected at the same conjunct).  Kept commented so the tripwire
   compiles; uncomment to reconfirm the abstract peel leaves an open goal
   (a wrong ek-coupling an admit would swallow -- hence functionalize).

lemma init_ek_peel_bad
  (G <: PRG {-Gm, -R}) (KP <: KEMPQ {-Gm, -R, -G})
  (KT <: KEMT {-Gm, -R, -G, -KP}) :
  equiv [ Gm(G, KP, KT).initialize ~ R(G, KP, KT).initialize :
      ={glob G, glob KP, glob KT} ==>
        ={glob G, glob KP, glob KT}
     /\ Gm.gek{1} = R.rek{2} /\ Gm.gseed{1} = R.rseed{2}
     /\ (R.rek{2}, R.rseed{2}) =
        ( ( (ev_dkp_pq (sl_pq (ev_evaluate R.rseed{2}))).`1,
            (ev_dkp_t  (sl_t  (ev_evaluate R.rseed{2}))).`1 ),
          R.rseed{2} ) ].
proof.
  proc. wp. call (_: true). call (_: true). wp. call (_: true). auto.
qed.
*)
