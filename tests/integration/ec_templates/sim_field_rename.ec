(* Decisive test: does `proc; sim` relate a module to a STRUCTURALLY IDENTICAL
   twin whose FIELDS have different names, proving the cross-module field
   equality post?  If yes, the outer legs of the twin route can turn a raw
   wrapper (EC-inline names) into a known-name twin without naming its locals. *)
require import AllCore Distr.
type ekp, dkp, scal, seed.
op ev_f : seed -> scal.
op dseed : seed distr.
module type KEMPQ = { proc keygen() : ekp * dkp }.
module type NGT = { proc f (s : seed) : scal }.

(* "Raw" module: fields named dk0/dk1, some local names. *)
module Raw (KP : KEMPQ, NG : NGT) = {
  var dk0 : dkp * scal
  var dk1 : dkp * scal
  proc initialize() : unit = {
    var a0, a1 : ekp; var b0, b1 : dkp; var u0, u1 : seed; var w0, w1 : scal;
    (a0, b0) <@ KP.keygen(); u0 <$ dseed; w0 <@ NG.f(u0);
    (a1, b1) <@ KP.keygen(); u1 <$ dseed; w1 <@ NG.f(u1);
    dk0 <- (b0, w0); dk1 <- (b1, w1);
  }
}.
(* Twin: fields named tk0/tk1 (DIFFERENT), different local names, same body. *)
module Twin (KP : KEMPQ, NG : NGT) = {
  var tk0 : dkp * scal
  var tk1 : dkp * scal
  proc initialize() : unit = {
    var e0, e1 : ekp; var d0, d1 : dkp; var s0, s1 : seed; var v0, v1 : scal;
    (e0, d0) <@ KP.keygen(); s0 <$ dseed; v0 <@ NG.f(s0);
    (e1, d1) <@ KP.keygen(); s1 <$ dseed; v1 <@ NG.f(s1);
    tk0 <- (d0, v0); tk1 <- (d1, v1);
  }
}.

lemma raw_to_twin (KP <: KEMPQ {-Raw, -Twin}) (NG <: NGT {-Raw, -Twin, -KP}) :
  equiv [ Raw(KP, NG).initialize ~ Twin(KP, NG).initialize :
     ={glob KP, glob NG} ==>
       ={glob KP, glob NG} /\ Raw.dk0{1} = Twin.tk0{2} /\ Raw.dk1{1} = Twin.tk1{2} ].
proof.
proc.
sim.
qed.
