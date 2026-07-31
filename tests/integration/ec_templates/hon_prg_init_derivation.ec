(* Tripwire: the HON_BIND query-delegate INIT lemma.
 *
 * Shape (CG_seedbased_HON_BIND_K_*, hop_0/hop_12 `initialize`): a theorem game
 * whose decaps key IS the seedbased master seed, related to a PRG QUERY-delegate
 * reduction that stores the DERIVED material.  Both sides run the SAME linear
 * backbone -- one sample, then a chain of DETERMINISTIC abstract calls -- but the
 * postcondition (the `_prg_query_game_coupling` derivation chain) states each of
 * the reduction's fields as the `ev_` form of the game's seed.
 *
 * The generic init backbone peel (`wp; call (_: true)` per call) proves `={res}`
 * but learns NOTHING about what the abstract calls returned, so the derivation
 * conjuncts are unprovable and the closing `skip => /#` fails -- exactly how
 * CG_HON's hop_0_initialize dies in EC.
 *
 * This file pins the fix: couple the two samples with `seq 1 1` + `rnd`, freeze
 * the post-sample memory with `exists*`, then peel BOTH tails ONE-SIDED
 * back-to-front with the `<M>_<m>_det` phoare axioms, which replaces every call
 * by its `ev_` value over the frozen seed.  Because nothing is coupled
 * two-sidedly after the seq, the two sides' call interleaving is irrelevant --
 * which is what makes the recipe robust to the reduction and the game deriving
 * the same material in different orders.
 *)

require import AllCore Distr.

type seedt, fullt, pqt, tt, ekt, dkt, scalart, elemt.

op dseed : seedt distr.
axiom dseed_ll : is_lossless dseed.

op slice_pq : fullt -> pqt.
op slice_t  : fullt -> tt.

(* --- abstract primitives, each with its deterministic `ev_` companion ------- *)

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

(* The rendered flat states are FUNCTORS over the scheme module types (the
 * exporter's shape), defined at top level; the section then declares the
 * abstract instances and restricts them from the states' globals. *)

module Game (G : PRG, K : KEM, N : NGrp) = {
  var dk0 : seedt
  var ek0 : ekt * elemt

  proc initialize () : ekt * elemt = {
    var s : seedt;
    var full : fullt;
    var spq : pqt;
    var st : tt;
    var kp : ekt * dkt;
    var dkT : scalart;
    var gen : elemt;
    var ekT : elemt;
    s <$ dseed;
    full <@ G.evaluate(s);
    spq <- slice_pq full;
    st <- slice_t full;
    kp <@ K.derivekeypair(spq);
    dkT <@ N.randomscalar(st);
    gen <@ N.generator();
    ekT <@ N.exp(gen, dkT);
    ek0 <- (kp.`1, ekT);
    dk0 <- s;
    return ek0;
  }
}.

module Red (G : PRG, K : KEM, N : NGrp) = {
  var pq_keys_0 : ekt * dkt
  var dk_T_0 : scalart
  var ek_T_0 : elemt

  proc initialize () : ekt * elemt = {
    var q : seedt;
    var full : fullt;
    var spq : pqt;
    var st : tt;
    var gen : elemt;
    q <$ dseed;
    full <@ G.evaluate(q);
    spq <- slice_pq full;
    st <- slice_t full;
    pq_keys_0 <@ K.derivekeypair(spq);
    dk_T_0 <@ N.randomscalar(st);
    gen <@ N.generator();
    ek_T_0 <@ N.exp(gen, dk_T_0);
    return (pq_keys_0.`1, ek_T_0);
  }
}.

section Main.

declare module G  <: PRG  {-Game, -Red}.
declare module K  <: KEM  {-Game, -Red, -G}.
declare module N  <: NGrp {-Game, -Red, -G, -K}.

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

(* --- THE TARGET: sample-couple, freeze, one-sided det peels on BOTH sides -- *)

lemma hop_init_derivation_chain :
  equiv [ Game(G, K, N).initialize ~ Red(G, K, N).initialize :
          ={glob G, glob K, glob N}
          ==> ={res} /\ ={glob G, glob K, glob N}
              /\ Red.pq_keys_0{2} = ev_derivekeypair (slice_pq (ev_evaluate Game.dk0{1}))
              /\ Red.dk_T_0{2} = ev_randomscalar (slice_t (ev_evaluate Game.dk0{1}))
              /\ Red.ek_T_0{2} =
                   ev_exp ev_generator (ev_randomscalar (slice_t (ev_evaluate Game.dk0{1}))) ].
proof.
  proc.
  (* 1. couple the two leading samples; nothing else has run yet. *)
  seq 1 1 : (={glob G, glob K, glob N} /\ s{1} = q{2}).
  + rnd; skip => />.
  (* 2. freeze the post-sample memory: every callee glob + the coupled seed. *)
  exists* (glob G){1}, (glob K){1}, (glob N){1}, s{1}.
  elim* => gG gK gN sv.
  (* 3. peel BOTH tails one-sided, back to front. Each `_det` axiom replaces a
   *    call by its `ev_` value over already-frozen arguments, so the call-order
   *    interleaving between the two sides is irrelevant -- nothing is coupled
   *    two-sidedly any more. *)
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
qed.

end section Main.
