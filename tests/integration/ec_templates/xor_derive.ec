(* Tripwire: the exporter's per-type XOR axiom family (invol / commut / assoc)
   DERIVED from EC's List + Bool theories over the bool-list representation --
   companion to slice_concat_derive.ec. *)
require import AllCore List Bool.

op bxor (a b : bool list) : bool list =
  map (fun (p : bool * bool) => p.`1 ^^ p.`2) (zip a b).

lemma bxor_size (a b : bool list) :
  size a = size b => size (bxor a b) = size a.
proof. by move => h; rewrite /bxor size_map size_zip h. qed.

lemma bxor_nth (a b : bool list) (i : int) :
  size a = size b => 0 <= i < size a =>
  nth false (bxor a b) i = nth false a i ^^ nth false b i.
proof.
move => h hi; rewrite /bxor (nth_map (false, false)) ?size_zip 1:/#.
by rewrite nth_zip.
qed.

lemma bxor_commut (a b : bool list) :
  size a = size b => bxor a b = bxor b a.
proof.
move => h; apply (eq_from_nth false); 1: by rewrite !bxor_size /#.
move => i; rewrite bxor_size // => hi.
by rewrite !bxor_nth 1..4:/#; smt(xorC).
qed.

lemma bxor_invol (a b : bool list) :
  size a = size b => bxor (bxor a b) b = a.
proof.
move => h; apply (eq_from_nth false); 1: by rewrite !bxor_size /#.
move => i; rewrite bxor_size 1:bxor_size // => hi.
rewrite bxor_nth 1:bxor_size /#.
qed.

lemma bxor_assoc (a b c : bool list) :
  size a = size b => size b = size c =>
  bxor a (bxor b c) = bxor (bxor a b) c.
proof.
move => hab hbc; apply (eq_from_nth false).
+ by rewrite !bxor_size /#.
move => i; rewrite bxor_size 1:/# => hi.
by rewrite !bxor_nth ?bxor_size 1..8:/#; smt(xorA).
qed.
