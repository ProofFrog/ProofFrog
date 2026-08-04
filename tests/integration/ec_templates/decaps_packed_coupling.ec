(* ============================================================ *)
(* PACKED-vs-SEPARATE `decaps` -- VALIDATED EC TEMPLATE           *)
(*   (regression tripwire).                                       *)
(*                                                               *)
(* The CFRG `_PQ` IND-CCA `decaps` hops. The two bodies are        *)
(* statement-for-statement IDENTICAL and differ only in field      *)
(* REFERENCES: the reduction keeps its correctness challenger's    *)
(* whole 5-tuple in one `corr` field and reads `corr.`2/`3/`5`,    *)
(* while the game holds the same material as separate             *)
(* `pq_keys`/`kem_ct`/`ss_PQ` fields.                              *)
(*                                                               *)
(* TWO things had to be true, and only one of them is a tactic:    *)
(*                                                               *)
(*  1. THE COUPLING HAS TO CARRY THOSE EQUALITIES. It did not --  *)
(*     `_packed_decomposition_coupling` walked the GAME's fields   *)
(*     and dropped every one the reduction did not hold by name    *)
(*     or classify through a packed KeyGen, which is every scalar  *)
(*     field here. The lemma was therefore UNPROVABLE as stated,   *)
(*     and no tactic could have fixed it. The route now also       *)
(*     matches a game field against a COMPONENT of a reduction's   *)
(*     packed field (the mirror of the packed-game direction it    *)
(*     already implemented).                                       *)
(*                                                               *)
(*  2. `sim` CANNOT USE THEM. It relates globals by NAME, so a     *)
(*     body reading `MRed.corr.`3` is not matched against one      *)
(*     reading `MGame.kem_ct` however the coupling relates them.   *)
(*     The structural peel walks the shared skeleton instead and   *)
(*     hands each differing expression to the closing `smt` with   *)
(*     the coupling in scope.                                      *)
(*                                                               *)
(* Load-bearing details of the peel:                               *)
(*  * `#pre` carries the whole coupling into the `seq` invariant,  *)
(*    so the only names emitted are the locals the branch reads    *)
(*    -- and this route never inlines, so those are the module's   *)
(*    OWN rendered locals and EC never renames them;                *)
(*  * each peel round's LEADING `wp` absorbs the assignments below  *)
(*    the coupled statement, so a trailing assignment needs no      *)
(*    separate step -- but a branch with NO call at all (`r <-      *)
(*    None`) has no `wp`, and closes with `auto` instead;           *)
(*  * the `if` guards go to `smt` precisely because one of them IS  *)
(*    a coupled reference (`ct_PQ = corr.`3` against               *)
(*    `ct_PQ = kem_ct`).                                            *)
(* ============================================================ *)

require import AllCore Distr.

type EK, DK, CT, SS, Scalar, Elem, Seed, KdfOut, KdfIn, NSS.

op concat : SS -> NSS -> KdfIn.

module type KEM = {
  proc decaps(dk : DK, ct : CT) : SS
  proc encodesharedsecret(s : SS) : SS
}.

module type NGT = {
  proc randomscalar(s : Seed) : Scalar
  proc exp(e : Elem, x : Scalar) : Elem
  proc elementtosharedsecret(e : Elem) : NSS
}.

module type HT = { proc evaluate(x : KdfIn) : KdfOut }.

(* REDUCTION: holds the challenger's whole 5-tuple in one packed field. *)
module MRed (K : KEM, N : NGT, H : HT) = {
  var corr : EK * DK * CT * SS * SS
  var seed_T : Seed
  var ctStar : CT * Elem
  proc decaps(ct : CT * Elem) : KdfOut option = {
    var r : KdfOut option;
    var dk_T : Scalar;
    var ct_PQ : CT;
    var ct_T : Elem;
    var e0 : Elem;
    var dss : NSS;
    var s8 : SS;
    var o1 : KdfOut;
    var dsp : SS;
    var s1 : SS;
    var o2 : KdfOut;
    if (ct = ctStar) {
      r <- None;
    } else {
      dk_T <@ N.randomscalar(seed_T);
      ct_PQ <- ct.`1;
      ct_T <- ct.`2;
      e0 <@ N.exp(ct_T, dk_T);
      dss <@ N.elementtosharedsecret(e0);
      if (ct_PQ = corr.`3) {
        s8 <@ K.encodesharedsecret(corr.`5);
        o1 <@ H.evaluate(concat s8 dss);
        r <- Some (o1);
      } else {
        dsp <@ K.decaps(corr.`2, ct_PQ);
        s1 <@ K.encodesharedsecret(dsp);
        o2 <@ H.evaluate(concat s1 dss);
        r <- Some (o2);
      }
    }
    return r;
  }
}.

(* GAME: holds the same material under three separate field names. *)
module MGame (K : KEM, N : NGT, H : HT) = {
  var pq_keys : EK * DK
  var seed_T : Seed
  var kem_ct : CT
  var ss_PQ : SS
  var ctStar : CT * Elem
  proc decaps(ct : CT * Elem) : KdfOut option = {
    var r : KdfOut option;
    var dk_T : Scalar;
    var ct_PQ : CT;
    var ct_T : Elem;
    var e0 : Elem;
    var dss : NSS;
    var s8 : SS;
    var o1 : KdfOut;
    var dsp : SS;
    var s1 : SS;
    var o2 : KdfOut;
    if (ct = ctStar) {
      r <- None;
    } else {
      dk_T <@ N.randomscalar(seed_T);
      ct_PQ <- ct.`1;
      ct_T <- ct.`2;
      e0 <@ N.exp(ct_T, dk_T);
      dss <@ N.elementtosharedsecret(e0);
      if (ct_PQ = kem_ct) {
        s8 <@ K.encodesharedsecret(ss_PQ);
        o1 <@ H.evaluate(concat s8 dss);
        r <- Some (o1);
      } else {
        dsp <@ K.decaps(pq_keys.`2, ct_PQ);
        s1 <@ K.encodesharedsecret(dsp);
        o2 <@ H.evaluate(concat s1 dss);
        r <- Some (o2);
      }
    }
    return r;
  }
}.

section.
declare module K <: KEM {-MRed, -MGame}.
declare module N <: NGT {-K, -MRed, -MGame}.
declare module H <: HT {-K, -N, -MRed, -MGame}.

equiv hop_2_decaps :
  MRed(K, N, H).decaps ~ MGame(K, N, H).decaps :
    ={ct} /\ ={glob K} /\ ={glob N} /\ ={glob H}
    /\ MGame.pq_keys.`1{2} = MRed.corr.`1{1}
    /\ MGame.pq_keys.`2{2} = MRed.corr.`2{1}
    /\ MGame.seed_T{2} = MRed.seed_T{1}
    /\ MGame.kem_ct{2} = MRed.corr.`3{1}
    /\ MGame.ss_PQ{2} = MRed.corr.`4{1}
    /\ MGame.ctStar{2} = MRed.ctStar{1}
    /\ MRed.corr{1}.`5 = MRed.corr{1}.`4
    ==> ={res} /\ ={glob K} /\ ={glob N} /\ ={glob H}
    /\ MGame.pq_keys.`1{2} = MRed.corr.`1{1}
    /\ MGame.pq_keys.`2{2} = MRed.corr.`2{1}
    /\ MGame.seed_T{2} = MRed.seed_T{1}
    /\ MGame.kem_ct{2} = MRed.corr.`3{1}
    /\ MGame.ss_PQ{2} = MRed.corr.`4{1}
    /\ MGame.ctStar{2} = MRed.ctStar{1}
    /\ MRed.corr{1}.`5 = MRed.corr{1}.`4.
proof.
proc.
if.
smt().
auto.
seq 5 5 : (#pre /\ ={ct_PQ, dss}).
wp; call (_: true); wp; call (_: true); wp; call (_: true); skip => /#.
if; 1: smt().
wp; call (_: true); wp; call (_: true); skip => /#.
wp; call (_: true); wp; call (_: true); wp; call (_: true); skip => /#.
qed.

end section.
