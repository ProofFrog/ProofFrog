(* Tripwire: the slice/concat AND XOR axiom families both DERIVED, by
 * representing a sized bitstring as an EC `BitWord` clone instead of an
 * abstract type.
 *
 * Today the exporter emits `type bs_N.` (abstract) plus ~11 slice/concat
 * round-trip AXIOMS and the XOR laws as AXIOMS. Deletion probes (cycles 115,
 * 116) show those are load-bearing on every HON_BIND cell -- 12 of the 33-35
 * real TCB entries per cell -- so they are the largest reducible chunk of the
 * trusted base.
 *
 * The stdlib already has the right structure, which is the point of this file:
 *
 *     Word.eca:     subtype word = { w : t list | size w = n }
 *                   op ofword = val        (word -> t list)
 *                   op mkword               (t list -> word)
 *                   lemma size_word : size (ofword w) = n
 *                   lemma mkwordK  : cancel ofword mkword
 *                   lemma ofwordK  : size s = n => ofword (mkword s) = s
 *     BitWord.eca:  the XOR laws as LEMMAS (xorwA, xorwC, xorwK, xorw0)
 *
 * So a bitstring is ALREADY a size-indexed list subtype. Concat/slice are
 * definable through `ofword`/`mkword`, and the round-trip laws follow from the
 * plain list lemmas -- no axiom. Widths stay SYMBOLIC here (`na`, `nb`),
 * matching the exporter, which never knows concrete lengths.
 *
 * If this compiles, the type-foundation change is: emit
 * `clone BitWord as BS_N with op n <- N` instead of `type bs_N.`, and emit
 * these three as lemmas instead of axioms.
 *)

require import AllCore List.
require (*--*) BitWord.

op na : int.
axiom gt0_na : 0 < na.
op nb : int.
axiom gt0_nb : 0 < nb.

clone BitWord as WA  with op n <- na      proof gt0_n by exact gt0_na.
clone BitWord as WB  with op n <- nb      proof gt0_n by exact gt0_nb.
clone BitWord as WAB with op n <- na + nb proof gt0_n by smt(gt0_na gt0_nb).

(* the exporter's `concat` / `slice`, defined through the list bridge *)
op concat (a : WA.word) (b : WB.word) : WAB.word =
  WAB.mkword (WA.ofword a ++ WB.ofword b).

(* The exporter's slice takes EXPLICIT (i, j) indices, not a fixed split, so
   the proofs must also normalise `j - i`. Matching that signature here is the
   point: a fixed-split tripwire would not have exercised it. *)
op slice_ab_a (s : WAB.word) (i j : int) : WA.word =
  WA.mkword (take (j - i) (drop i (WAB.ofword s))).
op slice_ab_b (s : WAB.word) (i j : int) : WB.word =
  WB.mkword (take (j - i) (drop i (WAB.ofword s))).

(* the concatenation really does have the summed width -- the side condition
   every `mkword` below discharges *)
lemma size_cat_ab (a : WA.word) (b : WB.word) :
  size (WA.ofword a ++ WB.ofword b) = na + nb.
proof. by rewrite size_cat WA.size_word WB.size_word. qed.

(* --- the three round-trip laws, at the EXPORTER'S signature ------------- *)

lemma slice_concat_left (a : WA.word) (b : WB.word) :
  slice_ab_a (concat a b) 0 na = a.
proof.
rewrite /slice_ab_a /concat (WAB.ofwordK _ (size_cat_ab a b)) drop0.
have ->: na - 0 = na by smt().
have <- := WA.size_word a.
by rewrite take_size_cat // WA.mkwordK.
qed.

lemma slice_concat_right (a : WA.word) (b : WB.word) :
  slice_ab_b (concat a b) na (na + nb) = b.
proof.
rewrite /slice_ab_b /concat (WAB.ofwordK _ (size_cat_ab a b)).
have ->: na + nb - na = nb by smt().
have <- := WA.size_word a.
rewrite drop_size_cat //.
have <- := WB.size_word b.
by rewrite take_size WB.mkwordK.
qed.

lemma concat_slices_id (s : WAB.word) :
  concat (slice_ab_a s 0 na) (slice_ab_b s na (na + nb)) = s.
proof.
have hs : size (WAB.ofword s) = na + nb by exact WAB.size_word.
rewrite /concat /slice_ab_a /slice_ab_b drop0.
have ->: na - 0 = na by smt().
have ->: na + nb - na = nb by smt().
have h1 : size (take na (WAB.ofword s)) = na by rewrite size_take; smt(gt0_na gt0_nb).
have hd : size (drop na (WAB.ofword s)) = nb by rewrite size_drop; smt(gt0_na gt0_nb).
(* the trailing `take` must go BEFORE `ofwordK`, or its size side-condition is
   about the wrong term and the rewrite finds nothing *)
have ht : take nb (drop na (WAB.ofword s)) = drop na (WAB.ofword s)
  by rewrite take_oversize // hd.
have h2 : size (take nb (drop na (WAB.ofword s))) = nb by rewrite ht hd.
rewrite (WA.ofwordK _ h1) (WB.ofwordK _ h2) ht.
by rewrite cat_take_drop WAB.mkwordK.
qed.

(* --- and the XOR family comes free, as BitWord LEMMAS -------------------- *)
lemma xor_involutive (w : WA.word) : WA.(+^) w w = WA.zerow.
proof. exact WA.xorwK. qed.

lemma xor_commutative (w1 w2 : WA.word) : WA.(+^) w1 w2 = WA.(+^) w2 w1.
proof. exact WA.xorwC. qed.

lemma xor_associative (w1 w2 w3 : WA.word) :
  WA.(+^) (WA.(+^) w1 w2) w3 = WA.(+^) w1 (WA.(+^) w2 w3).
proof. by rewrite WA.xorwA. qed.
