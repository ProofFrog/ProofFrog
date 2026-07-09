(*
   CFRG binding -- CHALLENGE case-split ELIMINATION, FAITHFUL shape.

   Extends binding_challenge_casesplit.ec (which modelled the game decaps as a
   single kdf_of call) to the REAL structure the concrete expanded-LEAK binding
   proofs export, pinning the exact tactic the challenge-chain synthesizer must
   emit. Two faithful complications this tripwire adds:

   1. REORDERED deterministic backbone. The game's hybrid Decaps computes both
      component decapsulations FIRST, then both shared-secret encodings
      (`sPQ<-decaps_PQ; sT<-decaps_T; ePQ<-enc_PQ sPQ; eT<-enc_T sT`), while the
      reduction interleaves them (`decaps_PQ; enc_PQ; decaps_T; enc_T`). The
      reorder crosses DIFFERENT abstract modules (KEM_PQ.enc vs KEM_T.decaps ->
      disjoint globs), so EC `swap` reorders them but a naive `call (_: true)`
      peel cannot align them.

   2. Per-branch call structure. The game applies the KDF `H.evaluate`
      UNCONDITIONALLY to both kdf_in's (k0, k1); the reduction applies it only in
      the ELSE branch and calls KEM_PQ.decaps (the inlined KEM_PQ-binding
      challenger) only in the IF branch. So `sim` is impossible.

   SOUNDNESS of the elimination is the same as the simplified tripwire: in the IF
   branch `kdf_in_0 = kdf_in_1` + concat-component-injectivity + EncodeSharedSecret
   injectivity give `decaps_PQ dk0 ct0pq = decaps_PQ dk1 ct1pq`, and the guard
   `ct0pq <> ct1pq` makes both the reduction's KEM_PQ predicate and the game's
   hybrid predicate true; the ELSE branch is the hybrid predicate on both sides.

   Every call is deterministic + glob-preserving, so both oracles are pure
   functions -- modelled here directly with deterministic ops (the real export
   functionalizes the abstract calls via the `_det` phoare axioms first). The
   injectivity facts (`mk_kdf_inj` = concat/slice component injectivity,
   `encss_inj` = the EncodeSharedSecret `_inj` axiom) are the exact facts the
   synthesizer threads into the closing `smt`.
*)

require import AllCore.

type dkpq, dkt, ekt, ctpq, ctt, sspq, sst, comp_t, kdf, kout.

(* Deterministic component operations (the ev_<m> of each `deterministic`
   method; the real export gets them from the `_det` phoare axioms). *)
op decaps_pq : dkpq -> ctpq -> sspq.
op decaps_t  : dkt  -> ctt  -> sst.
op encss_pq  : sspq -> sspq.               (* EncodeSharedSecret, injective *)
op encss_t   : sst  -> sst.

axiom encss_pq_inj (a a' : sspq) : encss_pq a = encss_pq a' => a = a'.

(* The KDF input: an injective concat of the PQ encoding and everything else
   (T encoding, ciphertext/key encodings, label). Equality of two kdf_in's
   gives equality of both components (concat/slice injectivity). *)
op mk_kdf : sspq -> comp_t -> kdf.
axiom mk_kdf_inj (a a' : sspq) (b b' : comp_t) :
  mk_kdf a b = mk_kdf a' b' => a = a' /\ b = b'.

(* The remaining (T-side + label) component -- a deterministic function of the
   T decaps and the ciphertexts. *)
op rest : sst -> ctpq -> ctt -> comp_t.

(* The KDF H.evaluate, deterministic. *)
op hop : kdf -> kout.

(* the hybrid ct-inequality: ct0 <> ct1 iff a component differs; in the IF
   branch the PQ component differs. *)
op hyb_ct_neq : (ctpq * ctt) -> (ctpq * ctt) -> bool.
axiom hyb_ct_neq_pq (c0 c1 : ctpq * ctt) :
  c0.`1 <> c1.`1 => hyb_ct_neq c0 c1.

(* Shared decaps keys (the packed hybrid keys' PQ+T components). *)
module St = {
  var dk_pq_0 : dkpq
  var dk_pq_1 : dkpq
  var dk_t_0  : dkt
  var dk_t_1  : dkt
}.

(* Game side: the hybrid Decaps computes both decaps first, then both encodes
   (the canonicalized game order), applies H unconditionally. *)
module G = {
  proc kdf_of(dk_pq : dkpq, dk_t : dkt, c : ctpq * ctt) : kdf = {
    var s_pq : sspq; var s_t : sst; var e_pq : sspq; var e_t : sst;
    s_pq <- decaps_pq dk_pq c.`1;
    s_t  <- decaps_t  dk_t  c.`2;
    e_pq <- encss_pq s_pq;
    e_t  <- encss_t  s_t;
    return mk_kdf e_pq (rest s_t c.`1 c.`2);
  }
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var kdf0, kdf1 : kdf;
    kdf0 <@ kdf_of(St.dk_pq_0, St.dk_t_0, ct0);
    kdf1 <@ kdf_of(St.dk_pq_1, St.dk_t_1, ct1);
    return hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
  }
}.

(* Reduction side: interleaved backbone (decaps_pq; enc_pq; decaps_t; enc_t) +
   case-split; the IF branch is the inlined KEM_PQ-binding challenger. *)
module R = {
  proc kdf_of(dk_pq : dkpq, dk_t : dkt, c : ctpq * ctt) : kdf = {
    var s_pq : sspq; var e_pq : sspq; var s_t : sst; var e_t : sst;
    s_pq <- decaps_pq dk_pq c.`1;
    e_pq <- encss_pq s_pq;
    s_t  <- decaps_t  dk_t  c.`2;
    e_t  <- encss_t  s_t;
    return mk_kdf e_pq (rest s_t c.`1 c.`2);
  }
  proc challenge(ct0 ct1 : ctpq * ctt) : bool = {
    var kdf0, kdf1 : kdf; var r : bool; var s0, s1 : sspq;
    kdf0 <@ kdf_of(St.dk_pq_0, St.dk_t_0, ct0);
    kdf1 <@ kdf_of(St.dk_pq_1, St.dk_t_1, ct1);
    if (kdf0 = kdf1 /\ ct0.`1 <> ct1.`1) {
      s0 <- decaps_pq St.dk_pq_0 ct0.`1;
      s1 <- decaps_pq St.dk_pq_1 ct1.`1;
      r <- s0 = s1 /\ ct0.`1 <> ct1.`1;
    } else {
      r <- hop kdf0 = hop kdf1 /\ hyb_ct_neq ct0 ct1;
    }
    return r;
  }
}.

lemma challenge_casesplit_reorder_elim :
  equiv [ G.challenge ~ R.challenge :
     ={arg, glob St} ==> ={res} ].
proof.
  (* The synthesizer's target, post-functionalization: `wp` collapses BOTH the
     reordered deterministic backbone (order-agnostic for pure assignments) AND
     the reduction's case-split (branch -> conditional post); `skip => />`
     discharges the else-branch (the hybrid predicate on both sides) and leaves
     the IF-branch obligation; `smt` closes it from concat/slice injectivity
     (mk_kdf_inj), EncodeSharedSecret injectivity (encss_pq_inj = the `_inj`
     axiom), and the hybrid ct-inequality. No manual swap or case tactic needed.
     The real export inserts one call-functionalization step per abstract call
     (`exists* (glob M){i}, args{i}; elim* => ...; call{i} (M_m_det ...)`)
     between `inline *` and `wp`. *)
  proc.
  inline *.
  wp.
  skip => />.
  smt(mk_kdf_inj encss_pq_inj hyb_ct_neq_pq).
qed.
