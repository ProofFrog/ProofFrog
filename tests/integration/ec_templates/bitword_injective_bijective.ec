(* ============================================================ *)
(* INJECTIVE ENDO-MAP ON A BITWORD TYPE IS BIJECTIVE, hence it    *)
(* carries the uniform distribution to itself.                    *)
(*   -- VALIDATED EC TEMPLATE (regression tripwire), admit-free.  *)
(*                                                               *)
(* The foundation IND-CCA `initialize` hop_5 needs. Its two sides *)
(* feed the KDF `encode(ss_PQ)` and `challenger_k`, both drawn    *)
(* from the same uniform bitstring distribution; they agree       *)
(* exactly when encoding a uniform shared secret is uniform.      *)
(*                                                               *)
(* WHY IT IS DERIVABLE AND NOT AN AXIOM. `EncodeSharedSecret` is  *)
(* declared `deterministic injective`, which alone gives          *)
(* uniformity only on the IMAGE. What closes the gap is that the  *)
(* exporter's clone binds BOTH `sharedsecret` and `bs_Nss_t` to   *)
(* the SAME BitWord type, so the map is an injective ENDO-map on  *)
(* a FINITE type. The emitted axiom already has this shape:       *)
(*                                                               *)
(*   declare axiom KEM_PQ_encodesharedsecret_inj                  *)
(*     (a0 b0 : bs_kem_pq_nss) :                                  *)
(*     ev_encodesharedsecret a0 = ev_encodesharedsecret b0        *)
(*     => a0 = b0                                                 *)
(*                                                               *)
(* so the derivation adds NO trusted base: injectivity is the     *)
(* already-licensed `_inj` family and finiteness comes from       *)
(* `Word.eca`'s `FinType` clone.                                  *)
(*                                                               *)
(* THE THREE STEPS, and where each primitive lives:               *)
(*  1. pigeonhole -> surjective. `List.leq_size_perm` is the one  *)
(*     EC has no ready-made lemma for; `map ev_enc words` is uniq *)
(*     (injectivity) and the same size, so it covers `words`.     *)
(*  2. surjective + injective -> `bijective`, with the inverse    *)
(*     built by `choiceb`.                                        *)
(*  3. `dmap1E_can` + `DWord.dunifin_funi` -> the distribution is *)
(*     carried to itself.                                         *)
(*                                                               *)
(* SECOND TRAP, found only when this derivation was run against  *)
(* the REAL export: `size_map` must be given its function        *)
(* EXPLICITLY. `BW.words` is itself defined through a `map`, so a *)
(* bare `rewrite size_map` fires inside THAT definition (leaving  *)
(* `size (BW.Enum.wordn n) <= size (map ev_enc BW.words)`) rather *)
(* than on the goal's own map. Here a following bare `smt()`      *)
(* happened to recover; in the real export, where the same        *)
(* derivation sits inside a section over a `declare axiom`, it    *)
(* did not -- the file failed with "cannot prove goal (strict)".  *)
(*                                                               *)
(* NAMING TRAP that cost two rounds: `Word.eca` does              *)
(* `clone include FinType ... rename [op] "enum" as "words"`, so  *)
(* the OP is `BW.words` while the LEMMAS keep `BW.enumP` /        *)
(* `BW.enum_uniq`. The rename is ops-only.                        *)
(*                                                               *)
(* Width kept SYMBOLIC, as the exporter's is.                     *)
(* ============================================================ *)

require import AllCore Distr List FinType.
require BitWord.

op n : int.
axiom gt0_n : 0 < n.

clone BitWord as BW with
  op n <- n
  proof gt0_n by exact gt0_n.

type bs = BW.word.
op dbs : bs distr = BW.DWord.dunifin.

(* The exporter's `_inj` axiom, verbatim in shape. *)
op ev_enc : bs -> bs.
axiom ev_enc_inj (a b : bs) : ev_enc a = ev_enc b => a = b.

(* --- step 1: injective + finite => surjective (the pigeonhole) ----------- *)
lemma ev_enc_surj (y : bs) : exists x, ev_enc x = y.
proof.
have huniq : uniq (map ev_enc BW.words).
+ apply/map_inj_in_uniq; last exact BW.enum_uniq.
  by move=> a b _ _; apply ev_enc_inj.
have hsub : forall z, z \in map ev_enc BW.words => z \in BW.words.
+ by move=> z _; apply BW.enumP.
have hsize : size BW.words <= size (map ev_enc BW.words).
+ by rewrite (size_map ev_enc).
have [hmem _] := leq_size_perm (map ev_enc BW.words) BW.words
                   huniq hsub hsize.
have : y \in map ev_enc BW.words by rewrite hmem; apply BW.enumP.
by move/mapP => [x [_ hx]]; exists x; rewrite hx.
qed.

(* --- step 2: hence bijective -------------------------------------------- *)
lemma ev_enc_bij : bijective ev_enc.
proof.
pose g := fun y => choiceb (fun x => ev_enc x = y) witness.
exists g; split.
+ move=> x; rewrite /g.
  have := choicebP (fun z => ev_enc z = ev_enc x) witness _.
  + by exists x.
  by apply ev_enc_inj.
move=> y; rewrite /g.
by apply (choicebP (fun z => ev_enc z = y) witness); apply ev_enc_surj.
qed.

(* --- step 3: so it carries the uniform distribution to itself ------------ *)
lemma dbs_enc : dmap dbs ev_enc = dbs.
proof.
have [g [hgf hfg]] := ev_enc_bij.
apply eq_distr => x.
rewrite (dmap1E_can dbs ev_enc g x _ _).
+ exact hfg.
+ by move=> a _; apply hgf.
by apply BW.DWord.dunifin_funi.
qed.
