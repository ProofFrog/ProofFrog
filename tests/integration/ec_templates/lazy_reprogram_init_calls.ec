(* Tripwire: the CGLazyRO *Lazy* hop init equiv WITH the abstract derivekeypair
   + NominalGroup backbone (wall 3o STEP D). Extends lazy_reprogram_init.ec,
   which modelled the derivation as deterministic ops; the real hop_2_initialize
   interleaves the reprogramming with abstract module calls (K.derivekeypair, and
   NG.randomscalar / NG.generator / NG.exp) that must be COUPLED name-independently
   (`call (_: true)`), NOT dropped -- both sides run the SAME call sequence.

   Side 1 = R_LazyRO_L(...Lazy_Mat): materialized `h <- RO.h`; sample s0,y0_pq,y0_t;
   reprogram `if (x = s0) { concat }`; derive from the slices.
   Side 2 = R_KG_L(...FromDeriveKeyPair): sample seed (+ seed_0, s_T) directly.
   Identically distributed via `slice(concat a b) = a/b` + the uniform samples.

   Goal: find the closing tactic for the DEDICATED reprogramming-Lazy init route. *)

require import AllCore Distr.

type bs_lambda, bs_pq, bs_t, bs_full, ek, dk, elem, scalar.

op dbs_lambda : bs_lambda distr.   axiom dbs_lambda_ll : is_lossless dbs_lambda.
op d_pq : bs_pq distr.              axiom d_pq_ll : is_lossless d_pq.
op d_t : bs_t distr.                axiom d_t_ll : is_lossless d_t.

op concat : bs_pq -> bs_t -> bs_full.
op slice_pq : bs_full -> bs_pq.
op slice_t  : bs_full -> bs_t.
axiom slice_concat_pq : forall a b, slice_pq (concat a b) = a.
axiom slice_concat_t  : forall a b, slice_t  (concat a b) = b.

module type K_t  = { proc derivekeypair(s : bs_pq) : ek * dk }.
module type NG_t = {
  proc randomscalar(s : bs_t) : scalar
  proc generator() : elem
  proc exp(e : elem, x : scalar) : elem
}.

module RO = { var h : bs_lambda -> bs_full }.

module Lazy (K : K_t, NG : NG_t) = {
  var h : bs_lambda -> bs_full
  var s0 : bs_lambda
  var y0_pq : bs_pq
  var y0_t : bs_t
  proc init() : (ek * elem) * bs_lambda = {
    var x : bs_lambda; var r : bs_full; var seed : bs_pq;
    var kp : ek * dk; var dk_T : scalar; var g : elem; var ek_T : elem;
    h <- RO.h;                       (* MATERIALIZED *)
    s0 <$ dbs_lambda;
    y0_pq <$ d_pq;
    y0_t <$ d_t;
    x <- s0;
    if (x = s0) { r <- concat y0_pq y0_t; } else { r <- h x; }
    seed <- slice_pq r;
    kp <@ K.derivekeypair(seed);
    dk_T <@ NG.randomscalar(slice_t r);
    g <@ NG.generator();
    ek_T <@ NG.exp(g, dk_T);
    return ((kp.`1, ek_T), s0);
  }
}.

module Ref (K : K_t, NG : NG_t) = {
  var seed_0 : bs_lambda
  proc init() : (ek * elem) * bs_lambda = {
    var seed : bs_pq; var s_T : bs_t;
    var kp : ek * dk; var dk_T : scalar; var g : elem; var ek_T : elem;
    seed <$ d_pq;
    kp <@ K.derivekeypair(seed);
    seed_0 <$ dbs_lambda;
    s_T <$ d_t;
    dk_T <@ NG.randomscalar(s_T);
    g <@ NG.generator();
    ek_T <@ NG.exp(g, dk_T);
    return ((kp.`1, ek_T), seed_0);
  }
}.

lemma init_eq (K <: K_t {-RO, -Lazy, -Ref}) (NG <: NG_t {-RO, -Lazy, -Ref, -K}) :
  equiv [ Lazy(K, NG).init ~ Ref(K, NG).init :
          ={glob RO, glob K, glob NG} ==>
          ={res, glob RO, glob K, glob NG} /\ Lazy.h{1} = RO.h{1} ].
proof.
  proc.
  (* collapse the always-true reprogramming (x = s0 by x <- s0) *)
  rcondt{1} 6.
  + auto.
  (* peel the shared call backbone tail-to-front, coupling each abstract call;
     the samples are position-misaligned so reorder them to the front first. *)
  swap{2} 3 -2.              (* seed_0 to the front *)
  swap{2} 4 -1.              (* s_T up, so side-2 samples are seed_0; seed; s_T *)
  wp.
  call (_: true).            (* exp *)
  call (_: true).            (* generator *)
  call (_: true).            (* randomscalar -- leaves slice_t r{1} = s_T{2} *)
  wp.
  call (_: true).            (* derivekeypair -- leaves slice_pq r{1} = seed{2} *)
  wp.
  rnd. rnd. rnd.
  auto => />.
  smt(slice_concat_pq slice_concat_t).
qed.
