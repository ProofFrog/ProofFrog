(* Tripwire: the split-seed `initialize` shape whose per-keypair TAIL is
 * COMMON to both sides -- the CG_seedbased HON_BIND hop_2 / hop_10 bodies.
 *
 * HOW IT DIFFERS from prg_vs_keygen_init_segmented.ec (the CK shape the
 * exporter already emits), and why that changes the closer:
 *
 *   CK   grouped side: [Generate, seed<$, T.derivekeypair, proj, proj]
 *        split   side: [Query, slice, slice, P.derivekeypair, T.derivekeypair]
 *        The t derivation happens ONCE on each side but its RESULT is
 *        destructured only on the grouped side, and the hop's post states the
 *        t keys in `ev_` form -- so the closer must peel that call ONE-SIDED
 *        with its `_det` phoare to learn the value.
 *
 *   CG   grouped side: [Generate, seed<$, NG.randomscalar, NG.generator, NG.exp]
 *        split   side: [Query, slice, slice, P.derivekeypair,
 *                       NG.randomscalar, NG.generator, NG.exp]
 *        The three-call NG derivation is IDENTICAL ON BOTH SIDES and the hop's
 *        post is plain cross-side field equality -- no `ev_` anywhere. So once
 *        the seeds are coupled the tail couples TWO-SIDED with `call (_: true)`
 *        and no `_det` axiom, no `exists*` freeze and no ev-form invariant is
 *        needed at all.
 *
 * Everything up to and including the split-uniform seed coupling is verbatim
 * from the CK tripwire; only the segment closer changes. Modelled in the REAL
 * orientation (the split side is side 1), so the emitted leading `symmetry.` is
 * validated here too, and with the grouped side's t seed as a proc LOCAL (on
 * this shape nothing in the post names it, so the exporter does not lift it to
 * a field -- the CK shape does).
 *)

require import AllCore Distr.

type pqs, ts, fulls, pkt, skt, scal, elem.

op dpqs : pqs distr.
op dts : ts distr.
op dfulls : fulls distr.

axiom dpqs_ll : is_lossless dpqs.
axiom dts_ll : is_lossless dts.

op nl : int.
op nr : int.

op concat : pqs -> ts -> fulls.
op slice_l : fulls -> int -> int -> pqs.
op slice_r : fulls -> int -> int -> ts.

(* the virtual concat triple's axioms, as the exporter emits them *)
axiom slice_concat_left  : forall a b, slice_l (concat a b) 0 nl = a.
axiom slice_concat_right : forall a b, slice_r (concat a b) nl (nl + nr) = b.
axiom concat_slices_id   :
  forall s, concat (slice_l s 0 nl) (slice_r s nl (nl + nr)) = s.
axiom dfulls_split_dlet :
  dfulls = dlet dpqs (fun (v1 : pqs) => dmap dts (fun (v2 : ts) => concat v1 v2)).

module type KEMP = { proc derivekeypair (s : pqs) : pkt * skt }.

module type NGT = {
  proc randomscalar (s : ts) : scal
  proc generator () : elem
  proc exp (b : elem, e : scal) : elem
}.

module type KGE = { proc generate () : pkt * skt }.
module type PRGO = { proc query () : fulls }.

module KeyGenEquiv_FromDeriveKeyPair (K : KEMP) : KGE = {
  proc generate () : pkt * skt = {
    var seed : pqs;
    var _r0 : pkt * skt;
    seed <$ dpqs;
    _r0 <@ K.derivekeypair(seed);
    return _r0;
  }
}.

module PRGSec_Random : PRGO = {
  proc query () : fulls = {
    var r : fulls;
    r <$ dfulls;
    return r;
  }
}.

module RedPRGc (P : KEMP, NG : NGT, Challenger : PRGO) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var seed_full_0 : fulls;
    var seed_PQ_0 : pqs;
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_full_1 : fulls;
    var seed_PQ_1 : pqs;
    var seed_T_1 : ts;
    var _r1 : elem;
    seed_full_0 <@ Challenger.query();
    seed_PQ_0 <- slice_l seed_full_0 0 nl;
    seed_T_0 <- slice_r seed_full_0 nl (nl + nr);
    pq_keys_0 <@ P.derivekeypair(seed_PQ_0);
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    seed_full_1 <@ Challenger.query();
    seed_PQ_1 <- slice_l seed_full_1 0 nl;
    seed_T_1 <- slice_r seed_full_1 nl (nl + nr);
    pq_keys_1 <@ P.derivekeypair(seed_PQ_1);
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

module RedKGc (P : KEMP, NG : NGT, Challenger : KGE) = {
  var pq_keys_0, pq_keys_1 : pkt * skt
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elem

  proc initialize () : (pkt * elem) * (pkt * elem) = {
    var seed_T_0 : ts;
    var _r0 : elem;
    var seed_T_1 : ts;
    var _r1 : elem;
    pq_keys_0 <@ Challenger.generate();
    seed_T_0 <$ dts;
    dk_T_0 <@ NG.randomscalar(seed_T_0);
    _r0 <@ NG.generator();
    ek_T_0 <@ NG.exp(_r0, dk_T_0);
    pq_keys_1 <@ Challenger.generate();
    seed_T_1 <$ dts;
    dk_T_1 <@ NG.randomscalar(seed_T_1);
    _r1 <@ NG.generator();
    ek_T_1 <@ NG.exp(_r1, dk_T_1);
    return ((pq_keys_0.`1, ek_T_0), (pq_keys_1.`1, ek_T_1));
  }
}.

section Main.

declare module P <: KEMP {-RedPRGc, -RedKGc}.
declare module NG <: NGT {-RedPRGc, -RedKGc, -P}.

lemma prg_vs_keygen_init_common_tail :
  equiv [ RedPRGc(P, NG, PRGSec_Random).initialize
          ~ RedKGc(P, NG, KeyGenEquiv_FromDeriveKeyPair(P)).initialize :
          ={glob P, glob NG}
          ==> ={res} /\ ={glob P, glob NG}
              /\ RedPRGc.pq_keys_0{1} = RedKGc.pq_keys_0{2}
              /\ RedPRGc.pq_keys_1{1} = RedKGc.pq_keys_1{2}
              /\ RedPRGc.dk_T_0{1} = RedKGc.dk_T_0{2}
              /\ RedPRGc.dk_T_1{1} = RedKGc.dk_T_1{2}
              /\ RedPRGc.ek_T_0{1} = RedKGc.ek_T_0{2}
              /\ RedPRGc.ek_T_1{1} = RedKGc.ek_T_1{2} ].
proof.
  proc.
  (* the split side is side 1 in the real hop; `symmetry` puts the grouped side
     at {1}, which is the only orientation the coupling below is validated for *)
  symmetry.
  (* keypair 0: grouped side has 5 statements, split side 7 *)
  seq 5 7 : (={glob P, glob NG}
             /\ RedKGc.pq_keys_0{1} = RedPRGc.pq_keys_0{2}
             /\ RedKGc.dk_T_0{1} = RedPRGc.dk_T_0{2}
             /\ RedKGc.ek_T_0{1} = RedPRGc.ek_T_0{2}).
  + inline *.
    (* side 1 after inline: 1 seed<$  2 P.dkp  3 pq_keys_0<-  4 seed_T_0<$
                            5 randomscalar  6 generator  7 exp *)
    swap{1} 4 -2.
    seq 2 4 : (={glob P, glob NG}
               /\ seed{1} = seed_PQ_0{2}
               /\ seed_T_0{1} = seed_T_0{2}).
    - wp.
      rndsem*{1} 0.
      rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
          (fun (sf : fulls) => (slice_l sf 0 nl, slice_r sf nl (nl + nr))).
      skip => />.
      rewrite dfulls_split_dlet.
      split.
      * move => sf hsf; rewrite concat_slices_id //.
      move => _; split.
      * move => sf hsf.
        rewrite !dlet1E; congr; apply fun_ext => a /=.
        rewrite !dmap1E /(\o) /pred1 /=.
        congr; apply mu_eq => b /=.
        by rewrite eqboolP;
           smt(slice_concat_left slice_concat_right concat_slices_id).
      move => _ p hp.
      have h1 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
      have h2 : p.`2 \in dts by smt(supp_dlet supp_dmap).
      split.
      * rewrite supp_dlet; exists p.`1; rewrite h1 /=.
        by rewrite supp_dmap; exists p.`2; rewrite h2.
      move => _; smt(slice_concat_left slice_concat_right).
    seq 2 1 : (={glob P, glob NG}
               /\ seed_T_0{1} = seed_T_0{2}
               /\ RedKGc.pq_keys_0{1} = RedPRGc.pq_keys_0{2}).
    - wp; call (_: true); skip => />.
    (* the COMMON TAIL: three calls, identical on both sides -- couple them
       two-sided back-to-front; no `_det`, no `exists*` freeze *)
    wp; call (_: true).
    wp; call (_: true).
    wp; call (_: true).
    skip => />.
  (* keypair 1: same shape, invariant carries keypair 0's conjuncts *)
  seq 5 7 : (={glob P, glob NG}
             /\ RedKGc.pq_keys_0{1} = RedPRGc.pq_keys_0{2}
             /\ RedKGc.dk_T_0{1} = RedPRGc.dk_T_0{2}
             /\ RedKGc.ek_T_0{1} = RedPRGc.ek_T_0{2}
             /\ RedKGc.pq_keys_1{1} = RedPRGc.pq_keys_1{2}
             /\ RedKGc.dk_T_1{1} = RedPRGc.dk_T_1{2}
             /\ RedKGc.ek_T_1{1} = RedPRGc.ek_T_1{2}).
  + inline *.
    swap{1} 4 -2.
    seq 2 4 : (={glob P, glob NG}
               /\ RedKGc.pq_keys_0{1} = RedPRGc.pq_keys_0{2}
               /\ RedKGc.dk_T_0{1} = RedPRGc.dk_T_0{2}
               /\ RedKGc.ek_T_0{1} = RedPRGc.ek_T_0{2}
               /\ seed{1} = seed_PQ_1{2}
               /\ seed_T_1{1} = seed_T_1{2}).
    - wp.
      rndsem*{1} 0.
      rnd (fun (p : pqs * ts) => concat p.`1 p.`2)
          (fun (sf : fulls) => (slice_l sf 0 nl, slice_r sf nl (nl + nr))).
      skip => />.
      rewrite dfulls_split_dlet.
      split.
      * move => sf hsf; rewrite concat_slices_id //.
      move => _; split.
      * move => sf hsf.
        rewrite !dlet1E; congr; apply fun_ext => a /=.
        rewrite !dmap1E /(\o) /pred1 /=.
        congr; apply mu_eq => b /=.
        by rewrite eqboolP;
           smt(slice_concat_left slice_concat_right concat_slices_id).
      move => _ p hp.
      have h1 : p.`1 \in dpqs by smt(supp_dlet supp_dmap).
      have h2 : p.`2 \in dts by smt(supp_dlet supp_dmap).
      split.
      * rewrite supp_dlet; exists p.`1; rewrite h1 /=.
        by rewrite supp_dmap; exists p.`2; rewrite h2.
      move => _; smt(slice_concat_left slice_concat_right).
    seq 2 1 : (={glob P, glob NG}
               /\ RedKGc.pq_keys_0{1} = RedPRGc.pq_keys_0{2}
               /\ RedKGc.dk_T_0{1} = RedPRGc.dk_T_0{2}
               /\ RedKGc.ek_T_0{1} = RedPRGc.ek_T_0{2}
               /\ seed_T_1{1} = seed_T_1{2}
               /\ RedKGc.pq_keys_1{1} = RedPRGc.pq_keys_1{2}).
    - wp; call (_: true); skip => />.
    wp; call (_: true).
    wp; call (_: true).
    wp; call (_: true).
    skip => />.
  skip => />.
qed.

end section Main.
