(* ============================================================ *)
(* BUNDLED-DELEGATE vs EXPLICIT init reorder                      *)
(*   -- VALIDATED EC TEMPLATE (regression tripwire).               *)
(*                                                                *)
(* Mirrors `hop_10_initialize` of the CFRG `_PQ` IND-CCA cells:    *)
(*                                                                *)
(*   RE(.., KDFPRFSec_Real(H)).initialize                          *)
(* ~ RC(.., KEM_INDCCA_Random(KEM_PQ)).initialize                  *)
(*                                                                *)
(* One side runs a VOID delegate `Challenger.initialize()` and     *)
(* then does `keygen; <NG chain>; encaps` ITSELF; the other gets   *)
(* the whole PQ triple from ONE tuple-returning delegate           *)
(* (`keygen; encaps; ssStar <$`) and then runs both NG chains back *)
(* to back.  After `inline *` the two bodies are an exact          *)
(* PERMUTATION -- `encaps` sits either side of the first NG chain  *)
(* -- plus one DEAD one-sided sample on EACH side.                 *)
(*                                                                *)
(* THREE load-bearing facts, each measured (cycle 124):            *)
(*                                                                *)
(*  1. EC's `swap` DOES commute two ABSTRACT module calls, as long *)
(*     as the modules are mutually RESTRICTED.  The plan's premise *)
(*     that this needs the stateless-`Ideal` machinery was WRONG:  *)
(*     what EC actually rejects is `N` reading `glob K`, which     *)
(*     happens only when `N` is declared without `{-K}`.  The      *)
(*     exporter ALREADY emits that restriction chain               *)
(*     (`declare module NG <: NG_c.Scheme {-KEM_PQ, ...}`), so the *)
(*     plain `swap{1} [a..b] -d` is available here.                *)
(*                                                                *)
(*  2. The swap is computed against the POST-`inline *` bodies,    *)
(*     not the rendered pre-inline ones: the delegate contributes  *)
(*     SEVERAL statements, which is exactly the case the existing  *)
(*     `_synth_init_backbone_peel` declines (it aligns backbones   *)
(*     read off the flat states, where the delegate is one event). *)
(*                                                                *)
(*  3. A dead one-sided sample is dropped with `rnd{i}`, which     *)
(*     leaves an `is_lossless d` obligation for the closing `smt`. *)
(*     Both sides have one here (`k <$ dKey` on the left, the      *)
(*     challenger's `ssStar <$ dSS` on the right), and they are    *)
(*     dropped at DIFFERENT points of the backwards peel.          *)
(*                                                                *)
(* If this stops compiling, the bundled-delegate reorder route     *)
(* must be re-derived before the synthesizer that emits it can be  *)
(* trusted.                                                        *)
(* ============================================================ *)

require import AllCore Distr.

type EK, DK, CT, SS, Scalar, Elem, Seed, KdfOut, Key.

op dSeed : Seed distr.
op dKdfOut : KdfOut distr.
op dSS : SS distr.
op dKey : Key distr.

axiom dSeed_ll : is_lossless dSeed.
axiom dKdfOut_ll : is_lossless dKdfOut.
axiom dSS_ll : is_lossless dSS.
axiom dKey_ll : is_lossless dKey.

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

module type HT = {
  proc evaluate(x : Key) : KdfOut
}.

(* --- the two challengers, as the exporter renders them --- *)

module type KDFPRFSec_Oracle = {
  proc initialize() : unit
}.

module KDFPRFSec_Real (H : HT) : KDFPRFSec_Oracle = {
  var k : Key
  proc initialize() : unit = {
    k <$ dKey;
  }
}.

module type KEM_INDCCA_Oracle = {
  proc initialize() : EK * SS * CT
}.

module KEM_INDCCA_Random (K : KEM) : KEM_INDCCA_Oracle = {
  var dk : DK
  var ctStar : CT
  proc initialize() : EK * SS * CT = {
    var _tup : EK * DK;
    var ek : EK;
    var _tup_0 : SS * CT;
    var ss_unused : SS;
    var ssStar : SS;
    _tup <@ K.keygen();
    ek <- _tup.`1;
    dk <- _tup.`2;
    _tup_0 <@ K.encaps(ek);
    ss_unused <- _tup_0.`1;
    ctStar <- _tup_0.`2;
    ssStar <$ dSS;
    return (ek, ssStar, ctStar);
  }
}.

(* --- the two reductions --- *)

module RE (KEM_PQ : KEM, NG : NGT, H : HT, Challenger : KDFPRFSec_Oracle) = {
  var pq_keys : EK * DK
  var seed_T : Seed
  var kem_ct : CT
  var ctStar : CT * Elem
  proc initialize() : (EK * Elem) * KdfOut * (CT * Elem) = {
    var dk_T : Scalar;
    var _r0 : Elem;
    var ek_T : Elem;
    var ek_PQ : EK;
    var _tup : SS * CT;
    var ss_unused : SS;
    var seed_E : Seed;
    var sk_E : Scalar;
    var _r1 : Elem;
    var ct_T : Elem;
    var ss : KdfOut;
    Challenger.initialize();
    pq_keys <@ KEM_PQ.keygen();
    seed_T <$ dSeed;
    dk_T <@ NG.randomscalar(seed_T);
    _r0 <@ NG.generator();
    ek_T <@ NG.exp(_r0, dk_T);
    ek_PQ <- pq_keys.`1;
    _tup <@ KEM_PQ.encaps(ek_PQ);
    ss_unused <- _tup.`1;
    kem_ct <- _tup.`2;
    seed_E <$ dSeed;
    sk_E <@ NG.randomscalar(seed_E);
    _r1 <@ NG.generator();
    ct_T <@ NG.exp(_r1, sk_E);
    ss <$ dKdfOut;
    ctStar <- (kem_ct, ct_T);
    return ((ek_PQ, ek_T), ss, ctStar);
  }
}.

module RC (KEM_PQ : KEM, NG : NGT, H : HT, Challenger : KEM_INDCCA_Oracle) = {
  var ek_PQ : EK
  var seed_T : Seed
  var kem_ct : CT
  var ss_PQ : SS
  var ctStar : CT * Elem
  proc initialize() : (EK * Elem) * KdfOut * (CT * Elem) = {
    var _tup : EK * SS * CT;
    var dk_T : Scalar;
    var _r0 : Elem;
    var ek_T : Elem;
    var seed_E : Seed;
    var sk_E : Scalar;
    var _r1 : Elem;
    var ct_T : Elem;
    var ss : KdfOut;
    _tup <@ Challenger.initialize();
    ek_PQ <- _tup.`1;
    ss_PQ <- _tup.`2;
    kem_ct <- _tup.`3;
    seed_T <$ dSeed;
    dk_T <@ NG.randomscalar(seed_T);
    _r0 <@ NG.generator();
    ek_T <@ NG.exp(_r0, dk_T);
    seed_E <$ dSeed;
    sk_E <@ NG.randomscalar(seed_E);
    _r1 <@ NG.generator();
    ct_T <@ NG.exp(_r1, sk_E);
    ss <$ dKdfOut;
    ctStar <- (kem_ct, ct_T);
    return ((ek_PQ, ek_T), ss, ctStar);
  }
}.

section.
declare module KEM_PQ <: KEM {-RE, -RC, -KDFPRFSec_Real, -KEM_INDCCA_Random}.
declare module NG <: NGT {-KEM_PQ, -RE, -RC, -KDFPRFSec_Real, -KEM_INDCCA_Random}.
declare module H <: HT {-KEM_PQ, -NG, -RE, -RC, -KDFPRFSec_Real, -KEM_INDCCA_Random}.

equiv hop_10_initialize :
  RE(KEM_PQ, NG, H, KDFPRFSec_Real(H)).initialize ~
  RC(KEM_PQ, NG, H, KEM_INDCCA_Random(KEM_PQ)).initialize :
    ={glob KEM_PQ} /\ ={glob NG} /\ ={glob H}
    ==> ={res} /\ ={glob KEM_PQ} /\ ={glob NG} /\ ={glob H}
        /\ RC.seed_T{2} = RE.seed_T{1}
        /\ RC.kem_ct{2} = RE.kem_ct{1}
        /\ RC.ctStar{2} = RE.ctStar{1}
        /\ RC.kem_ct{2} = KEM_INDCCA_Random.ctStar{2}.
proof.
proc.
inline *.
swap{1} [7..10] -4.
wp; rnd; call (_: true); call (_: true); call (_: true); rnd; call (_: true); call (_: true); call (_: true); rnd.
wp.
rnd{2}.
wp; call (_: true); wp; call (_: true); rnd{1}; skip.
smt(dKey_ll dSS_ll).
qed.

(* VARIANT the synthesizer actually emits: the `swap` runs on the UN-INLINED
   body, so its positions can be read straight off the rendered module without
   modelling how many statements the delegate expands to.  Same peel. *)
equiv hop_10_initialize_swap_first :
  RE(KEM_PQ, NG, H, KDFPRFSec_Real(H)).initialize ~
  RC(KEM_PQ, NG, H, KEM_INDCCA_Random(KEM_PQ)).initialize :
    ={glob KEM_PQ} /\ ={glob NG} /\ ={glob H}
    ==> ={res} /\ ={glob KEM_PQ} /\ ={glob NG} /\ ={glob H}
        /\ RC.seed_T{2} = RE.seed_T{1}
        /\ RC.kem_ct{2} = RE.kem_ct{1}
        /\ RC.ctStar{2} = RE.ctStar{1}
        /\ RC.kem_ct{2} = KEM_INDCCA_Random.ctStar{2}.
proof.
proc.
swap{1} [7..10] -4.
inline *.
wp; rnd.
wp; call (_: true).
wp; call (_: true).
wp; call (_: true).
wp; rnd.
wp; call (_: true).
wp; call (_: true).
wp; call (_: true).
wp; rnd.
wp.
rnd{2}.
wp; call (_: true).
wp; call (_: true).
rnd{1}.
skip.
smt(dKey_ll dSS_ll).
qed.

end section.
