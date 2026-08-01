(* Tripwire: the KeyGenEquiv `initialize` hop (CK hop_4 / hop_14 shape).
 *
 * Two reductions run the SAME operation multiset in DIFFERENT interleavings:
 *   left  : keygen; sample; derivekeypair;  keygen; sample; derivekeypair
 *   right : keygen; keygen;  generate; generate      (each `generate` inlining
 *                                                     to sample; derivekeypair)
 * and the hop's post is not just `={res}` -- it carries the cross-stage
 * derivation conjunct `t_keys_k{2} = ev_derivekeypair (seed_T_k{1})` that
 * `_cross_stage_field_coupling` emits. Closing THIS lemma is what converts that
 * coupling from ASSUMED to EC-checked.
 *
 * FINDING recorded by this file: EC's `swap` DOES reorder two abstract
 * PROBABILISTIC calls when their globs are disjoint. The branch notes said
 * `swap` refuses to reorder abstract scheme calls; that holds for same-module or
 * dependency-crossing moves, not for this one. `swap{2} 2 1` therefore aligns
 * the two interleavings with no `Ideal`/stateless machinery at all.
 *
 * After the alignment the shape is the familiar one: segment per keypair, couple
 * the samples with `rnd`, freeze, and peel each derivekeypair ONE-SIDED with its
 * `_det` axiom -- a two-sided `call (_: true)` proves `={res}` but learns nothing
 * about the returned value, which is exactly what the derivation conjunct needs.
 *)

require import AllCore Distr.

type pkt, skt, tkt, tst, seedt.

op dseed : seedt distr.
axiom dseed_ll : is_lossless dseed.

op ev_derivekeypair : seedt -> tkt * tst.

module type KEMP = { proc keygen () : pkt * skt }.
module type KEMT = { proc derivekeypair (s : seedt) : tkt * tst }.

(* the KeyGenEquiv FromDeriveKeyPair challenger the right side delegates to *)
module Chal (T : KEMT) = {
  proc generate () : tkt * tst = {
    var s : seedt;
    var r : tkt * tst;
    s <$ dseed;
    r <@ T.derivekeypair(s);
    return r;
  }
}.

module RedL (P : KEMP, T : KEMT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var seed_T_0, seed_T_1 : seedt

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var t0, t1 : tkt * tst;
    pq_keys_0 <@ P.keygen();
    seed_T_0 <$ dseed;
    t0 <@ T.derivekeypair(seed_T_0);
    pq_keys_1 <@ P.keygen();
    seed_T_1 <$ dseed;
    t1 <@ T.derivekeypair(seed_T_1);
    return ((pq_keys_0.`1, t0.`1), (pq_keys_1.`1, t1.`1));
  }
}.

module RedR (P : KEMP, T : KEMT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var t_keys_0, t_keys_1 : tkt * tst

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    pq_keys_0 <@ P.keygen();
    pq_keys_1 <@ P.keygen();
    t_keys_0 <@ Chal(T).generate();
    t_keys_1 <@ Chal(T).generate();
    return ((pq_keys_0.`1, t_keys_0.`1), (pq_keys_1.`1, t_keys_1.`1));
  }
}.

section Main.

declare module P <: KEMP {-RedL, -RedR}.
declare module T <: KEMT {-RedL, -RedR, -P}.

declare axiom T_derivekeypair_det (g : (glob T)) (a0 : seedt) :
  phoare[ T.derivekeypair : (glob T) = g /\ s = a0
          ==> (glob T) = g /\ res = ev_derivekeypair a0 ] = 1%r.

lemma keygenequiv_init :
  equiv [ RedL(P, T).initialize ~ RedR(P, T).initialize :
          ={glob P, glob T}
          ==> ={res} /\ ={glob P, glob T}
              /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
              /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}
              /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
              /\ RedR.t_keys_1{2} = ev_derivekeypair RedL.seed_T_1{1} ].
proof.
  proc.
  (* 1. ALIGN the interleavings. EC accepts this: the two abstract probabilistic
        calls write disjoint globs (`glob P` vs `glob T`). *)
  swap{2} 2 1.
  (* 2. keypair 0: couple the keygens, then the samples, then peel the
        derivekeypair ONE-SIDED on each side so the post learns the VALUE. *)
  (* Segment on the UN-inlined bodies -- side 1 [keygen; sample; derivekeypair]
     = 3, side 2 [keygen; generate] = 2 -- and put `inline *` INSIDE the bullet.
     That way only ONE `generate` is inlined per segment, so its sample local is
     the bare `s` every time and no collision suffix has to be predicted. With a
     single top-level `inline *` the second segment's local becomes `s0` and the
     invariant silently names the wrong variable. *)
  seq 3 2 : (={glob P, glob T}
             /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
             /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
             (* side 1's derivekeypair result is a LOCAL read at the return, so
                the segment must carry its value too -- same carried-local rule
                the n-keypair init needed. *)
             /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}).
  + inline *.
    seq 1 1 : (={glob P, glob T} /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}).
    - call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T} /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
               /\ RedL.seed_T_0{1} = s{2}).
    - rnd; skip => />.
    exists* (glob T){1}, RedL.seed_T_0{1}.
    elim* => gT sv.
    wp.
    call{2} (T_derivekeypair_det gT sv).
    call{1} (T_derivekeypair_det gT sv).
    skip => />.
  (* 3. keypair 1: same shape, invariant carries keypair 0's conjuncts. *)
  seq 3 2 : (={glob P, glob T}
             /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
             /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
             /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
             /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}
             /\ RedR.t_keys_1{2} = ev_derivekeypair RedL.seed_T_1{1}
             /\ t1{1} = ev_derivekeypair RedL.seed_T_1{1}).
  + inline *.
    seq 1 1 : (={glob P, glob T}
               /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
               /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
               /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
               /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}).
    - call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T}
               /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
               /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
               /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
               /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}
               /\ RedL.seed_T_1{1} = s{2}).
    - rnd; skip => />.
    exists* (glob T){1}, RedL.seed_T_1{1}.
    elim* => gT sv.
    wp.
    call{2} (T_derivekeypair_det gT sv).
    call{1} (T_derivekeypair_det gT sv).
    skip => />.
  skip => />.
qed.

end section Main.
