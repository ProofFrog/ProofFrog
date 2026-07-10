(* PK-shaped ev-ASSIGNMENT-twin blueprint: confirms the design that avoids the
   NG-calling-twin middle-leg smt wall. ek_T = exp(gen, rs s) is NG-derived and
   SHARED across ek0=(ep,ekT) and dk0=(dp,dt,ekT). Twins hold ev-ASSIGNMENTS
   (NG calls already functionalized), so the middle leg is a FLAT `sp. skip => /#`
   (no nested foralls); the outer legs functionalize the game/reduction NG calls
   top-down. Mirrors the CT cg_ng_init_twin_blueprint.ec. *)
require import AllCore Distr.
type ekp, dkp, scal, elt, seed.
op ev_rs  : seed -> scal.
op ev_gen : elt.
op ev_exp : elt -> scal -> elt.
op dseed  : seed distr.
axiom dseed_ll : is_lossless dseed.
module type KEMPQ = { proc keygen() : ekp * dkp }.
module type NGT = {
  proc rs (s : seed) : scal
  proc gen () : elt
  proc exp (b : elt, x : scal) : elt
}.
axiom NG_rs_det (NG <: NGT) (g : (glob NG)) (a0 : seed) :
  phoare[ NG.rs : (glob NG) = g /\ s = a0 ==> (glob NG) = g /\ res = ev_rs a0 ] = 1%r.
axiom NG_gen_det (NG <: NGT) (g : (glob NG)) :
  phoare[ NG.gen : (glob NG) = g ==> (glob NG) = g /\ res = ev_gen ] = 1%r.
axiom NG_exp_det (NG <: NGT) (g : (glob NG)) (b0 : elt) (x0 : scal) :
  phoare[ NG.exp : (glob NG) = g /\ b = b0 /\ x = x0 ==> (glob NG) = g /\ res = ev_exp b0 x0 ] = 1%r.

(* GAME: interleaved, real NG calls, packed ek0/dk0/ek1/dk1 fields. *)
module G (KP : KEMPQ, NG : NGT) = {
  var ek0 : ekp * elt
  var dk0 : dkp * scal * elt
  var ek1 : ekp * elt
  var dk1 : dkp * scal * elt
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var dp0, dp1 : dkp; var s0, s1 : seed;
    var dt0, dt1 : scal; var r0, r1, et0, et1 : elt;
    (ep0, dp0) <@ KP.keygen(); s0 <$ dseed; dt0 <@ NG.rs(s0); r0 <@ NG.gen(); et0 <@ NG.exp(r0, dt0);
    (ep1, dp1) <@ KP.keygen(); s1 <$ dseed; dt1 <@ NG.rs(s1); r1 <@ NG.gen(); et1 <@ NG.exp(r1, dt1);
    ek0 <- (ep0, et0); dk0 <- (dp0, dt0, et0); ek1 <- (ep1, et1); dk1 <- (dp1, dt1, et1);
  }
}.
(* FG twin: same interleaving, NG calls -> ev-assignments. *)
module FG (KP : KEMPQ, NG : NGT) = {
  var ek0 : ekp * elt
  var dk0 : dkp * scal * elt
  var ek1 : ekp * elt
  var dk1 : dkp * scal * elt
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var dp0, dp1 : dkp; var s0, s1 : seed;
    var dt0, dt1 : scal; var r0, r1, et0, et1 : elt;
    (ep0, dp0) <@ KP.keygen(); s0 <$ dseed; dt0 <- ev_rs s0; r0 <- ev_gen; et0 <- ev_exp r0 dt0;
    (ep1, dp1) <@ KP.keygen(); s1 <$ dseed; dt1 <- ev_rs s1; r1 <- ev_gen; et1 <- ev_exp r1 dt1;
    ek0 <- (ep0, et0); dk0 <- (dp0, dt0, et0); ek1 <- (ep1, et1); dk1 <- (dp1, dt1, et1);
  }
}.
(* REDUCTION: grouped, real NG calls, component fields. *)
module R (KP : KEMPQ, NG : NGT) = {
  var ek_PQ_0, ek_PQ_1 : ekp
  var dk_PQ_0, dk_PQ_1 : dkp
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elt
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var s0, s1 : seed; var r0, r1 : elt;
    (ep0, dk_PQ_0) <@ KP.keygen(); (ep1, dk_PQ_1) <@ KP.keygen();
    s0 <$ dseed; s1 <$ dseed;
    dk_T_0 <@ NG.rs(s0); r0 <@ NG.gen(); ek_T_0 <@ NG.exp(r0, dk_T_0);
    dk_T_1 <@ NG.rs(s1); r1 <@ NG.gen(); ek_T_1 <@ NG.exp(r1, dk_T_1);
    ek_PQ_0 <- ep0; ek_PQ_1 <- ep1;
  }
}.
(* FR twin: same grouping, NG calls -> ev-assignments. *)
module FR (KP : KEMPQ, NG : NGT) = {
  var ek_PQ_0, ek_PQ_1 : ekp
  var dk_PQ_0, dk_PQ_1 : dkp
  var dk_T_0, dk_T_1 : scal
  var ek_T_0, ek_T_1 : elt
  proc initialize() : unit = {
    var ep0, ep1 : ekp; var s0, s1 : seed; var r0, r1 : elt;
    (ep0, dk_PQ_0) <@ KP.keygen(); (ep1, dk_PQ_1) <@ KP.keygen();
    s0 <$ dseed; s1 <$ dseed;
    dk_T_0 <- ev_rs s0; r0 <- ev_gen; ek_T_0 <- ev_exp r0 dk_T_0;
    dk_T_1 <- ev_rs s1; r1 <- ev_gen; ek_T_1 <- ev_exp r1 dk_T_1;
    ek_PQ_0 <- ep0; ek_PQ_1 <- ep1;
  }
}.

lemma main (KP <: KEMPQ {-G, -FG, -R, -FR}) (NG <: NGT {-G, -FG, -R, -FR, -KP}) :
  equiv [ G(KP, NG).initialize ~ R(KP, NG).initialize :
     ={glob KP, glob NG} ==>
       ={glob KP, glob NG}
    /\ G.ek0{1} = (R.ek_PQ_0, R.ek_T_0){2}
    /\ G.dk0{1} = (R.dk_PQ_0, R.dk_T_0, R.ek_T_0){2}
    /\ G.ek1{1} = (R.ek_PQ_1, R.ek_T_1){2}
    /\ G.dk1{1} = (R.dk_PQ_1, R.dk_T_1, R.ek_T_1){2} ].
proof.
(* leg1: G ~ FG -- functionalize the game's NG calls top-down (program order). *)
transitivity FG(KP, NG).initialize
  (={glob KP, glob NG} ==> ={glob KP, glob NG} /\ ={ek0, dk0, ek1, dk1}(G, FG))
  (={glob KP, glob NG} ==> ={glob KP, glob NG}
     /\ FG.ek0{1} = (R.ek_PQ_0, R.ek_T_0){2} /\ FG.dk0{1} = (R.dk_PQ_0, R.dk_T_0, R.ek_T_0){2}
     /\ FG.ek1{1} = (R.ek_PQ_1, R.ek_T_1){2} /\ FG.dk1{1} = (R.dk_PQ_1, R.dk_T_1, R.ek_T_1){2}).
smt().
smt().
proc.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0}). + call (_: true); auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0}). + auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0}).
  wp. exists* (glob NG){1}, s0{1}; elim* => g a0. call{1} (NG_rs_det NG g a0). auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0}).
  wp. exists* (glob NG){1}; elim* => g. call{1} (NG_gen_det NG g). auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0}).
  wp. exists* (glob NG){1}, r0{1}, dt0{1}; elim* => g b0 x0. call{1} (NG_exp_det NG g b0 x0). auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0, ep1, dp1}). + call (_: true); auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0, ep1, dp1, s1}). + auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0, ep1, dp1, s1, dt1}).
  wp. exists* (glob NG){1}, s1{1}; elim* => g a0. call{1} (NG_rs_det NG g a0). auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0, ep1, dp1, s1, dt1, r1}).
  wp. exists* (glob NG){1}; elim* => g. call{1} (NG_gen_det NG g). auto.
  seq 1 1 : (={glob KP, glob NG, ep0, dp0, s0, dt0, r0, et0, ep1, dp1, s1, dt1, r1, et1}).
  wp. exists* (glob NG){1}, r1{1}, dt1{1}; elim* => g b0 x0. call{1} (NG_exp_det NG g b0 x0). auto.
  auto.
(* leg_mid: FG ~ FR -- both ev-assignment; swap-group + FLAT sp. skip => /#. *)
transitivity FR(KP, NG).initialize
  (={glob KP, glob NG} ==> ={glob KP, glob NG}
     /\ FG.ek0{1} = (FR.ek_PQ_0, FR.ek_T_0){2} /\ FG.dk0{1} = (FR.dk_PQ_0, FR.dk_T_0, FR.ek_T_0){2}
     /\ FG.ek1{1} = (FR.ek_PQ_1, FR.ek_T_1){2} /\ FG.dk1{1} = (FR.dk_PQ_1, FR.dk_T_1, FR.ek_T_1){2})
  (={glob KP, glob NG} ==> ={glob KP, glob NG}
     /\ (FR.ek_PQ_0, FR.ek_T_0){1} = (R.ek_PQ_0, R.ek_T_0){2}
     /\ (FR.dk_PQ_0, FR.dk_T_0, FR.ek_T_0){1} = (R.dk_PQ_0, R.dk_T_0, R.ek_T_0){2}
     /\ (FR.ek_PQ_1, FR.ek_T_1){1} = (R.ek_PQ_1, R.ek_T_1){2}
     /\ (FR.dk_PQ_1, FR.dk_T_1, FR.ek_T_1){1} = (R.dk_PQ_1, R.dk_T_1, R.ek_T_1){2}).
smt().
smt().
proc.
  swap{1} 6 -4.
  swap{1} 7 -3.
  seq 4 4 : (={glob KP, glob NG} /\ dp0{1} = FR.dk_PQ_0{2} /\ ep0{1} = ep0{2} /\ dp1{1} = FR.dk_PQ_1{2} /\ ep1{1} = ep1{2} /\ s0{1} = s0{2} /\ s1{1} = s1{2}).
  rnd. rnd. call (_: true). call (_: true). auto.
  sp. skip => /#.
(* leg3: FR ~ R -- functionalize the reduction's NG calls top-down. *)
proc.
seq 1 1 : (={glob KP, glob NG, ep0} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2}). + call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2}). + call (_: true); auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2}). + auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2}). + auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2}).
wp. exists* (glob NG){2}, s0{2}; elim* => g a0. call{2} (NG_rs_det NG g a0). auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2} /\ r0{1} = r0{2}).
wp. exists* (glob NG){2}; elim* => g. call{2} (NG_gen_det NG g). auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2} /\ r0{1} = r0{2} /\ FR.ek_T_0{1} = R.ek_T_0{2}).
wp. exists* (glob NG){2}, r0{2}, R.dk_T_0{2}; elim* => g b0 x0. call{2} (NG_exp_det NG g b0 x0). auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2} /\ FR.ek_T_0{1} = R.ek_T_0{2} /\ FR.dk_T_1{1} = R.dk_T_1{2}).
wp. exists* (glob NG){2}, s1{2}; elim* => g a0. call{2} (NG_rs_det NG g a0). auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2} /\ FR.ek_T_0{1} = R.ek_T_0{2} /\ FR.dk_T_1{1} = R.dk_T_1{2} /\ r1{1} = r1{2}).
wp. exists* (glob NG){2}; elim* => g. call{2} (NG_gen_det NG g). auto.
seq 1 1 : (={glob KP, glob NG, ep0, ep1, s0, s1} /\ FR.dk_PQ_0{1} = R.dk_PQ_0{2} /\ FR.dk_PQ_1{1} = R.dk_PQ_1{2} /\ FR.dk_T_0{1} = R.dk_T_0{2} /\ FR.ek_T_0{1} = R.ek_T_0{2} /\ FR.dk_T_1{1} = R.dk_T_1{2} /\ FR.ek_T_1{1} = R.ek_T_1{2}).
wp. exists* (glob NG){2}, r1{2}, R.dk_T_1{2}; elim* => g b0 x0. call{2} (NG_exp_det NG g b0 x0). auto.
auto.
qed.
