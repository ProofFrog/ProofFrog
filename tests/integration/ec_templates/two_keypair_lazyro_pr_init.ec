(* Tripwire: the two-keypair lazy-RO pr-init (CG PK / CG DIFFKEY hop_0_pr wall).
   Game side interleaves per-keypair [lookup; dkp; rs; gen; exp]; the reduction
   batches per-op and holds fields; the reduction ALSO samples the game's shared
   RO (dead on its side). The route under validation: couple the sample prefix
   with rnd/seq FIRST, then exists*-freeze the post-sample memory and peel every
   deterministic abstract call ONE-SIDEDLY (order-independent -- dissolves the
   interleave-vs-batch mispairing), closing with the bounded ladder. *)
require import AllCore Distr Dexcepted.

type lam, bsY, kseed, nseed, ek, dk, elem, scalar.
op dlam : lam distr.
axiom dlam_ll : is_lossless dlam.
op pred1 : lam -> lam -> bool.
op dfun : (lam -> bsY) distr.
axiom dfun_ll : is_lossless dfun.
op slice_k : bsY -> kseed.
op slice_n : bsY -> nseed.

module type K_t = { proc dkp(s : kseed) : ek * dk }.
module type NG_t = {
  proc rs(s : nseed) : scalar
  proc gen() : elem
  proc exp(b : elem, x : scalar) : elem
}.

op ev_dkp : kseed -> ek * dk.
op ev_rs : nseed -> scalar.
op ev_gen : elem.
op ev_exp : elem -> scalar -> elem.

module RO = { var h : lam -> bsY }.
module Hon = { var hh : lam -> bsY }.

module G1 (K : K_t) (NG : NG_t) = {
  var gdk0, gdk1 : lam
  var gek0, gek1 : ek * elem
  proc init() : unit = {
    var y0, y1 : bsY; var kp0, kp1 : ek * dk;
    var r0, r1 : scalar; var g0, g1 : elem; var e0, e1 : elem;
    RO.h <$ dfun;
    gdk0 <$ dlam;
    gdk1 <$ dlam \ pred1 gdk0;
    y0 <- RO.h gdk0;
    kp0 <@ K.dkp(slice_k y0);
    r0 <@ NG.rs(slice_n y0);
    g0 <@ NG.gen();
    e0 <@ NG.exp(g0, r0);
    gek0 <- (kp0.`1, e0);
    y1 <- RO.h gdk1;
    kp1 <@ K.dkp(slice_k y1);
    r1 <@ NG.rs(slice_n y1);
    g1 <@ NG.gen();
    e1 <@ NG.exp(g1, r1);
    gek1 <- (kp1.`1, e1);
  }
}.

module R1 (K : K_t) (NG : NG_t) = {
  var s0, s1 : lam
  var dkpq0, dkpq1 : dk
  var ekpq0, ekpq1 : ek
  var dkt0, dkt1 : scalar
  var ekt0, ekt1 : elem
  proc init() : unit = {
    var y0, y1 : bsY; var t0, t1 : ek * dk;
    var g0, g1 : elem;
    RO.h <$ dfun;                (* DEAD on this side *)
    Hon.hh <$ dfun;
    s0 <$ dlam;
    s1 <$ dlam \ pred1 s0;
    y0 <- Hon.hh s0;
    y1 <- Hon.hh s1;
    t0 <@ K.dkp(slice_k y0);
    ekpq0 <- t0.`1;
    dkpq0 <- t0.`2;
    t1 <@ K.dkp(slice_k y1);
    ekpq1 <- t1.`1;
    dkpq1 <- t1.`2;
    dkt0 <@ NG.rs(slice_n y0);
    dkt1 <@ NG.rs(slice_n y1);
    g0 <@ NG.gen();
    ekt0 <@ NG.exp(g0, dkt0);
    g1 <@ NG.gen();
    ekt1 <@ NG.exp(g1, dkt1);
  }
}.

section.
declare module K <: K_t{-RO, -Hon, -G1, -R1}.
declare module NG <: NG_t{-RO, -Hon, -G1, -R1, -K}.

declare axiom K_dkp_det (g : (glob K)) (a0 : kseed) :
  phoare[ K.dkp : (glob K) = g /\ s = a0 ==> (glob K) = g /\ res = ev_dkp a0 ] = 1%r.
declare axiom NG_rs_det (g : (glob NG)) (a0 : nseed) :
  phoare[ NG.rs : (glob NG) = g /\ s = a0 ==> (glob NG) = g /\ res = ev_rs a0 ] = 1%r.
declare axiom NG_gen_det (g : (glob NG)) :
  phoare[ NG.gen : (glob NG) = g ==> (glob NG) = g /\ res = ev_gen ] = 1%r.
declare axiom NG_exp_det (g : (glob NG)) (a0 : elem) (a1 : scalar) :
  phoare[ NG.exp : (glob NG) = g /\ b = a0 /\ x = a1 ==> (glob NG) = g /\ res = ev_exp a0 a1 ] = 1%r.

lemma pr_init :
  equiv [ G1(K, NG).init ~ R1(K, NG).init :
    ={glob K, glob NG} ==>
    ={glob K, glob NG}
    /\ RO.h{1} = Hon.hh{2}
    /\ G1.gdk0{1} = R1.s0{2}
    /\ G1.gdk1{1} = R1.s1{2}
    /\ R1.dkpq0{2} = (ev_dkp (slice_k (RO.h{1} G1.gdk0{1}))).`2
    /\ R1.dkpq1{2} = (ev_dkp (slice_k (RO.h{1} G1.gdk1{1}))).`2
    /\ R1.dkt0{2} = ev_rs (slice_n (RO.h{1} G1.gdk0{1}))
    /\ R1.dkt1{2} = ev_rs (slice_n (RO.h{1} G1.gdk1{1}))
    /\ G1.gek0{1}.`1 = R1.ekpq0{2}
    /\ G1.gek1{1}.`1 = R1.ekpq1{2}
    /\ G1.gek0{1}.`2 = R1.ekt0{2}
    /\ G1.gek1{1}.`2 = R1.ekt1{2}
    /\ (G1.gek0{1}, G1.gdk0{1}) = (((ev_dkp (slice_k (RO.h{1} G1.gdk0{1}))).`1,
         ev_exp ev_gen (ev_rs (slice_n (RO.h{1} G1.gdk0{1})))), G1.gdk0{1})
    /\ (G1.gek1{1}, G1.gdk1{1}) = (((ev_dkp (slice_k (RO.h{1} G1.gdk1{1}))).`1,
         ev_exp ev_gen (ev_rs (slice_n (RO.h{1} G1.gdk1{1})))), G1.gdk1{1}) ].
proof.
proc.
(* drop the reduction's dead shared-RO sample below its live samples, then
   couple RO{1}~hh{2}, gdk0~s0, gdk1~s1 *)
swap{2} 1 3.
seq 3 3 : (={glob K, glob NG} /\ RO.h{1} = Hon.hh{2}
           /\ G1.gdk0{1} = R1.s0{2} /\ G1.gdk1{1} = R1.s1{2}).
+ rnd. rnd. rnd. skip => />.
seq 0 1 : (={glob K, glob NG} /\ RO.h{1} = Hon.hh{2}
           /\ G1.gdk0{1} = R1.s0{2} /\ G1.gdk1{1} = R1.s1{2}).
+ rnd{2}; auto => />; smt(dfun_ll).
(* post-sample freeze: every later det-call arg derives from these *)
exists* (glob K){1}, (glob NG){1}, RO.h{1}, G1.gdk0{1}, G1.gdk1{1},
        (glob K){2}, (glob NG){2}, Hon.hh{2}, R1.s0{2}, R1.s1{2};
elim* => gk1 gn1 roh gd0 gd1 gk2 gn2 hoh rs0 rs1.
(* game side: interleaved peel, back-to-front, one-sided *)
wp.
call{1} (NG_exp_det gn1 (ev_gen) (ev_rs (slice_n (roh gd1)))).
wp.
call{1} (NG_gen_det gn1).
wp.
call{1} (NG_rs_det gn1 (slice_n (roh gd1))).
wp.
call{1} (K_dkp_det gk1 (slice_k (roh gd1))).
wp.
call{1} (NG_exp_det gn1 (ev_gen) (ev_rs (slice_n (roh gd0)))).
wp.
call{1} (NG_gen_det gn1).
wp.
call{1} (NG_rs_det gn1 (slice_n (roh gd0))).
wp.
call{1} (K_dkp_det gk1 (slice_k (roh gd0))).
wp.
(* reduction side: batched peel, back-to-front, one-sided *)
call{2} (NG_exp_det gn2 (ev_gen) (ev_rs (slice_n (hoh rs1)))).
wp.
call{2} (NG_gen_det gn2).
wp.
call{2} (NG_exp_det gn2 (ev_gen) (ev_rs (slice_n (hoh rs0)))).
wp.
call{2} (NG_gen_det gn2).
wp.
call{2} (NG_rs_det gn2 (slice_n (hoh rs1))).
wp.
call{2} (NG_rs_det gn2 (slice_n (hoh rs0))).
wp.
call{2} (K_dkp_det gk2 (slice_k (hoh rs1))).
wp.
call{2} (K_dkp_det gk2 (slice_k (hoh rs0))).
wp.
skip; move => &1 &2 H.
do 16! (simplify;
  (   (split; [ by smt() | move => ? ? ? [-> ->] ])
   || (split; [ by smt() | move => ? ? ? [-> ?] ])
   || (split; [ by smt() | move => ? ? ? [? ->] ])
   || (split; [ by smt() | move => ? ? ? [? ?] ])
   || (move => ? ? [-> ->])
   || (move => ? ? [-> ?])
   || (move => ? ? [? ->])
   || (move => ? ? [? ?]))).
simplify.
smt().
qed.
end section.
