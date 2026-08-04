(* Tripwire: the 3-WAY concat family DERIVED over BitWord clones.
 *
 * Companion to `bitword_slice_concat.ec` (2-way round-trip laws) and
 * `bitword_uniform_split.ec` (the distribution family). This one covers what
 * `TypeCollector.emit`'s `_concat3_ops` loop emits for a marginal partial
 * split -- five more axioms per 3-way triple:
 *
 *     op    concat3_L_R_G_to_RES
 *     axiom slice_concat3_p1 / _p2 / _p3
 *     axiom concat3_slices_id
 *     axiom dRES_split3_L_R_G   (nested dlet/dlet/dmap)
 *
 * THE REAL SHAPE, matched deliberately: on the only corpus instance the three
 * components are the SAME type, so all three slices are the SAME op
 * (`slice_bs_3_lambda_to_bs_lambda`) and the widths are the sympy-canonical
 * `lambda` / `lambda + lambda` / `3*lambda`. A tripwire with three distinct
 * component types would not have exercised either -- notably the fact that ONE
 * `rewrite /slice` unfolds all three occurrences, so an emitter that unfolds
 * per-component would error with "nothing to rewrite" on the second.
 *
 * Widths stay symbolic. The slice signature is the exporter's explicit
 * `(s, i, j)`.
 *)

require import AllCore List Distr DProd DMap.
require (*--*) BitWord.

op lambda : int.
axiom gt0_lambda : 0 < lambda.

clone BitWord as W1 with op n <- lambda   proof gt0_n by smt(gt0_lambda).
clone BitWord as W3 with op n <- 3*lambda proof gt0_n by smt(gt0_lambda).

type bs_lambda   = W1.word.
type bs_3_lambda = W3.word.

op [smt_opaque] dbs_lambda   : bs_lambda   distr = W1.DWord.dunifin.
op [smt_opaque] dbs_3_lambda : bs_3_lambda distr = W3.DWord.dunifin.

lemma dbs_lambda_ll : is_lossless dbs_lambda.
proof. exact W1.DWord.dunifin_ll. qed.
lemma dbs_lambda_fu : is_funiform dbs_lambda.
proof. exact W1.DWord.dunifin_funi. qed.
lemma dbs_lambda_full : is_full dbs_lambda.
proof. exact W1.DWord.dunifin_fu. qed.
lemma dbs_3_lambda_ll : is_lossless dbs_3_lambda.
proof. exact W3.DWord.dunifin_ll. qed.
lemma dbs_3_lambda_fu : is_funiform dbs_3_lambda.
proof. exact W3.DWord.dunifin_funi. qed.
lemma dbs_3_lambda_full : is_full dbs_3_lambda.
proof. exact W3.DWord.dunifin_fu. qed.

op [smt_opaque] concat3 : bs_lambda -> bs_lambda -> bs_lambda -> bs_3_lambda =
  fun (a b c : bs_lambda) =>
    W3.mkword (W1.ofword a ++ W1.ofword b ++ W1.ofword c).

op [smt_opaque] slice3 : bs_3_lambda -> int -> int -> bs_lambda =
  fun (s : bs_3_lambda) (i j : int) =>
    W1.mkword (take (j - i) (drop i (W3.ofword s))).

lemma size_cat3 :
  forall (a b c : bs_lambda),
  size (W1.ofword a ++ W1.ofword b ++ W1.ofword c) = 3*lambda.
proof.
  move => a b c.
  rewrite !size_cat !W1.size_word.
  by smt().
qed.

lemma size_cat3_ab :
  forall (a b : bs_lambda), size (W1.ofword a ++ W1.ofword b) = lambda + lambda.
proof. move => a b; by rewrite size_cat !W1.size_word. qed.

(* --- p1 ------------------------------------------------------------------ *)
lemma slice_concat3_p1 :
  forall (a b c : bs_lambda), slice3 (concat3 a b c) 0 lambda = a.
proof.
  move => a b c.
  rewrite /slice3 /concat3 (W3.ofwordK _ (size_cat3 a b c)) drop0.
  have ->: lambda - 0 = lambda by smt().
  (* EC's `++` is LEFT-associative, so the emitted `A ++ B ++ C` is `(A ++ B) ++ C`
     and the head of the cat is NOT the first component; re-associate first. *)
  by rewrite -catA (take_size_cat _ _ _ (W1.size_word a)) W1.mkwordK.
qed.

(* --- p2 ------------------------------------------------------------------ *)
lemma slice_concat3_p2 :
  forall (a b c : bs_lambda),
  slice3 (concat3 a b c) lambda (lambda + lambda) = b.
proof.
  move => a b c.
  rewrite /slice3 /concat3 (W3.ofwordK _ (size_cat3 a b c)).
  have ->: lambda + lambda - lambda = lambda by smt().
  rewrite -catA (drop_size_cat _ _ _ (W1.size_word a)).
  by rewrite (take_size_cat _ _ _ (W1.size_word b)) W1.mkwordK.
qed.

(* --- p3: the left-nested cat already has `A ++ B` as its head ------------ *)
lemma slice_concat3_p3 :
  forall (a b c : bs_lambda),
  slice3 (concat3 a b c) (lambda + lambda) (3*lambda) = c.
proof.
  move => a b c.
  rewrite /slice3 /concat3 (W3.ofwordK _ (size_cat3 a b c)).
  have ->: 3*lambda - (lambda + lambda) = lambda by smt().
  rewrite (drop_size_cat _ _ _ (size_cat3_ab a b)).
  have hc : size (W1.ofword c) = lambda by exact W1.size_word.
  by rewrite -hc take_size W1.mkwordK.
qed.

(* --- the identity law ---------------------------------------------------- *)
lemma concat3_slices_id :
  forall (s : bs_3_lambda),
  concat3 (slice3 s 0 lambda) (slice3 s lambda (lambda + lambda))
          (slice3 s (lambda + lambda) (3*lambda)) = s.
proof.
  move => s.
  have hs : size (W3.ofword s) = 3*lambda by exact W3.size_word.
  (* ONE unfold reaches all three slice occurrences *)
  rewrite /concat3 /slice3 drop0.
  have ->: lambda - 0 = lambda by smt().
  have ->: lambda + lambda - lambda = lambda by smt().
  have ->: 3*lambda - (lambda + lambda) = lambda by smt().
  have h1 : size (take lambda (W3.ofword s)) = lambda
    by rewrite size_take; smt(gt0_lambda).
  have h2 : size (take lambda (drop lambda (W3.ofword s))) = lambda
    by rewrite size_take ?size_drop; smt(gt0_lambda).
  have hd3 : size (drop (lambda + lambda) (W3.ofword s)) = lambda
    by rewrite size_drop; smt(gt0_lambda).
  have ht3 : take lambda (drop (lambda + lambda) (W3.ofword s))
           = drop (lambda + lambda) (W3.ofword s)
    by rewrite take_oversize // hd3.
  have h3 : size (take lambda (drop (lambda + lambda) (W3.ofword s))) = lambda
    by rewrite ht3 hd3.
  rewrite (W1.ofwordK _ h1) (W1.ofwordK _ h2) (W1.ofwordK _ h3) ht3 -catA.
  have ->: drop (lambda + lambda) (W3.ofword s)
         = drop lambda (drop lambda (W3.ofword s))
    by rewrite drop_drop; smt(gt0_lambda).
  by rewrite cat_take_drop cat_take_drop W3.mkwordK.
qed.

(* --- the nested-dlet 3-way distribution split ---------------------------- *)
lemma dbs_3_lambda_split3_prod :
  dbs_3_lambda =
  dmap (dbs_lambda `*` (dbs_lambda `*` dbs_lambda))
       (fun (p : bs_lambda * (bs_lambda * bs_lambda)) =>
          concat3 p.`1 p.`2.`1 p.`2.`2).
proof.
apply: eq_funi_ll.
+ exact dbs_3_lambda_fu.
+ exact dbs_3_lambda_ll.
+ apply: is_full_funiform.
  + apply: dmap_fu_in => w.
    exists (slice3 w 0 lambda,
            (slice3 w lambda (lambda + lambda),
             slice3 w (lambda + lambda) (3*lambda))).
    rewrite !supp_dprod /=; split.
    + by split; [exact dbs_lambda_full | split; exact dbs_lambda_full].
    by rewrite concat3_slices_id.
  apply: dmap_uni_in_inj.
  + move => [x1 [y1 z1]] [x2 [y2 z2]] _ _ /= heq.
    have hx : x1 = x2
      by rewrite -(slice_concat3_p1 x1 y1 z1) -(slice_concat3_p1 x2 y2 z2) heq.
    have hy : y1 = y2
      by rewrite -(slice_concat3_p2 x1 y1 z1) -(slice_concat3_p2 x2 y2 z2) heq.
    have hz : z1 = z2
      by rewrite -(slice_concat3_p3 x1 y1 z1) -(slice_concat3_p3 x2 y2 z2) heq.
    by rewrite hx hy hz.
  apply: dprod_uni; first by apply: funi_uni; exact dbs_lambda_fu.
  by apply: dprod_uni; apply: funi_uni; exact dbs_lambda_fu.
apply: dmap_ll; rewrite dprod_ll; split; first exact dbs_lambda_ll.
by rewrite dprod_ll; split; exact dbs_lambda_ll.
qed.

lemma dbs_3_lambda_split3 :
  dbs_3_lambda =
  dlet dbs_lambda (fun (v1 : bs_lambda) =>
    dlet dbs_lambda (fun (v2 : bs_lambda) =>
      dmap dbs_lambda (concat3 v1 v2))).
proof.
rewrite dbs_3_lambda_split3_prod dprod_dlet dmap_dlet /=.
apply eq_dlet => // a.
rewrite dmap_comp /(\o) /= dprod_dlet dmap_dlet /=.
apply eq_dlet => // b.
by rewrite dmap_comp /(\o) /=.
qed.
