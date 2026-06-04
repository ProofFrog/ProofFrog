(* ============================================================ *)
(* Multi-oracle LIVE-STATE coupling when the post-init oracle    *)
(* CALLS an abstract stateless scheme -- VALIDATED EC TEMPLATE.   *)
(*                                                               *)
(* Extends multi_oracle_deadfield_coupling.ec to the realistic    *)
(* KEMPRF shape where the post-init `challenge` oracle invokes an  *)
(* abstract Scheme E (KEMPRF's challenge calls K.encaps /         *)
(* F.evaluate). The deadfield template's post-init oracle used    *)
(* only operators, so it never exercised an abstract call under   *)
(* the live-state coupling. This template pins the EXTRA          *)
(* load-bearing fact that case needs:                            *)
(*                                                               *)
(*  RESTRICTION. The abstract scheme module E must be RESTRICTED   *)
(*  from the state-holding modules named in the coupling          *)
(*  (`declare module E <: Scheme {-Chal, -GR}`). Without it EC     *)
(*  rejects the Pr lemma's `call (_: Chal.pk{1} = GR.pk{2})` with  *)
(*  "The module E can write GR.pk" -- because an unrestricted      *)
(*  abstract module is assumed to write every in-scope global,     *)
(*  including the live-state field. The adversary is likewise      *)
(*  restricted `{-Chal, -GR, -E}`.                                 *)
(*                                                               *)
(* The per-oracle equiv lemmas are admit here (the live-state      *)
(* coupling is not an `={}`-shaped invariant, so `sim` cannot      *)
(* infer it once an abstract call is present -- closing those      *)
(* bodies is a separate concern); this template's CLAIM is that    *)
(* the Pr-lemma STRUCTURE + the E/A restrictions typecheck and     *)
(* compose, which is what un-blocks the KEMPRF Pr lemmas.          *)
(* ============================================================ *)

require import AllCore Distr.

type pkey, skey, ss, ct, output.
op dkp : (pkey * skey) distr.
axiom dkp_ll : is_lossless dkp.
op drand : ss distr.
axiom drand_ll : is_lossless drand.
op g : ss -> output.

module type Scheme = {
  proc encaps(pk : pkey) : ss * ct
}.

module type Oracle = {
  proc init() : pkey
  proc challenge() : output * ct
}.

module type Adv (O : Oracle) = {
  proc distinguish(pk : pkey) : bool {O.challenge}
}.

(* Assumption challenger: holds pk + a DEAD sk; delegates encaps to E. *)
module Chal (E : Scheme) = {
  var pk : pkey
  var sk : skey
  proc cinit() : pkey = { var kp; kp <$ dkp; pk <- kp.`1; sk <- kp.`2; return pk; }
  proc cchallenge() : ss * ct = { var rsp; var r; rsp <@ E.encaps(pk); r <$ drand; return (r, rsp.`2); }
}.

(* Reduction endpoint: no own state, delegates to Chal(E). *)
module R (E : Scheme) : Oracle = {
  proc init() : pkey = { var pk; pk <@ Chal(E).cinit(); return pk; }
  proc challenge() : output * ct = {
    var rsp; rsp <@ Chal(E).cchallenge(); return (g rsp.`1, rsp.`2);
  }
}.

(* Intermediate-game endpoint: only pk; calls E directly. *)
module GR (E : Scheme) : Oracle = {
  var pk : pkey
  proc init() : pkey = { var kp; kp <$ dkp; pk <- kp.`1; return pk; }
  proc challenge() : output * ct = {
    var rsp; var r; rsp <@ E.encaps(pk); r <$ drand; return (g r, rsp.`2);
  }
}.

module Game (O : Oracle, A : Adv) = {
  proc main() : bool = {
    var b : bool;
    var pk : pkey;
    pk <@ O.init();
    b <@ A(O).distinguish(pk);
    return b;
  }
}.

section Test.
(* Load-bearing: restrict the abstract scheme from the state modules. *)
declare module E <: Scheme {-Chal, -GR}.

lemma hop_init :
  equiv [ R(E).init ~ GR(E).init : true ==> ={res} /\ Chal.pk{1} = GR.pk{2} ].
proof. admit. qed.

lemma hop_challenge :
  equiv [ R(E).challenge ~ GR(E).challenge :
    Chal.pk{1} = GR.pk{2} ==> ={res} /\ Chal.pk{1} = GR.pk{2} ].
proof. admit. qed.

lemma main_eq (A <: Adv {-Chal, -GR, -E}) &m :
  Pr[Game(R(E), A).main() @ &m : res] = Pr[Game(GR(E), A).main() @ &m : res].
proof.
byequiv (_: ={glob A} ==> ={res}) => //.
proc.
call (_: Chal.pk{1} = GR.pk{2}).
+ conseq hop_challenge.
call hop_init.
auto.
qed.

end section Test.
