(* TRIPWIRE -- the IND-CCA `hop_7_initialize` distribution step, in the small.

   One endpoint draws the whole random function and READS it at the challenge
   point; the other draws the function AND an independent challenge value. The
   two are equidistributed because reprogramming one point of a `dfun` draw with
   a fresh sample is again a `dfun` draw (`MUniFinFun.dlet_dfun_update`), so the
   hop's post can relate them by

       <left>.rF{1} = <right>.rF{2}.[x0 <- res{2}]

   which is the WEAKENED conjunct the real hop needs -- full function equality
   there is provably unachievable (it would force the right's independent draw to
   be a function of its own random function).

   The exporter's shape is mirrored: `dfn` is `MUF.dfun (fun _ => dcod)` behind an
   `op [smt_opaque]`, exactly as `type_collector` emits it, so a route derived
   here transfers. `x0` stands in for the challenge KDF input, which in the real
   hop is a deterministic expression over stored fields. *)

require import AllCore Distr List FinType.

type dom, cod.

clone FinType as FT with type t <- dom.

clone MUniFinFun as MUF with
  type t <- dom,
  op FinT.enum <- FT.enum
  proof FinT.enum_spec by exact FT.enum_spec.

op dcod : cod distr.
axiom dcod_ll : is_lossless dcod.

op [smt_opaque] dfn : (dom -> cod) distr = MUF.dfun (fun _ => dcod).

lemma dfn_ll : is_lossless dfn.
proof. by rewrite /dfn; apply/MUF.dfun_ll => x; exact dcod_ll. qed.

(* The challenge point. In the real hop it is the challenge KDF input, and it is
   NOT expressible over stored state -- its first component needs a Diffie-Hellman
   fact the NominalGroup primitive deliberately withholds. What matters, and what
   is modelled here, is its SHAPE: a builder `mk` (the KDF-input concat) applied to
   a first component nothing relates and a second component that IS the challenge
   ciphertext. `mk_inj` is concat injectivity plus `Encode`'s declared
   `deterministic injective`. *)
type ctxt.

op ctStar : ctxt.
op ssT    : cod.            (* the DH-derived component -- deliberately unrelated *)
op decss  : ctxt -> cod.    (* what Decaps computes in that slot *)
op mk     : cod -> ctxt -> dom.

axiom mk_inj (a b : cod) (c d : ctxt) : mk a c = mk b d => a = b /\ c = d.

op [smt_opaque] x0 : dom = mk ssT ctStar.

module L = {
  var rF : dom -> cod

  proc init() : cod = {
    var ss : cod;
    rF <$ dfn;
    ss <- rF x0;
    return ss;
  }
}.

module R = {
  var rF : dom -> cod

  proc init() : cod = {
    var ss : cod;
    rF <$ dfn;
    ss <$ dcod;
    return ss;
  }
}.

(* ------------------------------------------------------------------ *)
(* THE MATHEMATICAL CONTENT OF THE HOP, AND IT IS PROVED.               *)
(*                                                                      *)
(* `rndsem*` folds each side's sampling into ONE draw over pairs:       *)
(*                                                                      *)
(*   left   dmap dfn (fun f => (f, f x0))                               *)
(*   right  dlet dfn (fun g => dmap dcod (fun y => (g, y)))             *)
(*                                                                      *)
(* and the hop's post says the left pair is the right pair PUSHED       *)
(* FORWARD through h (g, y) = (g.[x0 <- y], y). This lemma is that      *)
(* push-forward, i.e. exactly the claim that reprogramming one point of *)
(* a `dfun` draw with a fresh sample is again a `dfun` draw. It is      *)
(* DERIVED from `MUniFinFun.dlet_dfun_update`, so no axiom is involved. *)
(* ------------------------------------------------------------------ *)
lemma fold_eq :
    dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => (g.[x0 <- y], y)))
  = dmap dfn (fun (f : dom -> cod) => (f, f x0)).
proof.
have -> :
    dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => (g.[x0 <- y], y)))
  = dmap (dlet dfn (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => g.[x0 <- y])))
        (fun (f : dom -> cod) => (f, f x0)).
+ rewrite dmap_dlet; apply eq_dlet => // g; rewrite dmap_comp /(\o) /=;
  apply eq_dmap => y /=; rewrite fupdate_eq //.
congr; rewrite /dfn (MUF.dlet_dfun_update (fun (_ : dom) => dcod) x0) /=.
by rewrite (dcod_ll) dscalar1.
qed.

(* ------------------------------------------------------------------ *)
(* WHY THE COUPLING NEEDS A THIRD PROGRAM.                              *)
(*                                                                      *)
(* `fold_eq` is the content, but EasyCrypt cannot USE it directly:      *)
(* `rnd f finv` demands a BIJECTION between the two supports, and h is  *)
(* not injective -- the right's `g` carries entropy at `x0` that the    *)
(* post discards, so every `g` agreeing with f off `x0` maps to one     *)
(* left point. Both argument orders were measured and both obligations  *)
(* are false:                                                           *)
(*                                                                      *)
(*   rnd h id  -> `forall r in dRight, r = h r`                (false)  *)
(*   rnd id h  -> `mu1 dRight l = mu1 dLeft l`                 (false)  *)
(*                                                                      *)
(* Rewriting a distribution does not help either: `dfunE_dlet_fix1` on  *)
(* EITHER side leaves the surplus as a `dlet` INSIDE one sample, which  *)
(* a one-sided `rnd{2}` cannot reach. The surplus has to be an explicit *)
(* PROGRAM STATEMENT, so interpose Mid, which draws the value at `x0`   *)
(* FIRST and then the function PINNED to it. The legs then split:       *)
(*                                                                      *)
(*   Mid ~ R   an IDENTITY coupling -- `dfunE_dlet_fix1` says drawing   *)
(*             the value then the pinned function IS drawing the        *)
(*             function. PROVED below.                                  *)
(*   L ~ Mid   a BIJECTIVE coupling -- on the pinned support `g x0 = v` *)
(*             is known, so `g` is recoverable from `g.[x0 <- y]`, and  *)
(*             `dlet_dfun_fupdate_ll` is its distribution identity. Its *)
(*             surplus `v` goes one-sided at the front under `dcod_ll`  *)
(*             once the tail no longer needs it. Its three `rnd`        *)
(*             obligations are pure function-update bookkeeping, all    *)
(*             discharged. PROVED below.                                *)
(*                                                                      *)
(* `reprogram` at the end composes the two into the hop's own statement,*)
(* and this file is ADMIT-FREE: the whole argument is proved, no axiom.  *)
(* ------------------------------------------------------------------ *)

module Mid = {
  var rF : dom -> cod

  proc init() : cod = {
    var ss : cod;
    var v : cod;
    v  <$ dcod;
    rF <$ MUF.dfun (fun (_ : dom) => dcod).[x0 <- dunit v];
    ss <$ dcod;
    return ss;
  }
}.

(* LEG 1: Mid ~ R -- an IDENTITY coupling. Drawing the value at x0 first and then
   the PINNED function is drawing the function (`dfunE_dlet_fix1`). *)
equiv leg_mid_r : Mid.init ~ R.init :
  true ==> ={res} /\ Mid.rF{1} = R.rF{2}.
proof.
proc.
seq 2 1 : (Mid.rF{1} = R.rF{2}); last by rnd; skip => /#.
rndsem*{1} 0.
conseq (: _ ==> Mid.rF{1} = R.rF{2}) => //.
rnd (fun (f : dom -> cod) => f) (fun (f : dom -> cod) => f); skip => />.
have dEq : dlet dcod (fun (v : cod) => dmap (MUF.dfun (fun (_ : dom) => dcod).[x0 <- dunit v]) (fun (rF : dom -> cod) => rF)) = dfn.
+ rewrite /dfn (MUF.dfunE_dlet_fix1 (fun (_ : dom) => dcod) x0) /=;
  apply eq_dlet => // v; exact dmap_id.
by rewrite dEq.
qed.

(* Function-update algebra the coupling needs. *)
lemma fupd2 (f : dom -> cod) (a b : cod) : f.[x0 <- a].[x0 <- b] = f.[x0 <- b].
proof. by apply fun_ext => z; rewrite !fupdateE; case: (x0 = z). qed.

lemma fupd_id (f : dom -> cod) : f.[x0 <- f x0] = f.
proof. by apply fun_ext => z; rewrite fupdateE; case: (x0 = z) => [->|]. qed.

(* Support fact: under the pin the drawn function's value at x0 is KNOWN, and
   that is exactly what makes the coupling below injective. *)
lemma pin_supp (v : cod) (g : dom -> cod) :
  g \in MUF.dfun (fun (_ : dom) => dcod).[x0 <- dunit v] => g x0 = v.
proof. by move/MUF.dfun_supp => /(_ x0); rewrite fupdate_eq supp_dunit. qed.

abbrev pinD (v : cod) =
  dlet (MUF.dfun (fun (_ : dom) => dcod).[x0 <- dunit v])
       (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => (g, y))).

abbrev reprog (p : (dom -> cod) * cod) = (p.`1.[x0 <- p.`2], p.`2).

lemma pinR_supp (v : cod) (p : (dom -> cod) * cod) : p \in pinD v => p.`1 x0 = v.
proof.
by move/supp_dlet => [g] [hg] /supp_dmap [y] [_ ->] /=; exact (pin_supp v g hg).
qed.

(* THE PINNED IDENTITY, stated as the push-forward the coupling actually uses.
   Same four-line shape as `fold_eq`, but over the PINNED draw, which is what
   makes the map injective -- `dlet_dfun_fupdate_ll` is its distribution law. *)
lemma fold_eq_pin (v : cod) :
  dmap (pinD v) reprog = dmap dfn (fun (f : dom -> cod) => (f, f x0)).
proof.
have -> : dmap (pinD v) reprog
  = dmap (dlet (MUF.dfun (fun (_ : dom) => dcod).[x0 <- dunit v])
               (fun (g : dom -> cod) => dmap dcod (fun (y : cod) => g.[x0 <- y])))
        (fun (f : dom -> cod) => (f, f x0)).
+ rewrite !dmap_dlet; apply eq_dlet => // g; rewrite !dmap_comp /(\o) /=;
  apply eq_dmap => y /=; rewrite fupdate_eq //.
congr; rewrite /dfn (MUF.dlet_dfun_fupdate_ll (fun (_ : dom) => dcod) x0 v) //.
qed.

lemma dfn_at (f : dom -> cod) (z : dom) : f \in dfn => f z \in dcod.
proof. by rewrite /dfn => /MUF.dfun_supp /(_ z). qed.

lemma dL_supp (p : (dom -> cod) * cod) :
  p \in dmap dfn (fun (f : dom -> cod) => (f, f x0)) =>
  p.`1 \in dfn /\ p.`2 = p.`1 x0.
proof. by move/supp_dmap => [f] [hf ->]. qed.

lemma pinD_mem (v : cod) (f : dom -> cod) (y : cod) :
  f \in dfn => y \in dcod => (f.[x0 <- v], y) \in pinD v.
proof.
move=> hf hy; apply/supp_dlet; exists (f.[x0 <- v]); split.
+ apply/MUF.dfun_supp => z; rewrite !fupdateE; case: (x0 = z) => [_|_].
  + exact supp_dunit.
  by move: hf; rewrite /dfn => /MUF.dfun_supp /(_ z).
by apply/supp_dmap; exists y.
qed.

(* LEG 2: L ~ Mid -- the BIJECTIVE coupling, with Mid's surplus `v` dropped
   one-sided at the front once the tail no longer needs it. *)
equiv leg_l_mid : L.init ~ Mid.init :
  true ==> ={res} /\ L.rF{1} = Mid.rF{2}.[x0 <- res{2}].
proof.
proc.
seq 0 1 : true; first by rnd{2}; skip => />; exact dcod_ll.
exists* v{2}; elim* => v0.
rndsem*{1} 0; rndsem*{2} 0.
rnd (fun (p : (dom -> cod) * cod) => (p.`1.[x0 <- v0], p.`2)) reprog; skip => />.
split; [ | move=> _; split; [ | move=> _ ] ].
+ by move=> r hr; rewrite fupd2 -(pinR_supp v0 r hr) fupd_id; smt().
+ move=> [f y] hr /=.
  have hcol : f.[x0 <- y].[x0 <- v0] = f
    by rewrite fupd2 -(pinR_supp v0 (f, y) hr) fupd_id.
  rewrite -(fold_eq_pin v0).
  rewrite (in_dmap1E_can _ _ (fun (p : (dom -> cod) * cod) => (p.`1.[x0 <- v0], p.`2))) /=.
  + by rewrite !fupd2.
  + move=> [g w] hy /= [hy1 hy2].
    have e1 : g = g.[x0 <- w].[x0 <- v0]
      by rewrite fupd2 -(pinR_supp v0 (g, w) hy) fupd_id.
    by rewrite hcol; smt().
  by rewrite hcol.
move=> l hl; case: (dL_supp l hl) => h1 h2.
split; [ by apply pinD_mem => //; rewrite h2; exact (dfn_at l.`1 x0 h1) | move=> _ ].
split; [ by rewrite fupd2 h2 fupd_id; smt() | move=> _ ].
by rewrite fupd2 h2 fupd_id.
qed.

(* THE HOP'S OWN STATEMENT, as the composition of the two legs. This is what the
   exporter has to emit; the legs are the parts. It inherits leg 2's one open
   obligation and nothing else. *)
equiv reprogram : L.init ~ R.init :
  true ==> ={res} /\ L.rF{1} = R.rF{2}.[x0 <- res{2}].
proof.
transitivity Mid.init
  (true ==> ={res} /\ L.rF{1} = Mid.rF{2}.[x0 <- res{2}])
  (true ==> ={res} /\ Mid.rF{1} = R.rF{2}) => //.
+ exact leg_l_mid.
exact leg_mid_r.
qed.

(* ------------------------------------------------------------------ *)
(* PART (c): what the CONSUMER actually gets.                           *)
(*                                                                      *)
(* The reprogramming point is not expressible over stored state, so it   *)
(* must not appear in the hop's post. It does not need to: it is an      *)
(* internal WITNESS, and what the post carries is the consequence        *)
(* `Decaps` needs -- that the two random functions agree at every input  *)
(* `Decaps` can query. `Decaps` queries only at `mk (decss c) c` for     *)
(* `c <> ctStar`, and `mk_inj` separates every such input from `x0`      *)
(* through its SECOND component alone. The first components (`ssT`       *)
(* against `decss c`) are never related -- which is exactly why no       *)
(* Diffie-Hellman fact is needed.                                       *)
(* ------------------------------------------------------------------ *)
lemma agree_off (f : dom -> cod) (y : cod) (c : ctxt) :
  c <> ctStar => f.[x0 <- y] (mk (decss c) c) = f (mk (decss c) c).
proof.
move=> hc.
have hne : x0 <> mk (decss c) c.
+ rewrite /x0; apply/negP => h.
  have [_ hh] := mk_inj ssT (decss c) ctStar c h.
  by move: hc; rewrite hh.
by rewrite fupdate_neq.
qed.

(* The hop's post as the consumer will consume it. Derived from `reprogram`,
   so it inherits its proof and adds only the separation. *)
equiv reprogram_agree : L.init ~ R.init :
  true ==>
     ={res}
  /\ forall (c : ctxt), c <> ctStar =>
       L.rF{1} (mk (decss c) c) = R.rF{2} (mk (decss c) c).
proof.
conseq reprogram => />.
by move=> result_R rF_R c hc; apply agree_off.
qed.
