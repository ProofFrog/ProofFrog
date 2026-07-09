(*
   CFRG binding CHALLENGE case-split ELIMINATION -- the COMPLETE, name-independent
   tactic the challenge-chain synthesizer must emit (validated end-to-end).

   Structure matches the real concrete expanded-LEAK binding export:
   - GAME side calls the CONCRETE hybrid scheme's decaps (`Sch(K,H).decaps`),
     which internally computes a kdf_in and applies the KDF `H.evaluate`.
   - REDUCTION side (`R`) is FLAT with exporter-controlled local names
     (`_r0/_r1/_r2/_r3`, `kdf_in_0/1`) -- the shape the Challenge if-lowering
     renders -- ending in the case-split: on `kdf_in_0 = kdf_in_1 /\ ct_pq differ`
     it re-decapsulates (the inlined KEM_PQ-binding challenger), else applies the
     KDF (the direct hybrid predicate).
   (Simplified vs the real export to ONE component KEM + KDF: the real hybrid
   kdf_in concatenates KEM_PQ + KEM_T shared-secret/ciphertext/key encodings + a
   label. The TACTIC PATTERN is identical; only the number of functionalization
   steps grows with the component count.)

   THE TACTIC (all name-independent -- no `inline *`, no predicted names):
   1. GAME functionalization: synthesize a per-proc functional-value phoare lemma
      `Sch_decaps_val` (proved by functionalizing Sch.decaps's OWN body -- its
      exporter-controlled locals), then `call{1} (Sch_decaps_val gk gh dk ct)` at
      each game call site (args = the challenge's own `St.dk0`/`ct0`, extracted
      once via `exists*`).
   2. REDUCTION prefix: `seq 0 <prefix_len>` with an invariant carrying the glob /
      St / ct equalities AND each `kdf_in_i` in functional (`ev_`-op) form; the
      first goal functionalizes the flat prefix FORWARD -- each `K.encss` gets the
      *functional value* of its decaps input as its `call{2}` argument
      (`ev_dec dk ct` -- NOT an `exists*` of the intermediate local, which would
      capture its pre-assignment value), and the following `K.decaps` `call{2}`
      discharges the resulting side condition.
   3. BRANCH: `case` the guard; `rcondt{2}`/`rcondf{2}` (guard side-goal closed by
      `auto`); functionalize the branch's own calls; the IF-branch closes
      `skip => />; smt(mk_inj ev_enc_inj hneq_pq)` (concat/slice injectivity +
      EncodeSharedSecret injectivity = the `_inj` axiom + the hybrid ct-inequality)
      and the ELSE-branch closes with `skip => />` alone (both sides literally the
      hybrid predicate).

   If this stops compiling, the challenge-chain synthesizer's target tactic must
   be re-derived.
*)
(* Faithful challenge case-split elimination: game calls the CONCRETE scheme's
   decaps (functionalize via a synthesized *_val phoare lemma, NO inline);
   reduction is FLAT with exporter-controlled names (functionalize its primitive
   calls directly with known args). This is the exact structure + tactic the
   challenge-chain synthesizer must emit. *)
require import AllCore.

type dkpq, ctpq, ctt, sspq, comp_t, kdf, kout.

module type KP = {
  proc decaps(k : dkpq, c : ctpq) : sspq
  proc encss(s : sspq) : sspq
}.
module type HH = { proc evaluate(x : kdf) : kout }.

op ev_dec : dkpq -> ctpq -> sspq.
op ev_enc : sspq -> sspq.
op ev_ev  : kdf -> kout.
axiom ev_enc_inj (a a' : sspq) : ev_enc a = ev_enc a' => a = a'.
op mk : sspq -> comp_t -> kdf.
axiom mk_inj (a a' : sspq) (b b' : comp_t) : mk a b = mk a' b' => a = a' /\ b = b'.
op rst : ctpq -> comp_t.
op hneq : (ctpq * ctt) -> (ctpq * ctt) -> bool.
axiom hneq_pq (c0 c1 : ctpq * ctt) : c0.`1 <> c1.`1 => hneq c0 c1.

module St = { var dk0 : dkpq  var dk1 : dkpq }.

(* Concrete hybrid scheme: decaps computes kdf_in then H.evaluate. *)
module Sch (K : KP, H : HH) = {
  proc decaps(dk : dkpq, c : ctpq * ctt) : kout = {
    var s : sspq; var e : sspq; var ki : kdf; var r : kout;
    s <@ K.decaps(dk, c.`1);
    e <@ K.encss(s);
    ki <- mk e (rst c.`1);
    r <@ H.evaluate(ki);
    return r;
  }
}.

module G (K : KP, H : HH) = {
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var k0, k1 : kout;
    k0 <@ Sch(K, H).decaps(St.dk0, ct0);
    k1 <@ Sch(K, H).decaps(St.dk1, ct1);
    return k0 = k1 /\ hneq ct0 ct1;
  }
}.

(* Reduction: FLAT rendered body (exporter names) + case-split. *)
module R (K : KP, H : HH) = {
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var _r0, _r2 : sspq; var _r1, _r3 : sspq;
    var kdf_in_0, kdf_in_1 : kdf; var s0, s1 : sspq; var k0, k1 : kout; var r : bool;
    _r0 <@ K.decaps(St.dk0, ct0.`1);
    _r1 <@ K.encss(_r0);
    kdf_in_0 <- mk _r1 (rst ct0.`1);
    _r2 <@ K.decaps(St.dk1, ct1.`1);
    _r3 <@ K.encss(_r2);
    kdf_in_1 <- mk _r3 (rst ct1.`1);
    if (kdf_in_0 = kdf_in_1 /\ ct0.`1 <> ct1.`1) {
      s0 <@ K.decaps(St.dk0, ct0.`1);
      s1 <@ K.decaps(St.dk1, ct1.`1);
      r <- s0 = s1 /\ ct0.`1 <> ct1.`1;
    } else {
      k0 <@ H.evaluate(kdf_in_0);
      k1 <@ H.evaluate(kdf_in_1);
      r <- k0 = k1 /\ hneq ct0 ct1;
    }
    return r;
  }
}.

section.
  declare module K <: KP {-St}.
  declare module H <: HH {-St, -K}.

  declare axiom dec_det (g : (glob K)) (a0 : dkpq) (a1 : ctpq) :
    phoare[ K.decaps : (glob K) = g /\ k = a0 /\ c = a1
      ==> (glob K) = g /\ res = ev_dec a0 a1 ] = 1%r.
  declare axiom enc_det (g : (glob K)) (a0 : sspq) :
    phoare[ K.encss : (glob K) = g /\ s = a0
      ==> (glob K) = g /\ res = ev_enc a0 ] = 1%r.
  declare axiom ev_det (g : (glob H)) (a0 : kdf) :
    phoare[ H.evaluate : (glob H) = g /\ x = a0
      ==> (glob H) = g /\ res = ev_ev a0 ] = 1%r.

  (* Synthesized functional-value lemma for the concrete scheme's decaps.
     Proved by functionalizing Sch.decaps's OWN body (exporter-controlled
     locals s,e,ki,r) -- no inline in the main proof. *)
  lemma Sch_decaps_val (gk : (glob K)) (gh : (glob H)) (dkv : dkpq) (cv : ctpq * ctt) :
    phoare[ Sch(K, H).decaps :
      (glob K) = gk /\ (glob H) = gh /\ dk = dkv /\ c = cv
      ==> (glob K) = gk /\ (glob H) = gh
          /\ res = ev_ev (mk (ev_enc (ev_dec dkv cv.`1)) (rst cv.`1)) ] = 1%r.
  proof.
    proc.
    call (ev_det gh (mk (ev_enc (ev_dec dkv cv.`1)) (rst cv.`1))).
    wp.
    call (enc_det gk (ev_dec dkv cv.`1)).
    call (dec_det gk dkv cv.`1).
    skip => />.
  qed.

  lemma challenge_elim :
    equiv [ G(K, H).challenge ~ R(K, H).challenge :
       ={arg, glob St, glob K, glob H} ==> ={res} ].
  proof.
    proc.
    exists* (glob K){1}, (glob H){1}, St.dk0{1}, St.dk1{1}, ct0{1}, ct1{1};
    elim* => gk gh d0 d1 c0 c1.
    call{1} (Sch_decaps_val gk gh d1 c1).
    call{1} (Sch_decaps_val gk gh d0 c0).
    seq 0 6 : (gk = (glob K){1} /\ gk = (glob K){2} /\ gh = (glob H){1} /\ gh = (glob H){2} /\ d0 = St.dk0{1} /\ d0 = St.dk0{2} /\ d1 = St.dk1{1} /\ d1 = St.dk1{2} /\ c0 = ct0{1} /\ c0 = ct0{2} /\ c1 = ct1{1} /\ c1 = ct1{2} /\ kdf_in_0{2} = mk (ev_enc (ev_dec d0 c0.`1)) (rst c0.`1) /\ kdf_in_1{2} = mk (ev_enc (ev_dec d1 c1.`1)) (rst c1.`1)).
    + exists* (glob K){2}; elim* => gk2.
      wp. call{2} (enc_det gk2 (ev_dec d1 (c1.`1))). call{2} (dec_det gk2 d1 (c1.`1)).
      wp. call{2} (enc_det gk2 (ev_dec d0 (c0.`1))). call{2} (dec_det gk2 d0 (c0.`1)).
      skip => /#.
    case (kdf_in_0{2} = kdf_in_1{2} /\ ct0{2}.`1 <> ct1{2}.`1).
    + rcondt{2} 1; first by auto.
      exists* (glob K){2}; elim* => gk2.
      wp. call{2} (dec_det gk2 d1 (c1.`1)). call{2} (dec_det gk2 d0 (c0.`1)).
      skip => />. smt(mk_inj ev_enc_inj hneq_pq).
    rcondf{2} 1; first by auto.
    exists* (glob H){2}; elim* => gh2.
    wp. call{2} (ev_det gh2 (mk (ev_enc (ev_dec d1 (c1.`1))) (rst (c1.`1)))).
    call{2} (ev_det gh2 (mk (ev_enc (ev_dec d0 (c0.`1))) (rst (c0.`1)))).
    skip => />.
  qed.
end section.
