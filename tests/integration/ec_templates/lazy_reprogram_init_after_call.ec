(* Tripwire: discharging an `rcondt{1} ^if` side condition when an ABSTRACT
   CALL sits in the if's prefix.  Models the CK_seedbased lazy-RO init hop_2:
   the reprogramming `if (x0 = s0)` for the SECOND component key comes after
   the first component's `derivekeypair` call, so `+ auto.` cannot cross it. *)
require import AllCore Distr.

type sd.
type sdpq.
type sdt.
type sdfull.
type ekpq. type dkpq.
type ekt.  type dkt.

op dsd : sd distr.
op dpq : sdpq distr.
op dt  : sdt distr.
axiom dsd_ll : is_lossless dsd.
axiom dpq_ll : is_lossless dpq.
axiom dt_ll  : is_lossless dt.

op concat : sdpq -> sdt -> sdfull.
op slice_pq : sdfull -> sdpq.
op slice_t  : sdfull -> sdt.
axiom slice_concat_left  (a : sdpq) (b : sdt) : slice_pq (concat a b) = a.
axiom slice_concat_right (a : sdpq) (b : sdt) : slice_t  (concat a b) = b.

module type KPQ = { proc derivekeypair(_ : sdpq) : ekpq * dkpq }.
module type KTT = { proc derivekeypair(_ : sdt)  : ekt  * dkt  }.

module Mat = {
  var h : sd -> sdfull
  var s0 : sd
  var y0pq : sdpq
  var y0t : sdt
}.

module RO = { var h : sd -> sdfull }.

module RL = { var dkpq : sdpq  var ekt : ekt  var dkt : dkt }.
module RR = { var dkpq : sdpq  var ekt : ekt  var dkt : dkt  var seed0 : sd  var st : sdt }.

(* LEFT: reprogramming-Lazy side. *)
module L (KP : KPQ, KTm : KTT) = {
  proc initialize() : (ekpq * ekt) * sd = {
    var seed_0, x, x0 : sd;
    var r0, r1 : sdfull;
    var seed : sdpq;
    var tp : ekpq * dkpq;
    var tt : ekt * dkt;
    Mat.h <- RO.h;
    Mat.s0 <$ dsd;
    Mat.y0pq <$ dpq;
    Mat.y0t <$ dt;
    seed_0 <- Mat.s0;
    x <- seed_0;
    if (x = Mat.s0) { r0 <- concat Mat.y0pq Mat.y0t; } else { r0 <- Mat.h x; }
    seed <- slice_pq r0;
    tp <@ KP.derivekeypair(seed);
    RL.dkpq <- seed;
    x0 <- seed_0;
    if (x0 = Mat.s0) { r1 <- concat Mat.y0pq Mat.y0t; } else { r1 <- Mat.h x0; }
    tt <@ KTm.derivekeypair(slice_t r1);
    RL.ekt <- tt.`1;
    RL.dkt <- tt.`2;
    return ((tp.`1, RL.ekt), seed_0);
  }
}.

(* RIGHT: KeyGen side -- samples in a different order, calls in the same order. *)
module R (KP : KPQ, KTm : KTT) = {
  proc initialize() : (ekpq * ekt) * sd = {
    var seed : sdpq;
    var tp : ekpq * dkpq;
    var tt : ekt * dkt;
    seed <$ dpq;
    tp <@ KP.derivekeypair(seed);
    RR.dkpq <- seed;
    RR.seed0 <$ dsd;
    RR.st <$ dt;
    tt <@ KTm.derivekeypair(RR.st);
    RR.ekt <- tt.`1;
    RR.dkt <- tt.`2;
    return ((tp.`1, RR.ekt), RR.seed0);
  }
}.

section.

declare module KP <: KPQ {-Mat, -RO, -RL, -RR}.
declare module KTm <: KTT {-Mat, -RO, -RL, -RR, -KP}.

lemma hop :
  equiv [ L(KP, KTm).initialize ~ R(KP, KTm).initialize :
          ={glob KP} /\ ={glob KTm} /\ ={glob RO} ==>
          ={res} /\ ={glob KP} /\ ={glob KTm} /\ ={glob RO} /\
          RR.dkpq{2} = RL.dkpq{1} /\ RR.ekt{2} = RL.ekt{1} /\ RR.dkt{2} = RL.dkt{1} /\
          Mat.h{1} = RO.h{1} /\ Mat.s0{1} = RR.seed0{2} /\
          Mat.y0pq{1} = RR.dkpq{2} /\ Mat.y0t{1} = RR.st{2} ].
proof.
  proc.
  inline *.
do! (rcondt{1} ^if; first (auto; do? (call (_: true); auto))).
  rcondt{1} ^if.
  + auto.
  rcondt{1} ^if.
  + auto; do! (call (_: true); auto).
  swap{2} ^ <${3} @ 0.
  swap{2} ^ <${2} @ 0.
  swap{2} ^ <${3} @ 0.
  wp.
  call (_: true).
  wp.
  call (_: true).
  wp.
  rnd.
  wp.
  rnd.
  wp.
  rnd.
  auto => />.
  smt(slice_concat_left slice_concat_right).
qed.

end section.
