(* Tripwire: the TWO-KEYPAIR binding `challenge` under a derivation-chain
 * coupling -- the single blocker that keeps the n-keypair PRG coupling parked
 * (see `_prg_query_game_coupling`'s `len(seed_flds) != 1` guard).
 *
 * Shape (CG_seedbased_HON_BIND_K_PK / _CT_DIFFKEY, hop_0/hop_12 `challenge`):
 * the theorem game holds TWO master seeds and RE-DERIVES both keypairs on every
 * call, while the query-delegate reduction reads the two keypairs it stored at
 * `Initialize` and REPACKS each encaps key as a tuple `(pq_keys_i.`1, ek_T_i)`.
 * The win term is a PACKED-TUPLE DISEQUALITY `ek0 <> ek1`, which is what makes
 * this harder than the single-keypair case: there the challenge compares
 * ciphertexts (`ct0 <> ct1`), so nothing had to relate two re-derived tuples.
 *
 * `_synth_derivation_oracle_peel` closes the single-keypair version but leaves
 * this one open ("cannot save an incomplete proof") -- measured on
 * `.ec-tmp/run/CG_HON_PK6.ec`, the artifact produced with the n-keypair guard
 * lifted.
 *
 * RESULT: the recipe CLOSES this shape -- the peel plus a bare `skip => />`,
 * no smt. So the packed-tuple disequality is NOT the obstacle, and the real
 * export's "cannot save an incomplete proof" must come from a DIFFERENCE
 * between the emitted peel and this hand-written one (ordering, a missing
 * `wp`, or an argument), not from the goal being hard. Diagnose by diffing the
 * emitted `hop_0_challenge` tactic against this file.
 *)

require import AllCore Distr.

type seedt, fullt, pqt, tt, ekt, dkt, scalart, elemt, sst.

op dseed : seedt distr.
axiom dseed_ll : is_lossless dseed.

op slice_pq : fullt -> pqt.
op slice_t  : fullt -> tt.

op ev_evaluate      : seedt -> fullt.
op ev_derivekeypair : pqt -> ekt * dkt.
op ev_randomscalar  : tt -> scalart.
op ev_generator     : elemt.
op ev_exp           : elemt -> scalart -> elemt.
op ev_decaps        : dkt -> ekt -> sst.

module type PRG = { proc evaluate (x : seedt) : fullt }.

module type KEM  = {
  proc derivekeypair (seed : pqt) : ekt * dkt
  proc decaps (dk : dkt, c : ekt) : sst
}.

module type NGrp = {
  proc randomscalar (seed : tt) : scalart
  proc generator () : elemt
  proc exp (base : elemt, e : scalart) : elemt
}.

(* --- the GAME: holds two master seeds, re-derives both keypairs per call --- *)

module Game2 (G : PRG, K : KEM, N : NGrp) = {
  var dk0 : seedt
  var dk1 : seedt

  proc challenge (c0 : ekt, c1 : ekt) : bool = {
    var f0, f1 : fullt;
    var kp0, kp1 : ekt * dkt;
    var d0, d1 : scalart;
    var g0, g1, e0, e1 : elemt;
    var s0, s1 : sst;
    var ek0, ek1 : ekt * elemt;
    f0  <@ G.evaluate(dk0);
    kp0 <@ K.derivekeypair(slice_pq f0);
    d0  <@ N.randomscalar(slice_t f0);
    g0  <@ N.generator();
    e0  <@ N.exp(g0, d0);
    s0  <@ K.decaps(kp0.`2, c0);
    f1  <@ G.evaluate(dk1);
    kp1 <@ K.derivekeypair(slice_pq f1);
    d1  <@ N.randomscalar(slice_t f1);
    g1  <@ N.generator();
    e1  <@ N.exp(g1, d1);
    s1  <@ K.decaps(kp1.`2, c1);
    ek0 <- (kp0.`1, e0);
    ek1 <- (kp1.`1, e1);
    return (s0 = s1) /\ ek0 <> ek1;
  }
}.

(* --- the REDUCTION: reads what it stored, repacks each encaps key ---------- *)

module Red2 (G : PRG, K : KEM, N : NGrp) = {
  var pq_keys_0, pq_keys_1 : ekt * dkt
  var ek_T_0, ek_T_1 : elemt

  proc challenge (c0 : ekt, c1 : ekt) : bool = {
    var s0, s1 : sst;
    var ek0, ek1 : ekt * elemt;
    s0  <@ K.decaps(pq_keys_0.`2, c0);
    s1  <@ K.decaps(pq_keys_1.`2, c1);
    ek0 <- (pq_keys_0.`1, ek_T_0);
    ek1 <- (pq_keys_1.`1, ek_T_1);
    return (s0 = s1) /\ ek0 <> ek1;
  }
}.

section Main.

declare module G <: PRG  {-Game2, -Red2}.
declare module K <: KEM  {-Game2, -Red2, -G}.
declare module N <: NGrp {-Game2, -Red2, -G, -K}.

declare axiom G_evaluate_det (g : (glob G)) (a0 : seedt) :
  phoare[ G.evaluate : (glob G) = g /\ x = a0
          ==> (glob G) = g /\ res = ev_evaluate a0 ] = 1%r.

declare axiom K_derivekeypair_det (g : (glob K)) (a0 : pqt) :
  phoare[ K.derivekeypair : (glob K) = g /\ seed = a0
          ==> (glob K) = g /\ res = ev_derivekeypair a0 ] = 1%r.

declare axiom K_decaps_det (g : (glob K)) (a0 : dkt) (a1 : ekt) :
  phoare[ K.decaps : (glob K) = g /\ dk = a0 /\ c = a1
          ==> (glob K) = g /\ res = ev_decaps a0 a1 ] = 1%r.

declare axiom N_randomscalar_det (g : (glob N)) (a0 : tt) :
  phoare[ N.randomscalar : (glob N) = g /\ seed = a0
          ==> (glob N) = g /\ res = ev_randomscalar a0 ] = 1%r.

declare axiom N_generator_det (g : (glob N)) :
  phoare[ N.generator : (glob N) = g ==> (glob N) = g /\ res = ev_generator ] = 1%r.

declare axiom N_exp_det (g : (glob N)) (a0 : elemt) (a1 : scalart) :
  phoare[ N.exp : (glob N) = g /\ base = a0 /\ e = a1
          ==> (glob N) = g /\ res = ev_exp a0 a1 ] = 1%r.

(* The hop coupling as `_prg_query_game_coupling` emits it once generalized to
 * n keypairs: one derivation chain per keypair, ordinally. *)
lemma two_keypair_challenge_derivation :
  equiv [ Game2(G, K, N).challenge ~ Red2(G, K, N).challenge :
          ={c0, c1} /\ ={glob G, glob K, glob N}
          /\ Red2.pq_keys_0{2} = ev_derivekeypair (slice_pq (ev_evaluate Game2.dk0{1}))
          /\ Red2.pq_keys_1{2} = ev_derivekeypair (slice_pq (ev_evaluate Game2.dk1{1}))
          /\ Red2.ek_T_0{2} = ev_exp ev_generator (ev_randomscalar (slice_t (ev_evaluate Game2.dk0{1})))
          /\ Red2.ek_T_1{2} = ev_exp ev_generator (ev_randomscalar (slice_t (ev_evaluate Game2.dk1{1})))
          ==> ={res} ].
proof.
  proc.
  (* Freeze both sides' read state and the two arguments, then peel each tail
   * one-sided with the `_det` axioms -- the same recipe that closes the
   * SINGLE-keypair challenge in `hon_prg_init_derivation.ec`. *)
  exists* (glob G){1}, (glob K){1}, (glob N){1},
          Game2.dk0{1}, Game2.dk1{1}, c0{1}, c1{1},
          Red2.pq_keys_0{2}, Red2.pq_keys_1{2}, Red2.ek_T_0{2}, Red2.ek_T_1{2}.
  elim* => gG gK gN dv0 dv1 cv0 cv1 rk0 rk1 re0 re1.
  wp.
  call{2} (K_decaps_det gK (rk1.`2) cv1).
  call{2} (K_decaps_det gK (rk0.`2) cv0).
  wp.
  call{1} (K_decaps_det gK ((ev_derivekeypair (slice_pq (ev_evaluate dv1))).`2) cv1).
  call{1} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate dv1)))).
  call{1} (N_generator_det gN).
  call{1} (N_randomscalar_det gN (slice_t (ev_evaluate dv1))).
  call{1} (K_derivekeypair_det gK (slice_pq (ev_evaluate dv1))).
  call{1} (G_evaluate_det gG dv1).
  call{1} (K_decaps_det gK ((ev_derivekeypair (slice_pq (ev_evaluate dv0))).`2) cv0).
  call{1} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate dv0)))).
  call{1} (N_generator_det gN).
  call{1} (N_randomscalar_det gN (slice_t (ev_evaluate dv0))).
  call{1} (K_derivekeypair_det gK (slice_pq (ev_evaluate dv0))).
  call{1} (G_evaluate_det gG dv0).
  (* `=> />` alone closes it: after the peel both sides' `ek_i` are the SAME
   * ev-terms (the coupling rewrites the reduction's stored fields into the
   * game's derivations), so the packed-tuple disequality matches syntactically.
   * No smt call is needed. *)
  skip => />.
qed.

end section Main.
