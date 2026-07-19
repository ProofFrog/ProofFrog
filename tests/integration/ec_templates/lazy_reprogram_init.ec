(* Tripwire: the CGLazyRO *Lazy* hop init equiv (wall 3o).

   hop_2_initialize relates `R_LazyRO_L(...CGLazyROOneSeeded_Lazy).initialize`
   (side 1) to `R_KG_L(...KeyGenEquiv_FromDeriveKeyPair).initialize` (side 2).
   The Lazy game reprograms the shared RO at the exposed seed s0: its Initialize
   samples s0, y0_pq, y0_t and answers Hash(s0) with `y0_pq || y0_t`. Because the
   reduction feeds x = s0 (the just-exposed seed) the reprogramming `if (x = s0)`
   is ALWAYS TRUE, so the derived keypair comes from the FRESH y0_pq/y0_t; the
   reference (side 2) derives from a fresh seed + T-seed directly. The two are
   identically distributed via `slice(concat a b) = a/b` and the uniform samples.

   The Lazy challenger's RO field `h` is MATERIALIZED to the shared RO (`h <- RO.h`,
   the wall-3o render fix) so the post `Lazy.h{1} = RO.h{1}` holds; in THIS hop the
   reprogramming fires so `h` is otherwise dead. This tripwire validates the
   closing tactic shape: rcondt the always-true if, then couple the reprogrammed
   fresh samples to the reference's direct samples via slice_concat + rnd. The
   abstract derivekeypair/NG backbone peel is already handled by the existing init
   synthesizer, so it is modelled here as deterministic ops. *)

require import AllCore Distr.

type bs_lambda.
type bs_pq.
type bs_t.
type bs_full.
type ek.
type scalar.

op dbs_lambda : bs_lambda distr.
axiom dbs_lambda_ll : is_lossless dbs_lambda.

op d_pq : bs_pq distr.
axiom d_pq_ll : is_lossless d_pq.

op d_t : bs_t distr.
axiom d_t_ll : is_lossless d_t.

op concat : bs_pq -> bs_t -> bs_full.
op slice_pq : bs_full -> bs_pq.
op slice_t  : bs_full -> bs_t.
axiom slice_concat_pq : forall a b, slice_pq (concat a b) = a.
axiom slice_concat_t  : forall a b, slice_t  (concat a b) = b.

(* deterministic stand-ins for derivekeypair / randomscalar *)
op derive : bs_pq -> ek.
op sc     : bs_t  -> scalar.

module RO = { var h : bs_lambda -> bs_full }.

module Lazy = {
  var h : bs_lambda -> bs_full
  var s0 : bs_lambda
  var y0_pq : bs_pq
  var y0_t : bs_t
  proc init() : (ek * scalar) * bs_lambda = {
    var x : bs_lambda;
    var r : bs_full;
    var seed : bs_pq;
    var st : bs_t;
    h <- RO.h;                     (* MATERIALIZED: Lazy.h = RO.h *)
    s0 <$ dbs_lambda;
    y0_pq <$ d_pq;
    y0_t <$ d_t;
    x <- s0;
    if (x = s0) {
      r <- concat y0_pq y0_t;
    } else {
      r <- h x;
    }
    seed <- slice_pq r;
    st <- slice_t r;
    return ((derive seed, sc st), s0);
  }
}.

module Ref = {
  var seed_0 : bs_lambda
  proc init() : (ek * scalar) * bs_lambda = {
    var seed : bs_pq;
    var st : bs_t;
    seed <$ d_pq;
    st <$ d_t;
    seed_0 <$ dbs_lambda;
    return ((derive seed, sc st), seed_0);
  }
}.

(* The post carries the Lazy.h = RO.h materialization identity (threaded to the
   later hops that read the RO), plus res equality. *)
lemma init_eq :
  equiv [ Lazy.init ~ Ref.init :
          ={glob RO} ==> ={res} /\ ={glob RO} /\ Lazy.h{1} = RO.h{1} ].
proof.
  proc.
  (* collapse the always-true reprogramming: x = s0 by the x <- s0 assignment *)
  rcondt{1} 6.
  + auto.
  (* side 1 now: h<-RO.h; s0<$; y0_pq<$; y0_t<$; x<-s0; r<-concat y0_pq y0_t;
     seed<-slice_pq r; st<-slice_t r; return ((derive seed, sc st), s0).
     side 2: seed<$; st<$; seed_0<$; return ((derive seed, sc st), seed_0). *)
  wp.
  (* couple the three samples: s0{1}~seed_0{2}, y0_t{1}~st{2}, y0_pq{1}~seed{2}.
     Sample orders differ, so align with swap, then rnd (backward). *)
  swap{2} 3 -2.                     (* bring seed_0 to the front on side 2 *)
  rnd.                             (* s0{1} ~ seed_0{2}   (dbs_lambda) *)
  rnd.                             (* y0_t{1} ~ st{2}      (d_t) *)
  rnd.                             (* y0_pq{1} ~ seed{2}   (d_pq) *)
  auto => />.
  smt(slice_concat_pq slice_concat_t).
qed.
