(* TRIPWIRE -- concat injectivity, DERIVED from the round-trip slice laws the
   exporter already emits.

   The IND-CCA `hop_7` separation needs "two KDF inputs that differ in one
   component are different". The exporter emits, for every concat triple, the
   pair

     slice_concat_left  : slice_L (concat a b) 0 n     = a
     slice_concat_right : slice_R (concat a b) n (n+m) = b

   and those give injectivity outright -- apply a slice to both sides of the
   hypothesis. So the separation costs NO NEW AXIOM: it is a proved lemma over
   facts already in scope, and `concat_slices_id` is not even needed.

   Shapes and index arithmetic mirror the emitted ones exactly (explicit
   `(s, i, j)` slices with symbolic widths), so a route derived here transfers. *)

require import AllCore.

type bsL, bsR, bsRES.

op nL, nR : int.

op concat : bsL -> bsR -> bsRES.
op slice_l : bsRES -> int -> int -> bsL.
op slice_r : bsRES -> int -> int -> bsR.

axiom slice_concat_left (a : bsL) (b : bsR) :
  slice_l (concat a b) 0 nL = a.
axiom slice_concat_right (a : bsL) (b : bsR) :
  slice_r (concat a b) nL (nL + nR) = b.

(* Both components at once. *)
lemma concat_inj (a c : bsL) (b d : bsR) :
  concat a b = concat c d => a = c /\ b = d.
proof.
move=> h; split.
+ by rewrite -(slice_concat_left a b) -(slice_concat_left c d) h.
by rewrite -(slice_concat_right a b) -(slice_concat_right c d) h.
qed.

(* The form the separation actually uses: differing in the RIGHT component is
   enough, and the left components are never related. That asymmetry is the
   whole point -- in the real hop the left component is a Diffie-Hellman value
   that nothing relates across the two sides. *)
lemma concat_neq_right (a c : bsL) (b d : bsR) :
  b <> d => concat a b <> concat c d.
proof.
move=> hbd; apply/negP => h.
by have [_ hb] := concat_inj a c b d h; move: hbd; rewrite hb.
qed.
