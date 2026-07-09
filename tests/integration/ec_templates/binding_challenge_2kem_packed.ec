(*
   CFRG binding CHALLENGE case-split elimination -- FULL 2-KEM PACKED-KEY structure
   (the exact real hop_0 shape the challenge-chain synthesizer must emit).

   Faithful to the concrete expanded-LEAK binding export's hop_0_challenge:
   - GAME holds a PACKED hybrid decaps key (dkpq*dkt*ekt) and calls the concrete
     hybrid scheme's decaps; that decaps runs 8 abstract calls (KEM_PQ + KEM_T
     decaps/encss, KEM_T ciphertext/encapskey encodings, a label get) building a
     4-deep concat, then the KDF `H.ev`.
   - REDUCTION holds the DECOMPOSED component fields (dp0/dt0/ek0, dp1/dt1/ek1)
     with a DECOMPOSITION COUPLING in the precondition
     (St.dk0{1} = (R.dp0, R.dt0, R.ek0){2}); its Challenge is FLAT (16-stmt
     prefix) + the case-split (if the two kdf_in's collide, re-decapsulate the
     PQ component -- the inlined KEM_PQ-binding challenger; else the hybrid
     predicate).

   THE COMPLETE VALIDATED TACTIC (name-independent; the synthesizer's target):
   1. GAME: `Sch_decaps_val` per-proc functional-value phoare lemma (proved by
      peeling the scheme decaps body's calls with each `_det` axiom, functional-
      value args) + `call{1}` at each game call site (packed keys/ct extracted
      once via `exists*`).
   2. REDUCTION prefix: `seq 0 <n>` under an invariant carrying the game-side glob
      equalities, the DECOMPOSITION COUPLING, and each `kdf_in_i` in functional
      form (the `kdfin` op). First goal functionalizes the flat prefix FORWARD --
      R fields + globs + ct extracted via `exists*`, each encss given the
      FUNCTIONAL VALUE of its decaps input as its `call{2}` arg.
   3. BRANCH: `case` the guard; IF -> `rcondt{2}; ...; wp; call{2}` the 2 re-decaps;
      `skip => />; rewrite /kdfin /=;` derive the PQ shared-secret equality from the
      concat equality via `smt(slice_concat_left_* )` then `ev_epq_inj` (the `_inj`
      axiom) then `smt(... hneq)`. ELSE -> `rcondf{2}; ...; call{2}` the 2 KDF calls;
      `skip => />` (both sides literally the hybrid predicate).

   The packed-key coupling threads through the invariant so the game's kdf (in the
   packed `D0` components) equals the reduction's kdf_in (in the R fields) and the
   if-branch re-decaps connects to the game via the coupling. If this stops
   compiling, the challenge synthesizer's target tactic must be re-derived.
*)
(* Faithful 2-KEM packed-key challenge case-split elimination -- the real hop_0
   structure: game holds a PACKED hybrid key (dkpq*dkt*ekt) and calls the concrete
   scheme's decaps; reduction holds DECOMPOSED component fields with a decomposition
   coupling; kdf_in is a 4-deep concat over both KEMs' encodings + a label. *)
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
axiom ev_epq_inj (a b : sspq) : ev_epq a = ev_epq b => a = b.

op c1 : epq -> et  -> k1t.  op s1 : k1t -> epq.  axiom sl1 (a:epq)(b:et ): s1 (c1 a b) = a.
op c2 : k1t -> ect -> k2t.  op s2 : k2t -> k1t.  axiom sl2 (a:k1t)(b:ect): s2 (c2 a b) = a.
op c3 : k2t -> eek -> k3t.  op s3 : k3t -> k2t.  axiom sl3 (a:k2t)(b:eek): s3 (c3 a b) = a.
op c4 : k3t -> lbl -> k4t.  op s4 : k4t -> k3t.  axiom sl4 (a:k3t)(b:lbl): s4 (c4 a b) = a.

op hneq : (ctpq*ctt) -> (ctpq*ctt) -> bool.
axiom hneq_pq (x y : ctpq*ctt) : x.`1 <> y.`1 => hneq x y.

op kdfin (dp:dkpq)(dt:dkt)(ek:ekt)(c:ctpq*ctt) : k4t =
  c4 (c3 (c2 (c1 (ev_epq (ev_dpq dp c.`1)) (ev_et (ev_dt dt c.`2))) (ev_ect c.`2)) (ev_eek ek)) ev_get.

module type KP = { proc dpq(k:dkpq, c:ctpq):sspq  proc epq_(s:sspq):epq }.
module type KT = { proc dt(k:dkt, c:ctt):sst  proc et_(s:sst):et  proc ect_(c:ctt):ect  proc eek_(k:ekt):eek }.
module type LL = { proc get():lbl }.
module type HH = { proc ev(x:k4t):kout }.

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

module G (P:KP, T:KT, L:LL, H:HH) = {
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var k0, k1 : kout;
    k0 <@ Sch(P,T,L,H).decaps(St.dk0, ct0);
    k1 <@ Sch(P,T,L,H).decaps(St.dk1, ct1);
    return k0 = k1 /\ hneq ct0 ct1;
  }
}.

(* Reduction: decomposed fields + flat body + case-split; if-branch re-decaps
   (the inlined KEM_PQ-binding challenger; the real export inlines Challenger). *)
module R (P:KP, T:KT, L:LL, H:HH) = {
  var dp0 : dkpq  var dt0 : dkt  var ek0 : ekt
  var dp1 : dkpq  var dt1 : dkt  var ek1 : ekt
  proc challenge(ct0 ct1 : ctpq*ctt) : bool = {
    var a0:sspq; var a1:et; var a2:ect; var a3:eek; var a4:lbl; var b0:epq; var b1:sst;
    var e0:sspq; var e1:et; var e2:ect; var e3:eek; var e4:lbl; var f0:epq; var f1:sst;
    var kdf_in_0, kdf_in_1 : k4t; var s0, s1 : sspq; var r : bool; var k0, k1 : kout;
    a0 <@ P.dpq(R.dp0, ct0.`1); b0 <@ P.epq_(a0);
    b1 <@ T.dt(R.dt0, ct0.`2); a1 <@ T.et_(b1);
    a2 <@ T.ect_(ct0.`2); a3 <@ T.eek_(R.ek0); a4 <@ L.get();
    kdf_in_0 <- c4 (c3 (c2 (c1 b0 a1) a2) a3) a4;
    e0 <@ P.dpq(R.dp1, ct1.`1); f0 <@ P.epq_(e0);
    f1 <@ T.dt(R.dt1, ct1.`2); e1 <@ T.et_(f1);
    e2 <@ T.ect_(ct1.`2); e3 <@ T.eek_(R.ek1); e4 <@ L.get();
    kdf_in_1 <- c4 (c3 (c2 (c1 f0 e1) e2) e3) e4;
    if (kdf_in_0 = kdf_in_1 /\ ct0.`1 <> ct1.`1) {
      s0 <@ P.dpq(R.dp0, ct0.`1);
      s1 <@ P.dpq(R.dp1, ct1.`1);
      r <- s0 = s1 /\ ct0.`1 <> ct1.`1;
    } else {
      k0 <@ H.ev(kdf_in_0);
      k1 <@ H.ev(kdf_in_1);
      r <- ev_ev kdf_in_0 = ev_ev kdf_in_1 /\ hneq ct0 ct1;
    }
    return r;
  }
}.

section.
  declare module P <: KP {-St, -R}.
  declare module T <: KT {-St, -R, -P}.
  declare module L <: LL {-St, -R, -P, -T}.
  declare module H <: HH {-St, -R, -P, -T, -L}.

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

  lemma challenge_elim :
    equiv [ G(P,T,L,H).challenge ~ R(P,T,L,H).challenge :
       ={arg} /\ ={glob P, glob T, glob L, glob H} /\
       St.dk0{1} = (R.dp0, R.dt0, R.ek0){2} /\ St.dk1{1} = (R.dp1, R.dt1, R.ek1){2}
       ==> ={res} ].
  proof.
    proc.
    exists* (glob P){1}, (glob T){1}, (glob L){1}, (glob H){1}, St.dk0{1}, St.dk1{1}, ct0{1}, ct1{1};
    elim* => gp gt gl gh D0 D1 C0 C1.
    call{1} (Sch_decaps_val gp gt gl gh D1 C1).
    call{1} (Sch_decaps_val gp gt gl gh D0 C0).
    seq 0 16 : ((glob P){1} = gp /\ (glob T){1} = gt /\ (glob L){1} = gl /\ (glob H){1} = gh /\ St.dk0{1} = (R.dp0, R.dt0, R.ek0){2} /\ St.dk1{1} = (R.dp1, R.dt1, R.ek1){2} /\ D0 = St.dk0{1} /\ D1 = St.dk1{1} /\ C0 = ct0{1} /\ C1 = ct1{1} /\ ct0{1} = ct0{2} /\ ct1{1} = ct1{2} /\ kdf_in_0{2} = kdfin R.dp0{2} R.dt0{2} R.ek0{2} ct0{2} /\ kdf_in_1{2} = kdfin R.dp1{2} R.dt1{2} R.ek1{2} ct1{2}).
    + exists* (glob P){2}, (glob T){2}, (glob L){2}, R.dp0{2}, R.dt0{2}, R.ek0{2}, R.dp1{2}, R.dt1{2}, R.ek1{2}, ct0{2}, ct1{2};
      elim* => gp2 gt2 gl2 dp0 dt0 ek0 dp1 dt1 ek1 c0 c1.
      wp.
      call{2} (get_det gl2).
      call{2} (eek_det gt2 ek1).
      call{2} (ect_det gt2 c1.`2).
      call{2} (et_det gt2 (ev_dt dt1 c1.`2)).
      call{2} (dt_det gt2 dt1 c1.`2).
      call{2} (epq_det gp2 (ev_dpq dp1 c1.`1)).
      call{2} (dpq_det gp2 dp1 c1.`1).
      wp.
      call{2} (get_det gl2).
      call{2} (eek_det gt2 ek0).
      call{2} (ect_det gt2 c0.`2).
      call{2} (et_det gt2 (ev_dt dt0 c0.`2)).
      call{2} (dt_det gt2 dt0 c0.`2).
      call{2} (epq_det gp2 (ev_dpq dp0 c0.`1)).
      call{2} (dpq_det gp2 dp0 c0.`1).
      skip => />.
    case (kdf_in_0{2} = kdf_in_1{2} /\ ct0{2}.`1 <> ct1{2}.`1).
    + rcondt{2} 1; first by auto.
      exists* (glob P){2}, R.dp0{2}, R.dp1{2}, ct0{2}, ct1{2}; elim* => gp3 xdp0 xdp1 xc0 xc1.
      wp.
      call{2} (dpq_det gp3 xdp1 xc1.`1).
      call{2} (dpq_det gp3 xdp0 xc0.`1).
      skip => />. rewrite /kdfin /=. move => &2 h hn.
      have he : ev_epq (ev_dpq xdp0 xc0.`1) = ev_epq (ev_dpq xdp1 xc1.`1) by smt(sl1 sl2 sl3 sl4).
      have hd : ev_dpq xdp0 xc0.`1 = ev_dpq xdp1 xc1.`1 by apply (ev_epq_inj _ _ he).
      rewrite h /=. smt(hneq_pq).
    rcondf{2} 1; first by auto.
    exists* (glob H){2}, kdf_in_0{2}, kdf_in_1{2}; elim* => gh2 ki0 ki1.
    wp.
    call{2} (ev_det gh2 ki1).
    call{2} (ev_det gh2 ki0).
    skip => />.
  qed.
end section.
