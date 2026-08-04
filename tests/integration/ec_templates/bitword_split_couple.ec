(* Tripwire: the SPLIT-UNIFORM coupling over the BitWord representation --
 * i.e. the CONSUMER of the derived bitstring foundation, not just the
 * foundation itself.
 *
 * `split_uniform_couple.ec` pins the same coupling over ABSTRACT bitstrings
 * with the round-trip facts as axioms. Once `bs_<w>` is a BitWord clone and
 * `dbs_<w>` is `DWord.dunifin`, the emitted tactic's LAST obligation changes
 * shape: EC discharges the support side condition on its own, so the witness
 * `rewrite supp_dlet` has nothing to rewrite and the goal that remains is the
 * round-trip equality. That is why the emitter closes it with
 * `(<witness proof>) || smt(<round-trip laws>)` -- this file pins the second
 * branch, `split_uniform_couple.ec` the first, and the emitter must keep
 * satisfying both.
 *
 * Everything above the modules is the derived foundation itself (clones,
 * defined slice/concat, defined distributions, the round-trip and split laws),
 * at symbolic widths and at the exporter's explicit `(s, i, j)` slice
 * signature.
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

(* --- THE CONSUMER: the split-uniform coupling the exporter emits ---------
   Same tactic as `split_uniform_couple.ec`, but over the BitWord
   representation (defined ops + defined distributions), which is what the
   exporter now emits. *)

module A = {
  proc f () : bs_a * bs_b = {
    var a : bs_a;
    var b : bs_b;
    a <$ dbs_a;
    b <$ dbs_b;
    return (a, b);
  }
}.

module B = {
  proc f () : bs_a * bs_b = {
    var s : bs_ab;
    s <$ dbs_ab;
    return (slice_ab_a s 0 na, slice_ab_b s na (na + nb));
  }
}.

lemma split_couple : equiv [ A.f ~ B.f : true ==> ={res} ].
proof.
  proc.
  rndsem*{1} 0.
  rnd (fun (p : bs_a * bs_b) => concat_ab p.`1 p.`2)
      (fun (sf : bs_ab) => (slice_ab_a sf 0 na, slice_ab_b sf na (na + nb))).
  skip => />.
  rewrite dbs_ab_split_dlet_a_b.
  split.
  * move => sf hsf; rewrite concat_slices_id_ab //.
  move => _; split.
  * move => sf hsf.
    rewrite !dlet1E; congr; apply fun_ext => a /=.
    rewrite !dmap1E /(\o) /pred1 /=.
    congr; apply mu_eq => b /=.
    by rewrite eqboolP; smt(slice_concat_left_ab slice_concat_right_ab concat_slices_id_ab).
  move => _ p hp.
  have h1 : p.`1 \in dbs_a by smt(supp_dlet supp_dmap).
  have h2 : p.`2 \in dbs_b by smt(supp_dlet supp_dmap).
  split.
  * by (rewrite supp_dlet; exists p.`1; rewrite h1 /=;
        rewrite supp_dmap; exists p.`2; rewrite h2)
       || smt(slice_concat_left_ab slice_concat_right_ab).
  move => _; smt(slice_concat_left_ab slice_concat_right_ab).
qed.
