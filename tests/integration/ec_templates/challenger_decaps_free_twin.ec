(* ============================================================ *)
(* DECAPS-FREE CHALLENGER TWIN -- VALIDATED EC TEMPLATE           *)
(*   (regression tripwire). Admit-free, release EC exit 0.        *)
(*                                                               *)
(* Closes hops 0 / 15 of the CFRG `_PQ` cells -- the ESTABLISHING *)
(* side of the ordering rule, whose post carries the             *)
(* `corr.`5 = ev_decaps corr.`2 corr.`3` that all ten `decaps`   *)
(* hops CONSUME.                                                  *)
(*                                                               *)
(* THE PROBLEM. The correctness reduction delegates to a          *)
(* challenger whose `compute` runs an extra `K.decaps(dk, ct)`    *)
(* the game does not. Dropping that one-sided call at the hop     *)
(* hits the `exists*` FREEZE ON THE GLOB: `exists* (glob K){2}`   *)
(* captures the value at the procedure ENTRY, but `keygen` and    *)
(* `encaps` run before the decaps and have already changed it, so *)
(* the residual demands `(glob K){1} = <entry glob>`, which is    *)
(* false. Splitting the prefix off with `seq` first would need an *)
(* invariant relating the two sides' `inline *`-generated LOCALS  *)
(* -- circular, since that is the dependence the route exists to  *)
(* dissolve. Four attempts died there.                            *)
(*                                                               *)
(* THE ROUTE THAT WORKS -- the hop never sees the extra call:      *)
(*                                                               *)
(*  1. Emit a DECAPS-FREE TWIN of the challenger whose `compute`  *)
(*     returns `ev_decaps dk ct` in slot 5 instead of calling     *)
(*     `K.decaps`. The exporter renders the challenger already;   *)
(*     the twin is that module minus one statement.               *)
(*  2. Prove `chal_twin` INSIDE the challenger's own `proc`, where *)
(*     every local is a name the exporter itself rendered (no     *)
(*     inlining, so EC never renames them) and the `seq 6 6`      *)
(*     splits the prefix so `exists*` freezes at the RIGHT memory. *)
(*  3. At the hop, `transitivity` through the twin. Leg 2 is the  *)
(*     tail peel + `symmetry; call chal_twin`. LEG 1 IS THE       *)
(*     ORDINARY BUNDLED-DELEGATE REORDER -- the shape             *)
(*     `_synth_bundled_delegate_reorder` already emits, because   *)
(*     the twin has no extra call. That is the whole point: the   *)
(*     twin turns an unsolved shape into a solved one.            *)
(*                                                               *)
(* Note the `ev_` conjunct in the post is TRUE BY CONSTRUCTION on *)
(* the twin (its slot 5 IS `ev_decaps dk ct`), so `wp` + `skip => *)
(* /#` discharges it -- which means the reorder synthesizer's     *)
(* `ev_post` decline can be relaxed once it runs against a twin.  *)
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

module type CorrOracle = {
  proc compute() : EK * DK * CT * SS * SS
}.

(* The delegate the exporter renders -- `KEMCorrectnessWithDK_FromDecaps`. *)
module CorrFromDecaps (K : KEM) : CorrOracle = {
  proc compute() : EK * DK * CT * SS * SS = {
    var _tup : EK * DK;
    var ek : EK;
    var dk : DK;
    var _tup_0 : SS * CT;
    var ss : SS;
    var ct : CT;
    var ss_d : SS;
    _tup <@ K.keygen();
    ek <- _tup.`1;
    dk <- _tup.`2;
    _tup_0 <@ K.encaps(ek);
    ss <- _tup_0.`1;
    ct <- _tup_0.`2;
    ss_d <@ K.decaps(dk, ct);
    return (ek, dk, ct, ss, ss_d);
  }
}.


(* IDEA (a) from the parked characterization: a DECAPS-FREE TWIN of the
   challenger, which the exporter can emit as easily as the challenger itself.
   The hop then never sees the extra one-sided call -- so no `exists*`, and
   therefore no freeze on the glob. *)
module CorrNoDecaps (K : KEM) : CorrOracle = {
  proc compute() : EK * DK * CT * SS * SS = {
    var _tup : EK * DK;
    var ek : EK;
    var dk : DK;
    var _tup_0 : SS * CT;
    var ss : SS;
    var ct : CT;
    _tup <@ K.keygen();
    ek <- _tup.`1;
    dk <- _tup.`2;
    _tup_0 <@ K.encaps(ek);
    ss <- _tup_0.`1;
    ct <- _tup_0.`2;
    return (ek, dk, ct, ss, ev_decaps dk ct);
  }
}.

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

module MRed (K : KEM, N : NGT, Challenger : CorrOracle) = {
  var corr : EK * DK * CT * SS * SS
  var ctStar : CT
  proc initialize() : (EK * Elem) * CT = {
    var seed : Seed;
    var sc : Scalar;
    var g : Elem;
    var ekT : Elem;
    corr <@ Challenger.compute();
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

declare axiom K_decaps_pres (g : (glob K)) :
  phoare[ K.decaps : (glob K) = g ==> (glob K) = g ] = 1%r.

(* A hoare form of the determinism axiom: `call` in a hoare goal will not take
   a phoare spec ("invalid goal shape"), and `conseq` is the sanctioned
   weakening from `phoare ... = 1%r`. *)
lemma K_decaps_det_h (g : (glob K)) (a0 : DK) (a1 : CT) :
  hoare[ K.decaps : (glob K) = g /\ dk = a0 /\ ct = a1
         ==> (glob K) = g /\ res = ev_decaps a0 a1 ].
proof. conseq (K_decaps_det g a0 a1). qed.

(* STEP 2: the per-challenger derived spec. Its STATEMENT mentions only `res`;
   its PROOF names only the challenger's own rendered locals. *)
lemma CorrFromDecaps_compute_ev :
  hoare[ CorrFromDecaps(K).compute : true ==> res.`5 = ev_decaps res.`2 res.`3 ].
proof.
proc.
seq 6 : (true).
trivial.
exists* (glob K), dk, ct; elim* => g a0 a1.
call (K_decaps_det_h g a0 a1); skip => /#.
qed.

(* STEP 3: the hop. The 3-argument `conseq` pushes the `ev_` conjunct -- which
   mentions ONLY side 2's module globals -- into a one-sided HOARE goal, so the
   equiv goal is the plain bundled-delegate reorder plus a one-sided call the
   GLOB-ONLY `_pres` axiom drops (no `exists*` on a local, hence no freeze). *)
equiv chal_twin :
  CorrFromDecaps(K).compute ~ CorrNoDecaps(K).compute :
    ={glob K} ==> ={res} /\ ={glob K}.
proof.
proc.
seq 6 6 : (={glob K, ek, dk, ct, ss}).
+ sim.
exists* (glob K){1}, dk{1}, ct{1}; elim* => g a0 a1.
call{1} (K_decaps_det g a0 a1).
skip => /#.
qed.

equiv hop_0_initialize :
  MGame(K, N).initialize ~ MRed(K, N, CorrFromDecaps(K)).initialize :
    ={glob K} /\ ={glob N}
    ==> ={res} /\ ={glob K} /\ ={glob N}
        /\ MGame.ctStar{1} = MRed.ctStar{2}
        /\ MRed.corr{2}.`5 = ev_decaps (MRed.corr{2}.`2) (MRed.corr{2}.`3).
proof.
transitivity MRed(K, N, CorrNoDecaps(K)).initialize
  (={glob K, glob N} ==> ={res} /\ ={glob K, glob N}
     /\ MGame.ctStar{1} = MRed.ctStar{2}
     /\ MRed.corr{2}.`5 = ev_decaps (MRed.corr{2}.`2) (MRed.corr{2}.`3))
  (={glob K, glob N, glob MRed} ==> ={res} /\ ={glob K, glob N, glob MRed}).
+ smt().
+ smt().
+ proc.
  inline *.
  swap{1} [6..8] -4.
  wp; call (_: true).
  wp; call (_: true).
  wp; call (_: true).
  wp; rnd.
  wp; call (_: true).
  wp; call (_: true).
  wp; skip => /#.
proc.
wp; call (_: true); wp; call (_: true); wp; call (_: true); wp; rnd.
symmetry.
call chal_twin.
skip => /#.
qed.

end section.
