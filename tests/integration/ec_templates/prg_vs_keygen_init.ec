(* Tripwire: the hop_14 `initialize` shape -- a KeyGenEquiv-grouped reduction
 * against a PRG-query reduction, i.e. FOUR independent samples against TWO full
 * seeds that are each sliced.
 *
 * This is the last of the four `initialize` shapes on the CFRG HON cells, and
 * closing it is what turns hop_14's cross-stage coupling from ASSUMED into
 * EC-CHECKED.
 *
 * It assembles four separately-validated pieces:
 *   - split_uniform_couple.ec  : the two-samples-vs-one-full-seed coupling,
 *                                using the DLET-form split axiom;
 *   - swap_sample_past_call.ec : `swap` lifts a sample past an abstract
 *                                probabilistic call, so the samples belonging to
 *                                one full seed can be made ADJACENT (`rndsem`
 *                                folds only CONSECUTIVE samples);
 *   - the virtual concat triple + its dlet-form split axiom, which the exporter
 *     now emits on demand for a type that is sliced but never concatenated.
 *
 * Side 1 draws pq_seed_0, pq_seed_1, t_seed_0, t_seed_1 (the pq seeds come from
 * its KeyGenEquiv challenger's Generate); side 2 draws full_0, full_1 and slices
 * each into (pq, t). The post is the usual pair: `pq_keys_k` equal, plus the
 * cross-stage `t_keys_k{2} = ev_derivekeypair (seed_T_k{1})`.
 *
 * FINDINGS recorded by this file:
 *   - STATEMENT POSITIONS for `swap` are the POST-`inline *` ones. The samples
 *     sit at 1, 4, 7, 8 after inlining, not at their source positions; a first
 *     attempt using the un-inlined 5/7 was rejected with "the two statements are
 *     not independent".
 *   - `rndsem*{i} 0` folds a pair of samples even when one target is a GLOBAL
 *     (module) variable, not just a local -- which is the case that matters,
 *     since the seeds are reduction FIELDS in the real hop.
 *   - side 2's T calls are INTERLEAVED between the keypairs while side 1's are
 *     both at the end; one `swap{2}` restores the shape the one-sided `_det`
 *     peel needs (the call must be the LAST statement).
 *   - the split-uniform closer transplants VERBATIM from
 *     split_uniform_couple.ec: `skip => />` leaves the pure obligation with no
 *     memories to introduce, so no `move => &1 &2` may precede it.
 *)

require import AllCore Distr.

type pqs, ts, fulls, pkt, skt, tkt, tst.

op dpqs : pqs distr.
op dts : ts distr.
op dfulls : fulls distr.

axiom dpqs_ll : is_lossless dpqs.
axiom dts_ll : is_lossless dts.

op concat : pqs -> ts -> fulls.
op slice_l : fulls -> pqs.
op slice_r : fulls -> ts.

op ev_dkp_t : ts -> tkt * tst.

(* the virtual concat triple's axioms, as the exporter emits them *)
axiom slice_concat_left  : forall a b, slice_l (concat a b) = a.
axiom slice_concat_right : forall a b, slice_r (concat a b) = b.
axiom concat_slices_id   : forall s, concat (slice_l s) (slice_r s) = s.
axiom dfulls_split_dlet :
  dfulls = dlet dpqs (fun (v1 : pqs) => dmap dts (fun (v2 : ts) => concat v1 v2)).

module type KEMP = { proc derivekeypair (s : pqs) : pkt * skt }.
module type KEMT = { proc derivekeypair (s : ts) : tkt * tst }.

(* side 1's challenger: KeyGenEquiv FromDeriveKeyPair *)
module ChalKG (P : KEMP) = {
  proc generate () : pkt * skt = {
    var s : pqs;
    var r : pkt * skt;
    s <$ dpqs;
    r <@ P.derivekeypair(s);
    return r;
  }
}.

(* side 2's challenger: PRGSec_Random -- one uniform FULL seed *)
module ChalPRG = {
  proc query () : fulls = {
    var r : fulls;
    r <$ dfulls;
    return r;
  }
}.

module RedKG (P : KEMP, T : KEMT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var seed_T_0, seed_T_1 : ts

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var u0, u1 : tkt * tst;
    var ek0, ek1 : tkt;
    pq_keys_0 <@ ChalKG(P).generate();
    pq_keys_1 <@ ChalKG(P).generate();
    seed_T_0 <$ dts;
    seed_T_1 <$ dts;
    u0 <@ T.derivekeypair(seed_T_0);
    ek0 <- u0.`1;
    u1 <@ T.derivekeypair(seed_T_1);
    ek1 <- u1.`1;
    return ((pq_keys_0.`1, ek0), (pq_keys_1.`1, ek1));
  }
}.

module RedPRG (P : KEMP, T : KEMT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var t_keys_0, t_keys_1 : tkt * tst

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var f0, f1 : fulls;
    var sp0, sp1 : pqs;
    var st0, st1 : ts;
    f0 <@ ChalPRG.query();
    sp0 <- slice_l f0;
    st0 <- slice_r f0;
    pq_keys_0 <@ P.derivekeypair(sp0);
    t_keys_0 <@ T.derivekeypair(st0);
    f1 <@ ChalPRG.query();
    sp1 <- slice_l f1;
    st1 <- slice_r f1;
    pq_keys_1 <@ P.derivekeypair(sp1);
    t_keys_1 <@ T.derivekeypair(st1);
    return ((pq_keys_0.`1, t_keys_0.`1), (pq_keys_1.`1, t_keys_1.`1));
  }
}.

section Main.

declare module P <: KEMP {-RedKG, -RedPRG}.
declare module T <: KEMT {-RedKG, -RedPRG, -P}.

declare axiom T_derivekeypair_det (g : (glob T)) (a0 : ts) :
  phoare[ T.derivekeypair : (glob T) = g /\ s = a0
          ==> (glob T) = g /\ res = ev_dkp_t a0 ] = 1%r.

lemma prg_vs_keygen_init :
  equiv [ RedKG(P, T).initialize ~ RedPRG(P, T).initialize :
          ={glob P, glob T}
          ==> ={res} /\ ={glob P, glob T}
              /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
              /\ RedKG.pq_keys_1{1} = RedPRG.pq_keys_1{2}
              /\ RedPRG.t_keys_0{2} = ev_dkp_t RedKG.seed_T_0{1}
              /\ RedPRG.t_keys_1{2} = ev_dkp_t RedKG.seed_T_1{1} ].
proof.
  proc.
  inline *.
  (* Make each (pq_seed, t_seed) pair ADJACENT so `rndsem` can fold it.
     Order matters: lift t0 first, then t1 -- see swap_sample_past_call.ec. *)
  (* post-inline side 1 is
       1 s<$  2 P.dkp  3 pq_keys_0<-  4 s0<$  5 P.dkp  6 pq_keys_1<-
       7 t0<$ 8 t1<$   9 T.dkp 10 ek0<- 11 T.dkp 12 ek1<-
     so the samples sit at 1, 4, 7, 8 and the pairing wanted is (1,7) / (4,8). *)
  swap{1} 7 -5.
  swap{1} 8 -2.
  (* post-inline side 2 is
       1 r<$dfulls 2 f0<- 3 sp0<- 4 st0<- 5 P.dkp 6 T.dkp
       7 r0<$      8 f1<- 9 sp1<- 10 st1<- 11 P.dkp 12 T.dkp
     so side 2's T calls are INTERLEAVED where side 1's are both at the end.
     Push the first one down so both sides end with their two T calls -- the
     one-sided `_det` peel needs the call to be the LAST statement. *)
  swap{2} 6 5.
  (* keypair 0 seeds: two independent samples against one sliced full seed *)
  seq 2 4 : (={glob P, glob T}
             /\ s{1} = sp0{2}
             /\ RedKG.seed_T_0{1} = st0{2}).
  + wp.
    rndsem*{1} 0.
    rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
        (fun (sf : fulls) => (slice_l sf, slice_r sf)).
    skip => />.
    rewrite dfulls_split_dlet.
    split.
    - move => sf hsf; rewrite concat_slices_id //.
    move => _; split.
    - move => sf hsf.
      rewrite !dlet1E; congr; apply fun_ext => a /=.
      rewrite !dmap1E /(\o) /pred1 /=.
      congr; apply mu_eq => b /=.
      by rewrite eqboolP;
         smt(slice_concat_left slice_concat_right concat_slices_id).
    move => _ p hp.
    have h1 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
    have h2 : p.`2 \in dts by smt(supp_dlet supp_dmap).
    split.
    - rewrite supp_dlet; exists p.`1; rewrite h1 /=.
      by rewrite supp_dmap; exists p.`2; rewrite h2.
    move => _; smt(slice_concat_left slice_concat_right).
  (* keypair 0's pq derivekeypair: equal arguments, two-sided *)
  seq 2 1 : (={glob P, glob T}
             /\ RedKG.seed_T_0{1} = st0{2}
             /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}).
  + wp; call (_: true); skip => />.
  (* keypair 1 seeds: the same coupling on the second full seed *)
  seq 2 4 : (={glob P, glob T}
             /\ RedKG.seed_T_0{1} = st0{2}
             /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
             /\ s0{1} = sp1{2}
             /\ RedKG.seed_T_1{1} = st1{2}).
  + wp.
    rndsem*{1} 0.
    rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
        (fun (sf : fulls) => (slice_l sf, slice_r sf)).
    skip => />.
    rewrite dfulls_split_dlet.
    split.
    - move => sf hsf; rewrite concat_slices_id //.
    move => _; split.
    - move => sf hsf.
      rewrite !dlet1E; congr; apply fun_ext => a /=.
      rewrite !dmap1E /(\o) /pred1 /=.
      congr; apply mu_eq => b /=.
      by rewrite eqboolP;
         smt(slice_concat_left slice_concat_right concat_slices_id).
    move => _ p hp.
    have h2 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
    have h3 : p.`2 \in dts by smt(supp_dlet supp_dmap).
    split.
    - rewrite supp_dlet; exists p.`1; rewrite h2 /=.
      by rewrite supp_dmap; exists p.`2; rewrite h3.
    move => _; smt(slice_concat_left slice_concat_right).
  (* keypair 1's pq derivekeypair *)
  seq 2 1 : (={glob P, glob T}
             /\ RedKG.seed_T_0{1} = st0{2}
             /\ RedKG.seed_T_1{1} = st1{2}
             /\ RedKG.pq_keys_0{1} = RedPRG.pq_keys_0{2}
             /\ RedKG.pq_keys_1{1} = RedPRG.pq_keys_1{2}).
  + wp; call (_: true); skip => />.
  (* both t derivekeypairs, peeled ONE-SIDED back to front so the post learns the
     VALUE (a two-sided `call (_: true)` would only give `={res}`). *)
  exists* (glob T){1}, RedKG.seed_T_0{1}, RedKG.seed_T_1{1}.
  elim* => gT sv0 sv1.
  wp.
  call{2} (T_derivekeypair_det gT sv1).
  call{1} (T_derivekeypair_det gT sv1).
  wp.
  call{2} (T_derivekeypair_det gT sv0).
  call{1} (T_derivekeypair_det gT sv0).
  skip => />.
qed.

end section Main.
