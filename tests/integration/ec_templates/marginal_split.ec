(* ============================================================ *)
(* Marginal partial-split `Split Uniform Samples` (PRG-stretch)  *)
(* — VALIDATED EC TEMPLATE (regression tripwire).                 *)
(*                                                               *)
(* The hand-derived, EasyCrypt-compiling target shape the         *)
(* `_marginal_split_helpers` synthesizer must emit for a partial  *)
(* `Split Uniform Samples` whose single big sample feeds a        *)
(* COMPLEX downstream tail (module calls, not a return-concat),    *)
(* with |L| + |R| < |RES| (a dead tail-gap window):               *)
(*                                                               *)
(*   S5: orig <$ d_RES; .. KPQ(slice_L orig); KT(slice_R orig); ..*)
(*   S6: a <$ d_L; b <$ d_R; .. KPQ(a); KT(b); ..                 *)
(*                                                               *)
(* Strategy: build Mid (S5 with orig <$ d_RES expanded to         *)
(* a<$d_L; b<$d_R; gap<$d_GAP; orig <- concat3 a b gap) and Aug    *)
(* (S6 with a dead gap), then chain S5 ~ Mid ~ Aug ~ S6:           *)
(*  - left_to_mid  : rndsem*{2} + rnd-identity bijection + split3  *)
(*                   couple the one big sample to the 3-sample     *)
(*                   form; sim the identical tail.                 *)
(*  - mid_to_aug   : seq establishing slice_concat3 round-trips    *)
(*                   slice_L orig{1}=a{2} / slice_R orig{1}=b{2},  *)
(*                   then peel the whole tail call-by-call with    *)
(*                   wp; (call || rnd) repeated -- sim alone cannot *)
(*                   use a relational fact to equate the two        *)
(*                   slice-consuming head calls' arguments.        *)
(*  - aug_to_right : drop the dead gap (rnd{1} + d_GAP_ll); sim.   *)
(* A common deterministic prefix (here L.get()) is peeled with     *)
(* `seq c c; first sim`. The reversed (_rev) micro prepends        *)
(* `symmetry.` then runs the forward chain.                        *)
(*                                                               *)
(* If this stops compiling, the `_marginal_split_helpers`          *)
(* synthesizer's target tactic must be re-derived before any       *)
(* automation relying on it can be trusted.                        *)
(* ============================================================ *)

require import AllCore Distr DProd DMap.

(* ---- bitstring carriers (RES = L ++ R ++ GAP) ---- *)
type bs_res.
type bs_l.
type bs_r.
type bs_gap.

op dbs_res : bs_res distr.
op dbs_l   : bs_l   distr.
op dbs_r   : bs_r   distr.
op dbs_gap : bs_gap distr.

axiom dbs_l_ll   : is_lossless dbs_l.
axiom dbs_r_ll   : is_lossless dbs_r.
axiom dbs_gap_ll : is_lossless dbs_gap.

(* abstract lengths *)
op len_l : int.
op len_r : int.
op len_res : int.

(* slice ops *)
op slice_res_to_l : bs_res -> int -> int -> bs_l.
op slice_res_to_r : bs_res -> int -> int -> bs_r.

(* concat3 + round-trip / distribution-split axioms (tail-gap layout) *)
op concat3_l_r_gap_to_res : bs_l -> bs_r -> bs_gap -> bs_res.

axiom slice_concat3_p1 :
  forall (a : bs_l) (b : bs_r) (c : bs_gap),
    slice_res_to_l (concat3_l_r_gap_to_res a b c) 0 len_l = a.
axiom slice_concat3_p2 :
  forall (a : bs_l) (b : bs_r) (c : bs_gap),
    slice_res_to_r (concat3_l_r_gap_to_res a b c) len_l (len_l + len_r) = b.
axiom dbs_res_split3 :
  dbs_res =
    dlet dbs_l (fun (v1 : bs_l) =>
       dlet dbs_r (fun (v2 : bs_r) =>
          dmap dbs_gap (concat3_l_r_gap_to_res v1 v2))).

(* ---- abstract modules modelling the proof's tail ---- *)
type tlabel.
type tpq.
type tt.
type tout.

module type LGET = { proc get() : tlabel }.
module type KPQ  = { proc derivekeypair(s : bs_l) : tpq }.
module type KT   = {
  proc derivekeypair(s : bs_r) : tt
  proc finalize(lab : tlabel, x : tpq, y : tt) : tout
}.

(* before: one big sample, used only via two non-overlapping slices.
   The tail is long: two slice-consuming calls plus a downstream call
   that consumes the prefix var `lab` and both call results. *)
module S5 (L : LGET, KPQ : KPQ, KT : KT) = {
  proc compute() : tout = {
    var lab : tlabel;
    var orig : bs_res;
    var tup : tpq;
    var tup0 : tt;
    var fin : tout;
    lab <@ L.get();
    orig <$ dbs_res;
    tup  <@ KPQ.derivekeypair(slice_res_to_l orig 0 len_l);
    tup0 <@ KT.derivekeypair(slice_res_to_r orig len_l (len_l + len_r));
    fin  <@ KT.finalize(lab, tup, tup0);
    return fin;
  }
}.

module S6 (L : LGET, KPQ : KPQ, KT : KT) = {
  proc compute() : tout = {
    var lab : tlabel;
    var a : bs_l;
    var b : bs_r;
    var tup : tpq;
    var tup0 : tt;
    var fin : tout;
    lab <@ L.get();
    a <$ dbs_l;
    b <$ dbs_r;
    tup  <@ KPQ.derivekeypair(a);
    tup0 <@ KT.derivekeypair(b);
    fin  <@ KT.finalize(lab, tup, tup0);
    return fin;
  }
}.

module Mid (L : LGET, KPQ : KPQ, KT : KT) = {
  proc compute() : tout = {
    var lab : tlabel;
    var orig : bs_res;
    var a : bs_l;
    var b : bs_r;
    var gap : bs_gap;
    var tup : tpq;
    var tup0 : tt;
    var fin : tout;
    lab <@ L.get();
    a <$ dbs_l;
    b <$ dbs_r;
    gap <$ dbs_gap;
    orig <- concat3_l_r_gap_to_res a b gap;
    tup  <@ KPQ.derivekeypair(slice_res_to_l orig 0 len_l);
    tup0 <@ KT.derivekeypair(slice_res_to_r orig len_l (len_l + len_r));
    fin  <@ KT.finalize(lab, tup, tup0);
    return fin;
  }
}.

module Aug (L : LGET, KPQ : KPQ, KT : KT) = {
  proc compute() : tout = {
    var lab : tlabel;
    var a : bs_l;
    var b : bs_r;
    var gap : bs_gap;
    var tup : tpq;
    var tup0 : tt;
    var fin : tout;
    lab <@ L.get();
    a <$ dbs_l;
    b <$ dbs_r;
    gap <$ dbs_gap;
    tup  <@ KPQ.derivekeypair(a);
    tup0 <@ KT.derivekeypair(b);
    fin  <@ KT.finalize(lab, tup, tup0);
    return fin;
  }
}.

section.
declare module L   <: LGET.
declare module KPQ <: KPQ {-L}.
declare module KT  <: KT  {-L, -KPQ}.

lemma left_to_mid :
  equiv [ S5(L, KPQ, KT).compute ~ Mid(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  proc.
  seq 1 1 : (={glob L, glob KPQ, glob KT, lab}); first sim.
  seq 1 4 : (={glob L, glob KPQ, glob KT, lab} /\ orig{1} = orig{2}); last by sim.
  rndsem*{2} 0.
  conseq (: ={glob L, glob KPQ, glob KT, lab} ==>
            ={glob L, glob KPQ, glob KT, lab} /\ orig{1} = orig{2}) => //.
  rnd (fun (z : bs_res) => z) (fun (z : bs_res) => z); skip => />.
  rewrite -dbs_res_split3 /=; smt(dbs_res_split3).
qed.

lemma mid_to_aug :
  equiv [ Mid(L, KPQ, KT).compute ~ Aug(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  proc.
  seq 1 1 : (={glob L, glob KPQ, glob KT, lab}); first sim.
  seq 4 3 : (={glob L, glob KPQ, glob KT, lab, a, b, gap} /\
             slice_res_to_l orig{1} 0 len_l = a{2} /\
             slice_res_to_r orig{1} len_l (len_l + len_r) = b{2}).
  - by auto; smt(slice_concat3_p1 slice_concat3_p2).
  wp; call (_: true); wp; call (_: true); wp; call (_: true); auto => /> *.
qed.

lemma aug_to_right :
  equiv [ Aug(L, KPQ, KT).compute ~ S6(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  proc.
  seq 1 1 : (={glob L, glob KPQ, glob KT, lab}); first sim.
  seq 3 2 : (={glob L, glob KPQ, glob KT, lab, a, b}).
  - by rnd{1}; auto; smt(dbs_gap_ll).
  sim.
qed.

lemma left_to_aug :
  equiv [ S5(L, KPQ, KT).compute ~ Aug(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  transitivity Mid(L, KPQ, KT).compute
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT})
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT});
    [ smt() | smt() | apply left_to_mid | apply mid_to_aug ].
qed.

lemma micro :
  equiv [ S5(L, KPQ, KT).compute ~ S6(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  transitivity Aug(L, KPQ, KT).compute
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT})
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT});
    [ smt() | smt() | apply left_to_aug | apply aug_to_right ].
qed.

(* reversed direction (the _rev micros): symmetry then the forward proof *)
lemma micro_rev :
  equiv [ S6(L, KPQ, KT).compute ~ S5(L, KPQ, KT).compute :
          ={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT} ].
proof.
  symmetry.
  transitivity Aug(L, KPQ, KT).compute
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT})
    (={glob L, glob KPQ, glob KT} ==> ={res, glob L, glob KPQ, glob KT});
    [ smt() | smt() | apply left_to_aug | apply aug_to_right ].
qed.

end section.
