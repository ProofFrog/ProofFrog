(* Tripwire: the exporter's slice/concat axiom family DERIVED from EC's List
   theory, over SYMBOLIC lengths -- feasibility evidence for replacing the
   axioms with lemmas once bs_* types are represented as sized bool lists. *)
require import AllCore List.

op n1 : int.
axiom ge0_n1 : 0 <= n1.
op n2 : int.
axiom ge0_n2 : 0 <= n2.

op concat (a b : bool list) : bool list = a ++ b.
op slice (s : bool list) (i j : int) : bool list = take (j - i) (drop i s).

lemma slice_concat_left (a b : bool list) :
  size a = n1 => slice (concat a b) 0 n1 = a.
proof.
move => h; rewrite /slice /concat drop0 /=.
by rewrite -h take_size_cat.
qed.

lemma slice_concat_right (a b : bool list) :
  size a = n1 => size b = n2 => slice (concat a b) n1 (n1 + n2) = b.
proof.
move => ha hb; rewrite /slice /concat -ha drop_size_cat //.
have -> : size a + n2 - size a = n2 by smt().
by rewrite -hb take_size.
qed.

lemma concat_slices_id (s : bool list) :
  size s = n1 + n2 =>
  concat (slice s 0 n1) (slice s n1 (n1 + n2)) = s.
proof.
move => h; rewrite /slice /concat drop0 /=.
have -> : n1 + n2 - n1 = n2 by smt().
have -> : take n2 (drop n1 s) = drop n1 s
  by rewrite take_oversize // size_drop; smt(size_ge0).
by rewrite cat_take_drop.
qed.
