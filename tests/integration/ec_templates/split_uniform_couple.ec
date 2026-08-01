(* Tripwire: the SPLIT-UNIFORM coupling behind hop_2 / hop_12 / hop_14
 * `initialize` -- one side draws two independent uniform pieces, the other
 * draws one uniform FULL string and slices it.
 *
 * WHY THIS FILE EXISTS: cycle 69 established that the recipe and the four
 * axioms the virtual concat triple emits are correct, but the proof would not
 * close, and the residue was purely the DISTRIBUTION FORM. `rndsem*{1} 0`
 * produces `dlet dpq (fun a => dmap dt (fun b => (a, b)))`, while the emitted
 * split axiom is stated over ``dpq `*` dt``; `dprod_dlet` does not bridge them
 * in the support obligation (four attempts).
 *
 * THE FIX, confirmed here: state the 2-way split axiom in DLET FORM, exactly as
 * `type_collector` already does for the 3-way concat3 case, whose comment says
 * it does so because that "matches the shape produced by EC's `rndsem*{i} 0`".
 * With `dfull_split_dlet` the measure obligation reduces to a pointwise
 * `mu_eq` over `dt` and the whole lemma closes -- EC exit 0, admit-free.
 *
 * Both forms are kept below so the difference is legible: `dfull_split` is the
 * ``\`*\``-form the emitter produces today (unused by this proof), and
 * `dfull_split_dlet` is the variant the emitter needs to add.
 *)

require import AllCore Distr DProd.

type pqt, tt, fullt.

op dpq : pqt distr.
op dt  : tt distr.
op dfull : fullt distr.

axiom dpq_ll : is_lossless dpq.
axiom dt_ll  : is_lossless dt.

op concat : pqt -> tt -> fullt.
op slice_l : fullt -> pqt.
op slice_r : fullt -> tt.

(* the four axioms the virtual triple emits *)
axiom slice_concat_left  : forall a b, slice_l (concat a b) = a.
axiom slice_concat_right : forall a b, slice_r (concat a b) = b.
axiom concat_slices_id   : forall s, concat (slice_l s) (slice_r s) = s.
axiom dfull_split : dfull = dmap (dpq `*` dt) (fun (p : pqt * tt) => concat p.`1 p.`2).

(* the DLET-form variant, shaped like what `rndsem*{i} 0` actually produces --
   the same treatment type_collector already gives the 3-way concat3 case *)
axiom dfull_split_dlet :
  dfull = dlet dpq (fun (v1 : pqt) => dmap dt (fun (v2 : tt) => concat v1 v2)).

module A = {
  proc f () : pqt * tt = {
    var a : pqt;
    var b : tt;
    a <$ dpq;
    b <$ dt;
    return (a, b);
  }
}.

module B = {
  proc f () : pqt * tt = {
    var s : fullt;
    s <$ dfull;
    return (slice_l s, slice_r s);
  }
}.

lemma split_couple : equiv [ A.f ~ B.f : true ==> ={res} ].
proof.
  proc.
  rndsem*{1} 0.
  rnd (fun (p : pqt * tt) => concat p.`1 p.`2)
      (fun (s : fullt) => (slice_l s, slice_r s)).
  skip => />.
  rewrite dfull_split_dlet.
  split.
  + move => s hs; rewrite concat_slices_id //.
  move => _; split.
  + move => s hs.
    rewrite !dlet1E; congr; apply fun_ext => a /=.
    rewrite !dmap1E /(\o) /pred1 /=.
    congr; apply mu_eq => b /=.
    by rewrite eqboolP;
       smt(slice_concat_left slice_concat_right concat_slices_id).
  move => _ p hp.
  have h1 : p.`1 \in dpq by smt(supp_dlet supp_dmap).
  have h2 : p.`2 \in dt by smt(supp_dlet supp_dmap).
  split.
  + rewrite supp_dlet; exists p.`1; rewrite h1 /=.
    by rewrite supp_dmap; exists p.`2; rewrite h2.
  move => _; smt(slice_concat_left slice_concat_right).
qed.
