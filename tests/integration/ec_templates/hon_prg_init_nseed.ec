(* Tripwire: the n-KEYPAIR HON_BIND query-delegate INIT lemma.
 *
 * Shape (CG/CK_seedbased HON_BIND, hop_0/hop_12 `initialize`, TWO keypairs): the
 * theorem game re-runs `KeyGen` once per keypair (each KeyGen samples its own
 * master seed), while the query-delegate reduction queries its PRG challenger
 * once per keypair and stores the derived material. The validated single-keypair
 * recipe (`hon_prg_init_derivation.ec`) does NOT scale: it couples ONE leading
 * sample with `seq 1 1` + `rnd` and freezes ONE seed, but with n keypairs the n
 * samples are INTERLEAVED with their derivations.
 *
 * The design this file pins: do NOT hoist samples and do NOT compute
 * post-`inline *` positions. Decompose on the UN-inlined wrapper, where the
 * per-keypair segment lengths are exactly what the exporter rendered
 * (game: `keygen; ek <- .`1; dk <- .`2` = 3; reduction: `query; slice; slice;
 * derivekeypair; randomscalar; generator; exp` = 7). One `seq 3 7` per keypair,
 * whose invariant is the PREFIX of the final post covering keypairs 0..k --
 * statable in terms of the game FIELDS because `dk_k <- _tup.`2` lands inside
 * segment k. Each segment subgoal is then EXACTLY the single-keypair shape, so
 * the existing peel applies verbatim, and inside one segment each inlined local
 * is a first-and-only occurrence again -- no inline-name collision to predict.
 *
 * What this file is really testing is the TACTIC PLUMBING: whether a `seq` whose
 * first subgoal itself needs a nested `seq` + `rnd` + `exists*` peel can be
 * written as a bullet block, and whether the invariant threads.
 *)

require import AllCore Distr.

type seedt, fullt, pqt, tt, ekt, dkt, scalart, elemt.

op dseed : seedt distr.
axiom dseed_ll : is_lossless dseed.

op slice_pq : fullt -> pqt.
op slice_t  : fullt -> tt.

op ev_evaluate      : seedt -> fullt.
op ev_derivekeypair : pqt -> ekt * dkt.
op ev_randomscalar  : tt -> scalart.
op ev_generator     : elemt.
op ev_exp           : elemt -> scalart -> elemt.

module type PRG = { proc evaluate (x : seedt) : fullt }.
module type KEM = { proc derivekeypair (seed : pqt) : ekt * dkt }.
module type NGrp = {
  proc randomscalar (seed : tt) : scalart
  proc generator () : elemt
  proc exp (base : elemt, e : scalart) : elemt
}.

(* --- the concrete scheme: KeyGen samples a seed, DeriveKeyPair derives ------ *)

module Scheme (G : PRG, K : KEM, N : NGrp) = {
  proc derivekeypair (seed : seedt) : (ekt * elemt) * seedt = {
    var full : fullt;
    var kp : ekt * dkt;
    var dkT : scalart;
    var gen : elemt;
    var ekT : elemt;
    full <@ G.evaluate(seed);
    kp <@ K.derivekeypair(slice_pq full);
    dkT <@ N.randomscalar(slice_t full);
    gen <@ N.generator();
    ekT <@ N.exp(gen, dkT);
    return ((kp.`1, ekT), seed);
  }

  proc keygen () : (ekt * elemt) * seedt = {
    var s : seedt;
    var r : (ekt * elemt) * seedt;
    s <$ dseed;
    r <@ derivekeypair(s);
    return r;
  }
}.

(* --- the GAME wrapper: one KeyGen per keypair, fields assigned by projection - *)

module Game (G : PRG, K : KEM, N : NGrp) = {
  var ek0, ek1 : ekt * elemt
  var dk0, dk1 : seedt

  proc initialize () : (ekt * elemt) * (ekt * elemt) = {
    var t, t0 : (ekt * elemt) * seedt;
    t  <@ Scheme(G, K, N).keygen();
    ek0 <- t.`1;
    dk0 <- t.`2;
    t0 <@ Scheme(G, K, N).keygen();
    ek1 <- t0.`1;
    dk1 <- t0.`2;
    return (ek0, ek1);
  }
}.

(* --- the challenger the reduction delegates its query to -------------------- *)

module Chal (G : PRG) = {
  proc query () : fullt = {
    var q : seedt;
    var r : fullt;
    q <$ dseed;
    r <@ G.evaluate(q);
    return r;
  }
}.

(* --- the REDUCTION: one challenger query per keypair, stores the material ---- *)

module Red (G : PRG, K : KEM, N : NGrp, C : PRG) = {
  var pq_keys_0, pq_keys_1 : ekt * dkt
  var dk_T_0, dk_T_1 : scalart
  var ek_T_0, ek_T_1 : elemt

  proc initialize () : (ekt * elemt) * (ekt * elemt) = {
    var full_0, full_1 : fullt;
    var gen : elemt;
    full_0 <@ Chal(G).query();
    pq_keys_0 <@ K.derivekeypair(slice_pq full_0);
    dk_T_0 <@ N.randomscalar(slice_t full_0);
    gen <@ N.generator();
    ek_T_0 <@ N.exp(gen, dk_T_0);
    full_1 <@ Chal(G).query();
    pq_keys_1 <@ K.derivekeypair(slice_pq full_1);
    dk_T_1 <@ N.randomscalar(slice_t full_1);
    gen <@ N.generator();
    ek_T_1 <@ N.exp(gen, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

section Main.

declare module G <: PRG  {-Game, -Red}.
declare module K <: KEM  {-Game, -Red, -G}.
declare module N <: NGrp {-Game, -Red, -G, -K}.

declare axiom G_evaluate_det (g : (glob G)) (a0 : seedt) :
  phoare[ G.evaluate : (glob G) = g /\ x = a0
          ==> (glob G) = g /\ res = ev_evaluate a0 ] = 1%r.

declare axiom K_derivekeypair_det (g : (glob K)) (a0 : pqt) :
  phoare[ K.derivekeypair : (glob K) = g /\ seed = a0
          ==> (glob K) = g /\ res = ev_derivekeypair a0 ] = 1%r.

declare axiom N_randomscalar_det (g : (glob N)) (a0 : tt) :
  phoare[ N.randomscalar : (glob N) = g /\ seed = a0
          ==> (glob N) = g /\ res = ev_randomscalar a0 ] = 1%r.

declare axiom N_generator_det (g : (glob N)) :
  phoare[ N.generator : (glob N) = g ==> (glob N) = g /\ res = ev_generator ] = 1%r.

declare axiom N_exp_det (g : (glob N)) (a0 : elemt) (a1 : scalart) :
  phoare[ N.exp : (glob N) = g /\ base = a0 /\ e = a1
          ==> (glob N) = g /\ res = ev_exp a0 a1 ] = 1%r.

(* The keypair-k conjuncts, as `_prg_query_game_coupling` emits them (reduction
   fields + the game's own derived public half). *)
op inv0 (pq : ekt * dkt) (dt : scalart) (et : elemt)
        (ek : ekt * elemt) (dk : seedt) =
     pq = ev_derivekeypair (slice_pq (ev_evaluate dk))
  /\ dt = ev_randomscalar (slice_t (ev_evaluate dk))
  /\ et = ev_exp ev_generator (ev_randomscalar (slice_t (ev_evaluate dk)))
  /\ ek = ((ev_derivekeypair (slice_pq (ev_evaluate dk))).`1,
           ev_exp ev_generator (ev_randomscalar (slice_t (ev_evaluate dk)))).

lemma hop_init_two_keypairs :
  equiv [ Game(G, K, N).initialize ~ Red(G, K, N, G).initialize :
          ={glob G, glob K, glob N}
          ==> ={res} /\ ={glob G, glob K, glob N}
              /\ inv0 Red.pq_keys_0{2} Red.dk_T_0{2} Red.ek_T_0{2}
                      Game.ek0{1} Game.dk0{1}
              /\ inv0 Red.pq_keys_1{2} Red.dk_T_1{2} Red.ek_T_1{2}
                      Game.ek1{1} Game.dk1{1} ].
proof.
  proc.
  (* ---- segment 0: game statements 1..3, reduction statements 1..5 --------- *)
  seq 3 5 : (={glob G, glob K, glob N}
             /\ inv0 Red.pq_keys_0{2} Red.dk_T_0{2} Red.ek_T_0{2}
                     Game.ek0{1} Game.dk0{1}).
  + inline *.
    (* inside ONE segment each inlined local is a first-and-only occurrence, so
       the two sample names are the bare source names -- no collision to predict *)
    seq 1 1 : (={glob G, glob K, glob N} /\ s{1} = q{2}).
    - rnd; skip => />.
    exists* (glob G){1}, (glob K){1}, (glob N){1}, s{1}.
    elim* => gG gK gN sv.
    wp.
    call{1} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate sv)))).
    call{1} (N_generator_det gN).
    call{1} (N_randomscalar_det gN (slice_t (ev_evaluate sv))).
    call{1} (K_derivekeypair_det gK (slice_pq (ev_evaluate sv))).
    wp.
    call{1} (G_evaluate_det gG sv).
    call{2} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate sv)))).
    call{2} (N_generator_det gN).
    call{2} (N_randomscalar_det gN (slice_t (ev_evaluate sv))).
    call{2} (K_derivekeypair_det gK (slice_pq (ev_evaluate sv))).
    wp.
    call{2} (G_evaluate_det gG sv).
    skip => />.
    rewrite /inv0 => />.
  (* ---- segment 1: same shape, invariant carries segment 0's conjuncts ----- *)
  seq 3 5 : (={glob G, glob K, glob N}
             /\ inv0 Red.pq_keys_0{2} Red.dk_T_0{2} Red.ek_T_0{2}
                     Game.ek0{1} Game.dk0{1}
             /\ inv0 Red.pq_keys_1{2} Red.dk_T_1{2} Red.ek_T_1{2}
                     Game.ek1{1} Game.dk1{1}).
  + inline *.
    seq 1 1 : (={glob G, glob K, glob N}
               /\ inv0 Red.pq_keys_0{2} Red.dk_T_0{2} Red.ek_T_0{2}
                       Game.ek0{1} Game.dk0{1}
               /\ s{1} = q{2}).
    - rnd; skip => />.
    exists* (glob G){1}, (glob K){1}, (glob N){1}, s{1}.
    elim* => gG gK gN sv.
    wp.
    call{1} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate sv)))).
    call{1} (N_generator_det gN).
    call{1} (N_randomscalar_det gN (slice_t (ev_evaluate sv))).
    call{1} (K_derivekeypair_det gK (slice_pq (ev_evaluate sv))).
    wp.
    call{1} (G_evaluate_det gG sv).
    call{2} (N_exp_det gN ev_generator (ev_randomscalar (slice_t (ev_evaluate sv)))).
    call{2} (N_generator_det gN).
    call{2} (N_randomscalar_det gN (slice_t (ev_evaluate sv))).
    call{2} (K_derivekeypair_det gK (slice_pq (ev_evaluate sv))).
    wp.
    call{2} (G_evaluate_det gG sv).
    skip => />.
    rewrite /inv0 => />.
  (* ---- both returns are now the same ev-terms ----------------------------- *)
  skip => />.
qed.

end section Main.
