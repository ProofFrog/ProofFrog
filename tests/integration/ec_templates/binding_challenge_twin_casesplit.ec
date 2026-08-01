(* Tripwire: the TWIN-PREFIX binding `Challenge` case-split, reduction ~ reduction.
 *
 * Shape (CG/CK_seedbased HON_BIND, hop_4/6/8 `challenge`): both endpoints are
 * REDUCTIONS running the same expanded KDF backbone. Measured on the rendered
 * wrappers of CG_seedbased_HON_BIND_K_PK, they are statement-wise twins up to
 * the `if`, differing only in
 *   (i)  `ss_PQ_k <@ K.decaps(pq_keys_k.`2, ...)`  vs
 *        `ss_PQ_k <@ C.decaps<k>(...)`   -- the same call after `inline`, args
 *        equal BY THE COUPLING;
 *   (ii) `ek_k <- (pq_keys_k.`1, ek_T_k)` vs `ek_k <- (ek_PQ_k, ek_T_k)` -- again
 *        equal by the coupling;
 *   (iii) side 2's trailing `if (kdf_in_0 = kdf_in_1) { return C.challenge(..) }`.
 *
 * The existing `_challenge_casesplit_route` cannot serve this: it assumes the
 * LEFT endpoint is the theorem GAME running the concrete hybrid scheme, taking
 * `scheme_expr` positionally and functionalizing the whole left decaps with one
 * `<Scheme>_decaps_val` phoare. Here the left backbone is already expanded.
 *
 * This file pins the replacement recipe: `seq n n` on the common prefix (n read
 * off the rendered wrappers), a count-free TWO-SIDED peel for it (`sim` cannot
 * -- it relates globals by name and the decaps args are cross-named), then
 * `case` on the collision guard with `rcondt`/`rcondf`.
 *
 * The concat/KDF structure is modelled by an abstract `kdf_in` op over its four
 * components plus an injectivity axiom -- standing in for the real
 * `concat_*`/`slice_concat_left_*` chain, whose peeling is already validated
 * elsewhere. What is under test here is the CONTROL FLOW: seq/peel/case/rcond,
 * and whether the collision branch's two sides really do agree.
 *)

require import AllCore Distr.

type ekt, dkt, ctt, sst, elemt, scalart, ssT, kdft, outt.

op ev_decaps  : dkt -> ctt -> sst.
op ev_exp     : elemt -> scalart -> elemt.
op ev_e2ss    : elemt -> ssT.
op ev_get     : outt.
op ev_evaluate : kdft -> outt.

(* the KDF input, over its four components; injective in each *)
op kdf_in : sst -> ssT -> elemt -> elemt -> kdft.
axiom kdf_in_inj (a a' : sst) (b b' : ssT) (c c' : elemt) (d d' : elemt) :
  kdf_in a b c d = kdf_in a' b' c' d' => a = a' /\ b = b' /\ c = c' /\ d = d'.

module type KEM = { proc decaps (dk : dkt, c : ctt) : sst }.
module type NGrp = {
  proc exp (base : elemt, e : scalart) : elemt
  proc elementtosharedsecret (x : elemt) : ssT
}.
module type KDF = { proc evaluate (x : kdft) : outt }.

(* --- the inner PQ binding challenger side 2 delegates to ------------------- *)

module Chal (K : KEM) = {
  var ek0, ek1 : ekt
  var dk0, dk1 : dkt

  proc decaps0 (c : ctt) : sst = { var r; r <@ K.decaps(dk0, c); return r; }
  proc decaps1 (c : ctt) : sst = { var r; r <@ K.decaps(dk1, c); return r; }

  proc challenge (c0 : ctt, c1 : ctt) : bool = {
    var s0, s1 : sst;
    s0 <@ K.decaps(dk0, c0);
    s1 <@ K.decaps(dk1, c1);
    return (s0 = s1) /\ ek0 <> ek1;
  }
}.

(* --- side 1: holds its own packed PQ keypairs ------------------------------ *)

module RedL (K : KEM, N : NGrp, H : KDF) = {
  var pq_keys_0, pq_keys_1 : ekt * dkt
  var dk_T_0, dk_T_1 : scalart
  var ek_T_0, ek_T_1 : elemt

  proc challenge (ct0 : ctt * elemt, ct1 : ctt * elemt) : bool = {
    var ct_T_0, ct_T_1, r0, r4 : elemt;
    var ss_PQ_0, ss_PQ_1 : sst;
    var ss_T_0, ss_T_1 : ssT;
    var kdf_in_0, kdf_in_1 : kdft;
    var ek0, ek1 : ekt * elemt;
    var r8, r9 : outt;
    ct_T_0 <- ct0.`2;
    ct_T_1 <- ct1.`2;
    ss_PQ_0 <@ K.decaps(pq_keys_0.`2, ct0.`1);
    r0 <@ N.exp(ct_T_0, dk_T_0);
    ss_T_0 <@ N.elementtosharedsecret(r0);
    kdf_in_0 <- kdf_in ss_PQ_0 ss_T_0 ct_T_0 ek_T_0;
    ss_PQ_1 <@ K.decaps(pq_keys_1.`2, ct1.`1);
    r4 <@ N.exp(ct_T_1, dk_T_1);
    ss_T_1 <@ N.elementtosharedsecret(r4);
    kdf_in_1 <- kdf_in ss_PQ_1 ss_T_1 ct_T_1 ek_T_1;
    ek0 <- (pq_keys_0.`1, ek_T_0);
    ek1 <- (pq_keys_1.`1, ek_T_1);
    r8 <@ H.evaluate(kdf_in_0);
    r9 <@ H.evaluate(kdf_in_1);
    return (r8 = r9) /\ ek0 <> ek1;
  }
}.

(* --- side 2: delegates its PQ decaps, and forwards a collision ------------- *)

module RedR (K : KEM, N : NGrp, H : KDF, C : KEM) = {
  var ek_PQ_0, ek_PQ_1 : ekt
  var dk_T_0, dk_T_1 : scalart
  var ek_T_0, ek_T_1 : elemt

  proc challenge (ct0 : ctt * elemt, ct1 : ctt * elemt) : bool = {
    var ct_T_0, ct_T_1, r0, r4 : elemt;
    var ss_PQ_0, ss_PQ_1 : sst;
    var ss_T_0, ss_T_1 : ssT;
    var kdf_in_0, kdf_in_1 : kdft;
    var ek0, ek1 : ekt * elemt;
    var r8, r9 : outt;
    var r10 : bool;
    ct_T_0 <- ct0.`2;
    ct_T_1 <- ct1.`2;
    ss_PQ_0 <@ Chal(K).decaps0(ct0.`1);
    r0 <@ N.exp(ct_T_0, dk_T_0);
    ss_T_0 <@ N.elementtosharedsecret(r0);
    kdf_in_0 <- kdf_in ss_PQ_0 ss_T_0 ct_T_0 ek_T_0;
    ss_PQ_1 <@ Chal(K).decaps1(ct1.`1);
    r4 <@ N.exp(ct_T_1, dk_T_1);
    ss_T_1 <@ N.elementtosharedsecret(r4);
    kdf_in_1 <- kdf_in ss_PQ_1 ss_T_1 ct_T_1 ek_T_1;
    if (kdf_in_0 = kdf_in_1) {
      r10 <@ Chal(K).challenge(ct0.`1, ct1.`1);
    } else {
      ek0 <- (ek_PQ_0, ek_T_0);
      ek1 <- (ek_PQ_1, ek_T_1);
      r8 <@ H.evaluate(kdf_in_0);
      r9 <@ H.evaluate(kdf_in_1);
      r10 <- (r8 = r9) /\ ek0 <> ek1;
    }
    return r10;
  }
}.

section Main.

declare module K <: KEM  {-RedL, -RedR, -Chal}.
declare module N <: NGrp {-RedL, -RedR, -Chal, -K}.
declare module H <: KDF  {-RedL, -RedR, -Chal, -K, -N}.

declare axiom K_decaps_det (g : (glob K)) (a0 : dkt) (a1 : ctt) :
  phoare[ K.decaps : (glob K) = g /\ dk = a0 /\ c = a1
          ==> (glob K) = g /\ res = ev_decaps a0 a1 ] = 1%r.

declare axiom N_exp_det (g : (glob N)) (a0 : elemt) (a1 : scalart) :
  phoare[ N.exp : (glob N) = g /\ base = a0 /\ e = a1
          ==> (glob N) = g /\ res = ev_exp a0 a1 ] = 1%r.

declare axiom N_e2ss_det (g : (glob N)) (a0 : elemt) :
  phoare[ N.elementtosharedsecret : (glob N) = g /\ x = a0
          ==> (glob N) = g /\ res = ev_e2ss a0 ] = 1%r.

declare axiom H_evaluate_det (g : (glob H)) (a0 : kdft) :
  phoare[ H.evaluate : (glob H) = g /\ x = a0
          ==> (glob H) = g /\ res = ev_evaluate a0 ] = 1%r.

(* the hop coupling: side 1's packed keypairs decompose to the challenger's
   fields, and the T material is shared by name *)
lemma hop_challenge_twin :
  equiv [ RedL(K, N, H).challenge ~ RedR(K, N, H, K).challenge :
          ={ct0, ct1} /\ ={glob K, glob N, glob H}
          /\ RedL.dk_T_0{1} = RedR.dk_T_0{2}
          /\ RedL.dk_T_1{1} = RedR.dk_T_1{2}
          /\ RedL.ek_T_0{1} = RedR.ek_T_0{2}
          /\ RedL.ek_T_1{1} = RedR.ek_T_1{2}
          /\ RedL.pq_keys_0{1}.`1 = Chal.ek0{2}
          /\ RedL.pq_keys_1{1}.`1 = Chal.ek1{2}
          /\ RedL.pq_keys_0{1}.`2 = Chal.dk0{2}
          /\ RedL.pq_keys_1{1}.`2 = Chal.dk1{2}
          /\ RedR.ek_PQ_0{2} = Chal.ek0{2}
          /\ RedR.ek_PQ_1{2} = Chal.ek1{2}
          ==> ={res} ].
proof.
  proc.
  (* --- the common 10-statement prefix ------------------------------------- *)
  seq 10 10 : (={ct0, ct1, kdf_in_0, kdf_in_1}
               /\ ={glob K, glob N, glob H}
               /\ RedL.ek_T_0{1} = RedR.ek_T_0{2}
               /\ RedL.ek_T_1{1} = RedR.ek_T_1{2}
               /\ RedL.pq_keys_0{1}.`1 = Chal.ek0{2}
               /\ RedL.pq_keys_1{1}.`1 = Chal.ek1{2}
               /\ RedR.ek_PQ_0{2} = Chal.ek0{2}
               /\ RedR.ek_PQ_1{2} = Chal.ek1{2}
               (* the ev-FORMS, not just `={...}`: the collision branch has to
                  relate side 2's challenger decaps to the prefix's, and to
                  apply KDF-input injectivity it needs the kdf_in STRUCTURE.
                  A two-sided `call (_: true)` peel proves only `={...}` and
                  loses both -- measured. *)
               /\ ss_PQ_0{2} = ev_decaps Chal.dk0{2} ct0{2}.`1
               /\ ss_PQ_1{2} = ev_decaps Chal.dk1{2} ct1{2}.`1
               /\ kdf_in_0{2} = kdf_in ss_PQ_0{2}
                     (ev_e2ss (ev_exp ct0{2}.`2 RedR.dk_T_0{2})) ct0{2}.`2
                     RedR.ek_T_0{2}
               /\ kdf_in_1{2} = kdf_in ss_PQ_1{2}
                     (ev_e2ss (ev_exp ct1{2}.`2 RedR.dk_T_1{2})) ct1{2}.`2
                     RedR.ek_T_1{2}).
  + inline *.
    (* one-sided det peels on BOTH sides -- `sim` relates globals by name and the
       decaps args are cross-named, and a two-sided `call (_: true)` peel would
       learn nothing about the returned values. *)
    exists* (glob K){1}, (glob N){1}, RedL.pq_keys_0{1}, RedL.pq_keys_1{1},
            RedL.dk_T_0{1}, RedL.dk_T_1{1}, ct0{1}, ct1{1},
            Chal.dk0{2}, Chal.dk1{2}, RedR.dk_T_0{2}, RedR.dk_T_1{2}.
    elim* => gK gN p0 p1 t0 t1 a0 a1 q0 q1 u0 u1.
    wp.
    call{1} (N_e2ss_det gN (ev_exp a1.`2 t1)).
    wp.
    call{1} (N_exp_det gN a1.`2 t1).
    wp.
    call{1} (K_decaps_det gK (p1.`2) (a1.`1)).
    wp.
    call{1} (N_e2ss_det gN (ev_exp a0.`2 t0)).
    wp.
    call{1} (N_exp_det gN a0.`2 t0).
    wp.
    call{1} (K_decaps_det gK (p0.`2) (a0.`1)).
    wp.
    call{2} (N_e2ss_det gN (ev_exp a1.`2 u1)).
    wp.
    call{2} (N_exp_det gN a1.`2 u1).
    wp.
    call{2} (K_decaps_det gK q1 (a1.`1)).
    wp.
    call{2} (N_e2ss_det gN (ev_exp a0.`2 u0)).
    wp.
    call{2} (N_exp_det gN a0.`2 u0).
    wp.
    call{2} (K_decaps_det gK q0 (a0.`1)).
    wp; skip => />.
  (* --- the case split ----------------------------------------------------- *)
  case (kdf_in_0{2} = kdf_in_1{2}).
  + rcondt{2} 1; first by move => &m; skip.
    inline *.
    (* side 1 still evaluates the KDF twice; side 2 runs the challenger's two
       decaps. Functionalize both, then the collision does the rest. *)
    exists* (glob H){1}, kdf_in_0{1}, kdf_in_1{1}.
    elim* => gH a0 a1.
    call{1} (H_evaluate_det gH a1).
    call{1} (H_evaluate_det gH a0).
    exists* (glob K){2}, Chal.dk0{2}, Chal.dk1{2}, ct0{2}, ct1{2}.
    elim* => gK d0 d1 c0 c1.
    (* both sides now end in an assignment (side 1's `ek_k <- ...`, side 2's
       `r10 <- ...` from the inlined challenger), so `wp` before `call{2}` *)
    wp.
    call{2} (K_decaps_det gK d1 (c1.`1)).
    call{2} (K_decaps_det gK d0 (c0.`1)).
    (* Do NOT `=> />` here: it destructs the collision hypothesis away, and that
       hypothesis is exactly what the branch needs. The collision gives
       ss_PQ_0 = ss_PQ_1 and ek_T_0 = ek_T_1, so side 1's packed disequality
       reduces to the challenger's own encaps-key one. *)
    wp; skip; smt(kdf_in_inj).
  + rcondf{2} 1; first by move => &m; skip.
    (* both bodies are now identical modulo the coupled fields *)
    do ! (wp; call (_: true)).
    wp; skip => /#.
qed.

end section Main.
