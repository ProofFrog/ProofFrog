(* ============================================================ *)
(* CONCAT REGROUPING (associativity) -- VALIDATED EC TEMPLATE     *)
(*   (regression tripwire), admit-free.                           *)
(*                                                               *)
(* The third component of IND-CCA `initialize` hop_5, and the one *)
(* `indcca_kdf_key_substitution.ec` sidesteps by using a single   *)
(* `concat` op. The real hop builds the same five pieces under    *)
(* two different nestings:                                        *)
(*                                                               *)
(*   L: kdf_in = C4(C3(C2(C1(enc_k, ss_T), e_ct), e_ek), label)   *)
(*   R: input  = CX(challenger_k, D3(D2(D1(ss_T, e_ct), e_ek), l))*)
(*                                                               *)
(* equal by ASSOCIATIVITY -- for which the exporter emits nothing *)
(* (only the round-trip family: `concat_slices_id`,               *)
(* `slice_concat_left`, `slice_concat_right`). This derives the   *)
(* core two-step law, from which the five-piece regrouping        *)
(* follows by iteration:                                          *)
(*                                                               *)
(*   cat_pq_r (cat_p_q a b) c = cat_p_qr a (cat_q_r b c)          *)
(*                                                               *)
(* Note the four ops have FOUR DIFFERENT type indices, so this is *)
(* not one op's associativity -- it relates a whole family, which *)
(* is why it has to be emitted per triple of widths rather than   *)
(* once.                                                          *)
(*                                                               *)
(* LOAD-BEARING: the ops carry `[smt_opaque]` exactly as the      *)
(* exporter's do, so `smt` will not unfold them and the proof     *)
(* must go through `rewrite /op` and the `ofword`/`mkword` bridge. *)
(* The two `ofwordK` side conditions are discharged from          *)
(* `size_cat` + `size_word`; then it is just `catA`. Widths are   *)
(* SYMBOLIC, as the exporter's are.                              *)
(* ============================================================ *)

require import AllCore List.
require BitWord.

op p, q, r : int.
axiom gt0_p : 0 < p.
axiom gt0_q : 0 < q.
axiom gt0_r : 0 < r.

clone BitWord as Wp   with op n <- p       proof gt0_n by smt(gt0_p).
clone BitWord as Wq   with op n <- q       proof gt0_n by smt(gt0_q).
clone BitWord as Wr   with op n <- r       proof gt0_n by smt(gt0_r).
clone BitWord as Wpq  with op n <- p + q   proof gt0_n by smt(gt0_p gt0_q).
clone BitWord as Wqr  with op n <- q + r   proof gt0_n by smt(gt0_q gt0_r).
clone BitWord as Wpqr with op n <- p + q + r
  proof gt0_n by smt(gt0_p gt0_q gt0_r).

type bs_p = Wp.word.
type bs_q = Wq.word.
type bs_r = Wr.word.
type bs_pq = Wpq.word.
type bs_qr = Wqr.word.
type bs_pqr = Wpqr.word.

(* The exporter's shape, verbatim. *)
op [smt_opaque] cat_p_q : bs_p -> bs_q -> bs_pq =
  fun (a : bs_p) (b : bs_q) => Wpq.mkword (Wp.ofword a ++ Wq.ofword b).
op [smt_opaque] cat_q_r : bs_q -> bs_r -> bs_qr =
  fun (a : bs_q) (b : bs_r) => Wqr.mkword (Wq.ofword a ++ Wr.ofword b).
op [smt_opaque] cat_pq_r : bs_pq -> bs_r -> bs_pqr =
  fun (a : bs_pq) (b : bs_r) => Wpqr.mkword (Wpq.ofword a ++ Wr.ofword b).
op [smt_opaque] cat_p_qr : bs_p -> bs_qr -> bs_pqr =
  fun (a : bs_p) (b : bs_qr) => Wpqr.mkword (Wp.ofword a ++ Wqr.ofword b).

lemma cat_assoc (a : bs_p) (b : bs_q) (c : bs_r) :
  cat_pq_r (cat_p_q a b) c = cat_p_qr a (cat_q_r b c).
proof.
rewrite /cat_pq_r /cat_p_q /cat_p_qr /cat_q_r /=.
rewrite Wpq.ofwordK 1:size_cat 1:!Wp.size_word 1:Wq.size_word //.
rewrite Wqr.ofwordK 1:size_cat 1:Wq.size_word 1:Wr.size_word //.
by rewrite catA.
qed.
