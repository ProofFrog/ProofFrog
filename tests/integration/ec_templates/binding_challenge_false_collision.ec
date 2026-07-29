(* Tripwire: the CFRG binding hop_6_challenge shape --
   CASE-SPLIT-vs-CASE-SPLIT where the LEFT's collision branch is a CONSTANT
   `false` (the reduction runs under the UNBREAKABLE component-binding
   challenger), rather than the inlined binding challenger that
   `_challenge_hop2_route` expects.

     LEFT  (R_PQ_Bind, Unbreakable PQ challenger):
       if (k0 = k1 /\ ct0.`1 <> ct1.`1) { false }
       else                             { H(k0) = H(k1) /\ ct0 <> ct1 }
     RIGHT (R_KDF, KDFCollision Breakable challenger):
       if (ct0 = ct1)                   { false }
       else                             { H(k0) = H(k1) /\ k0 <> k1 }

   They agree because the KDF input BINDS the trans ciphertext: k0 = k1 forces
   ct0.`2 = ct1.`2 through the EncodeCiphertext leaf, so under ct0 <> ct1 it
   forces ct0.`1 <> ct1.`1 -- which is exactly the LEFT guard's second
   conjunct. *)
require import AllCore Distr.

type ctpq. type ctt.
type dkpq. type dkt.
type sspq. type sst.
type bspq. type bst. type bsct. type bslbl.
type bs1. type bs2. type bs3.
type kout.

op ev_decaps_pq : dkpq -> ctpq -> sspq.
op ev_decaps_t  : dkt  -> ctt  -> sst.
op enc_pq  : sspq -> bspq.
op enc_t   : sst  -> bst.
op enc_ct  : ctt  -> bsct.
op lbl     : bslbl.
op ev_evaluate : bs3 -> kout.

op c1 : bspq -> bst   -> bs1.
op c2 : bs1  -> bsct  -> bs2.
op c3 : bs2  -> bslbl -> bs3.

axiom slice_c2_right (a : bs1)  (b : bsct) (a' : bs1) (b' : bsct) :
  c2 a b = c2 a' b' => b = b'.
axiom slice_c3_left  (a : bs2)  (b : bslbl) (a' : bs2) (b' : bslbl) :
  c3 a b = c3 a' b' => a = a'.
axiom enc_ct_inj (a b : ctt) : enc_ct a = enc_ct b => a = b.

op kdf (dp : dkpq) (dt : dkt) (ct : ctpq * ctt) : bs3 =
  c3 (c2 (c1 (enc_pq (ev_decaps_pq dp ct.`1)) (enc_t (ev_decaps_t dt ct.`2)))
         (enc_ct ct.`2))
     lbl.

module type KDF = { proc evaluate(x : bs3) : kout }.

module RL = { var dp : dkpq  var dt : dkt }.
module RR = { var dp : dkpq  var dt : dkt }.

(* LEFT: collision branch is a constant false (Unbreakable challenger). *)
module L (H : KDF) = {
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var k0, k1 : bs3;
    var y0, y1 : kout;
    var r : bool;
    k0 <- kdf RL.dp RL.dt ct0;
    k1 <- kdf RL.dp RL.dt ct1;
    if (k0 = k1 /\ ct0.`1 <> ct1.`1) {
      r <- false;
    } else {
      y0 <@ H.evaluate(k0);
      y1 <@ H.evaluate(k1);
      r <- y0 = y1 /\ ct0 <> ct1;
    }
    return r;
  }
}.

(* RIGHT: forwards to the KDF-collision challenger. *)
module R (H : KDF) = {
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var k0, k1 : bs3;
    var y0, y1 : kout;
    var r : bool;
    k0 <- kdf RR.dp RR.dt ct0;
    k1 <- kdf RR.dp RR.dt ct1;
    if (ct0 = ct1) {
      r <- false;
    } else {
      y0 <@ H.evaluate(k0);
      y1 <@ H.evaluate(k1);
      r <- y0 = y1 /\ k0 <> k1;
    }
    return r;
  }
}.

section.

declare module H <: KDF {-RL, -RR}.

declare axiom H_evaluate_det (g : (glob H)) (a0 : bs3) :
  phoare[ H.evaluate : (glob H) = g /\ x = a0 ==> (glob H) = g /\ res = ev_evaluate a0 ] = 1%r.

lemma hop6 :
  equiv [ L(H).challenge ~ R(H).challenge :
          ={ct0, ct1, glob H} /\ RR.dp{2} = RL.dp{1} /\ RR.dt{2} = RL.dt{1} ==>
          ={res, glob H} /\ RR.dp{2} = RL.dp{1} /\ RR.dt{2} = RL.dt{1} ].
proof.
  proc.
  sp.
  case (ct0{1} = ct1{1}).
  (* ct0 = ct1: RIGHT returns false; LEFT's guard fails on its 2nd conjunct and
     its else-branch returns `.. /\ ct0 <> ct1` = false. *)
  + rcondt{2} 1; first by auto.
    rcondf{1} 1; first by (auto; smt()).
    wp.
    exists* (glob H){1}, k1{1}; elim* => g1 a1.
    call{1} (H_evaluate_det g1 a1).
    exists* (glob H){1}, k0{1}; elim* => g0 a0.
    call{1} (H_evaluate_det g0 a0).
    skip => /#.
  (* ct0 <> ct1 *)
  rcondf{2} 1; first by auto.
  case (k0{1} = k1{1}).
  (* k0 = k1: the KDF binds ct.`2, so ct0.`2 = ct1.`2, hence ct0.`1 <> ct1.`1 --
     the LEFT guard holds and returns false; the RIGHT's `k0 <> k1` conjunct is
     false, so it returns false too. *)
  + rcondt{1} 1; first by (auto; smt(slice_c3_left slice_c2_right enc_ct_inj)).
    wp.
    exists* (glob H){2}, k1{2}; elim* => g1 a1.
    call{2} (H_evaluate_det g1 a1).
    exists* (glob H){2}, k0{2}; elim* => g0 a0.
    call{2} (H_evaluate_det g0 a0).
    skip => /#.
  (* k0 <> k1: both sides take the else-branch and agree. *)
  rcondf{1} 1; first by (auto; smt()).
  wp.
  call (_: true).
  call (_: true).
  skip => /#.
qed.

end section.
