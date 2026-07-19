(* Faithful tripwire for the KDF-layer hop_6/8_initialize shape: two reduction
   inits that sample the SAME 3 distributions + make the SAME 4 abstract calls in
   the SAME relative order, differing ONLY in sample interleaving (a reorder) +
   deterministic tuple plumbing. LEFT samples s_pq first (dkp immediately), then
   s_lam/s_t late; RIGHT samples all 3 up front, dkp after. Find a swap-align +
   peel that closes it, to drive a synthesizer route. *)

require import AllCore Distr.

type ek, dk, elem, scalar, bs_lam, bs_pq, bs_t.
op d_lam : bs_lam distr.   axiom d_lam_ll : is_lossless d_lam.
op d_pq  : bs_pq distr.    axiom d_pq_ll  : is_lossless d_pq.
op d_t   : bs_t distr.     axiom d_t_ll   : is_lossless d_t.

module type K_t  = { proc derivekeypair(s : bs_pq) : ek * dk }.
module type NG_t = {
  proc randomscalar(s : bs_t) : scalar
  proc generator() : elem
  proc exp(e : elem, x : scalar) : elem
}.

module RL (K : K_t, NG : NG_t) = {
  var s_pq : bs_pq  var s_t : bs_t  var seed : bs_lam
  proc initialize() : (ek * elem) * bs_lam = {
    var tup1 : ek * dk; var ek_inner : ek; var g : elem; var ek_T : elem;
    var dk_T : scalar; var tup0 : ek * bs_pq; var ek0 : ek; var tup : (ek*elem)*bs_lam;
    s_pq <$ d_pq;
    tup1 <@ K.derivekeypair(s_pq);
    ek_inner <- tup1.`1;
    tup0 <- (ek_inner, s_pq);
    ek0 <- tup0.`1;
    seed <$ d_lam;
    s_t <$ d_t;
    dk_T <@ NG.randomscalar(s_t);
    g <@ NG.generator();
    ek_T <@ NG.exp(g, dk_T);
    tup <- ((ek0, ek_T), seed);
    return tup;
  }
}.
module RR (K : K_t, NG : NG_t) = {
  var s_pq : bs_pq  var s_t : bs_t  var seed : bs_lam
  proc initialize() : (ek * elem) * bs_lam = {
    var tup0 : ek * dk; var ek_inner : ek; var g : elem; var ek_T : elem;
    var dk_T : scalar; var tup : ek * bs_pq; var ek_PQ : ek;
    seed <$ d_lam;
    s_pq <$ d_pq;
    s_t <$ d_t;
    tup0 <@ K.derivekeypair(s_pq);
    ek_inner <- tup0.`1;
    tup <- (ek_inner, s_pq);
    ek_PQ <- tup.`1;
    dk_T <@ NG.randomscalar(s_t);
    g <@ NG.generator();
    ek_T <@ NG.exp(g, dk_T);
    return ((ek_PQ, ek_T), seed);
  }
}.

lemma init_reorder (K <: K_t {-RL, -RR}) (NG <: NG_t {-RL, -RR, -K}) :
  equiv [ RL(K, NG).initialize ~ RR(K, NG).initialize :
    ={glob K, glob NG} ==>
    ={res, glob K, glob NG} /\ RR.s_pq{2} = RL.s_pq{1}
    /\ RR.s_t{2} = RL.s_t{1} /\ RR.seed{2} = RL.seed{1} ].
proof.
  proc.
  (* align LEFT's late samples (seed@6, s_t@7) up to the front to match RIGHT *)
  swap{1} 6 -5.
  swap{1} 7 -4.
  (* peel the now-common backbone tail-to-front: 4 abstract calls, 3 samples *)
  wp. call (_: true).
  wp. call (_: true).
  wp. call (_: true).
  wp. call (_: true).
  rnd. rnd. rnd.
  skip => /#.
qed.
