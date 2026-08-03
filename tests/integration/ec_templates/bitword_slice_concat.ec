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

op sliceL (s : WAB.word) : WA.word = WA.mkword (take na (WAB.ofword s)).
op sliceR (s : WAB.word) : WB.word = WB.mkword (drop na (WAB.ofword s)).

(* the concatenation really does have the summed width -- the side condition
   every `mkword` below discharges *)
lemma size_cat_ab (a : WA.word) (b : WB.word) :
  size (WA.ofword a ++ WB.ofword b) = na + nb.
proof. by rewrite size_cat WA.size_word WB.size_word. qed.

(* --- the three round-trip laws, as LEMMAS ------------------------------- *)

lemma slice_concat_left (a : WA.word) (b : WB.word) :
  sliceL (concat a b) = a.
proof.
rewrite /sliceL /concat (WAB.ofwordK _ (size_cat_ab a b)).
have <- := WA.size_word a.
by rewrite take_size_cat // WA.mkwordK.
qed.

lemma slice_concat_right (a : WA.word) (b : WB.word) :
  sliceR (concat a b) = b.
proof.
rewrite /sliceR /concat (WAB.ofwordK _ (size_cat_ab a b)).
have <- := WA.size_word a.
by rewrite drop_size_cat // WB.mkwordK.
qed.

lemma concat_slices_id (s : WAB.word) :
  concat (sliceL s) (sliceR s) = s.
proof.
have hs : size (WAB.ofword s) = na + nb by exact WAB.size_word.
have h1 : size (take na (WAB.ofword s)) = na by rewrite size_take; smt(gt0_na gt0_nb).
have h2 : size (drop na (WAB.ofword s)) = nb by rewrite size_drop; smt(gt0_na gt0_nb).
rewrite /concat /sliceL /sliceR (WA.ofwordK _ h1) (WB.ofwordK _ h2).
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
