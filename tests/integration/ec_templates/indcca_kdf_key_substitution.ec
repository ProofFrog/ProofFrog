(* ============================================================ *)
(* IND-CCA `initialize` hop_5 -- the KDF-KEY SUBSTITUTION.        *)
(*   -- VALIDATED EC TEMPLATE (regression tripwire), admit-free,  *)
(*      and proved from INJECTIVITY alone.                        *)
(*                                                               *)
(* Measured shape (flat states of `CG_expanded_INDCCA_PQ`):       *)
(*                                                               *)
(*   LEFT  (RB at KEM_INDCCA_Random)  RIGHT (RD at KDFPRFSec_Real)*)
(*     keygen                           k <$ dbs   <- drawndirectly   *)
(*     encaps                           keygen                    *)
(*     ss_PQ <$ dbs                     seed <$                   *)
(*     seed <$                          NG step                   *)
(*     NG step                          encaps                    *)
(*     e3 <@ encodesharedsecret(ss_PQ)  (absent)                  *)
(*     H.evaluate(concat e3 rest)       H.evaluate(concat k rest) *)
(*                                                               *)
(* Three things at once, which is why the earlier reading of this *)
(* hop as "plumbing" was wrong: the bundled-delegate REORDER, a    *)
(* one-sided DETERMINISTIC `encodesharedsecret`, and the KDF key   *)
(* being `encode(ss_PQ)` on one side against a fresh draw on the   *)
(* other. The last is the hop's content.                           *)
(*                                                               *)
(* THE TACTIC, in the order that works:                            *)
(*  1. two `swap`s -- hoist the explicit side's `encaps` block to  *)
(*     sit after `keygen`, and hoist the left''s sample to the     *)
(*     front (a sample is glob-independent of everything above it);*)
(*  2. `seq` at the NG call, with the invariant carrying           *)
(*     `k{2} = ev_enc ssPQ{1}` -- the coupling itself;             *)
(*  3. the prefix peel ends in `rnd ev_enc g`, coupling the two    *)
(*     draws THROUGH THE BIJECTION. This is where the foundation   *)
(*     is spent;                                                   *)
(*  4. `seq 1 0` isolates the one-sided `encodesharedsecret` so    *)
(*     `exists*` freezes at the POST-PREFIX memory (where `ssPQ`   *)
(*     is defined), then its `_det` axiom functionalizes it.       *)
(*                                                               *)
(* ASSUMES ONLY ALREADY-ADJUDICATED FAMILIES -- `gt0_n` (bit-length*)
(* positivity), a distribution losslessness, the licensed `_inj`,  *)
(* and the licensed `_det`. Bijectivity is DERIVED from `_inj`     *)
(* plus the BitWord type's finiteness, not assumed; see           *)
(* `bitword_injective_bijective.ec` for that step in isolation.    *)
(* ============================================================ *)

require import AllCore Distr List FinType.
require BitWord.

op n : int.
axiom gt0_n : 0 < n.
clone BitWord as BW with op n <- n proof gt0_n by exact gt0_n.
type bs = BW.word.
op dbs : bs distr = BW.DWord.dunifin.

type EK, DK, CT, Elem, Seed, KdfIn, KdfOut.
op dSeed : Seed distr.
axiom dSeed_ll : is_lossless dSeed.
op concat : bs -> Elem -> KdfIn.

op ev_enc : bs -> bs.
axiom ev_enc_inj (a b : bs) : ev_enc a = ev_enc b => a = b.

module type KEM = {
  proc keygen() : EK * DK
  proc encaps(ek : EK) : bs * CT
  proc encodesharedsecret(s : bs) : bs
}.
module type NGT = { proc randomscalar(s : Seed) : Elem }.
module type HT = { proc evaluate(x : KdfIn) : KdfOut }.

(* LEFT: the KDF key is the ENCODING of the challenger's random shared secret. *)
module MEnc (K : KEM, N : NGT, H : HT) = {
  proc initialize() : KdfOut = {
    var kp : EK * DK; var ek : EK; var t : bs * CT; var ssPQ : bs;
    var seed : Seed; var e : Elem; var e3 : bs; var o : KdfOut;
    kp <@ K.keygen();
    ek <- kp.`1;
    t <@ K.encaps(ek);
    ssPQ <$ dbs;
    seed <$ dSeed;
    e <@ N.randomscalar(seed);
    e3 <@ K.encodesharedsecret(ssPQ);
    o <@ H.evaluate(concat e3 e);
    return o;
  }
}.

(* RIGHT: the KDF key is drawn directly, and `encaps` sits after the NG step. *)
module MKey (K : KEM, N : NGT, H : HT) = {
  proc initialize() : KdfOut = {
    var kp : EK * DK; var ek : EK; var t : bs * CT; var k : bs;
    var seed : Seed; var e : Elem; var o : KdfOut;
    k <$ dbs;
    kp <@ K.keygen();
    seed <$ dSeed;
    e <@ N.randomscalar(seed);
    ek <- kp.`1;
    t <@ K.encaps(ek);
    o <@ H.evaluate(concat k e);
    return o;
  }
}.

section.
declare module K <: KEM {-MEnc, -MKey}.
declare module N <: NGT {-K, -MEnc, -MKey}.
declare module H <: HT {-K, -N, -MEnc, -MKey}.

declare axiom K_encodesharedsecret_det (g : (glob K)) (a0 : bs) :
  phoare[ K.encodesharedsecret : (glob K) = g /\ s = a0
          ==> (glob K) = g /\ res = ev_enc a0 ] = 1%r.

(* The foundation, DERIVED here rather than assumed: injectivity plus the
   BitWord type's finiteness gives bijectivity. Same proof as
   ec_templates/bitword_injective_bijective.ec. *)
lemma ev_enc_surj (y : bs) : exists x, ev_enc x = y.
proof.
have huniq : uniq (map ev_enc BW.words).
+ apply/map_inj_in_uniq; last exact BW.enum_uniq.
  by move=> a b _ _; apply ev_enc_inj.
have hsub : forall z, z \in map ev_enc BW.words => z \in BW.words.
+ by move=> z _; apply BW.enumP.
have hsize : size BW.words <= size (map ev_enc BW.words).
+ rewrite size_map; smt().
have [hmem _] := leq_size_perm (map ev_enc BW.words) BW.words huniq hsub hsize.
have : y \in map ev_enc BW.words by rewrite hmem; apply BW.enumP.
by move/mapP => [x [_ hx]]; exists x; rewrite hx.
qed.

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

equiv hop_5_initialize : MEnc(K, N, H).initialize ~ MKey(K, N, H).initialize :
  ={glob K} /\ ={glob N} /\ ={glob H} ==> ={res} /\ ={glob K} /\ ={glob N} /\ ={glob H}.
proof.
have [g [hgf hfg]] := ev_enc_bij.
proc.
swap{2} [5..6] -2.
swap{1} 4 -3.
seq 6 6 : (={glob K, glob N, glob H, e} /\ k{2} = ev_enc ssPQ{1}).
+ wp; call (_: true).
  wp; rnd.
  wp; call (_: true).
  wp; call (_: true).
  rnd ev_enc g.
  skip => /#.
seq 1 0 : (={glob K, glob N, glob H, e} /\ k{2} = ev_enc ssPQ{1} /\ e3{1} = k{2}).
+ exists* (glob K){1}, ssPQ{1}; elim* => gk a0.
  call{1} (K_encodesharedsecret_det gk a0); skip => /#.
call (_: true); skip => /#.
qed.

end section.
