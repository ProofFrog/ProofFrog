(* hop_6 challenge -- BOTH-case-split (RP ~ RK) with a SEEDED-WRAPPER PQ decaps.
   This is the MERGE of two validated shapes:
     - binding_challenge_hop2_casesplit.ec : both reductions case-split (RP guards
       on the kdf collision -> PQ-binding Unbreakable challenger; RK guards on
       ct-equality -> KDF-collision Breakable challenger), per-call ev_ prefix
       functionalization, un-inlined challengers needing inline{i} 1.
     - binding_challenge_seeded_wrapper.ec : the PQ decaps is a SeededKEMWrapper
       functor (derivekeypair; inner-decaps), functionalized via dkp_det/dec_det;
       the collision branch's challenger RE-decapsulates through the wrapper.

   SAMEKEY: a single shared PQ seed `sd`; the challenger holds one key `sd0`.
   The tactic must, vs the non-wrapper hop2:
     (1) inline{1}/{2} <wrapper>.decaps <wrapper>.encodesharedsecret in the prefix
         peel, then functionalize the exposed derivekeypair/inner-decaps/epq;
     (2) in the LHS collision branch, inline the challenger AND its wrapper decaps,
         functionalizing the re-decapsulation via dkp_det/dec_det (not an atomic
         pq decaps_det) before the concat-injectivity close. *)
require import AllCore.

type seed, ekpq, dkpq, dkt, ekt, ctpq, ctt, sspq, sst, epq, et, ect, eek, lbl.
type k1t, k2t, k3t, k4t, kout.

op ev_dkp : seed -> ekpq * dkpq.     (* KEM_PQ_inner.derivekeypair ev-form *)
op ev_dec : dkpq -> ctpq -> sspq.    (* KEM_PQ_inner.decaps ev-form *)
op ev_epq : sspq -> epq.
op ev_dt  : dkt  -> ctt  -> sst.
op ev_et  : sst  -> et.
op ev_ect : ctt  -> ect.
op ev_eek : ekt  -> eek.
op ev_get : lbl.
op ev_ev  : k4t  -> kout.

(* the PQ shared secret of ciphertext c under seed s (seeded-wrapper decaps) *)
op ss_of (s : seed) (c : ctpq) : sspq = ev_dec (ev_dkp s).`2 c.

op c1 : epq -> et  -> k1t.
op c2 : k1t -> ect -> k2t.  op s2r : k2t -> ect. axiom sl2r (a:k1t)(b:ect): s2r (c2 a b) = b.
op c3 : k2t -> eek -> k3t.  op s3 : k3t -> k2t.  axiom sl3 (a:k2t)(b:eek): s3 (c3 a b) = a.
op c4 : k3t -> lbl -> k4t.  op s4 : k4t -> k3t.  axiom sl4 (a:k3t)(b:lbl): s4 (c4 a b) = a.
axiom ev_ect_inj (a b : ctt) : ev_ect a = ev_ect b => a = b.

op kdfin (sd:seed)(dt:dkt)(ek:ekt)(c:ctpq*ctt) : k4t =
  c4 (c3 (c2 (c1 (ev_epq (ss_of sd c.`1)) (ev_et (ev_dt dt c.`2))) (ev_ect c.`2)) (ev_eek ek)) ev_get.

module type KPQ = { proc derivekeypair(s:seed):ekpq*dkpq  proc decaps(k:dkpq, c:ctpq):sspq }.
module type KT  = { proc dt(k:dkt, c:ctt):sst  proc et_(s:sst):et  proc ect_(c:ctt):ect  proc eek_(k:ekt):eek }.
module type LL  = { proc get():lbl }.
module type HH  = { proc ev(x:k4t):kout }.
module type PQBind = { proc challenge(a b : ctpq) : bool }.
module type KDFColl = { proc challenge(x0 x1 : k4t) : bool }.

(* seeded PQ wrapper: decaps = derivekeypair; inner-decaps; encodesharedsecret = epq *)
module SW (P:KPQ) = {
  proc decaps(sd:seed, c:ctpq) : sspq = {
    var ek:ekpq; var dk:dkpq; var s:sspq;
    (ek, dk) <@ P.derivekeypair(sd);
    s        <@ P.decaps(dk, c);
    return s;
  }
  proc encodesharedsecret(s:sspq) : epq = { return ev_epq s; }
}.

module UnbrPQ (P:KPQ) : PQBind = {
  var sd0 : seed
  proc challenge(a b : ctpq) : bool = {
    var s0, s1 : sspq;
    s0 <@ SW(P).decaps(UnbrPQ.sd0, a);
    s1 <@ SW(P).decaps(UnbrPQ.sd0, b);
    return false;
  }
}.
module BrkKDF (H:HH) : KDFColl = {
  proc challenge(x0 x1 : k4t) : bool = {
    var h0, h1 : kout;
    h0 <@ H.ev(x0);
    h1 <@ H.ev(x1);
    return ev_ev x0 = ev_ev x1 /\ x0 <> x1;
  }
}.

module RP (P:KPQ, T:KT, L:LL, H:HH, CH:PQBind) = {
  var sd : seed  var dt0 : dkt  var ek0 : ekt  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var ct_T_0, ct_T_1 : ctt;
    var sp0:sspq; var a0:epq; var a1:et; var a2:ect; var a3:eek; var a4:lbl; var b1:sst;
    var sp1:sspq; var e0:epq; var e1:et; var e2:ect; var e3:eek; var e4:lbl; var f1:sst;
    var kdf_in_0, kdf_in_1 : k4t; var r : bool; var k0, k1 : kout;
    ct_T_0 <- ct0.`2;
    ct_T_1 <- ct1.`2;
    sp0 <@ SW(P).decaps(RP.sd, ct0.`1); a0 <@ SW(P).encodesharedsecret(sp0);
    b1 <@ T.dt(RP.dt0, ct_T_0); a1 <@ T.et_(b1);
    a2 <@ T.ect_(ct_T_0); a3 <@ T.eek_(RP.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 a0 a1) a2) a3) a4;
    sp1 <@ SW(P).decaps(RP.sd, ct1.`1); e0 <@ SW(P).encodesharedsecret(sp1);
    f1 <@ T.dt(RP.dt1, ct_T_1); e1 <@ T.et_(f1);
    e2 <@ T.ect_(ct_T_1); e3 <@ T.eek_(RP.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 e0 e1) e2) e3) e4;
    if (kdf_in_0 = kdf_in_1 /\ ct0.`1 <> ct1.`1) {
      r <@ CH.challenge(ct0.`1, ct1.`1);
    } else {
      k0 <@ H.ev(kdf_in_0);
      k1 <@ H.ev(kdf_in_1);
      r <- ev_ev kdf_in_0 = ev_ev kdf_in_1 /\ ct0 <> ct1;
    }
    return r;
  }
}.

module RK (P:KPQ, T:KT, L:LL, H:HH, CH:KDFColl) = {
  var sd : seed  var dt0 : dkt  var ek0 : ekt  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var ct_PQ_0, ct_PQ_1 : ctpq; var ct_T_0, ct_T_1 : ctt;
    var sp0:sspq; var st0:sst; var a0:epq; var a1:et; var a2:ect; var a3:eek; var a4:lbl;
    var sp1:sspq; var st1:sst; var e0:epq; var e1:et; var e2:ect; var e3:eek; var e4:lbl;
    var kdf_in_0, kdf_in_1 : k4t; var r : bool;
    ct_PQ_0 <- ct0.`1; ct_T_0 <- ct0.`2;
    sp0 <@ SW(P).decaps(RK.sd, ct_PQ_0); st0 <@ T.dt(RK.dt0, ct_T_0);
    a0 <@ SW(P).encodesharedsecret(sp0); a1 <@ T.et_(st0); a2 <@ T.ect_(ct_T_0); a3 <@ T.eek_(RK.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 a0 a1) a2) a3) a4;
    ct_PQ_1 <- ct1.`1; ct_T_1 <- ct1.`2;
    sp1 <@ SW(P).decaps(RK.sd, ct_PQ_1); st1 <@ T.dt(RK.dt1, ct_T_1);
    a0 <@ SW(P).encodesharedsecret(sp1); e1 <@ T.et_(st1); e2 <@ T.ect_(ct_T_1); e3 <@ T.eek_(RK.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 a0 e1) e2) e3) e4;
    if (ct0 = ct1) {
      r <- false;
    } else {
      r <@ CH.challenge(kdf_in_0, kdf_in_1);
    }
    return r;
  }
}.

section.
  declare module P <: KPQ {-RP, -RK, -UnbrPQ}.
  declare module T <: KT {-RP, -RK, -UnbrPQ, -P}.
  declare module L <: LL {-RP, -RK, -UnbrPQ, -P, -T}.
  declare module H <: HH {-RP, -RK, -UnbrPQ, -P, -T, -L}.

  declare axiom dkp_det (g:(glob P))(sd:seed): phoare[P.derivekeypair: (glob P)=g /\ s=sd ==> (glob P)=g /\ res = ev_dkp sd]=1%r.
  declare axiom dec_det (g:(glob P))(a0:dkpq)(a1:ctpq): phoare[P.decaps: (glob P)=g /\ k=a0 /\ c=a1 ==> (glob P)=g /\ res = ev_dec a0 a1]=1%r.
  declare axiom dt_det  (g:(glob T))(a0:dkt)(a1:ctt): phoare[T.dt: (glob T)=g /\ k=a0 /\ c=a1 ==> (glob T)=g /\ res = ev_dt a0 a1]=1%r.
  declare axiom et_det  (g:(glob T))(a0:sst): phoare[T.et_: (glob T)=g /\ s=a0 ==> (glob T)=g /\ res = ev_et a0]=1%r.
  declare axiom ect_det (g:(glob T))(a0:ctt): phoare[T.ect_: (glob T)=g /\ c=a0 ==> (glob T)=g /\ res = ev_ect a0]=1%r.
  declare axiom eek_det (g:(glob T))(a0:ekt): phoare[T.eek_: (glob T)=g /\ k=a0 ==> (glob T)=g /\ res = ev_eek a0]=1%r.
  declare axiom get_det (g:(glob L)): phoare[L.get: (glob L)=g ==> (glob L)=g /\ res = ev_get]=1%r.
  declare axiom ev_det  (g:(glob H))(a0:k4t): phoare[H.ev: (glob H)=g /\ x=a0 ==> (glob H)=g /\ res = ev_ev a0]=1%r.

  lemma hop6_elim :
    equiv [ RP(P,T,L,H,UnbrPQ(P)).challenge ~ RK(P,T,L,H,BrkKDF(H)).challenge :
       ={arg} /\ ={glob P, glob T, glob L, glob H} /\
       RP.sd{1}=RK.sd{2} /\ RP.dt0{1}=RK.dt0{2} /\ RP.ek0{1}=RK.ek0{2} /\
       RP.dt1{1}=RK.dt1{2} /\ RP.ek1{1}=RK.ek1{2} /\
       RP.sd{1}=UnbrPQ.sd0{1}
       ==> ={res} ].
  proof.
proc.
seq 18 20 : (={ct0, ct1} /\ kdf_in_0{1} = kdf_in_0{2} /\ kdf_in_1{1} = kdf_in_1{2} /\
             ={glob P, glob T, glob L, glob H} /\
             RP.sd{1}=UnbrPQ.sd0{1} /\
             RP.sd{1}=RK.sd{2} /\ RP.dt0{1}=RK.dt0{2} /\ RP.dt1{1}=RK.dt1{2} /\
             RP.ek0{1}=RK.ek0{2} /\ RP.ek1{1}=RK.ek1{2} /\
             kdf_in_0{2} = kdfin RK.sd{2} RK.dt0{2} RK.ek0{2} ct0{2} /\
             kdf_in_1{2} = kdfin RK.sd{2} RK.dt1{2} RK.ek1{2} ct1{2}).
+ inline{1} SW(P).decaps SW(P).encodesharedsecret.
  inline{2} SW(P).decaps SW(P).encodesharedsecret.
  sp.
  exists* (glob P){1}, (glob T){1}, (glob L){1}, RP.sd{1}, RP.dt0{1}, RP.ek0{1}, RP.dt1{1}, RP.ek1{1}, ct0{1}, ct1{1}, RK.sd{2}, RK.dt0{2}, RK.ek0{2}, RK.dt1{2}, RK.ek1{2};
  elim* => gp gt gl lsd ldt0 lek0 ldt1 lek1 lc0 lc1 rsd rdt0 rek0 rdt1 rek1.
  wp. call{1} (get_det gl). call{2} (get_det gl).
  wp. call{1} (eek_det gt lek1). call{2} (eek_det gt rek1).
  wp. call{1} (ect_det gt lc1.`2). call{2} (ect_det gt lc1.`2).
  wp. call{1} (et_det gt (ev_dt ldt1 lc1.`2)). call{2} (et_det gt (ev_dt rdt1 lc1.`2)).
  wp. call{1} (dt_det gt ldt1 lc1.`2). call{2} (dt_det gt rdt1 lc1.`2).
  wp. call{1} (dec_det gp (ev_dkp lsd).`2 lc1.`1). call{2} (dec_det gp (ev_dkp rsd).`2 lc1.`1).
  wp. call{1} (dkp_det gp lsd). call{2} (dkp_det gp rsd).
  wp. call{1} (get_det gl). call{2} (get_det gl).
  wp. call{1} (eek_det gt lek0). call{2} (eek_det gt rek0).
  wp. call{1} (ect_det gt lc0.`2). call{2} (ect_det gt lc0.`2).
  wp. call{1} (et_det gt (ev_dt ldt0 lc0.`2)). call{2} (et_det gt (ev_dt rdt0 lc0.`2)).
  wp. call{1} (dt_det gt ldt0 lc0.`2). call{2} (dt_det gt rdt0 lc0.`2).
  wp. call{1} (dec_det gp (ev_dkp lsd).`2 lc0.`1). call{2} (dec_det gp (ev_dkp rsd).`2 lc0.`1).
  wp. call{1} (dkp_det gp lsd). call{2} (dkp_det gp rsd).
  skip => />.
  case (ct0{2} = ct1{2}).
  + rcondt{2} 1; first by auto.
    rcondf{1} 1; first by auto; smt().
    exists* (glob H){1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.
    wp. call{1} (ev_det gh ki1). call{1} (ev_det gh ki0).
    skip => />.
  rcondf{2} 1; first by (auto; smt()).
  inline{2} 1.
  sp.
  case (kdf_in_0{1} = kdf_in_1{1} /\ ct0{1}.`1 <> ct1{1}.`1).
  + rcondt{1} 1; first by auto.
    inline{1} 1.
    inline{1} SW(P).decaps.
    sp.
    exists* (glob P){1}, UnbrPQ.sd0{1}, ct0{1}, ct1{1}; elim* => gp3 xsd xc0 xc1.
    exists* (glob H){2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ki0 ki1.
    wp. call{2} (ev_det gh2 ki1). call{2} (ev_det gh2 ki0).
    wp. call{1} (dec_det gp3 (ev_dkp xsd).`2 xc1.`1). call{1} (dkp_det gp3 xsd).
    wp. call{1} (dec_det gp3 (ev_dkp xsd).`2 xc0.`1). call{1} (dkp_det gp3 xsd).
    skip => />; smt().
  rcondf{1} 1; first by auto.
  exists* (glob H){1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.
  exists* (glob H){2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ri0 ri1.
  wp. call{1} (ev_det gh ki1). call{1} (ev_det gh ki0).
  call{2} (ev_det gh2 ri1). call{2} (ev_det gh2 ri0).
  skip => />. rewrite /kdfin /=. move => &1 &2 hg.
  smt(sl2r sl3 sl4 ev_ect_inj).
  qed.
end section.
