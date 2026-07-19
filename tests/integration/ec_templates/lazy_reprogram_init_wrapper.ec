(* Faithful wrapper-level tripwire for the reprogramming-Lazy init hop (wall 3o
   STEP D). Unlike lazy_reprogram_init_calls.ec (which pre-collapsed the if and
   modelled the derivation inline), this mirrors the REAL exported shape: a Lazy
   challenger MODULE with a sample-only `initialize` and a reprogramming `hash`,
   wrapped by a reduction R_L that calls challenger.initialize/hash then the
   abstract KEM/NG backbone; vs a KeyGen reduction R_R that samples directly.
   The lemma relates the two `.initialize` via `proc. inline *.`, so EC's inline
   reproduces the real single reprogramming `if` at its real position.

   Goal: confirm the position-ROBUST tactic (rcondt via `^if` codepos, no magic
   number) and the distribution-aware sample reorder. *)

require import AllCore Distr.

type bs_lambda, bs_pq, bs_t, bs_full, ek, dk, elem, scalar.

op dbs_lambda : bs_lambda distr.   axiom dbs_lambda_ll : is_lossless dbs_lambda.
op d_pq : bs_pq distr.              axiom d_pq_ll : is_lossless d_pq.
op d_t : bs_t distr.               axiom d_t_ll : is_lossless d_t.

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

(* --- the two challenger interfaces (materialized Lazy vs KeyGen) --- *)
module type Chal_t = {
  proc initialize() : bs_lambda
  proc hash(x : bs_lambda) : bs_full
}.

module Lazy_Mat : Chal_t = {
  var h : bs_lambda -> bs_full
  var s0 : bs_lambda
  var y0_pq : bs_pq
  var y0_t : bs_t
  proc initialize() : bs_lambda = {
    h <- RO.h;
    s0 <$ dbs_lambda;
    y0_pq <$ d_pq;
    y0_t <$ d_t;
    return s0;
  }
  proc hash(x : bs_lambda) : bs_full = {
    var r : bs_full;
    if (x = s0) { r <- concat y0_pq y0_t; } else { r <- h x; }
    return r;
  }
}.

(* Side 1: reduction wrapping the Lazy challenger + abstract KEM/NG backbone. *)
module R_L (K : K_t, NG : NG_t, C : Chal_t) = {
  proc initialize() : (ek * elem) * bs_lambda = {
    var seed_0 : bs_lambda; var y_0 : bs_full; var seed : bs_pq;
    var kp : ek * dk; var dk_T : scalar; var g : elem; var ek_T : elem;
    seed_0 <@ C.initialize();
    y_0 <@ C.hash(seed_0);
    seed <- slice_pq y_0;
    kp <@ K.derivekeypair(seed);
    dk_T <@ NG.randomscalar(slice_t y_0);
    g <@ NG.generator();
    ek_T <@ NG.exp(g, dk_T);
    return ((kp.`1, ek_T), seed_0);
  }
}.

(* Side 2: reduction sampling the KEM seed + T seed directly (KeyGen). *)
module R_R (K : K_t, NG : NG_t) = {
  proc initialize() : (ek * elem) * bs_lambda = {
    var seed : bs_pq; var seed_0 : bs_lambda; var s_T : bs_t;
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

lemma init_eq (K <: K_t {-RO, -Lazy_Mat}) (NG <: NG_t {-RO, -Lazy_Mat, -K}) :
  equiv [ R_L(K, NG, Lazy_Mat).initialize ~ R_R(K, NG).initialize :
          ={glob RO, glob K, glob NG} ==>
          ={res, glob RO, glob K, glob NG} /\ Lazy_Mat.h{1} = RO.h{1} ].
proof.
  proc.
  inline *.
  (* collapse the reprogramming if by CODE POSITION (^if), not a magic number *)
  rcondt{1} ^if.
  + auto.
  (* reorder side-2 samples to side-1's distribution order [lambda, pq, t]:
     side 1 samples s0(lambda), y0_pq(pq), y0_t(t) up front; side 2 is
     seed(pq), <derivekeypair>, seed_0(lambda), s_T(t). Address each sample by
     its OCCURRENCE (^ <${k}) and hoist to gap 0 (block front) -- position-
     robust, independent of how many tuple-unpack assigns inline * interposes.
     Hoisting in reverse target order lands them front in [lambda, pq, t]. *)
  swap{2} ^ <${3} @ 0.
  swap{2} ^ <${2} @ 0.
  swap{2} ^ <${3} @ 0.
  wp.
  call (_: true).            (* exp *)
  call (_: true).            (* generator *)
  call (_: true).            (* randomscalar *)
  wp.
  call (_: true).            (* derivekeypair *)
  wp.
  rnd. rnd. rnd.
  auto => />.
  smt(slice_concat_pq slice_concat_t).
qed.
