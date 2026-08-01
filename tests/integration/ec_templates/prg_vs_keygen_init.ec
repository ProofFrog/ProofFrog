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
 * STATUS: IN PROGRESS -- this file does NOT close yet. Validated so far: the
 * module shapes match the real hop_14 bodies, and the two `swap`s that make each
 * (pq_seed, t_seed) pair adjacent are accepted by EC on that real shape. What
 * remains is the fold-and-couple tail: `rndsem*{1} 0` per adjacent pair, then the
 * two-sided `rnd` bijection, per split_uniform_couple.ec. The trailing `admit.`
 * marks exactly that boundary.
 *)

require import AllCore Distr.

type pqs, ts, fulls, pkt, skt, tkt, tst.

op dpqs : pqs distr.
op dts : ts distr.
op dfulls : fulls distr.

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
  admit.
qed.

end section Main.
