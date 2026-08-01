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

(* the KeyGenEquiv FromKeyGen challenger the LEFT side delegates to *)
module ChalK (P : KEMP) = {
  proc generate () : pkt * skt = {
    var r : pkt * skt;
    r <@ P.keygen();
    return r;
  }
}.

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
    var ek0, ek1 : tkt;
    var dk0, dk1 : tst;
    pq_keys_0 <@ ChalK(P).generate();
    seed_T_0 <$ dseed;
    t0 <@ T.derivekeypair(seed_T_0);
    ek0 <- t0.`1;
    dk0 <- t0.`2;
    pq_keys_1 <@ ChalK(P).generate();
    seed_T_1 <$ dseed;
    t1 <@ T.derivekeypair(seed_T_1);
    ek1 <- t1.`1;
    dk1 <- t1.`2;
    return ((pq_keys_0.`1, ek0), (pq_keys_1.`1, ek1));
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

(* --- the ONE-KEYPAIR variant (the CT_SAMEKEY cells) ------------------------
   With n = 1 the two interleavings are ALREADY aligned, so the `swap{2} 2 1`
   that aligns them at n = 2 has nothing to do -- and would be out of range on a
   two-statement body. Everything else is the validated per-keypair shape.
   Validated here so the n = 1 gate can be relaxed on evidence rather than on
   "it should degenerate cleanly". *)

module RedL1 (P : KEMP, T : KEMT) = {
  var pq_keys_0 : pkt * skt
  var seed_T_0 : seedt

  proc initialize () : pkt * tkt = {
    var t0 : tkt * tst;
    var ek0 : tkt;
    var dk0 : tst;
    pq_keys_0 <@ ChalK(P).generate();
    seed_T_0 <$ dseed;
    t0 <@ T.derivekeypair(seed_T_0);
    ek0 <- t0.`1;
    dk0 <- t0.`2;
    return (pq_keys_0.`1, ek0);
  }
}.

module RedR1 (P : KEMP, T : KEMT) = {
  var pq_keys_0 : pkt * skt
  var t_keys_0 : tkt * tst

  proc initialize () : pkt * tkt = {
    pq_keys_0 <@ P.keygen();
    t_keys_0 <@ Chal(T).generate();
    return (pq_keys_0.`1, t_keys_0.`1);
  }
}.

(* --- the BATCHED variant (hop_12) -----------------------------------------
   Same operation multiset as the n = 2 lemma, but the derivekeypair side runs
   BOTH challenger generates first, then both seeds, then both derivekeypairs
   with their projections -- it is batched, not alternating. So on top of the
   `swap` that aligns the grouped side, the batched side must first be regrouped
   per keypair; after that every segment is exactly the validated shape.
   This is the last open `initialize` shape on the CK HON cells. *)

module RedL2 (P : KEMP, T : KEMT) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var seed_T_0, seed_T_1 : seedt

  proc initialize () : (pkt * tkt) * (pkt * tkt) = {
    var t0 : tkt * tst;
    var ek0 : tkt;
    var dk0 : tst;
    var t1 : tkt * tst;
    var ek1 : tkt;
    var dk1 : tst;
    pq_keys_0 <@ ChalK(P).generate();
    pq_keys_1 <@ ChalK(P).generate();
    seed_T_0 <$ dseed;
    seed_T_1 <$ dseed;
    t0 <@ T.derivekeypair(seed_T_0);
    ek0 <- t0.`1;
    dk0 <- t0.`2;
    t1 <@ T.derivekeypair(seed_T_1);
    ek1 <- t1.`1;
    dk1 <- t1.`2;
    return ((pq_keys_0.`1, ek0), (pq_keys_1.`1, ek1));
  }
}.

section Main.

declare module P <: KEMP {-RedL, -RedR, -RedL1, -RedR1, -RedL2}.
declare module T <: KEMT {-RedL, -RedR, -RedL1, -RedR1, -RedL2, -P}.

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
  seq 5 2 : (={glob P, glob T}
             /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
             /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
             (* side 1's derivekeypair result is a LOCAL read at the return, so
                the segment must carry its value too -- same carried-local rule
                the n-keypair init needed. *)
             /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
             (* the PROJECTION local is read at the return too: every side-1
                local surviving the segment must be carried, not just the call
                result. *)
             /\ ek0{1} = (ev_derivekeypair RedL.seed_T_0{1}).`1).
  + inline *.
    (* side 1's challenger inlines to [keygen; assign], so the keygen segment is
       2 statements there and 1 on side 2. *)
    seq 2 1 : (={glob P, glob T} /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}).
    - wp; call (_: true); skip => />.
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
  seq 5 2 : (={glob P, glob T}
             /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
             /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
             /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
             /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}
             /\ RedR.t_keys_1{2} = ev_derivekeypair RedL.seed_T_1{1}
             /\ t1{1} = ev_derivekeypair RedL.seed_T_1{1}
             /\ ek0{1} = (ev_derivekeypair RedL.seed_T_0{1}).`1
             /\ ek1{1} = (ev_derivekeypair RedL.seed_T_1{1}).`1).
  + inline *.
    seq 2 1 : (={glob P, glob T}
               /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
               /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
               /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
               /\ ek0{1} = (ev_derivekeypair RedL.seed_T_0{1}).`1
               /\ RedL.pq_keys_1{1} = RedR.pq_keys_1{2}).
    - wp; call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T}
               /\ RedL.pq_keys_0{1} = RedR.pq_keys_0{2}
               /\ RedR.t_keys_0{2} = ev_derivekeypair RedL.seed_T_0{1}
               /\ t0{1} = ev_derivekeypair RedL.seed_T_0{1}
               /\ ek0{1} = (ev_derivekeypair RedL.seed_T_0{1}).`1
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

(* n = 1: no alignment swap, one segment. *)
lemma keygenequiv_init_n1 :
  equiv [ RedL1(P, T).initialize ~ RedR1(P, T).initialize :
          ={glob P, glob T}
          ==> ={res} /\ ={glob P, glob T}
              /\ RedL1.pq_keys_0{1} = RedR1.pq_keys_0{2}
              /\ RedR1.t_keys_0{2} = ev_derivekeypair RedL1.seed_T_0{1} ].
proof.
  proc.
  seq 5 2 : (={glob P, glob T}
             /\ RedL1.pq_keys_0{1} = RedR1.pq_keys_0{2}
             /\ RedR1.t_keys_0{2} = ev_derivekeypair RedL1.seed_T_0{1}
             /\ t0{1} = ev_derivekeypair RedL1.seed_T_0{1}
             /\ ek0{1} = (ev_derivekeypair RedL1.seed_T_0{1}).`1
             /\ dk0{1} = (ev_derivekeypair RedL1.seed_T_0{1}).`2).
  + inline *.
    seq 2 1 : (={glob P, glob T} /\ RedL1.pq_keys_0{1} = RedR1.pq_keys_0{2}).
    - wp; call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T} /\ RedL1.pq_keys_0{1} = RedR1.pq_keys_0{2}
               /\ RedL1.seed_T_0{1} = s{2}).
    - rnd; skip => />.
    exists* (glob T){1}, RedL1.seed_T_0{1}.
    elim* => gT sv.
    wp.
    call{2} (T_derivekeypair_det gT sv).
    call{1} (T_derivekeypair_det gT sv).
    skip => />.
  skip => />.
qed.

(* the BATCHED alternating side: regroup it per keypair first. *)
lemma keygenequiv_init_batched :
  equiv [ RedR(P, T).initialize ~ RedL2(P, T).initialize :
          ={glob P, glob T}
          ==> ={res} /\ ={glob P, glob T}
              /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
              /\ RedR.pq_keys_1{1} = RedL2.pq_keys_1{2}
              /\ RedR.t_keys_0{1} = ev_derivekeypair RedL2.seed_T_0{2}
              /\ RedR.t_keys_1{1} = ev_derivekeypair RedL2.seed_T_1{2} ].
proof.
  proc.
  (* align the GROUPED side, exactly as the n = 2 lemma does *)
  swap{1} 2 1.
  (* regroup the BATCHED side per keypair:
       1 g0  2 g1  3 s0  4 s1  5 dkp0  6 ek0  7 dk0  8 dkp1  9 ek1  10 dk1
     and keypair 0's material is 1,3,5,6,7 -- the same four moves the split-seed
     route computes for the identical batched layout. *)
  swap{2} 3 -1.
  swap{2} 5 -2.
  swap{2} 6 -2.
  swap{2} 7 -2.
  seq 2 5 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
             /\ RedR.t_keys_0{1} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ t0{2} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ ek0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`1
             /\ dk0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`2).
  + inline *.
    seq 1 2 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}).
    - wp; call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
             /\ s{1} = RedL2.seed_T_0{2}).
    - rnd; skip => />.
    exists* (glob T){2}, RedL2.seed_T_0{2}.
    elim* => gT sv.
    wp.
    call{1} (T_derivekeypair_det gT sv).
    call{2} (T_derivekeypair_det gT sv).
    skip => />.
  seq 2 5 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
             /\ RedR.t_keys_0{1} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ t0{2} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ ek0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`1
             /\ dk0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`2
             /\ RedR.pq_keys_1{1} = RedL2.pq_keys_1{2}
             /\ RedR.t_keys_1{1} = ev_derivekeypair RedL2.seed_T_1{2}
             /\ t1{2} = ev_derivekeypair RedL2.seed_T_1{2}
             /\ ek1{2} = (ev_derivekeypair RedL2.seed_T_1{2}).`1
             /\ dk1{2} = (ev_derivekeypair RedL2.seed_T_1{2}).`2).
  + inline *.
    seq 1 2 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
             /\ RedR.t_keys_0{1} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ t0{2} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ ek0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`1
             /\ dk0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`2
             /\ RedR.pq_keys_1{1} = RedL2.pq_keys_1{2}).
    - wp; call (_: true); skip => />.
    seq 1 1 : (={glob P, glob T}
             /\ RedR.pq_keys_0{1} = RedL2.pq_keys_0{2}
             /\ RedR.t_keys_0{1} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ t0{2} = ev_derivekeypair RedL2.seed_T_0{2}
             /\ ek0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`1
             /\ dk0{2} = (ev_derivekeypair RedL2.seed_T_0{2}).`2
             /\ RedR.pq_keys_1{1} = RedL2.pq_keys_1{2}
             /\ s{1} = RedL2.seed_T_1{2}).
    - rnd; skip => />.
    exists* (glob T){2}, RedL2.seed_T_1{2}.
    elim* => gT sv.
    wp.
    call{1} (T_derivekeypair_det gT sv).
    call{2} (T_derivekeypair_det gT sv).
    skip => />.
  skip => />.
qed.

end section Main.
