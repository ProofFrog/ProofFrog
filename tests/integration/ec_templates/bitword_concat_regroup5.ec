(* ============================================================ *)
(* FIVE-PIECE CONCAT REGROUPING -- VALIDATED EC TEMPLATE          *)
(*   (regression tripwire), admit-free, no new axiom.             *)
(*                                                               *)
(* The identity IND-CCA `initialize` hop_5 actually needs. The     *)
(* two-step law in `bitword_concat_assoc.ec` CANNOT be iterated    *)
(* to reach it: the stepwise intermediates that would require --   *)
(* an op `bs_a x bs_bc -> bs_abc`, say -- are not among the eight  *)
(* the exporter emits. Measured on `CG_expanded_INDCCA_PQ`, the    *)
(* emitted set is exactly the four of the left nesting, the three  *)
(* of the right side's `rest`, and the one that prepends the key. *)
(* So the identity is stated and proved DIRECTLY at five pieces:   *)
(*                                                               *)
(*   cL4(cL3(cL2(cL1 k s) e1) e2) l = cPre k (cR3(cR2(cR1 s e1) e2) l) *)
(*                                                               *)
(* Widths SYMBOLIC, and `e1`/`e2` deliberately SHARE a width --    *)
(* both are NG element encodings in the real hop, and a tripwire   *)
(* that gave them distinct widths would not exercise the           *)
(* `!Wc.size_word` steps.                                          *)
(*                                                               *)
(* LOAD-BEARING: the ops carry `[smt_opaque]` exactly as the       *)
(* exporter's do, so `smt` will not unfold them -- the proof goes *)
(* through `rewrite /op` and the ofword/mkword bridge, with each   *)
(* `ofwordK` side condition discharged from `size_cat` +           *)
(* `size_word`, and only then `catA`.                              *)
(*                                                               *)
(* WIDTH ORDER IS LOAD-BEARING, and an earlier version of this   *)
(* tripwire got it wrong. The exporter SORTS the atoms in a       *)
(* bitstring type name, so `bs_ng_nelem_ng_nss` has width         *)
(* `ng_nelem + ng_nss` while its CONTENT is `ng_nss ++ ng_nelem`. *)
(* Each `ofwordK` side condition therefore reduces to a sum in a  *)
(* PERMUTED order, which `//` does not close -- it needs `/#`.    *)
(* The first version of this file put every clone's width in      *)
(* content order, so `//` sufficed and the file passed while the  *)
(* real hop failed at exactly that step. The clones below now use *)
(* the permuted order (`Wbc` is `c + b`, not `b + c`) so the      *)
(* tripwire exercises the real obligation.                        *)
(*                                                               *)
(* NAMING TRAP avoided deliberately: the ops are `cL*`/`cR*`/      *)
(* `cPre` rather than `cat*`, because an op named `catA` SHADOWS   *)
(* EC's list-associativity lemma of the same name, which is the   *)
(* very lemma the last line applies.                               *)
(* ============================================================ *)

require import AllCore List.
require BitWord.

op a, b, c, d : int.
axiom gt0_a : 0 < a.
axiom gt0_b : 0 < b.
axiom gt0_c : 0 < c.
axiom gt0_d : 0 < d.

clone BitWord as Wa     with op n <- a             proof gt0_n by smt(gt0_a).
clone BitWord as Wb     with op n <- b             proof gt0_n by smt(gt0_b).
clone BitWord as Wc     with op n <- c             proof gt0_n by smt(gt0_c).
clone BitWord as Wd     with op n <- d             proof gt0_n by smt(gt0_d).
clone BitWord as Wab    with op n <- a + b         proof gt0_n by smt(gt0_a gt0_b).
clone BitWord as Wabc   with op n <- a + b + c     proof gt0_n by smt(gt0_a gt0_b gt0_c).
clone BitWord as Wabcc  with op n <- a + b + c + c
  proof gt0_n by smt(gt0_a gt0_b gt0_c).
clone BitWord as Wabccd with op n <- a + b + c + c + d
  proof gt0_n by smt(gt0_a gt0_b gt0_c gt0_d).
clone BitWord as Wbc    with op n <- c + b         proof gt0_n by smt(gt0_b gt0_c).
clone BitWord as Wbcc   with op n <- c + c + b     proof gt0_n by smt(gt0_b gt0_c).
clone BitWord as Wbccd  with op n <- c + c + b + d
  proof gt0_n by smt(gt0_b gt0_c gt0_d).

type bs_a = Wa.word.       type bs_b = Wb.word.
type bs_c = Wc.word.       type bs_d = Wd.word.
type bs_ab = Wab.word.     type bs_abc = Wabc.word.
type bs_abcc = Wabcc.word. type bs_abccd = Wabccd.word.
type bs_bc = Wbc.word.     type bs_bcc = Wbcc.word.
type bs_bccd = Wbccd.word.

(* left nesting *)
op [smt_opaque] cL1 : bs_a -> bs_b -> bs_ab =
  fun x y => Wab.mkword (Wa.ofword x ++ Wb.ofword y).
op [smt_opaque] cL2 : bs_ab -> bs_c -> bs_abc =
  fun x y => Wabc.mkword (Wab.ofword x ++ Wc.ofword y).
op [smt_opaque] cL3 : bs_abc -> bs_c -> bs_abcc =
  fun x y => Wabcc.mkword (Wabc.ofword x ++ Wc.ofword y).
op [smt_opaque] cL4 : bs_abcc -> bs_d -> bs_abccd =
  fun x y => Wabccd.mkword (Wabcc.ofword x ++ Wd.ofword y).

(* right nesting *)
op [smt_opaque] cR1 : bs_b -> bs_c -> bs_bc =
  fun x y => Wbc.mkword (Wb.ofword x ++ Wc.ofword y).
op [smt_opaque] cR2 : bs_bc -> bs_c -> bs_bcc =
  fun x y => Wbcc.mkword (Wbc.ofword x ++ Wc.ofword y).
op [smt_opaque] cR3 : bs_bcc -> bs_d -> bs_bccd =
  fun x y => Wbccd.mkword (Wbcc.ofword x ++ Wd.ofword y).
op [smt_opaque] cPre : bs_a -> bs_bccd -> bs_abccd =
  fun x y => Wabccd.mkword (Wa.ofword x ++ Wbccd.ofword y).

lemma regroup5 (k : bs_a) (s : bs_b) (e1 e2 : bs_c) (l : bs_d) :
  cL4 (cL3 (cL2 (cL1 k s) e1) e2) l = cPre k (cR3 (cR2 (cR1 s e1) e2) l).
proof.
rewrite /cL4 /cL3 /cL2 /cL1 /cPre /cR3 /cR2 /cR1 /=.
rewrite Wab.ofwordK 1:size_cat 1:!Wa.size_word 1:!Wb.size_word 1:/#.
rewrite Wabc.ofwordK 1:size_cat 1:size_cat 1:!Wa.size_word 1:!Wb.size_word 1:!Wc.size_word 1:/#.
rewrite Wabcc.ofwordK 1:size_cat 1:size_cat 1:size_cat 1:!Wa.size_word 1:!Wb.size_word 1:!Wc.size_word 1:/#.
rewrite Wbc.ofwordK 1:size_cat 1:!Wb.size_word 1:!Wc.size_word 1:/#.
rewrite Wbcc.ofwordK 1:size_cat 1:size_cat 1:!Wb.size_word 1:!Wc.size_word 1:/#.
rewrite Wbccd.ofwordK 1:size_cat 1:size_cat 1:size_cat 1:!Wb.size_word 1:!Wc.size_word 1:!Wd.size_word 1:/#.
by rewrite !catA.
qed.
