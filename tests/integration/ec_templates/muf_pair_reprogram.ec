(* Tripwire: MUniFinFun over a PRODUCT of two BitWord types -- the pair-domain
   random function the CK/UK keyed-KDF reprogramming needs. Validates the
   product FinT.enum (allpairs of the two word enums) and the derived
   ll/funi/full facts, mirroring the flat-domain form c283 landed. *)
require import AllCore Distr DMap List.
require BitWord.

op na : int = 8.
op nb : int = 12.

clone BitWord as BWA with op n <- na proof gt0_n by trivial.
clone BitWord as BWB with op n <- nb proof gt0_n by trivial.

type ta = BWA.word.
type tb = BWB.word.
type tc = BWA.word.

op dcod : tc distr = BWA.DWord.dunifin.

lemma pair_enum_spec (x : ta * tb) :
  count (pred1 x)
    (allpairs (fun (a : ta) (b : tb) => (a, b)) BWA.words BWB.words) = 1.
proof.
case: x => a b.
rewrite count_uniq_mem.
+ apply allpairs_uniq; [exact BWA.enum_uniq | exact BWB.enum_uniq | smt()].
have -> /= : (a, b) \in allpairs (fun (a0 : ta) (b0 : tb) => (a0, b0)) BWA.words BWB.words
  by apply/allpairsP; exists (a, b); rewrite /= BWA.enumP BWB.enumP.
done.
qed.

clone MUniFinFun as MUF_pair with
  type t <- ta * tb,
  op FinT.enum <- allpairs (fun (a : ta) (b : tb) => (a, b)) BWA.words BWB.words
  proof FinT.enum_spec by exact pair_enum_spec.

op dfun_pair : (ta * tb -> tc) distr =
  MUF_pair.dfun (fun _ => dcod).

lemma dfun_pair_ll : is_lossless dfun_pair.
proof.
  by rewrite /dfun_pair; apply/MUF_pair.dfun_ll => x; exact BWA.DWord.dunifin_ll.
qed.

lemma dfun_pair_funi : is_funiform dfun_pair.
proof.
  rewrite /dfun_pair; apply/MUF_pair.dfun_funi.
  - by move=> x; apply/funi_uni/BWA.DWord.dunifin_funi.
  by move=> x; exact BWA.DWord.dunifin_fu.
qed.

lemma dfun_pair_fu : is_full dfun_pair.
proof.
  by rewrite /dfun_pair; apply/MUF_pair.dfun_fu => x; exact BWA.DWord.dunifin_fu.
qed.

(* The reprogramming identity at a PAIR pin point -- the leg-2 ingredient. *)
lemma pin_then_draw (pt : ta * tb) :
  dlet dcod
    (fun (v : tc) =>
       dmap (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[pt <- dunit v])
         (fun (f : ta * tb -> tc) => f))
  = dfun_pair.
proof.
  rewrite /dfun_pair (MUF_pair.dfunE_dlet_fix1 (fun (_ : ta * tb) => dcod) pt) /=.
  by apply eq_dlet => // v; exact dmap_id.
qed.

(* ---- rr7 helper family at the PAIR domain ---- *)
lemma rr7_fupd2 (x0 : ta * tb) (f : ta * tb -> tc) (a b : tc) :
  f.[x0 <- a].[x0 <- b] = f.[x0 <- b].
proof. by apply fun_ext => z; rewrite !fupdateE; case: (x0 = z). qed.

lemma rr7_fupd_id (x0 : ta * tb) (f : ta * tb -> tc) : f.[x0 <- f x0] = f.
proof. by apply fun_ext => z; rewrite fupdateE; case: (x0 = z) => [->|]. qed.

lemma rr7_pin_supp (x0 : ta * tb) (v : tc) (g : ta * tb -> tc) :
  g \in MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v] => g x0 = v.
proof. by move/MUF_pair.dfun_supp => /(_ x0); rewrite fupdate_eq supp_dunit. qed.

lemma rr7_pinR_supp (x0 : ta * tb) (v : tc) (p : (ta * tb -> tc) * tc) :
  p \in dlet (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v])
       (fun (g : ta * tb -> tc) => dmap dcod (fun (y : tc) => (g, y))) =>
  p.`1 x0 = v.
proof.
by move/supp_dlet => [g] [hg] /supp_dmap [y] [_ ->] /=;
   exact (rr7_pin_supp x0 v g hg).
qed.

lemma rr7_fold_eq_pin (x0 : ta * tb) (v : tc) :
    dmap (dlet (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v])
       (fun (g : ta * tb -> tc) => dmap dcod (fun (y : tc) => (g, y))))
         (fun (p : (ta * tb -> tc) * tc) => (p.`1.[x0 <- p.`2], p.`2))
  = dmap dfun_pair (fun (f : ta * tb -> tc) => (f, f x0)).
proof.
have -> :
    dmap (dlet (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v])
       (fun (g : ta * tb -> tc) => dmap dcod (fun (y : tc) => (g, y))))
         (fun (p : (ta * tb -> tc) * tc) => (p.`1.[x0 <- p.`2], p.`2))
  = dmap (dlet (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v])
               (fun (g : ta * tb -> tc) => dmap dcod (fun (y : tc) => g.[x0 <- y])))
         (fun (f : ta * tb -> tc) => (f, f x0)).
+ rewrite !dmap_dlet; apply eq_dlet => // g; rewrite !dmap_comp /(\o) /=;
  apply eq_dmap => y /=; rewrite fupdate_eq //.
congr; rewrite /dfun_pair
  (MUF_pair.dlet_dfun_fupdate_ll (fun (_ : ta * tb) => dcod) x0 v) //.
qed.

lemma rr7_dfn_at (f : ta * tb -> tc) (z : ta * tb) : f \in dfun_pair => f z \in dcod.
proof. by rewrite /dfun_pair => /MUF_pair.dfun_supp /(_ z). qed.

lemma rr7_dL_supp (x0 : ta * tb) (p : (ta * tb -> tc) * tc) :
  p \in dmap dfun_pair (fun (f : ta * tb -> tc) => (f, f x0)) =>
  p.`1 \in dfun_pair /\ p.`2 = p.`1 x0.
proof. by move/supp_dmap => [f] [hf ->]. qed.

lemma rr7_pinD_mem (x0 : ta * tb) (v : tc) (f : ta * tb -> tc) (y : tc) :
  f \in dfun_pair => y \in dcod =>
  (f.[x0 <- v], y) \in dlet (MUF_pair.dfun (fun (_ : ta * tb) => dcod).[x0 <- dunit v])
       (fun (g : ta * tb -> tc) => dmap dcod (fun (y : tc) => (g, y))).
proof.
move=> hf hy; apply/supp_dlet; exists (f.[x0 <- v]); split.
+ apply/MUF_pair.dfun_supp => z; rewrite !fupdateE; case: (x0 = z) => [_|_].
  + exact supp_dunit.
  by move: hf; rewrite /dfun_pair => /MUF_pair.dfun_supp /(_ z).
by apply/supp_dmap; exists y.
qed.
