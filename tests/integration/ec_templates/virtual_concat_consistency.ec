(* Tripwire: a CONSISTENCY MODEL for the VIRTUAL CONCAT TRIPLE -- the exact
 * five statements `TypeCollector.request_virtual_concat` emits, proved as
 * LEMMAS in a concrete bitstring model.
 *
 * WHY THIS FILE EXISTS. Six CFRG HON_BIND cells are admit-free and EC-accepted
 * only because of these five axioms (PROVISIONAL-AXIOMS.md, "VIRTUAL CONCAT
 * TRIPLE"). An axiom set that is inconsistent, or true only under a reading the
 * exporter does not actually guarantee, would make EasyCrypt certify a file
 * that proves nothing -- invisible to the dashboard, which checks EC-accepts
 * and not axiom-truth. So the ledger decision needs evidence of a different
 * kind from "it compiles": a MODEL in which all five hold simultaneously.
 *
 * WHAT IT SHOWS, precisely:
 *   1. The set is SATISFIABLE. Interpreting `bs_n` as `n`-bit bool lists,
 *      `concat` as `++`, `slice i j` as `take (j-i) o drop i`, and `d bs_n` as
 *      `dlist dbool n`, every emitted statement is a theorem. So the axioms
 *      cannot be used to derive `false`.
 *   2. The set is true in the INTENDED model -- the one the ledger's "intended
 *      model" paragraph claims -- not merely in some contrived one.
 *   3. It pins EXACTLY where the length hypothesis is load-bearing: each lemma
 *      below carries `size a = n1` / `size b = n2` / `size s = n1 + n2` as an
 *      explicit hypothesis, and those hypotheses are what the emitter's
 *      symbolic length-sum gate is standing in for. Drop them and the lemmas
 *      are false; that is the whole risk surface, made visible.
 *
 * WHAT IT DOES NOT SHOW. It does not verify that the exporter attaches the
 * right lengths to the right types for any particular proof -- that is the
 * length-sum + slice-OFFSET gates in `type_collector`, and it is code, not
 * mathematics. This file makes the mathematics unarguable so the review can
 * concentrate on the code.
 *
 * Companions: `slice_concat_derive.ec` (round-trip family, same model),
 * `dbs_split_derive.ec` (the `\`*\`` split law), `xor_derive.ec`. What is NEW
 * here is (a) the DLET-form split law, which the virtual triple emits and which
 * no earlier tripwire covered, and (b) all five in ONE model at once, which is
 * what consistency actually means.
 *)

require import AllCore List Distr DList DBool.

op n1 : int.
op n2 : int.
axiom ge0_n1 : 0 <= n1.
axiom ge0_n2 : 0 <= n2.

(* the model: bs_k = k-bit bool lists, uniform = dlist dbool k *)
op concat (a b : bool list) : bool list = a ++ b.
op slice (s : bool list) (i j : int) : bool list = take (j - i) (drop i s).
op dbs (n : int) : bool list distr = dlist dbool n.

(* --- 1/5  slice_concat_left_L_S_R ---------------------------------------- *)
lemma m_slice_concat_left (a b : bool list) :
  size a = n1 => slice (concat a b) 0 n1 = a.
proof.
move => h; rewrite /slice /concat drop0 /=.
by rewrite -h take_size_cat.
qed.

(* --- 2/5  slice_concat_right_L_S_R --------------------------------------- *)
lemma m_slice_concat_right (a b : bool list) :
  size a = n1 => size b = n2 => slice (concat a b) n1 (n1 + n2) = b.
proof.
move => ha hb; rewrite /slice /concat -ha drop_size_cat //.
have -> : size a + n2 - size a = n2 by smt().
by rewrite -hb take_size.
qed.

(* --- 3/5  concat_slices_id_L_S_R ----------------------------------------- *)
lemma m_concat_slices_id (s : bool list) :
  size s = n1 + n2 =>
  concat (slice s 0 n1) (slice s n1 (n1 + n2)) = s.
proof.
move => h; rewrite /slice /concat drop0 /=.
have -> : n1 + n2 - n1 = n2 by smt().
have -> : take n2 (drop n1 s) = drop n1 s
  by rewrite take_oversize // size_drop; smt(size_ge0).
by rewrite cat_take_drop.
qed.

(* --- 4/5  dR_split_L_S (the `*` form) ------------------------------------ *)
lemma m_dbs_split :
  dbs (n1 + n2) =
  dmap (dbs n1 `*` dbs n2) (fun (p : bool list * bool list) => concat p.`1 p.`2).
proof. by rewrite /dbs /concat dlist_add // ?ge0_n1 ?ge0_n2. qed.

(* --- 5/5  dR_split_dlet_L_S ---------------------------------------------
   The form `rndsem*{i} 0` actually produces, and the one no earlier tripwire
   covered. It follows from 4/5 by turning the product into a dlet and fusing
   the two dmaps -- exactly the bridge that cycle 69 measured `dprod_dlet`
   does NOT supply inside a support obligation, which is why the exporter emits
   this shape rather than deriving it on the spot. *)
lemma m_dbs_split_dlet :
  dbs (n1 + n2) =
  dlet (dbs n1) (fun (v1 : bool list) =>
    dmap (dbs n2) (fun (v2 : bool list) => concat v1 v2)).
proof.
rewrite m_dbs_split dprod_dlet dmap_dlet /=.
apply eq_dlet => // a.
by rewrite dmap_comp.
qed.
