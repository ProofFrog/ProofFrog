(* hop_4 challenge: R_KDF o Unbreakable ~ Hybrid_Unbreakable(CK_expanded).
   BOTH sides return FALSE.
   LHS (R_KDF o KDF-Unbreakable): prefix computes kdf_in_0/kdf_in_1; then
     if (ct0=ct1) { r<-false } else { r <@ CH.challenge(kdf0,kdf1) } where
     CH = KDF Unbreakable challenger (challenge returns false).
   RHS (Hybrid Unbreakable game): k0<@Sch.decaps(dk0,ct0); k1<@Sch.decaps(dk1,ct1);
     return false. Game holds the PACKED key; reduction holds decomposed fields
     (decomposition coupling in the precondition). *)
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

op c1 : epq -> et  -> k1t.
op c2 : k1t -> ect -> k2t.
op c3 : k2t -> eek -> k3t.
op c4 : k3t -> lbl -> k4t.

op kdfin (dp:dkpq)(dt:dkt)(ek:ekt)(c:ctpq*ctt) : k4t =
  c4 (c3 (c2 (c1 (ev_epq (ev_dpq dp c.`1)) (ev_et (ev_dt dt c.`2))) (ev_ect c.`2)) (ev_eek ek)) ev_get.

module type KP = { proc dpq(k:dkpq, c:ctpq):sspq  proc epq_(s:sspq):epq }.
module type KT = { proc dt(k:dkt, c:ctt):sst  proc et_(s:sst):et  proc ect_(c:ctt):ect  proc eek_(k:ekt):eek }.
module type LL = { proc get():lbl }.
module type HH = { proc ev(x:k4t):kout }.
module type KDFOracle = { proc challenge(x0 x1 : k4t) : bool }.

module St = { var dk0 : dkpq * dkt * ekt  var dk1 : dkpq * dkt * ekt }.

module Sch (P:KP, T:KT, L:LL, H:HH) = {
  proc decaps(dk : dkpq*dkt*ekt, ct : ctpq*ctt) : kout = {
    var vsp : sspq; var vst : sst; var r0:epq; var r1:et; var r2:ect; var r3:eek; var r4:lbl;
    var ki : k4t; var r : kout;
    vsp <@ P.dpq(dk.`1, ct.`1);
    vst <@ T.dt(dk.`2, ct.`2);
    r0 <@ P.epq_(vsp);
    r1 <@ T.et_(vst);
    r2 <@ T.ect_(ct.`2);
    r3 <@ T.eek_(dk.`3);
    r4 <@ L.get();
    ki <- c4 (c3 (c2 (c1 r0 r1) r2) r3) r4;
    r <@ H.ev(ki);
    return r;
  }
}.

(* RHS: Hybrid Unbreakable game -- 2 decaps then return false. *)
module GU (P:KP, T:KT, L:LL, H:HH) = {
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var k0, k1 : kout;
    k0 <@ Sch(P,T,L,H).decaps(St.dk0, ct0);
    k1 <@ Sch(P,T,L,H).decaps(St.dk1, ct1);
    return false;
  }
}.

(* KDF Unbreakable challenger: challenge returns false. *)
module UnbrKDF : KDFOracle = {
  proc challenge(x0 x1 : k4t) : bool = { return false; }
}.

(* LHS: R_KDF -- decomposed fields, flat prefix, then a ct-equality case-split
   forwarding to the KDF challenger (Unbreakable -> false). *)
module RKU (P:KP, T:KT, L:LL, H:HH, CH:KDFOracle) = {
  var dp0 : dkpq  var dt0 : dkt  var ek0 : ekt
  var dp1 : dkpq  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var ct_PQ_0, ct_PQ_1 : ctpq; var ct_T_0, ct_T_1 : ctt;
    var sp0:sspq; var st0:sst; var a0:epq; var a1:et; var a2:ect; var a3:eek; var a4:lbl;
    var sp1:sspq; var st1:sst; var e0:epq; var e1:et; var e2:ect; var e3:eek; var e4:lbl;
    var kdf_in_0, kdf_in_1 : k4t; var r : bool;
    ct_PQ_0 <- ct0.`1; ct_T_0 <- ct0.`2;
    sp0 <@ P.dpq(RKU.dp0, ct_PQ_0); st0 <@ T.dt(RKU.dt0, ct_T_0);
    a0 <@ P.epq_(sp0); a1 <@ T.et_(st0); a2 <@ T.ect_(ct_T_0); a3 <@ T.eek_(RKU.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 a0 a1) a2) a3) a4;
    ct_PQ_1 <- ct1.`1; ct_T_1 <- ct1.`2;
    sp1 <@ P.dpq(RKU.dp1, ct_PQ_1); st1 <@ T.dt(RKU.dt1, ct_T_1);
    e0 <@ P.epq_(sp1); e1 <@ T.et_(st1); e2 <@ T.ect_(ct_T_1); e3 <@ T.eek_(RKU.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 e0 e1) e2) e3) e4;
    if (ct0 = ct1) {
      r <- false;
    } else {
      r <@ CH.challenge(kdf_in_0, kdf_in_1);
    }
    return r;
  }
}.

section.
  declare module P <: KP {-St, -RKU}.
  declare module T <: KT {-St, -RKU, -P}.
  declare module L <: LL {-St, -RKU, -P, -T}.
  declare module H <: HH {-St, -RKU, -P, -T, -L}.

  declare axiom dpq_det (g:(glob P))(a0:dkpq)(a1:ctpq): phoare[P.dpq: (glob P)=g /\ k=a0 /\ c=a1 ==> (glob P)=g /\ res = ev_dpq a0 a1]=1%r.
  declare axiom epq_det (g:(glob P))(a0:sspq): phoare[P.epq_: (glob P)=g /\ s=a0 ==> (glob P)=g /\ res = ev_epq a0]=1%r.
  declare axiom dt_det  (g:(glob T))(a0:dkt)(a1:ctt): phoare[T.dt: (glob T)=g /\ k=a0 /\ c=a1 ==> (glob T)=g /\ res = ev_dt a0 a1]=1%r.
  declare axiom et_det  (g:(glob T))(a0:sst): phoare[T.et_: (glob T)=g /\ s=a0 ==> (glob T)=g /\ res = ev_et a0]=1%r.
  declare axiom ect_det (g:(glob T))(a0:ctt): phoare[T.ect_: (glob T)=g /\ c=a0 ==> (glob T)=g /\ res = ev_ect a0]=1%r.
  declare axiom eek_det (g:(glob T))(a0:ekt): phoare[T.eek_: (glob T)=g /\ k=a0 ==> (glob T)=g /\ res = ev_eek a0]=1%r.
  declare axiom get_det (g:(glob L)): phoare[L.get: (glob L)=g ==> (glob L)=g /\ res = ev_get]=1%r.
  declare axiom ev_det  (g:(glob H))(a0:k4t): phoare[H.ev: (glob H)=g /\ x=a0 ==> (glob H)=g /\ res = ev_ev a0]=1%r.

  lemma Sch_decaps_val (gp:(glob P))(gt:(glob T))(gl:(glob L))(gh:(glob H)) (dkv:dkpq*dkt*ekt) (ctv:ctpq*ctt):
    phoare[ Sch(P,T,L,H).decaps :
      (glob P)=gp /\ (glob T)=gt /\ (glob L)=gl /\ (glob H)=gh /\ dk=dkv /\ ct=ctv
      ==> (glob P)=gp /\ (glob T)=gt /\ (glob L)=gl /\ (glob H)=gh /\ res = ev_ev (kdfin dkv.`1 dkv.`2 dkv.`3 ctv) ] = 1%r.
  proof.
    proc.
    call (ev_det gh (kdfin dkv.`1 dkv.`2 dkv.`3 ctv)).
    wp.
    call (get_det gl).
    call (eek_det gt dkv.`3).
    call (ect_det gt ctv.`2).
    call (et_det gt (ev_dt dkv.`2 ctv.`2)).
    call (epq_det gp (ev_dpq dkv.`1 ctv.`1)).
    call (dt_det gt dkv.`2 ctv.`2).
    call (dpq_det gp dkv.`1 ctv.`1).
    wp.
    skip => />.
  qed.

  lemma hop4_elim :
    equiv [ RKU(P,T,L,H,UnbrKDF).challenge ~ GU(P,T,L,H).challenge :
       ={arg} /\ ={glob P, glob T, glob L, glob H} /\
       St.dk0{2} = (RKU.dp0, RKU.dt0, RKU.ek0){1} /\ St.dk1{2} = (RKU.dp1, RKU.dt1, RKU.ek1){1}
       ==> ={res} ].
  proof.
    proc.
    (* seq off BOTH prefixes (LHS 20 flat with projections, RHS 2 game decaps) --
       all dead, the result is false regardless -- establishing only the trivial
       invariant. `sp` substitutes the LHS ct_PQ/ct_T projections. *)
    seq 20 2 : (={glob P, glob T, glob L, glob H} /\ ct0{1} = ct0{2} /\ ct1{1} = ct1{2}).
    + sp.
      exists* (glob P){2}, (glob T){2}, (glob L){2}, (glob H){2}, St.dk0{2}, St.dk1{2}, ct0{2}, ct1{2},
              RKU.dp0{1}, RKU.dt0{1}, RKU.ek0{1}, RKU.dp1{1}, RKU.dt1{1}, RKU.ek1{1};
      elim* => gp gt gl gh D0 D1 C0 C1 dp0 dt0 ek0 dp1 dt1 ek1.
      call{2} (Sch_decaps_val gp gt gl gh D1 C1).
      call{2} (Sch_decaps_val gp gt gl gh D0 C0).
      wp.
      call{1} (get_det gl). call{1} (eek_det gt ek1). call{1} (ect_det gt C1.`2).
      call{1} (et_det gt (ev_dt dt1 C1.`2)). call{1} (epq_det gp (ev_dpq dp1 C1.`1)).
      call{1} (dt_det gt dt1 C1.`2). call{1} (dpq_det gp dp1 C1.`1).
      wp.
      call{1} (get_det gl). call{1} (eek_det gt ek0). call{1} (ect_det gt C0.`2).
      call{1} (et_det gt (ev_dt dt0 C0.`2)). call{1} (epq_det gp (ev_dpq dp0 C0.`1)).
      call{1} (dt_det gt dt0 C0.`2). call{1} (dpq_det gp dp0 C0.`1).
      skip => />.
    (* LHS branch remains; RHS is done (returns false) *)
    case (ct0{1} = ct1{1}).
    + rcondt{1} 1; first by auto.
      wp. skip => />.
    rcondf{1} 1; first by (auto; smt()).
    inline{1} 1.
    wp.
    skip => />.
  qed.
end section.
