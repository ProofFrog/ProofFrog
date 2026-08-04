(* Tripwire: the BITSTRING DISTRIBUTION family DERIVED, on top of the BitWord
 * representation validated by `bitword_slice_concat.ec`.
 *
 * That file removed the slice/concat round-trip AXIOMS. This one targets what
 * is left of the bitstring math in the emitted trusted base:
 *
 *     op    dbs_w : bs_w distr                   (* uninterpreted today *)
 *     axiom dbs_w_ll   : is_lossless dbs_w
 *     axiom dbs_w_fu   : is_funiform dbs_w
 *     axiom dbs_w_full : is_full dbs_w
 *     axiom dbs_R_split_L_S      : dR = dmap (dL `*` dS) (fun p => concat p.`1 p.`2)
 *     axiom dbs_R_split_dlet_L_S : dR = dlet dL (fun v1 => dmap dS (fun v2 => concat v1 v2))
 *
 * Once `bs_w` IS `BW_bs_w.word`, its uniform distribution is already in scope
 * as `BW_bs_w.DWord.dunifin` (Word.eca clones `MFinite`), so all six become
 * lemmas: the first three by `exact`, and the two split laws by `eq_funi_ll`
 * -- both sides lossless and funiform, with fullness/uniformity of the mapped
 * product coming from the round-trip laws (surjectivity of concat = the
 * identity law; injectivity = the two projection laws).
 *
 * Widths stay SYMBOLIC, matching the exporter, which never knows concrete
 * lengths. The slice signature is the exporter's explicit `(s, i, j)`.
 *)

require import AllCore List Distr DProd DMap.
require (*--*) BitWord.

op na : int.
axiom gt0_na : 0 < na.
op nb : int.
axiom gt0_nb : 0 < nb.

clone BitWord as WA  with op n <- na      proof gt0_n by smt(gt0_na).
clone BitWord as WB  with op n <- nb      proof gt0_n by smt(gt0_nb).
clone BitWord as WAB with op n <- na + nb proof gt0_n by smt(gt0_na gt0_nb).

type bs_a  = WA.word.
type bs_b  = WB.word.
type bs_ab = WAB.word.

(* --- the distributions, DEFINED rather than declared --------------------- *)
op [smt_opaque] dbs_a  : bs_a  distr = WA.DWord.dunifin.
op [smt_opaque] dbs_b  : bs_b  distr = WB.DWord.dunifin.
op [smt_opaque] dbs_ab : bs_ab distr = WAB.DWord.dunifin.

lemma dbs_a_ll : is_lossless dbs_a.
proof. exact WA.DWord.dunifin_ll. qed.
lemma dbs_a_fu : is_funiform dbs_a.
proof. exact WA.DWord.dunifin_funi. qed.
lemma dbs_a_full : is_full dbs_a.
proof. exact WA.DWord.dunifin_fu. qed.

lemma dbs_b_ll : is_lossless dbs_b.
proof. exact WB.DWord.dunifin_ll. qed.
lemma dbs_b_fu : is_funiform dbs_b.
proof. exact WB.DWord.dunifin_funi. qed.
lemma dbs_b_full : is_full dbs_b.
proof. exact WB.DWord.dunifin_fu. qed.

lemma dbs_ab_ll : is_lossless dbs_ab.
proof. exact WAB.DWord.dunifin_ll. qed.
lemma dbs_ab_fu : is_funiform dbs_ab.
proof. exact WAB.DWord.dunifin_funi. qed.
lemma dbs_ab_full : is_full dbs_ab.
proof. exact WAB.DWord.dunifin_fu. qed.

(* --- the exporter's ops, through the list bridge ------------------------- *)
op [smt_opaque] concat_ab : bs_a -> bs_b -> bs_ab =
  fun (a : bs_a) (b : bs_b) => WAB.mkword (WA.ofword a ++ WB.ofword b).

op [smt_opaque] slice_ab_a : bs_ab -> int -> int -> bs_a =
  fun (s : bs_ab) (i j : int) => WA.mkword (take (j - i) (drop i (WAB.ofword s))).
op [smt_opaque] slice_ab_b : bs_ab -> int -> int -> bs_b =
  fun (s : bs_ab) (i j : int) => WB.mkword (take (j - i) (drop i (WAB.ofword s))).

(* --- the round-trip laws (validated in bitword_slice_concat.ec) ---------- *)
lemma size_cat_ab :
  forall (a : bs_a) (b : bs_b), size (WA.ofword a ++ WB.ofword b) = na + nb.
proof.
  move => a b.
  rewrite size_cat WA.size_word WB.size_word.
  by smt().
qed.

lemma slice_concat_left_ab :
  forall (a : bs_a) (b : bs_b), slice_ab_a (concat_ab a b) 0 na = a.
proof.
  move => a b.
  rewrite /slice_ab_a /concat_ab (WAB.ofwordK _ (size_cat_ab a b)) drop0.
  have ->: na - 0 = na by smt().
  by rewrite (take_size_cat _ _ _ (WA.size_word a)) WA.mkwordK.
qed.

lemma slice_concat_right_ab :
  forall (a : bs_a) (b : bs_b), slice_ab_b (concat_ab a b) na (na + nb) = b.
proof.
  move => a b.
  rewrite /slice_ab_b /concat_ab (WAB.ofwordK _ (size_cat_ab a b)).
  have ->: na + nb - na = nb by smt().
  rewrite (drop_size_cat _ _ _ (WA.size_word a)).
  have hb : size (WB.ofword b) = nb by exact WB.size_word.
  by rewrite -hb take_size WB.mkwordK.
qed.

lemma concat_slices_id_ab :
  forall (s : bs_ab),
  concat_ab (slice_ab_a s 0 na) (slice_ab_b s na (na + nb)) = s.
proof.
  move => s.
  have hs : size (WAB.ofword s) = na + nb by exact WAB.size_word.
  rewrite /concat_ab /slice_ab_a /slice_ab_b drop0.
  have ->: na - 0 = na by smt().
  have ->: na + nb - na = nb by smt().
  have h1 : size (take na (WAB.ofword s)) = na
    by rewrite size_take; smt(gt0_na gt0_nb).
  have hd : size (drop na (WAB.ofword s)) = nb
    by rewrite size_drop; smt(gt0_na gt0_nb).
  have ht : take nb (drop na (WAB.ofword s)) = drop na (WAB.ofword s)
    by rewrite take_oversize // hd.
  have h2 : size (take nb (drop na (WAB.ofword s))) = nb
    by rewrite ht hd.
  rewrite (WA.ofwordK _ h1) (WB.ofwordK _ h2) ht.
  by rewrite cat_take_drop WAB.mkwordK.
qed.

(* --- the `*`-form distribution split, DERIVED ---------------------------- *)
lemma dbs_ab_split_a_b :
  dbs_ab =
  dmap (dbs_a `*` dbs_b) (fun (p : bs_a * bs_b) => concat_ab p.`1 p.`2).
proof.
apply: eq_funi_ll.
+ exact dbs_ab_fu.
+ exact dbs_ab_ll.
+ apply: is_full_funiform.
  + apply: dmap_fu_in => w.
    exists (slice_ab_a w 0 na, slice_ab_b w na (na + nb)).
    rewrite supp_dprod /=; split.
    + by split; [exact dbs_a_full | exact dbs_b_full].
    by rewrite concat_slices_id_ab.
  apply: dmap_uni_in_inj.
  + move => [x1 y1] [x2 y2] _ _ /= heq.
    have hx : x1 = x2
      by rewrite -(slice_concat_left_ab x1 y1) -(slice_concat_left_ab x2 y2) heq.
    have hy : y1 = y2
      by rewrite -(slice_concat_right_ab x1 y1)
                 -(slice_concat_right_ab x2 y2) heq.
    by rewrite hx hy.
  by apply: dprod_uni; apply: funi_uni; [exact dbs_a_fu | exact dbs_b_fu].
apply: dmap_ll; rewrite dprod_ll.
by split; [exact dbs_a_ll | exact dbs_b_ll].
qed.

(* --- the DLET-form split, the shape `rndsem*{i} 0` produces -------------- *)
lemma dbs_ab_split_dlet_a_b :
  dbs_ab =
  dlet dbs_a (fun (v1 : bs_a) =>
    dmap dbs_b (fun (v2 : bs_b) => concat_ab v1 v2)).
proof.
rewrite dbs_ab_split_a_b dprod_dlet dmap_dlet /=.
apply eq_dlet => // a.
by rewrite dmap_comp.
qed.
