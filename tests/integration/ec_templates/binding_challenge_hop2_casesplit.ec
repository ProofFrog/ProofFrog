(* hop_2 challenge: R_PQ_Bind o Unbreakable ~ R_KDF o Breakable.
   BOTH sides are case-split reductions computing the SAME kdf_in_0/kdf_in_1.
   LHS guard = (kdf0=kdf1 /\ ctPQ0<>ctPQ1); if-branch = inlined KEM_PQ Unbreakable
     challenger (2 dead decaps + r<-false); else = 2 H.ev + (ev_ev kdf0=ev_ev kdf1 /\ ct0<>ct1).
   RHS guard = (ct0=ct1); if-branch = r<-false; else = inlined KDF Breakable
     challenger (2 H.ev + (ev_ev kdf0=ev_ev kdf1 /\ kdf0<>kdf1)).
   Equivalence hinges on: kdf0=kdf1 /\ ctPQ0=ctPQ1 /\ ct0<>ct1 is impossible
   (kdf0=kdf1 => ev_ect ctT0 = ev_ect ctT1 => ctT0=ctT1; with ctPQ0=ctPQ1 => ct0=ct1). *)
require import AllCore.

type dkpq, dkt, ekt, ctpq, ctt, sspq, sst, epq, et, ect, eek, lbl.
type k1t, k2t, k3t, k4t, kout.

op ev_dpq : dkpq -> ctpq -> sspq.
op ev_dt  : dkt  -> ctt  -> sst.
op ev_epq : sspq -> epq.
op ev_et  : sst  -> et.
op ev_ect : ctt  -> ect.
op ev_eek : ekt  -> eek.
op ev_get : lbl.
op ev_ev  : k4t  -> kout.
axiom ev_ect_inj (a b : ctt) : ev_ect a = ev_ect b => a = b.

op c1 : epq -> et  -> k1t.  op s1 : k1t -> epq.  axiom sl1 (a:epq)(b:et ): s1 (c1 a b) = a.
op c2 : k1t -> ect -> k2t.  op s2 : k2t -> k1t.  axiom sl2 (a:k1t)(b:ect): s2 (c2 a b) = a.
op s2r : k2t -> ect. axiom sl2r (a:k1t)(b:ect): s2r (c2 a b) = b.
op c3 : k2t -> eek -> k3t.  op s3 : k3t -> k2t.  axiom sl3 (a:k2t)(b:eek): s3 (c3 a b) = a.
op c4 : k3t -> lbl -> k4t.  op s4 : k4t -> k3t.  axiom sl4 (a:k3t)(b:lbl): s4 (c4 a b) = a.

op kdfin (dp:dkpq)(dt:dkt)(ek:ekt)(c:ctpq*ctt) : k4t =
  c4 (c3 (c2 (c1 (ev_epq (ev_dpq dp c.`1)) (ev_et (ev_dt dt c.`2))) (ev_ect c.`2)) (ev_eek ek)) ev_get.

module type KP = { proc dpq(k:dkpq, c:ctpq):sspq  proc epq_(s:sspq):epq }.
module type KT = { proc dt(k:dkt, c:ctt):sst  proc et_(s:sst):et  proc ect_(c:ctt):ect  proc eek_(k:ekt):eek }.
module type LL = { proc get():lbl }.
module type HH = { proc ev(x:k4t):kout }.

(* LHS: R_PQ_Bind o Unbreakable. Interleaved decaps/encss per KEM. *)
module RP (P:KP, T:KT, L:LL, H:HH) = {
  var dp0 : dkpq  var dt0 : dkt  var ek0 : ekt
  var dp1 : dkpq  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var a0:sspq; var a1:et; var a2:ect; var a3:eek; var a4:lbl; var b0:epq; var b1:sst;
    var e0:sspq; var e1:et; var e2:ect; var e3:eek; var e4:lbl; var f0:epq; var f1:sst;
    var kdf_in_0, kdf_in_1 : k4t; var s0, s1 : sspq; var r : bool; var k0, k1 : kout;
    a0 <@ P.dpq(RP.dp0, ct0.`1); b0 <@ P.epq_(a0);
    b1 <@ T.dt(RP.dt0, ct0.`2); a1 <@ T.et_(b1);
    a2 <@ T.ect_(ct0.`2); a3 <@ T.eek_(RP.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 b0 a1) a2) a3) a4;
    e0 <@ P.dpq(RP.dp1, ct1.`1); f0 <@ P.epq_(e0);
    f1 <@ T.dt(RP.dt1, ct1.`2); e1 <@ T.et_(f1);
    e2 <@ T.ect_(ct1.`2); e3 <@ T.eek_(RP.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 f0 e1) e2) e3) e4;
    if (kdf_in_0 = kdf_in_1 /\ ct0.`1 <> ct1.`1) {
      s0 <@ P.dpq(RP.dp0, ct0.`1);
      s1 <@ P.dpq(RP.dp1, ct1.`1);
      r <- false;
    } else {
      k0 <@ H.ev(kdf_in_0);
      k1 <@ H.ev(kdf_in_1);
      r <- ev_ev kdf_in_0 = ev_ev kdf_in_1 /\ ct0 <> ct1;
    }
    return r;
  }
}.

(* RHS: R_KDF o Breakable. Both decaps first, then encss. *)
module RK (P:KP, T:KT, L:LL, H:HH) = {
  var dp0 : dkpq  var dt0 : dkt  var ek0 : ekt
  var dp1 : dkpq  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var sp0:sspq; var st0:sst; var a0:epq; var a1:et; var a2:ect; var a3:eek; var a4:lbl;
    var sp1:sspq; var st1:sst; var e0:epq; var e1:et; var e2:ect; var e3:eek; var e4:lbl;
    var kdf_in_0, kdf_in_1 : k4t; var r : bool; var h0, h1 : kout;
    sp0 <@ P.dpq(RK.dp0, ct0.`1); st0 <@ T.dt(RK.dt0, ct0.`2);
    a0 <@ P.epq_(sp0); a1 <@ T.et_(st0); a2 <@ T.ect_(ct0.`2); a3 <@ T.eek_(RK.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 a0 a1) a2) a3) a4;
    sp1 <@ P.dpq(RK.dp1, ct1.`1); st1 <@ T.dt(RK.dt1, ct1.`2);
    e0 <@ P.epq_(sp1); e1 <@ T.et_(st1); e2 <@ T.ect_(ct1.`2); e3 <@ T.eek_(RK.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 e0 e1) e2) e3) e4;
    if (ct0 = ct1) {
      r <- false;
    } else {
      h0 <@ H.ev(kdf_in_0);
      h1 <@ H.ev(kdf_in_1);
      r <- ev_ev kdf_in_0 = ev_ev kdf_in_1 /\ kdf_in_0 <> kdf_in_1;
    }
    return r;
  }
}.

section.
  declare module P <: KP {-RP, -RK}.
  declare module T <: KT {-RP, -RK, -P}.
  declare module L <: LL {-RP, -RK, -P, -T}.
  declare module H <: HH {-RP, -RK, -P, -T, -L}.

  declare axiom dpq_det (g:(glob P))(a0:dkpq)(a1:ctpq): phoare[P.dpq: (glob P)=g /\ k=a0 /\ c=a1 ==> (glob P)=g /\ res = ev_dpq a0 a1]=1%r.
  declare axiom epq_det (g:(glob P))(a0:sspq): phoare[P.epq_: (glob P)=g /\ s=a0 ==> (glob P)=g /\ res = ev_epq a0]=1%r.
  declare axiom dt_det  (g:(glob T))(a0:dkt)(a1:ctt): phoare[T.dt: (glob T)=g /\ k=a0 /\ c=a1 ==> (glob T)=g /\ res = ev_dt a0 a1]=1%r.
  declare axiom et_det  (g:(glob T))(a0:sst): phoare[T.et_: (glob T)=g /\ s=a0 ==> (glob T)=g /\ res = ev_et a0]=1%r.
  declare axiom ect_det (g:(glob T))(a0:ctt): phoare[T.ect_: (glob T)=g /\ c=a0 ==> (glob T)=g /\ res = ev_ect a0]=1%r.
  declare axiom eek_det (g:(glob T))(a0:ekt): phoare[T.eek_: (glob T)=g /\ k=a0 ==> (glob T)=g /\ res = ev_eek a0]=1%r.
  declare axiom get_det (g:(glob L)): phoare[L.get: (glob L)=g ==> (glob L)=g /\ res = ev_get]=1%r.
  declare axiom ev_det  (g:(glob H))(a0:k4t): phoare[H.ev: (glob H)=g /\ x=a0 ==> (glob H)=g /\ res = ev_ev a0]=1%r.

  lemma hop2_elim :
    equiv [ RP(P,T,L,H).challenge ~ RK(P,T,L,H).challenge :
       ={arg} /\ ={glob P, glob T, glob L, glob H} /\
       RP.dp0{1}=RK.dp0{2} /\ RP.dt0{1}=RK.dt0{2} /\ RP.ek0{1}=RK.ek0{2} /\
       RP.dp1{1}=RK.dp1{2} /\ RP.dt1{1}=RK.dt1{2} /\ RP.ek1{1}=RK.ek1{2}
       ==> ={res} ].
  proof.
    proc.
    seq 16 16 : (={ct0, ct1} /\ kdf_in_0{1} = kdf_in_0{2} /\ kdf_in_1{1} = kdf_in_1{2} /\
                 ={glob P, glob T, glob L, glob H} /\
                 kdf_in_0{2} = kdfin RK.dp0{2} RK.dt0{2} RK.ek0{2} ct0{2} /\
                 kdf_in_1{2} = kdfin RK.dp1{2} RK.dt1{2} RK.ek1{2} ct1{2}).
    + exists* (glob P){1}, (glob T){1}, (glob L){1},
              RP.dp0{1}, RP.dt0{1}, RP.ek0{1}, RP.dp1{1}, RP.dt1{1}, RP.ek1{1}, ct0{1}, ct1{1},
              RK.dp0{2}, RK.dt0{2}, RK.ek0{2}, RK.dp1{2}, RK.dt1{2}, RK.ek1{2};
      elim* => gp gt gl ldp0 ldt0 lek0 ldp1 ldt1 lek1 lc0 lc1 rdp0 rdt0 rek0 rdp1 rdt1 rek1.
      wp.
      (* index 1: peel both sides down to the kdf_in_0 assignment *)
      call{2} (get_det gl).
      call{2} (eek_det gt rek1).
      call{2} (ect_det gt lc1.`2).
      call{2} (et_det gt (ev_dt rdt1 lc1.`2)).
      call{2} (epq_det gp (ev_dpq rdp1 lc1.`1)).
      call{2} (dt_det gt rdt1 lc1.`2).
      call{2} (dpq_det gp rdp1 lc1.`1).
      call{1} (get_det gl).
      call{1} (eek_det gt lek1).
      call{1} (ect_det gt lc1.`2).
      call{1} (et_det gt (ev_dt ldt1 lc1.`2)).
      call{1} (dt_det gt ldt1 lc1.`2).
      call{1} (epq_det gp (ev_dpq ldp1 lc1.`1)).
      call{1} (dpq_det gp ldp1 lc1.`1).
      wp.
      (* index 0 *)
      call{2} (get_det gl).
      call{2} (eek_det gt rek0).
      call{2} (ect_det gt lc0.`2).
      call{2} (et_det gt (ev_dt rdt0 lc0.`2)).
      call{2} (epq_det gp (ev_dpq rdp0 lc0.`1)).
      call{2} (dt_det gt rdt0 lc0.`2).
      call{2} (dpq_det gp rdp0 lc0.`1).
      call{1} (get_det gl).
      call{1} (eek_det gt lek0).
      call{1} (ect_det gt lc0.`2).
      call{1} (et_det gt (ev_dt ldt0 lc0.`2)).
      call{1} (dt_det gt ldt0 lc0.`2).
      call{1} (epq_det gp (ev_dpq ldp0 lc0.`1)).
      call{1} (dpq_det gp ldp0 lc0.`1).
      skip => />.
    (* both `if`s remain *)
    case (ct0{2} = ct1{2}).
    + (* ct0 = ct1: RHS -> false; LHS guard's ctPQ0<>ctPQ1 false -> else; ct0<>ct1 false -> false *)
      rcondt{2} 1; first by auto.
      rcondf{1} 1; first by auto; smt().
      exists* (glob H){1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.
      wp. call{1} (ev_det gh ki1). call{1} (ev_det gh ki0).
      skip => />.
    (* ct0 <> ct1: RHS -> Breakable else branch *)
    rcondf{2} 1; first by (auto; smt()).
    case (kdf_in_0{1} = kdf_in_1{1} /\ ct0{1}.`1 <> ct1{1}.`1).
    + (* LHS collision branch: Unbreakable -> false. RHS: kdf0=kdf1 -> (.. /\ false) = false *)
      rcondt{1} 1; first by auto.
      exists* (glob P){1}, RP.dp0{1}, RP.dp1{1}, ct0{1}, ct1{1}; elim* => gp3 xdp0 xdp1 xc0 xc1.
      exists* (glob H){2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ki0 ki1.
      wp. call{2} (ev_det gh2 ki1). call{2} (ev_det gh2 ki0).
      call{1} (dpq_det gp3 xdp1 xc1.`1). call{1} (dpq_det gp3 xdp0 xc0.`1).
      skip => />; smt().
    (* LHS no-collision else branch: both are the hybrid predicate.
       kdf0<>kdf1 is redundant since kdf0=kdf1 => ct0=ct1 (via ect slice + inj) *)
    rcondf{1} 1; first by auto.
    exists* (glob H){1}, kdf_in_0{1}, kdf_in_1{1}; elim* => gh ki0 ki1.
    exists* (glob H){2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ri0 ri1.
    wp. call{1} (ev_det gh ki1). call{1} (ev_det gh ki0).
    call{2} (ev_det gh2 ri1). call{2} (ev_det gh2 ri0).
    skip => />. rewrite /kdfin /=. move => &1 &2 hg.
    smt(sl2r sl3 sl4 ev_ect_inj).
  qed.
end section.
