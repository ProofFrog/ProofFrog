(* ============================================================ *)
(* ONE-SIDED DETERMINISTIC CALL that ESTABLISHES an `ev_` fact    *)
(*   -- VALIDATED EC TEMPLATE (regression tripwire).              *)
(*                                                               *)
(* hop_0 / hop_15 of the CFRG `_PQ` IND-CCA cells: the            *)
(* correctness reduction's delegate runs an extra                 *)
(* `KEM_PQ.decaps(dk, ct)` the game does not, and the hop's post   *)
(* carries `corr.`5 = ev_decaps corr.`2 corr.`3`.  That conjunct   *)
(* is what EVERY `decaps` hop of the proof CONSUMES, so this is    *)
(* the establishing side of the ordering rule.                     *)
(*                                                               *)
(* Beyond the bundled-delegate reorder                             *)
(* (`bundled_delegate_encaps_reorder.ec`) this needs a one-sided    *)
(* DETERMINISTIC-call drop that also USES the determinism axiom.    *)
(* Three load-bearing facts:                                       *)
(*                                                               *)
(*  1. `exists*` freezes at the CURRENT judgment's initial memory,  *)
(*     so `exists* dk{2}, ct{2}` taken on the whole body captures   *)
(*     the UNINITIALIZED entry values.  The prefix must be split    *)
(*     off with `seq <a> <b>` first; only then does `exists*` see   *)
(*     the post-prefix values.                                     *)
(*  2. The one-sided call is the FIRST statement of the second      *)
(*     goal, and `call` works BACKWARDS, so it needs its own        *)
(*     `seq 0 1` to become the whole judgment.                     *)
(*  3. `call{2} (K_decaps_det g a0 a1)` then discharges it AND      *)
(*     leaves `ssd{2} = ev_decaps dk{2} ct{2}` in the invariant --  *)
(*     one step both drops the call and establishes the conjunct.   *)
(*                                                               *)
(* NOT YET EMITTABLE, and the obstacle is recorded rather than     *)
(* hidden: the two `seq` invariants name LOCALS (`ek`, `ct`,       *)
(* `ssd`, `dk`).  In the real hop those are `inline *`-generated,   *)
(* and EC appends collision suffixes the exporter cannot predict    *)
(* (the reduction and the challenger both declare `ss`).  The       *)
(* dissolution to try next is a per-challenger DERIVED spec whose   *)
(* statement mentions only `res`:                                   *)
(*                                                               *)
(*   lemma <Chal>_compute_ev :                                     *)
(*     phoare[ <Chal>(K).compute : true                            *)
(*             ==> res.`5 = ev_decaps res.`2 res.`3 ] = 1%r.       *)
(*                                                               *)
(* proved INSIDE the challenger's own `proc` (where every local is  *)
(* a name the exporter itself rendered, with no inlining and so no  *)
(* collision), and then used at the hop without unfolding the       *)
(* challenger at all.                                              *)
(* ============================================================ *)

require import AllCore Distr.

type EK, DK, CT, SS, Scalar, Elem, Seed.

op dSeed : Seed distr.
axiom dSeed_ll : is_lossless dSeed.

op ev_decaps : DK -> CT -> SS.

module type KEM = {
  proc keygen() : EK * DK
  proc encaps(ek : EK) : SS * CT
  proc decaps(dk : DK, ct : CT) : SS
}.

module type NGT = {
  proc randomscalar(s : Seed) : Scalar
  proc generator() : Elem
  proc exp(e : Elem, x : Scalar) : Elem
}.

(* GAME side: keygen; <NG chain>; encaps -- no decaps. *)
module MGame (K : KEM, N : NGT) = {
  var ctStar : CT
  proc initialize() : (EK * Elem) * CT = {
    var kp : EK * DK;
    var ek : EK;
    var seed : Seed;
    var sc : Scalar;
    var g : Elem;
    var ekT : Elem;
    var tup : SS * CT;
    kp <@ K.keygen();
    seed <$ dSeed;
    sc <@ N.randomscalar(seed);
    g <@ N.generator();
    ekT <@ N.exp(g, sc);
    ek <- kp.`1;
    tup <@ K.encaps(ek);
    ctStar <- tup.`2;
    return ((ek, ekT), ctStar);
  }
}.

(* REDUCTION side: the delegate bundled keygen; encaps; decaps up front. *)
module MRed (K : KEM, N : NGT) = {
  var corr : EK * DK * CT * SS * SS
  var ctStar : CT
  proc initialize() : (EK * Elem) * CT = {
    var kp : EK * DK;
    var ek : EK;
    var dk : DK;
    var tup : SS * CT;
    var ss : SS;
    var ct : CT;
    var ssd : SS;
    var seed : Seed;
    var sc : Scalar;
    var g : Elem;
    var ekT : Elem;
    kp <@ K.keygen();
    ek <- kp.`1;
    dk <- kp.`2;
    tup <@ K.encaps(ek);
    ss <- tup.`1;
    ct <- tup.`2;
    ssd <@ K.decaps(dk, ct);
    corr <- (ek, dk, ct, ss, ssd);
    seed <$ dSeed;
    sc <@ N.randomscalar(seed);
    g <@ N.generator();
    ekT <@ N.exp(g, sc);
    ctStar <- corr.`3;
    return ((corr.`1, ekT), ctStar);
  }
}.

section.
declare module K <: KEM {-MGame, -MRed}.
declare module N <: NGT {-K, -MGame, -MRed}.

declare axiom K_decaps_det (g : (glob K)) (a0 : DK) (a1 : CT) :
  phoare[ K.decaps : (glob K) = g /\ dk = a0 /\ ct = a1
          ==> (glob K) = g /\ res = ev_decaps a0 a1 ] = 1%r.

equiv hop_0_initialize :
  MGame(K, N).initialize ~ MRed(K, N).initialize :
    ={glob K} /\ ={glob N}
    ==> ={res} /\ ={glob K} /\ ={glob N}
        /\ MGame.ctStar{1} = MRed.ctStar{2}
        /\ MRed.corr{2}.`5 = ev_decaps (MRed.corr{2}.`2) (MRed.corr{2}.`3).
proof.
proc.
swap{1} [6..8] -4.
seq 4 6 : (={glob K, glob N} /\ ek{1} = ek{2} /\ MGame.ctStar{1} = ct{2}).
wp; call (_: true); wp; call (_: true); skip => /#.
seq 0 1 : (={glob K, glob N} /\ ek{1} = ek{2} /\ MGame.ctStar{1} = ct{2} /\ ssd{2} = ev_decaps dk{2} ct{2}).
exists* (glob K){2}, dk{2}, ct{2}; elim* => g a0 a1.
call{2} (K_decaps_det g a0 a1); skip => /#.
wp; call (_: true); wp; call (_: true); wp; call (_: true); wp; rnd; wp; skip => /#.
qed.

end section.
