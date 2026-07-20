(*
   CFRG binding -- CHALLENGE case-split ELIMINATION, SEEDED-WRAPPER shape
   (FAITHFUL: the collision branch RE-decapsulates).

   hop_4_challenge (R_KG_L ~ R_PQ_Bind) of the seedbased LEAK_BIND chain. Same
   encodesharedsecret-injectivity case-split elimination as the expanded variant
   (binding_challenge_casesplit.ec), with TWO structural differences the existing
   routes don't handle:

   1. The KEM is SeededKEMWrapper(KEM_inner): every `decaps(seed, ct)` inlines to
        (ek, dk) <@ KEM_inner.derivekeypair(seed);  s <@ KEM_inner.decaps(dk, ct);
      -- a TWO-call backbone rung, not a single `<clone>.decaps`.
   2. The inlined PQ binding challenger in the collision branch RE-DECAPSULATES
      (it is NOT CSE-deduped with the prefix): the then-branch holds 4 extra
      calls (2 derivekeypair + 2 inner-decaps), whose results feed the boolean.

   Both sides' PREFIXES are IDENTICAL (same wrapper decaps), so the tactic is a
   SYMMETRIC prefix peel; the reduction's trailing case-split is opened with
   `if{2}`, and the collision branch's re-decapsulation is dropped ONE-SIDED via
   the KEM's determinism axioms (`dkp_det`/`dec_det`, the `<M>_<m>_det` phoare =
   1%r foundation the export always emits), which pin the re-decapsulated `b_i`
   to the functional `ev_dec (ev_dkp s0).`2 ct_i` = the prefix's `ss_i`; then
   encss/concat injectivity closes `b0 = b1`.

   SAMEKEY: both ciphertexts decapsulate under the single shared seed `St.s0`.
*)

require import AllCore.

type seed, ek, dk, ct_pq, ct_t, ss, comp_t, kdf, kout.

op mk_kdf : ss -> comp_t -> kdf.
axiom mk_kdf_inj (a a' : ss) (b b' : comp_t) :
  mk_kdf a b = mk_kdf a' b' => a = a' /\ b = b'.

op encss : ss -> ss.
axiom encss_inj (a a' : ss) : encss a = encss a' => a = a'.

op rest : ct_pq -> ct_t -> comp_t.
op hyb_ct_neq : (ct_pq * ct_t) -> (ct_pq * ct_t) -> bool.
axiom hyb_ct_neq_pq (c0 c1 : ct_pq * ct_t) :
  c0.`1 <> c1.`1 => hyb_ct_neq c0 c1.

op hop : kdf -> kout.               (* the deterministic KDF (H.evaluate ev). *)
op ev_dkp : seed -> ek * dk.        (* KEM_inner.derivekeypair ev-form. *)
op ev_dec : dk -> ct_pq -> ss.      (* KEM_inner.decaps ev-form. *)

module type KEMinner = {
  proc derivekeypair(s : seed) : ek * dk
  proc decaps(k : dk, c : ct_pq) : ss
}.

module St = { var s0 : seed }.

module Common (K : KEMinner) = {
  proc kdf_of(c : ct_pq * ct_t) : ss * kdf = {
    var ekl : ek; var dkl : dk; var s : ss;
    (ekl, dkl) <@ K.derivekeypair(St.s0);
    s          <@ K.decaps(dkl, c.`1);
    return (s, mk_kdf (encss s) (rest c.`1 c.`2));
  }
}.

(* R_KG_L side: direct hybrid predicate (no case-split). *)
module G (K : KEMinner) = {
  proc challenge(ct0 ct1 : ct_pq * ct_t) : bool = {
    var s0, s1 : ss; var kdf0, kdf1 : kdf;
    (s0, kdf0) <@ Common(K).kdf_of(ct0);
    (s1, kdf1) <@ Common(K).kdf_of(ct1);
    return hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
  }
}.

(* R_PQ_Bind side: case-split; the inlined PQ binding challenger RE-derives and
   RE-decapsulates both ciphertexts (4 extra abstract calls). *)
module R (K : KEMinner) = {
  proc challenge(ct0 ct1 : ct_pq * ct_t) : bool = {
    var s0, s1 : ss; var kdf0, kdf1 : kdf; var r : bool;
    var ekb : ek; var dkb : dk; var b0, b1 : ss;
    (s0, kdf0) <@ Common(K).kdf_of(ct0);
    (s1, kdf1) <@ Common(K).kdf_of(ct1);
    if (kdf0 = kdf1 /\ ct0.`1 <> ct1.`1) {
      (ekb, dkb) <@ K.derivekeypair(St.s0);
      b0 <@ K.decaps(dkb, ct0.`1);
      (ekb, dkb) <@ K.derivekeypair(St.s0);
      b1 <@ K.decaps(dkb, ct1.`1);
      r <- b0 = b1 /\ ct0.`1 <> ct1.`1;
    } else {
      r <- hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
    }
    return r;
  }
}.

(* The functional form of a shared-secret decapsulation under the seed. *)
op ss_of (s0v : seed) (c : ct_pq * ct_t) : ss = ev_dec (ev_dkp s0v).`2 c.`1.
op kdf_of_f (s0v : seed) (c : ct_pq * ct_t) : kdf =
  mk_kdf (encss (ss_of s0v c)) (rest c.`1 c.`2).

section.

declare module K <: KEMinner {-St}.

declare axiom dkp_det (g : glob K) (sd : seed) :
  phoare[ K.derivekeypair :
    (glob K) = g /\ s = sd ==> (glob K) = g /\ res = ev_dkp sd ] = 1%r.
declare axiom dec_det (g : glob K) (kk : dk) (cc : ct_pq) :
  phoare[ K.decaps :
    (glob K) = g /\ k = kk /\ c = cc ==> (glob K) = g /\ res = ev_dec kk cc ] = 1%r.

(* kdf_of functionalized: the whole wrapper decaps (derivekeypair;decaps) +
   encode + concat as a single deterministic result. *)
local lemma kdf_of_det (g : glob K) (s0v : seed) (cc : ct_pq * ct_t) :
  phoare[ Common(K).kdf_of :
    (glob K) = g /\ St.s0 = s0v /\ c = cc ==>
    (glob K) = g /\ St.s0 = s0v /\ res = (ss_of s0v cc, kdf_of_f s0v cc) ] = 1%r.
proof.
  proc.
  call (dec_det g (ev_dkp s0v).`2 cc.`1).
  call (dkp_det g s0v).
  skip => />.
qed.

(* The case-split dissolves.  Functionalize both prefixes via kdf_of_det; the
   collision branch's re-decapsulation dropped one-sided via the det axioms;
   encss/concat injectivity closes the guard-implied `ss collide`. *)
lemma challenge_seeded_wrapper_elim :
  equiv [ G(K).challenge ~ R(K).challenge :
     ={arg, glob St, glob K} ==> ={res} ].
proof.
  proc.
  exists* (glob K){2}, St.s0{2}, ct0{2}, ct1{2}; elim* => g sd c0 c1.
  seq 2 2 : (={glob St, glob K, ct0, ct1} /\ (glob K){2} = g
             /\ St.s0{1} = sd /\ ct0{1} = c0 /\ ct1{1} = c1
             /\ s0{1} = ss_of sd c0 /\ kdf0{1} = kdf_of_f sd c0
             /\ s1{1} = ss_of sd c1 /\ kdf1{1} = kdf_of_f sd c1
             /\ s0{2} = s0{1} /\ kdf0{2} = kdf0{1}
             /\ s1{2} = s1{1} /\ kdf1{2} = kdf1{1}).
  + call{1} (kdf_of_det g sd c1). call{1} (kdf_of_det g sd c0).
    call{2} (kdf_of_det g sd c1). call{2} (kdf_of_det g sd c0).
    skip => />.
  if{2}.
  + wp.
    call{2} (dec_det g (ev_dkp sd).`2 c1.`1).
    call{2} (dkp_det g sd).
    call{2} (dec_det g (ev_dkp sd).`2 c0.`1).
    call{2} (dkp_det g sd).
    skip => />. rewrite /kdf_of_f /ss_of /=.
    smt(mk_kdf_inj encss_inj hyb_ct_neq_pq).
  + wp. skip => />.
qed.

end section.
