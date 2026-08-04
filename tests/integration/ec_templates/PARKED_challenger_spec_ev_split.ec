(* ============================================================ *)
(* PARKED PROBE -- the `ev_` post split, and the ONE step that    *)
(* still resists.  NOT a passing template: the final closer is    *)
(* left cut so the residual is readable.                          *)
(*                                                               *)
(* Target: hops 0 / 15 of the CFRG `_PQ` cells, the ESTABLISHING  *)
(* side of the ordering rule (their post carries the              *)
(* `corr.`5 = ev_decaps corr.`2 corr.`3` that all ten `decaps`    *)
(* hops consume).                                                 *)
(*                                                               *)
(* WHAT WORKS, both EC-validated here:                            *)
(*                                                               *)
(*  1. The 3-argument `conseq` splits the post: the `ev_`         *)
(*     conjunct mentions only side 2's module globals, so it      *)
(*     becomes a ONE-SIDED HOARE goal and leaves the equiv goal   *)
(*     as the plain bundled-delegate reorder.                      *)
(*  2. That hoare goal is discharged by a per-challenger DERIVED   *)
(*     spec whose STATEMENT mentions only `res`:                   *)
(*        hoare[ <Chal>(K).compute : true                          *)
(*               ==> res.`5 = ev_decaps res.`2 res.`3 ]            *)
(*     proved inside the challenger's OWN `proc`, where every      *)
(*     local is a name the exporter rendered -- no inlining, no    *)
(*     collision, no prediction.  `call` in a hoare goal will not  *)
(*     take a phoare spec ("invalid goal shape"), so the           *)
(*     determinism axiom is first weakened by `conseq` into        *)
(*     `K_decaps_det_h`.                                           *)
(*                                                                *)
(* WHAT RESISTS -- the one-sided drop of the reduction's extra     *)
(* `K.decaps` in the REMAINING equiv goal:                         *)
(*                                                                *)
(*   `exists* (glob K){2}; elim* => gk; call{2} (K_decaps_pres gk)` *)
(*   freezes `gk` at the JUDGMENT'S INITIAL memory, which is the   *)
(*   procedure ENTRY -- but `keygen` and `encaps` run before the   *)
(*   decaps and change `glob K`.  So the residual demands          *)
(*   `(glob K){1} = gk` for the ENTRY glob, which is false.  The   *)
(*   freeze trap again, on the GLOB this time rather than a local. *)
(*                                                                *)
(*   Fixing it needs the drop to happen AFTER a `seq` that splits  *)
(*   off the prefix -- and that `seq`'s invariant must relate the  *)
(*   two sides' `inline *`-generated LOCALS, which is exactly the  *)
(*   name-dependence this route was built to dissolve.  Circular   *)
(*   as it stands.                                                 *)
(*                                                                *)
(* NEXT IDEAS, in order of promise:                                *)
(*  a. give the whole one-sided `decaps` the same treatment as the *)
(*     `ev_` conjunct -- a per-challenger derived EQUIV spec       *)
(*     relating `<Chal>.compute` to a decaps-free twin module the  *)
(*     exporter also emits, so the hop never sees the extra call;  *)
(*  b. peel the head FORWARD (`seq 1 1` in program order, the      *)
(*     `_det_topdown_leg` shape) so the drop point's initial       *)
(*     memory is right by construction;                            *)
(*  c. state `_pres` relationally (an equiv of `K.decaps` against  *)
(*     `skip`) so no `exists*` is needed at all.                    *)
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
equiv hop_0_initialize :
  MGame(K, N).initialize ~ MRed(K, N, CorrFromDecaps(K)).initialize :
    ={glob K} /\ ={glob N}
    ==> ={res} /\ ={glob K} /\ ={glob N}
        /\ MGame.ctStar{1} = MRed.ctStar{2}
        /\ MRed.corr{2}.`5 = ev_decaps (MRed.corr{2}.`2) (MRed.corr{2}.`3).
proof.
conseq (: ={glob K} /\ ={glob N} ==> ={res} /\ ={glob K} /\ ={glob N} /\ MGame.ctStar{1} = MRed.ctStar{2}) (: true ==> true) (: true ==> MRed.corr.`5 = ev_decaps MRed.corr.`2 MRed.corr.`3).
smt().
trivial.
proc; wp; call (_: true); call (_: true); call (_: true); rnd; call (CorrFromDecaps_compute_ev); skip => /#.
proc; inline *.
swap{1} [6..8] -4.
wp; call (_: true); wp; call (_: true); wp; call (_: true); wp; rnd; wp.
exists* (glob K){2}; elim* => gk; call{2} (K_decaps_pres gk).
wp; call (_: true); wp; call (_: true); skip.

end section.
