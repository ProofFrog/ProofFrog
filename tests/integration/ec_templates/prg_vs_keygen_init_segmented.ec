(* Tripwire: the hop_14 `initialize` shape, SEGMENTED -- and this is the variant
 * the exporter emits. It supersedes prg_vs_keygen_init.ec as the emission
 * target; that file stays as the record of the swap/adjacency facts and of the
 * whole-body route.
 *
 * WHY A SECOND FILE. The whole-body route needs ONE top-level `inline *`, which
 * inlines BOTH copies of the challenger's `generate` and so forces the tactic to
 * PREDICT EC's collision suffix for the second copy's sample (`seed` -> `seed0`).
 * Predicting inline names is the exact fragility this project keeps designing
 * out. Cutting one `seq` per keypair FIRST and putting `inline *` inside each
 * bullet leaves a single `generate` per goal, so its sample is the bare source
 * name every time and no suffix is ever named.
 *
 * The bodies below are the REAL CK_seedbased_HON_BIND hop_14 bodies, copied
 * statement-for-statement from the export (including the two projections per
 * keypair, `ek_T`/`dk_T`, which the first tripwire simplified to one, and the
 * real challenger modules `KeyGenEquiv_FromDeriveKeyPair` / `PRGSec_Random`,
 * whose inlined lengths set every index used below).
 *
 * Recipe, in the order emitted:
 *   1. regroup side 1 per keypair on the UN-INLINED body (4 swaps for n=2) --
 *      indices are exact there because the exporter rendered those bodies;
 *   2. one `seq 5 5` per keypair;
 *   3. inside each bullet `inline *`, then ONE swap to make the keypair's two
 *      samples adjacent, then the split-uniform coupling (`seq 2 4`), the
 *      two-sided pq peel (`seq 2 1`), and the one-sided `_det` peel of the
 *      t derivekeypair.
 *
 * The split-uniform closer is transplanted verbatim from
 * split_uniform_couple.ec; the four axioms it needs are what the exporter's
 * virtual concat triple emits on demand for a type that is sliced but never
 * concatenated.
 *)

require import AllCore Distr.

type pqs, ts, fulls, pkt, skt, tkt, tst.

op dpqs : pqs distr.
op dts : ts distr.
op dfulls : fulls distr.

axiom dpqs_ll : is_lossless dpqs.
axiom dts_ll : is_lossless dts.

(* the REAL slice ops carry explicit OFFSET arguments, and the emitted axioms
   are stated at exactly the offsets the reduction bodies use -- model that, or
   the closer is validated against a shape the exporter never produces *)
op nl : int.
op nr : int.

op concat : pqs -> ts -> fulls.
op slice_l : fulls -> int -> int -> pqs.
op slice_r : fulls -> int -> int -> ts.

op ev_dkp_t : ts -> tkt * tst.

(* the virtual concat triple's axioms, as the exporter emits them *)
axiom slice_concat_left  : forall a b, slice_l (concat a b) 0 nl = a.
axiom slice_concat_right : forall a b, slice_r (concat a b) nl (nl + nr) = b.
axiom concat_slices_id   :
  forall s, concat (slice_l s 0 nl) (slice_r s nl (nl + nr)) = s.
axiom dfulls_split_dlet :
  dfulls = dlet dpqs (fun (v1 : pqs) => dmap dts (fun (v2 : ts) => concat v1 v2)).

module type KEMP = { proc derivekeypair (s : pqs) : pkt * skt }.
module type KEMT = { proc derivekeypair (s : ts) : tkt * tst }.

module type KGE = { proc generate () : pkt * skt }.
module type PRGO = { proc query () : fulls }.

(* both challengers exactly as the exporter renders them *)
module KeyGenEquiv_FromDeriveKeyPair (K : KEMP) : KGE = {
  proc generate () : pkt * skt = {
    var seed : pqs;
    var _r0 : pkt * skt;
    seed <$ dpqs;
    _r0 <@ K.derivekeypair(seed);
    return _r0;
  }
}.

module PRGSec_Random : PRGO = {
  proc query () : fulls = {
    var r : fulls;
    r <$ dfulls;
    return r;
  }
}.

module RedKG (P : KEMP, T : KEMT, Challenger : KGE) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var seed_T_0, seed_T_1 : ts

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var _tup : tkt * tst;
    var ek_T : tkt;
    var dk_T : tst;
    var _tup_0 : tkt * tst;
    var ek_T2 : tkt;
    var dk_unused : tst;
    pq_keys_0 <@ Challenger.generate();
    pq_keys_1 <@ Challenger.generate();
    seed_T_0 <$ dts;
    seed_T_1 <$ dts;
    _tup <@ T.derivekeypair(seed_T_0);
    ek_T <- _tup.`1;
    dk_T <- _tup.`2;
    _tup_0 <@ T.derivekeypair(seed_T_1);
    ek_T2 <- _tup_0.`1;
    dk_unused <- _tup_0.`2;
    return ((pq_keys_0.`1, ek_T), (pq_keys_1.`1, ek_T2));
  }
}.

module RedPRG (P : KEMP, T : KEMT, Challenger : PRGO) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var t_keys_0, t_keys_1 : tkt * tst

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var seed_full_0 : fulls;
    var seed_PQ_0 : pqs;
    var seed_T_0 : ts;
    var seed_full_1 : fulls;
    var seed_PQ_1 : pqs;
    var seed_T_1 : ts;
    seed_full_0 <@ Challenger.query();
    seed_PQ_0 <- slice_l seed_full_0 0 nl;
    seed_T_0 <- slice_r seed_full_0 nl (nl + nr);
    pq_keys_0 <@ P.derivekeypair(seed_PQ_0);
    t_keys_0 <@ T.derivekeypair(seed_T_0);
    seed_full_1 <@ Challenger.query();
    seed_PQ_1 <- slice_l seed_full_1 0 nl;
    seed_T_1 <- slice_r seed_full_1 nl (nl + nr);
    pq_keys_1 <@ P.derivekeypair(seed_PQ_1);
    t_keys_1 <@ T.derivekeypair(seed_T_1);
    return ((pq_keys_0.`1, t_keys_0.`1), (pq_keys_1.`1, t_keys_1.`1));
  }
}.

section Main.

declare module P <: KEMP {-RedKG, -RedPRG}.
declare module T <: KEMT {-RedKG, -RedPRG, -P}.

declare axiom T_derivekeypair_det (g : (glob T)) (a0 : ts) :
  phoare[ T.derivekeypair : (glob T) = g /\ s = a0
          ==> (glob T) = g /\ res = ev_dkp_t a0 ] = 1%r.

lemma prg_vs_keygen_init_segmented :
  equiv [ RedKG(P, T, KeyGenEquiv_FromDeriveKeyPair(P)).initialize
          ~ RedPRG(P, T, PRGSec_Random).initialize :
          ={glob P, glob T}
          ==> ={res} /\ ={glob P, glob T}
              /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
              /\ RedKG.pq_keys_1{1} = RedPRG.pq_keys_1{2}
              /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
              /\ RedPRG.t_keys_1{2} = ev_dkp_t RedKG.seed_T_1{1} ].
proof.
  proc.
  (* 1. REGROUP side 1 per keypair, on the UN-INLINED body. Side 1 runs both
        challenger generates first, then both t seeds, then both t
        derivekeypairs with their projections:
          1 Gen0  2 Gen1  3 s0<$  4 s1<$
          5 dkp0  6 ek_T  7 dk_T  8 dkp1  9 ek_T2  10 dk_unused
        and keypair 0's material is 1,3,5,6,7. Four swaps bring it together.
        Side 2 is already grouped per keypair (1-5 and 6-10), so it needs none. *)
  swap{1} 3 -1.
  swap{1} 5 -2.
  swap{1} 6 -2.
  swap{1} 7 -2.
  (* 2. keypair 0 *)
  seq 5 5 : (={glob P, glob T}
             /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
             /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
             /\ _tup{1} = ev_dkp_t RedKG.seed_T_0{1}
             /\ ek_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`1
             /\ dk_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`2).
  + inline *.
    (* one `generate` and one `query` in this goal, so every inlined local keeps
       its bare source name -- no collision suffix is ever predicted. Side 1 is
         1 seed<$  2 P.dkp  3 pq_keys_0<-  4 seed_T_0<$  5 T.dkp  6 ek_T  7 dk_T
       so one swap makes the keypair's two samples adjacent. *)
    swap{1} 4 -2.
    seq 2 4 : (={glob P, glob T}
               /\ seed{1} = seed_PQ_0{2}
               /\ RedKG.seed_T_0{1} = seed_T_0{2}).
    - wp.
      rndsem*{1} 0.
      rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
          (fun (sf : fulls) => (slice_l sf 0 nl, slice_r sf nl (nl + nr))).
      skip => />.
      rewrite dfulls_split_dlet.
      split.
      * move => sf hsf; rewrite concat_slices_id //.
      move => _; split.
      * move => sf hsf.
        rewrite !dlet1E; congr; apply fun_ext => a /=.
        rewrite !dmap1E /(\o) /pred1 /=.
        congr; apply mu_eq => b /=.
        by rewrite eqboolP;
           smt(slice_concat_left slice_concat_right concat_slices_id).
      move => _ p hp.
      have h1 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
      have h2 : p.`2 \in dts by smt(supp_dlet supp_dmap).
      split.
      * rewrite supp_dlet; exists p.`1; rewrite h1 /=.
        by rewrite supp_dmap; exists p.`2; rewrite h2.
      move => _; smt(slice_concat_left slice_concat_right).
    seq 2 1 : (={glob P, glob T}
               /\ RedKG.seed_T_0{1} = seed_T_0{2}
               /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}).
    - wp; call (_: true); skip => />.
    exists* (glob T){1}, RedKG.seed_T_0{1}.
    elim* => gT sv.
    wp.
    call{2} (T_derivekeypair_det gT sv).
    call{1} (T_derivekeypair_det gT sv).
    skip => />.
  (* 3. keypair 1 -- identical shape, invariant carries keypair 0's conjuncts *)
  seq 5 5 : (={glob P, glob T}
             /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
             /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
             /\ _tup{1} = ev_dkp_t RedKG.seed_T_0{1}
             /\ ek_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`1
             /\ dk_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`2
             /\ RedKG.pq_keys_1{1} = RedPRG.pq_keys_1{2}
             /\ RedPRG.t_keys_1{2} = ev_dkp_t RedKG.seed_T_1{1}
             /\ _tup_0{1} = ev_dkp_t RedKG.seed_T_1{1}
             /\ ek_T2{1} = (ev_dkp_t RedKG.seed_T_1{1}).`1
             /\ dk_unused{1} = (ev_dkp_t RedKG.seed_T_1{1}).`2).
  + inline *.
    swap{1} 4 -2.
    seq 2 4 : (={glob P, glob T}
               /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
               /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
               /\ _tup{1} = ev_dkp_t RedKG.seed_T_0{1}
               /\ ek_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`1
               /\ dk_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`2
               /\ seed{1} = seed_PQ_1{2}
               /\ RedKG.seed_T_1{1} = seed_T_1{2}).
    - wp.
      rndsem*{1} 0.
      rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
          (fun (sf : fulls) => (slice_l sf 0 nl, slice_r sf nl (nl + nr))).
      skip => />.
      rewrite dfulls_split_dlet.
      split.
      * move => sf hsf; rewrite concat_slices_id //.
      move => _; split.
      * move => sf hsf.
        rewrite !dlet1E; congr; apply fun_ext => a /=.
        rewrite !dmap1E /(\o) /pred1 /=.
        congr; apply mu_eq => b /=.
        by rewrite eqboolP;
           smt(slice_concat_left slice_concat_right concat_slices_id).
      move => _ p hp.
      have h1 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
      have h2 : p.`2 \in dts by smt(supp_dlet supp_dmap).
      split.
      * rewrite supp_dlet; exists p.`1; rewrite h1 /=.
        by rewrite supp_dmap; exists p.`2; rewrite h2.
      move => _; smt(slice_concat_left slice_concat_right).
    seq 2 1 : (={glob P, glob T}
               /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
               /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
               /\ _tup{1} = ev_dkp_t RedKG.seed_T_0{1}
               /\ ek_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`1
               /\ dk_T{1} = (ev_dkp_t RedKG.seed_T_0{1}).`2
               /\ RedKG.seed_T_1{1} = seed_T_1{2}
               /\ RedKG.pq_keys_1{1} = RedPRG.pq_keys_1{2}).
    - wp; call (_: true); skip => />.
    exists* (glob T){1}, RedKG.seed_T_1{1}.
    elim* => gT sv.
    wp.
    call{2} (T_derivekeypair_det gT sv).
    call{1} (T_derivekeypair_det gT sv).
    skip => />.
  skip => />.
qed.

end section Main.
