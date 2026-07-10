(* ============================================================ *)
(* CFRG binding init -- STATEFUL functional-twin BLUEPRINT.       *)
(*                                                               *)
(* The synthesizer target for the CG NG-group hop_0/hop_4 init   *)
(* reorder (game interleaves per-index keygen+seed+NG; reduction  *)
(* groups them; the NG calls are glob-NG-shared / swap-immovable).*)
(* Because EC's inline* generates the in-place locals the seq-INV *)
(* would name (unpredictable), the name-INDEPENDENT route builds  *)
(* functional-twin modules whose var/field names WE control:      *)
(*   game G (interleaved, NG.f calls, fields dk0/dk1)             *)
(*     ~ reduction R (grouped, NG.f calls, decomposed dp/dt)      *)
(*   via FG (game-interleaved ev-assignment twin)                *)
(*   and  FR (reduction-grouped ev-assignment twin),             *)
(* 3-leg transitivity G ~ FG ~ FR ~ R.                           *)
(*                                                               *)
(* VALIDATED leg tactics (this file, ec_compile OK) = the exact   *)
(* shapes the synthesizer emits:                                 *)
(*  - OUTER leg (G~FG, FR~R): proc; per-backbone-stmt            *)
(*    `seq 1 1 : (<coupled + cross-module field eqs>)` top-down   *)
(*    (keygen: `call(_:true);auto`; sample: `auto`; det NG call:  *)
(*    `wp. exists* (glob NG){side},<seed>; call{side}(NG_f_det..);*)
(*    auto`); then `sp. skip => /#` for the packing field writes  *)
(*    -- `sp` (NOT wp) discharges cross-module global assigns.    *)
(*  - MIDDLE leg (FG~FR, both ev-assigns): `swap{1}` group the    *)
(*    interleaved side's keygens+samples; `seq K K :` split the   *)
(*    aligned prob prefix with a CROSS-module coupling+seed INV;  *)
(*    peel `rnd/rnd/call/call/auto`; `sp. skip => /#` the tail.   *)
(*  - Decomposition coupling threads through both `transitivity`  *)
(*    calls via their two `smt()` side-conditions (equality       *)
(*    transitivity on the packed tuple).                         *)
(*                                                               *)
(* Challenger seam (reduction delegates Breakable.Initialize)    *)
(* dropped here -- separately solved by the consume-pk machinery. *)
(* ============================================================ *)
require import AllCore Distr.
type ekp, dkp, scal, seed.
op ev_f : seed -> scal.
op dseed : seed distr.
axiom dseed_ll : is_lossless dseed.
module type KEMPQ = { proc keygen() : ekp * dkp }.
module type NGT = { proc f (s : seed) : scal }.
axiom NG_f_det (NG <: NGT) (g : (glob NG)) (a0 : seed) :
  phoare[ NG.f : (glob NG) = g /\ s = a0 ==> (glob NG) = g /\ res = ev_f a0 ] = 1%r.

module G (KP : KEMPQ, NG : NGT) = {
  var dk0 : dkp * scal
  var dk1 : dkp * scal
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var dp0, dp1 : dkp; var s0, s1 : seed; var dt0, dt1 : scal;
    (ep0, dp0) <@ KP.keygen(); s0 <$ dseed; dt0 <@ NG.f(s0);
    (ep1, dp1) <@ KP.keygen(); s1 <$ dseed; dt1 <@ NG.f(s1);
    dk0 <- (dp0, dt0); dk1 <- (dp1, dt1);
  }
}.
module FG (KP : KEMPQ, NG : NGT) = {
  var dk0 : dkp * scal
  var dk1 : dkp * scal
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var dp0, dp1 : dkp; var s0, s1 : seed; var dt0, dt1 : scal;
    (ep0, dp0) <@ KP.keygen(); s0 <$ dseed; dt0 <- ev_f s0;
    (ep1, dp1) <@ KP.keygen(); s1 <$ dseed; dt1 <- ev_f s1;
    dk0 <- (dp0, dt0); dk1 <- (dp1, dt1);
  }
}.
module R (KP : KEMPQ, NG : NGT) = {
  var dp0, dp1 : dkp
  var dt0, dt1 : scal
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var s0, s1 : seed;
    (ep0, dp0) <@ KP.keygen(); (ep1, dp1) <@ KP.keygen();
    s0 <$ dseed; s1 <$ dseed;
    dt0 <@ NG.f(s0); dt1 <@ NG.f(s1);
  }
}.
module FR (KP : KEMPQ, NG : NGT) = {
  var dp0, dp1 : dkp
  var dt0, dt1 : scal
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var s0, s1 : seed;
    (ep0, dp0) <@ KP.keygen(); (ep1, dp1) <@ KP.keygen();
    s0 <$ dseed; s1 <$ dseed;
    dt0 <- ev_f s0; dt1 <- ev_f s1;
  }
}.

lemma main (KP <: KEMPQ {-G, -FG, -R, -FR}) (NG <: NGT {-G, -FG, -R, -FR, -KP}) :
  equiv [ G(KP, NG).initialize ~ R(KP, NG).initialize :
     ={glob KP, glob NG} ==>
       ={glob KP, glob NG}
    /\ G.dk0{1} = (R.dp0, R.dt0){2}
    /\ G.dk1{1} = (R.dp1, R.dt1){2} ].
proof.
transitivity FG(KP, NG).initialize (={glob KP, glob NG} ==> ={glob KP, glob NG} /\ G.dk0{1} = FG.dk0{2} /\ G.dk1{1} = FG.dk1{2}) (={glob KP, glob NG} ==> ={glob KP, glob NG} /\ FG.dk0{1} = (R.dp0, R.dt0){2} /\ FG.dk1{1} = (R.dp1, R.dt1){2}).
smt().
smt().
proc.
seq 1 1 : (={glob KP, glob NG, ep0, dp0}).
call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0}).
auto.
seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0}).
wp. exists* (glob NG){1}, s0{1}; elim* => g0 a0. call{1} (NG_f_det NG g0 a0). auto.
seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, ep1, dp1}).
call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, ep1, dp1, s1}).
auto.
seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, ep1, dp1, s1, dt1}).
wp. exists* (glob NG){1}, s1{1}; elim* => g1 a1. call{1} (NG_f_det NG g1 a1). auto.
sp. skip => /#.
transitivity FR(KP, NG).initialize (={glob KP, glob NG} ==> ={glob KP, glob NG} /\ FG.dk0{1} = (FR.dp0, FR.dt0){2} /\ FG.dk1{1} = (FR.dp1, FR.dt1){2}) (={glob KP, glob NG} ==> ={glob KP, glob NG} /\ (FR.dp0, FR.dt0){1} = (R.dp0, R.dt0){2} /\ (FR.dp1, FR.dt1){1} = (R.dp1, R.dt1){2}).
smt().
smt().
proc.
swap{1} 4 -2.
swap{1} 5 -1.
seq 4 4 : (={glob KP, glob NG} /\ dp0{1} = FR.dp0{2} /\ dp1{1} = FR.dp1{2} /\ s0{1} = s0{2} /\ s1{1} = s1{2}).
rnd.
rnd.
call (_: true).
call (_: true).
auto.
sp.
skip => /#.
proc.
seq 1 1 : (={glob KP, glob NG, ep0} /\ FR.dp0{1} = R.dp0{2}).
call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1} /\ FR.dp0{1} = R.dp0{2} /\ FR.dp1{1} = R.dp1{2}).
call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0} /\ FR.dp0{1} = R.dp0{2} /\ FR.dp1{1} = R.dp1{2}).
auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dp0{1} = R.dp0{2} /\ FR.dp1{1} = R.dp1{2}).
auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dp0{1} = R.dp0{2} /\ FR.dp1{1} = R.dp1{2} /\ FR.dt0{1} = R.dt0{2}).
wp. exists* (glob NG){2}, s0{2}; elim* => g0 a0. call{2} (NG_f_det NG g0 a0). auto.
wp. exists* (glob NG){2}, s1{2}; elim* => g1 a1. call{2} (NG_f_det NG g1 a1). auto.
qed.
